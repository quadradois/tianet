"""Casos de uso da conexão de WhatsApp do Credor (IMP-367/IMP-368, PLAN-034).

Três estados, e a distinção entre eles é o conteúdo real deste módulo:

- **inexistente** — nenhuma instância no provedor. Pede criar;
- **pendente** — instância existe, número não vinculado. Pede escanear um QR;
- **pareada** — número vinculado. Nada a fazer.

Colapsar as duas primeiras faria a tela oferecer a ação errada, e colapsar as
duas últimas faria anunciar sucesso com nenhum WhatsApp do outro lado: o
Evolution responde `Connected: true` com `LoggedIn: false` numa instância
recém-criada, verificado em 2026-08-31.

**O QR nunca entra na trilha.** Ele é o material que pareia um número; a
auditoria da ADR-002 é append-only, e o que entra lá não sai.

**Desconectar e excluir não são a mesma coisa** (IMP-368). O logout desvincula
o número e a instância continua lá, pronta para outro QR. Excluir apaga a
instância no provedor. Sem a segunda, cada instância abandonada fica no
Evolution para sempre — nome, token e sessão que ninguém usa — e o provedor
enche de conexão morta.
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

    **O QR não vive aqui, e a razão é de permissão.** Ele é credencial de
    pareamento: quem o escaneia vincula uma conta de WhatsApp ao Tenant. Devolvê-lo
    na consulta — protegida por `whatsapp.conexao.ler` — daria a um usuário
    somente-leitura o poder de *alterar* a conexão, contornando
    `whatsapp.conexao.gerir`. O QR sai por `ConectarWhatsApp`, e só por lá.
    """

    existe: bool
    pareada: bool
    conectado: bool
    instancia_nome: str | None
    nome_exibicao: str | None
    numero: str | None


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


@dataclass
class _FaseEfeito:
    """Marca se algum efeito **mutante** no provedor ja foi tentado.

    Existe para separar duas afirmacoes que a trilha append-only nao pode
    confundir: `rollback_aplicado` diz "nada sobrou la fora", e so e verdade
    quando nenhuma chamada que muda estado saiu. Antes disto o rollback era
    emitido apenas para `EfeitoNaoAplicadoError` — de modo que uma cifra ausente,
    que estoura ANTES de qualquer chamada, produzia so `conectar.falha` e deixava
    quem investiga sem saber se havia instancia orfa. Havia nao: nao houve
    chamada.

    Leitura NAO marca. `instancia_existente` e um GET: falhar nele nao muda nada
    no provedor, e tratar como efeito perderia justamente o caso mais comum de
    rollback legitimo.
    """

    tentado: bool = False


PREFIXO_NOME_INSTANCIA = "tianet_"


def nome_da_instancia(tenant_id: uuid.UUID) -> str:
    """O nome da instância deste Tenant. **Derivado, nunca digitado** (IMP-368).

    Três coisas dependem disto, e nenhuma sobrevive a um nome que alguém teclou:

    1. a adoção de `instancia_existente` casa **pelo nome**. Um caractere
       diferente e ela não acha nada, o `create` roda, e nasce uma segunda
       instância — não pareada — enquanto o WhatsApp do operador segue ligado
       na primeira;
    2. a recuperação do `create` cuja resposta se perdeu tem o nome como única
       pista, e ela precisa ser reconstruível sem consultar ninguém;
    3. um campo digitável transforma erro de digitação em instância nova e
       silenciosa no provedor.

    Determinístico a partir do `tenant_id`: a mesma entrada devolve o mesmo
    nome em qualquer máquina, em qualquer momento, sem estado guardado.
    """
    return f"{PREFIXO_NOME_INSTANCIA}{tenant_id}"


def _validar_nome(instancia_nome: str) -> str:
    """Recusa aqui o que o banco recusaria depois do efeito externo.

    O nome é gerado (`nome_da_instancia`) e hoje cabe folgado nos 100
    caracteres da coluna. A guarda fica porque quem mudar o formato descobre o
    estouro aqui, antes do provedor — e não no `save`, com a instância já
    criada lá fora e o token perdido.
    """
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
) -> tuple[ConexaoWhatsApp, EstadoPareamento, bool]:
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
        return conexao, estado, False

    if atualizada.numero_pareado != conexao.numero_pareado:
        uow.conexao_whatsapp.save(atualizada)
        return atualizada, estado, True
    return conexao, estado, False


