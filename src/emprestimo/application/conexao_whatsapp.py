"""Casos de uso da conexão de WhatsApp do Credor (IMP-367, PLAN-034).

Três operações, e a distinção entre elas é o conteúdo real deste módulo:

- **inexistente** — nenhuma instância no provedor. Pede criar;
- **pendente** — instância existe, número não vinculado. Pede escanear um QR;
- **pareada** — número vinculado. Nada a fazer.

Colapsar as duas primeiras faria a tela oferecer a ação errada, e colapsar as
duas últimas faria anunciar sucesso com nenhum WhatsApp do outro lado: o
Evolution responde `Connected: true` com `LoggedIn: false` numa instância
recém-criada, verificado em 2026-08-31.

**O QR nunca entra na trilha.** Ele é o material que pareia um número; a
auditoria da ADR-002 é append-only, e o que entra lá não sai.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from emprestimo.application.errors import (
    ConexaoWhatsAppNaoEncontradaError,
    NomeInstanciaInvalidoError,
)
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.platform.conexao_whatsapp import ConexaoWhatsApp, EstadoPareamento
from emprestimo.domain.platform.ports import (
    EfeitoNaoAplicadoError,
    ProvedorWhatsApp,
    QrCodeIndisponivelError,
)

ENTIDADE_AUDITORIA = "conexao_whatsapp"

LIMITE_NOME_INSTANCIA = 100
"""Tamanho da coluna `instancia_nome` (IMP-365).

