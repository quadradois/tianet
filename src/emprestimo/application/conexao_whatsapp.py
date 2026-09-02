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

from emprestimo.application.errors import ConexaoWhatsAppNaoEncontradaError
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.platform.conexao_whatsapp import ConexaoWhatsApp, EstadoPareamento
from emprestimo.domain.platform.ports import ProvedorWhatsApp, QrCodeIndisponivelError

ENTIDADE_AUDITORIA = "conexao_whatsapp"


@dataclass(frozen=True)
class EstadoConexaoWhatsApp:
    """O que a Presentation precisa para decidir o que oferecer ao operador.

    `existe` separado de `pareada` porque as duas ausências pedem ações
    diferentes.

    `nome_exibicao` é o push name da conta pareada, e **não o telefone**: o
    `/instance/status` não devolve número nenhum. A tela do IMP-369 precisa
    saber disso antes de rotular o campo.

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
    qrcode_base64: str | None


@dataclass(frozen=True)
class QrCodeConexao:
    """QR pronto para exibição, em base64.

    Tipo próprio em vez de `str` solta para que o valor não se confunda com
    nome, id ou token em nenhuma assinatura — e para que qualquer log acidental
    tenha de mencionar o nome deste campo.
    """

    qrcode_base64: str


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
    estado = provedor.estado(token)
    if estado.pareado and estado.nome_exibicao:
        atualizada = conexao.parear(estado.nome_exibicao)
    elif not estado.pareado:
        atualizada = conexao.desparear()
    else:
        # Pareado sem identificação: o provedor confirmou vínculo mas não disse
        # com quem. Preservar o que já se sabia é melhor que apagar por uma
        # resposta incompleta.
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
            nome_exibicao=atualizada.numero_pareado,
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
            instancia_id, token = self._provedor.criar_instancia(instancia_nome)
            conexao = ConexaoWhatsApp.criar(
                tenant_id=tenant_id,
                instancia_id=instancia_id,
                instancia_nome=instancia_nome,
            )
            uow.conexao_whatsapp.save(conexao, token=token)
            uow.commit()
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
            conexao, token = self._garantir_instancia(tenant_id, instancia_nome)
            self._provedor.conectar(token)
            qrcode = self._provedor.qrcode(token)
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
        try:
            with self._uow_factory() as uow:
                conexao = uow.conexao_whatsapp.find_by_tenant_id(tenant_id)
                token = uow.conexao_whatsapp.find_token(tenant_id)
                if conexao is None or token is None:
                    raise ConexaoWhatsAppNaoEncontradaError(tenant_id)

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
            # Desconectar não gera QR: quem quiser reconectar chama `conectar`.
            qrcode_base64=None,
        )