class ConsultarConexaoWhatsApp:
    """Lê o estado real, não o último estado conhecido."""

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
        with self._uow_factory() as uow:
            # Lock ANTES da leitura. Adquiri-lo depois nao serializa nada: a
            # segunda requisicao esperaria, e entao compararia contra o objeto
            # que carregou antes do lock — velho — e repetiria a escrita.
            uow.conexao_whatsapp.bloquear_tenant(tenant_id)
            conexao = uow.conexao_whatsapp.find_by_tenant_id(tenant_id)
            if conexao is None:
                return EstadoConexaoWhatsApp(
                    existe=False,
                    pareada=False,
                    conectado=False,
                    instancia_nome=None,
                    nome_exibicao=None,
                    numero=None,
                )
            token = uow.conexao_whatsapp.find_token(tenant_id)
            if token is None:
                # Conexão sem token é registro órfão: existe, e não pode falar
                # com o provedor. Nomear em vez de fingir que está desconectada.
                raise ConexaoWhatsAppNaoEncontradaError(tenant_id)

            atualizada, estado, mudou = _sincronizar(uow, conexao, token, self._provedor)
            uow.commit()

        # Depois do commit, e não dentro dele: a auditoria vive em sessão
        # independente (ADR-002) e não volta atrás. Registrar antes afirmaria
        # uma transição que o rollback desfaria — permanentemente.
        #
        # LIMITE CONHECIDO: o commit solta o advisory lock antes desta escrita,
        # então dois pollings simultâneos podem gravar seus eventos fora da
        # ordem em que commitaram. Serializar até aqui exigiria manter o lock
        # sobre uma sessão que já fechou. O sistema é single-tenant com um
        # operador (ADR-003) e o polling vem de uma aba — a ordem só se embaralha
        # com requisições concorrentes do mesmo usuário, e o `instancia_id` de
        # cada evento continua correlacionando corretamente.
        if mudou:
            self._auditoria.registrar(
                ENTIDADE_AUDITORIA,
                atualizada.id,
                "sincronizar.pareamento" if atualizada.pareada else "sincronizar.desparelhamento",
                "sucesso",
                # Sem o telefone: a trilha é append-only, e `instancia_id` já
                # correlaciona.
                detalhes=_detalhes(autoria, instancia_id=atualizada.instancia_id),
            )

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
        )


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
        autoria: dict[str, object],
        efeito: _FaseEfeito,
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
            nome = _validar_nome(nome_da_instancia(tenant_id))
            # Tabela local vazia NAO significa provedor vazio: o `create` pode
            # ter criado a instancia e a resposta ter se perdido antes de
            # chegarmos a gravar o `instancia_id`. Nessa janela o nome e a
            # unica pista, e por isso ele e derivado do Tenant — a proxima
            # tentativa reconstroi o mesmo nome e adota em vez de criar outra
            # orfa.
            existente = self._provedor.instancia_existente(nome)
            if existente is not None:
                instancia_id, token = existente
                adotada = ConexaoWhatsApp.criar(
                    tenant_id=tenant_id,
                    instancia_id=instancia_id,
                    instancia_nome=nome,
                )
                uow.conexao_whatsapp.save(adotada, token=token)
                uow.commit()
                self._auditoria.registrar(
                    ENTIDADE_AUDITORIA,
                    adotada.id,
                    "conectar.adocao",
                    "sucesso",
                    detalhes=_detalhes(autoria, instancia_id=instancia_id),
                )
                return adotada, token

            # A PARTIR DAQUI pode sobrar estado no provedor.
            efeito.tentado = True
            try:
                instancia_id, token = self._provedor.criar_instancia(nome)
            except EfeitoNaoAplicadoError:
                # Prova de nao criacao: nao ha orfa, nao ha o que conciliar.
                raise
            except Exception:
                # Timeout de leitura, reset, 5xx ou 2xx malformado: o provedor
                # pode ter criado a instancia e a resposta se perdido. Sem
                # `instancia_id`, o nome e a unica pista — e e o que a adoção da
                # proxima tentativa vai usar para achá-la.
                self._auditoria.registrar(
                    ENTIDADE_AUDITORIA,
                    None,
                    "conectar.divergencia",
                    "externo_aplicado_local_incerto",
                    detalhes=_detalhes(autoria, instancia_nome=nome),
                )
                raise
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
                    "externo_aplicado_local_incerto",
                    detalhes=_detalhes(autoria, instancia_id=instancia_id),
                )
                raise
            return conexao, token

    def executar(
        self,
        tenant_id: uuid.UUID,
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
        efeito = _FaseEfeito()
        try:
            # A transacao termina ANTES de pedir o QR, e isso nao e detalhe de
            # organizacao. `qrcode()` levanta `QrCodeAindaGerandoError` como
            # estado NORMAL logo apos o `connect` — o contrato manda esperar e
            # repetir. Se essa excecao atravessasse o UoW, o rollback apagaria a
            # conexao local enquanto a instancia ja existe no provedor, com um
            # token que so nos tinhamos: instancia orfa, inalcancavel, e uma nova
            # criada a cada tentativa.
            conexao, token = self._garantir_instancia(tenant_id, autoria, efeito)
            efeito.tentado = True
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
            if isinstance(exc, EfeitoNaoAplicadoError) or not efeito.tentado:
                # Duas provas distintas de que nada sobrou lá fora, e as duas
                # valem: `EfeitoNaoAplicadoError` é o provedor afirmando que não
                # agiu; `not efeito.tentado` é não termos chegado a pedir.
                #
                # A segunda foi acrescentada porque o comentário anterior
                # prometia o que o código não fazia: dizia "cifra ausente" — mas
                # `CifraIndisponivelError` não é `EfeitoNaoAplicadoError`, então
                # a falha mais precoce que existe, anterior a qualquer chamada,
                # era a única a NÃO registrar rollback. Quem investigasse via
                # `conectar.falha` sozinho e teria de sair procurando instância
                # órfã que nunca existiu.
                self._auditoria.registrar(
                    ENTIDADE_AUDITORIA,
                    None,
                    "conectar.rollback",
                    "rollback_aplicado",
                    detalhes=_detalhes(autoria),
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

    Quem quer a instância fora do provedor pede `ExcluirConexaoWhatsApp`, que é
    outra intenção: aqui o operador troca de número, lá ele encerra a conexão.
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
                # Mesmo lock dos outros dois: sem ele, um polling em voo pode
                # gravar "pareada" depois de o logout ter acontecido — e a
                # trilha ficaria com um pareamento posterior a desconexao.
                uow.conexao_whatsapp.bloquear_tenant(tenant_id)
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
                    "externo_aplicado_local_incerto",
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
        )


class ExcluirConexaoWhatsApp:
    """Apaga a instância no provedor e o registro local (IMP-368).

    Existe porque o logout sozinho **acumula**: cada instância abandonada segue
    no Evolution com nome, token e sessão que ninguém usa, e nada no sistema a
    remove. Com o tempo o provedor enche de conexão morta, e descobrir qual
    delas é a viva vira trabalho manual.

    Ordem dos efeitos, e ela não é arbitrária: apaga **primeiro lá fora**, e só
    então localmente. O inverso deixaria a instância órfã no provedor sem nada
    apontando para ela — nem o `instancia_id`, que é o que permite achá-la.
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
            "excluir.inicio",
            "iniciado",
            detalhes=_detalhes(autoria),
        )
        excluido_no_provedor: str | None = None
        try:
            with self._uow_factory() as uow:
                # Mesmo lock dos outros: sem ele um polling em voo grava
                # "pareada" depois da exclusao, e a trilha fica com um
                # pareamento posterior ao fim da conexao.
                uow.conexao_whatsapp.bloquear_tenant(tenant_id)
                conexao = uow.conexao_whatsapp.find_by_tenant_id(tenant_id)
                if conexao is None:
                    raise ConexaoWhatsAppNaoEncontradaError(tenant_id)

                # O token NAO e lido aqui, e isso e proposital: `/instance/delete`
                # autentica por Tenant. Exigir o token faria a limpeza depender
                # justamente do que pode estar perdido — conexao com cifra
                # ilegivel ou token ausente e exatamente a que mais precisa ser
                # removida, e ela ficaria presa para sempre.
                #
                # Marcado ANTES da chamada, pela regra da ADR-009: timeout ou
                # reset levantam sem provar que o provedor nao apagou. Marcar
                # depois faria o caso ambiguo cair em `rollback_aplicado` — a
                # afirmacao mais forte, e a unica que nao se retira.
                excluido_no_provedor = conexao.instancia_id
                self._provedor.excluir_instancia(conexao.instancia_id)
                uow.conexao_whatsapp.delete(tenant_id)
                uow.commit()
        except Exception as exc:
            self._auditoria.registrar(
                ENTIDADE_AUDITORIA,
                None,
                "excluir.falha",
                "falhou",
                detalhes=_detalhes(autoria, erro_tipo=type(exc).__name__),
            )
            if excluido_no_provedor is not None and not isinstance(exc, EfeitoNaoAplicadoError):
                # A instancia foi apagada la fora, ou pode ter sido — e nenhum
                # rollback de banco a traz de volta. O registro local
                # sobrevive apontando para uma instancia que talvez nao exista
                # mais. Chamar isso de `rollback_aplicado` numa trilha
                # append-only afirmaria, para sempre, que nada sobrou.
                self._auditoria.registrar(
                    ENTIDADE_AUDITORIA,
                    None,
                    "excluir.divergencia",
                    "externo_aplicado_local_incerto",
                    detalhes=_detalhes(autoria, instancia_id=excluido_no_provedor),
                )
            else:
                self._auditoria.registrar(
                    ENTIDADE_AUDITORIA,
                    None,
                    "excluir.rollback",
                    "rollback_aplicado",
                    detalhes=_detalhes(autoria),
                )
            raise

        self._auditoria.registrar(
            ENTIDADE_AUDITORIA,
            conexao.id,
            "excluir.sucesso",
            "sucesso",
            detalhes=_detalhes(autoria, instancia_id=excluido_no_provedor),
        )
        # O mesmo formato do "nao existe" da consulta, e nao um corpo proprio: a
        # tela acabou de voltar ao ponto de partida, e ler dois formatos para o
        # mesmo estado e como ela erra.
        return EstadoConexaoWhatsApp(
            existe=False,
            pareada=False,
            conectado=False,
            instancia_nome=None,
            nome_exibicao=None,
            numero=None,
        )