Validado ANTES de chamar o provedor: o Evolution aceita nomes que o nosso banco
recusa, e descobrir isso no `save` deixaria a instancia criada la fora sem
registro aqui.
"""


@dataclass(frozen=True)
class EstadoConexaoWhatsApp:
    """O que a Presentation precisa para decidir o que oferecer ao operador.

    `existe` separado de `pareada` porque as duas ausências pedem ações
    diferentes.

    `numero` é o telefone da conta pareada, extraído do `jid` de
    `/instance/info/:id` — que responde à autenticação de **Tenant**, e é por
    isso que o `/instance/status` nunca o mostrou. `nome_exibicao` é o push name
    (`"Barbosa"`), outra coisa: a tela mostra os dois, e rotulá-los trocados foi
    o que uma rodada de review pegou.

    `qrcode_base64` vem preenchido enquanto o pareamento está pendente, e é
    buscado a cada consulta — o QR vive ~20s e o provedor rotaciona sozinho, de
    modo que devolver o da chamada anterior seria devolver um QR morto. `None`
    significa "não há o que escanear": ou já pareou, ou o provedor ainda está
    gerando e a próxima consulta traz.
    """

    existe: bool
    pareada: bool
    conectado: bool
    instancia_nome: str | None
    nome_exibicao: str | None
    numero: str | None
    qrcode_base64: str | None


@dataclass(frozen=True)
class QrCodeConexao:
    """QR pronto para exibição, ou `None` enquanto o provedor ainda o gera.

    Tipo próprio em vez de `str` solta para que o valor não se confunda com
    nome, id ou token em nenhuma assinatura — e para que qualquer log acidental
    tenha de mencionar o nome deste campo.

    `None` **não é falha**: o contrato descreve a corrida — logo após conectar, o
    provedor responde "no QR code available, aguarde e tente de novo", até 5
    vezes. A tela já faz polling, então o pendente é um estado a devolver, não
    uma exceção a propagar.
    """

    qrcode_base64: str | None


def _validar_nome(instancia_nome: str) -> str:
    """Recusa aqui o que o banco recusaria depois do efeito externo."""
    limpo = instancia_nome.strip()
    if not limpo:
        raise NomeInstanciaInvalidoError("nome da instancia vazio")
    if len(limpo) > LIMITE_NOME_INSTANCIA:
        raise NomeInstanciaInvalidoError(
            f"nome da instancia com {len(limpo)} caracteres; o limite e {LIMITE_NOME_INSTANCIA}"
        )
    return limpo


def _autoria(usuario_id: uuid.UUID | None) -> dict[str, object]:
    """Base de `detalhes` de todo evento da trilha (IMP-361, ADR-002).

    Sem PII e sem segredo: o mesmo dicionário serve início, sucesso e falha.
    """
    return {"usuario_id": str(usuario_id) if usuario_id is not None else None}


def _detalhes(autoria: dict[str, object], **extras: object) -> str:
    return json.dumps({**autoria, **extras}, sort_keys=True)


def _sincronizar(
    uow: UnitOfWork,
    conexao: ConexaoWhatsApp,
    token: str,
    provedor: ProvedorWhatsApp,
) -> tuple[ConexaoWhatsApp, EstadoPareamento]:
    """Alinha o número guardado ao que o provedor reporta agora.

    O pareamento acontece **fora** daqui: o operador escaneia o QR no celular, e
    nenhuma requisição nossa observa esse instante. Por isso o número vem sempre
    de uma leitura do provedor, e nunca de inferência local.

    Devolve também o estado bruto do provedor: `conectado` e `pareado` são o
    agora, não fatos a guardar. Persistir qualquer um deles criaria um campo
    desatualizado desde o instante seguinte.
    """
    estado = provedor.estado(token, conexao.instancia_id)
    if estado.pareado and estado.numero:
        atualizada = conexao.parear(estado.numero)
    elif not estado.pareado:
        atualizada = conexao.desparear()
    else:
        # Pareado sem número: acontece com conta de privacidade total, onde o
        # WhatsApp entrega `@lid` e nenhum telefone. Preservar o que já se sabia
        # é melhor que apagar por uma resposta incompleta.
        return conexao, estado

    if atualizada.numero_pareado != conexao.numero_pareado:
        uow.conexao_whatsapp.save(atualizada)
        return atualizada, estado
    return conexao, estado


class ConsultarConexaoWhatsApp:
    """Lê o estado real, não o último estado conhecido."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        provedor: ProvedorWhatsApp,
    ) -> None:
        self._uow_factory = uow_factory
        self._provedor = provedor

    def executar(self, tenant_id: uuid.UUID) -> EstadoConexaoWhatsApp:
        with self._uow_factory() as uow:
            conexao = uow.conexao_whatsapp.find_by_tenant_id(tenant_id)
            if conexao is None:
                return EstadoConexaoWhatsApp(
                    existe=False,
                    pareada=False,
                    conectado=False,
                    instancia_nome=None,
                    nome_exibicao=None,
                    numero=None,
                    qrcode_base64=None,
                )
            token = uow.conexao_whatsapp.find_token(tenant_id)
            if token is None:
                # Conexão sem token é registro órfão: existe, e não pode falar
                # com o provedor. Nomear em vez de fingir que está desconectada.
                raise ConexaoWhatsAppNaoEncontradaError(tenant_id)

            atualizada, estado = _sincronizar(uow, conexao, token, self._provedor)
            uow.commit()

        # Fora da transação: buscar o QR é efeito externo, e nada aqui escreve.
        return EstadoConexaoWhatsApp(
            existe=True,
            # Direto do provedor: `LoggedIn` é a verdade do pareamento, e o que
            # guardamos localmente é consequência dele, não fonte.
            pareada=estado.pareado,
            conectado=estado.conectado,
            instancia_nome=atualizada.instancia_nome,
            nome_exibicao=estado.nome_exibicao,
            numero=atualizada.numero_pareado,
            qrcode_base64=None if estado.pareado else self._qrcode_pendente(token),
        )

    def _qrcode_pendente(self, token: str) -> str | None:
        """QR de agora, ou `None` enquanto o provedor ainda o gera.

        "Ainda gerando" é o estado normal logo após conectar, e a tela já faz
        polling — transformá-lo em erro faria a consulta falhar exatamente no
        momento em que ela é mais chamada.
        """
        try:
            return self._provedor.qrcode(token)
        except QrCodeIndisponivelError:
            return None


class ConectarWhatsApp:
    """Cria a instância se preciso, e devolve o QR para escanear.

    Criar e conectar num caso de uso só porque, do ponto de vista de quem opera,
    são um gesto: "quero ligar meu WhatsApp". Separá-los exporia ao operador uma
    etapa intermediária — instância criada e não conectada — que não corresponde
    a nada que ele queira fazer.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        provedor: ProvedorWhatsApp,
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._provedor = provedor
        self._auditoria = auditoria

    def _garantir_instancia(
        self,
        tenant_id: uuid.UUID,
        instancia_nome: str,
        autoria: dict[str, object],
    ) -> tuple[ConexaoWhatsApp, str]:
        """Devolve a conexao do Tenant, criando-a no provedor se preciso.

        Idempotente por construcao: `UNIQUE (tenant_id)` no banco e a consulta
        antes da criacao garantem uma instancia por Tenant, e repetir a chamada
        reaproveita em vez de criar outra. E por isso que este caso de uso nao
        registra `Idempotency-Key`: a chave replayaria o **QR** da primeira
        chamada, que expira em ~20s — devolver um QR morto e pior que gerar um
        novo. O que precisa ser idempotente aqui e o nascimento da instancia, e
        ele ja e.
        """
        with self._uow_factory() as uow:
            # Serializa antes de olhar: duas requisições sobrepostas passariam as
            # duas por uma consulta sem lock e criariam duas instâncias no
            # provedor. `UNIQUE (tenant_id)` só rejeitaria a segunda no commit,
            # quando o efeito externo já aconteceu.
            uow.conexao_whatsapp.bloquear_tenant(tenant_id)
            conexao = uow.conexao_whatsapp.find_by_tenant_id(tenant_id)
            if conexao is not None:
                token = uow.conexao_whatsapp.find_token(tenant_id)
                if token is None:
                    raise ConexaoWhatsAppNaoEncontradaError(tenant_id)
                return conexao, token

            # Antes do efeito externo: uma chave de cifra ausente descoberta no
            # `save` deixaria a instância criada no provedor e o token perdido.
            uow.conexao_whatsapp.exigir_disponibilidade()
            nome = _validar_nome(instancia_nome)
            # LIMITE CONHECIDO: se `/instance/create` for aceito e a resposta se
            # perder, a instancia fica no provedor sem registro local. Fechar
            # essa janela exige um estado "provisionando" persistido antes da
            # chamada — e a Entity exige `instancia_id`, que so existe depois
            # dela. E desenho, nao ajuste; fica nomeado para o IMP-368 decidir.
            instancia_id, token = self._provedor.criar_instancia(nome)
            conexao = ConexaoWhatsApp.criar(
                tenant_id=tenant_id,
                instancia_id=instancia_id,
                instancia_nome=nome,
            )
            try:
                uow.conexao_whatsapp.save(conexao, token=token)
                uow.commit()
            except Exception:
                # A instancia JA EXISTE no provedor, com um token que so esta
                # requisicao viu, e o banco vai voltar atras. Chamar isso de
                # `rollback_aplicado` afirmaria que nada sobrou — e sobrou uma
                # instancia orfa. E divergencia, mesma classificacao do
                # `desconectar`, e o `instancia_id` e o que permite acha-la.
                self._auditoria.registrar(
                    ENTIDADE_AUDITORIA,
                    None,
                    "conectar.divergencia",
                    "efeito_externo_aplicado_registro_local_incerto",
                    detalhes=_detalhes(autoria, instancia_id=instancia_id),
                )
                raise
            return conexao, token

    def executar(
        self,
        tenant_id: uuid.UUID,
        instancia_nome: str,
        usuario_id: uuid.UUID | None = None,
    ) -> QrCodeConexao:
        autoria = _autoria(usuario_id)
        self._auditoria.registrar(
            ENTIDADE_AUDITORIA,
            None,
            "conectar.inicio",
            "iniciado",
            detalhes=_detalhes(autoria),
        )
        try:
            # A transacao termina ANTES de pedir o QR, e isso nao e detalhe de
            # organizacao. `qrcode()` levanta `QrCodeAindaGerandoError` como
            # estado NORMAL logo apos o `connect` — o contrato manda esperar e
            # repetir. Se essa excecao atravessasse o UoW, o rollback apagaria a
            # conexao local enquanto a instancia ja existe no provedor, com um
            # token que so nos tinhamos: instancia orfa, inalcancavel, e uma nova
            # criada a cada tentativa.
            conexao, token = self._garantir_instancia(tenant_id, instancia_nome, autoria)
            self._provedor.conectar(token)
            try:
                qrcode: str | None = self._provedor.qrcode(token)
            except QrCodeIndisponivelError:
                # Estado normal, e o mais provavel: a instancia acabou de
                # conectar. Virar 5xx aqui faria o caminho feliz parecer falha.
                qrcode = None
        except Exception as exc:
            self._auditoria.registrar(
                ENTIDADE_AUDITORIA,
                None,
                "conectar.falha",
                "falhou",
                # Só o tipo: a mensagem do provedor pode carregar o token ou o
                # QR, e a trilha é append-only (IMP-361).
                detalhes=_detalhes(autoria, erro_tipo=type(exc).__name__),
            )
            raise

        self._auditoria.registrar(
            ENTIDADE_AUDITORIA,
            conexao.id,
            "conectar.sucesso",
            "sucesso",
            # `instancia_id` identifica; o QR não entra, nunca.
            detalhes=_detalhes(autoria, instancia_id=conexao.instancia_id),
        )
        return QrCodeConexao(qrcode_base64=qrcode)


class DesconectarWhatsApp:
    """Desvincula o número. A instância permanece.

    Apagar a instância obrigaria a recriá-la — e com ela um token novo — a cada
    desconexão. Reconectar deve custar um QR, não um ciclo de provisionamento.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        provedor: ProvedorWhatsApp,
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._provedor = provedor
        self._auditoria = auditoria

    def executar(
        self,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID | None = None,
    ) -> EstadoConexaoWhatsApp:
        autoria = _autoria(usuario_id)
        self._auditoria.registrar(
            ENTIDADE_AUDITORIA,
            None,
            "desconectar.inicio",
            "iniciado",
            detalhes=_detalhes(autoria),
        )
        desconectado_no_provedor: str | None = None
        try:
            with self._uow_factory() as uow:
                conexao = uow.conexao_whatsapp.find_by_tenant_id(tenant_id)
                token = uow.conexao_whatsapp.find_token(tenant_id)
                if conexao is None or token is None:
                    raise ConexaoWhatsAppNaoEncontradaError(tenant_id)

                # Marcado ANTES da chamada, e nao depois: um timeout ou reset
                # levanta sem provar que o `logout` nao foi aceito. E a mesma
                # regra da ADR-009 para envio — na duvida, assume-se que o
                # efeito externo aconteceu. Marcar depois faria justamente o
                # caso ambiguo cair em `rollback_aplicado`, que e a afirmacao
                # mais forte e a unica que nao se pode retirar.
                desconectado_no_provedor = conexao.instancia_id
                self._provedor.desconectar(token)
                despareada = conexao.desparear()
                uow.conexao_whatsapp.save(despareada)
                uow.commit()
        except Exception as exc:
            self._auditoria.registrar(
                ENTIDADE_AUDITORIA,
                None,
                "desconectar.falha",
                "falhou",
                detalhes=_detalhes(autoria, erro_tipo=type(exc).__name__),
            )
            if desconectado_no_provedor is not None and not isinstance(exc, EfeitoNaoAplicadoError):
                # O `logout` no provedor aconteceu, ou pode ter acontecido — e
                # nenhum rollback de banco o desfaz. O numero fica desvinculado
                # la enquanto o registro local volta a dizer "pareada". Chamar
                # isso de `rollback_aplicado` numa trilha append-only afirmaria
                # que o efeito foi revertido, para sempre. E divergencia, e quem
                # investigar precisa ler exatamente isso.
                #
                # `EfeitoNaoAplicadoError` e a excecao: o provedor recusou antes
                # de agir (401/403) ou a requisicao nem saiu da maquina. Ai ha
                # prova, e o rollback e verdadeiro.
                #
                # O status nao afirma que o registro local NAO existe: um
                # `commit` pode levantar depois de o servidor te-lo confirmado.
                # O que se sabe e o lado externo; o local fica declarado incerto,
                # que e o que a conciliacao precisa conferir.
                self._auditoria.registrar(
                    ENTIDADE_AUDITORIA,
                    None,
                    "desconectar.divergencia",
                    "efeito_externo_aplicado_registro_local_incerto",
                    detalhes=_detalhes(autoria, instancia_id=desconectado_no_provedor),
                )
            else:
                self._auditoria.registrar(
                    ENTIDADE_AUDITORIA,
                    None,
                    "desconectar.rollback",
                    "rollback_aplicado",
                    detalhes=_detalhes(autoria),
                )
            raise

        self._auditoria.registrar(
            ENTIDADE_AUDITORIA,
            despareada.id,
            "desconectar.sucesso",
            "sucesso",
            detalhes=_detalhes(autoria, instancia_id=despareada.instancia_id),
        )
        return EstadoConexaoWhatsApp(
            existe=True,
            pareada=False,
            conectado=False,
            instancia_nome=despareada.instancia_nome,
            nome_exibicao=None,
            numero=None,
            # Desconectar não gera QR: quem quiser reconectar chama `conectar`.
            qrcode_base64=None,
        )
