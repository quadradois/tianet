"""Erros da camada de Aplicação (TASK-043).

Conflitos de idempotência são erros de uso do serviço (AD-002): herdam de
``DomainError`` para que a API os traduza como 409, no mesmo caminho da
violação de unicidade.
"""

from __future__ import annotations

import uuid

from emprestimo.domain.common.errors import DomainError


class IdempotenciaConflitoError(DomainError):
    """A Idempotency-Key já foi utilizada com resultado diferente (AD-002).

    Levantada quando a mesma chave é reenviada com payload divergente
    (``solicitacao_hash`` diferente) ou enquanto um provisionamento com a
    mesma chave ainda está em andamento.
    """

    def __init__(self, idempotency_key: str, motivo: str) -> None:
        super().__init__(f"Conflito de Idempotency-Key {idempotency_key!r}: {motivo}")
        self.idempotency_key = idempotency_key
        self.motivo = motivo


class DevedorNaoEncontradoError(DomainError):
    """Devedor não encontrado na base (IMP-054).

    Levantada quando uma operação de atualização, estado ou consulta por ID
    não localiza o Devedor correspondente.
    """

    def __init__(self, devedor_id: uuid.UUID) -> None:
        super().__init__(f"Devedor não encontrado: {devedor_id}")
        self.devedor_id = devedor_id


class CarteiraNaoEncontradaError(DomainError):
    """Carteira nao encontrada ou fora do Tenant visivel."""

    def __init__(self, carteira_id: uuid.UUID) -> None:
        super().__init__(f"Carteira nao encontrada: {carteira_id}")
        self.carteira_id = carteira_id


class UsuarioNaoEncontradoError(DomainError):
    """Usuario nao encontrado ou fora do Tenant visivel (IMP-087)."""

    def __init__(self, usuario_id: uuid.UUID) -> None:
        super().__init__(f"Usuario nao encontrado: {usuario_id}")
        self.usuario_id = usuario_id


class CredencialInvalidaError(DomainError):
    """Credencial recusada sem revelar se usuario/credencial existem (IMP-087)."""

    def __init__(self) -> None:
        super().__init__("Credencial invalida")


class SimulacaoComercialNaoEncontradaError(DomainError):
    """Simulacao Comercial nao encontrada ou fora da fronteira informada."""

    def __init__(self, simulacao_id: uuid.UUID) -> None:
        super().__init__(f"Simulacao Comercial nao encontrada: {simulacao_id}")
        self.simulacao_id = simulacao_id


class PropostaComercialNaoEncontradaError(DomainError):
    """Proposta Comercial nao encontrada ou fora da fronteira informada."""

    def __init__(self, proposta_id: uuid.UUID) -> None:
        super().__init__(f"Proposta Comercial nao encontrada: {proposta_id}")
        self.proposta_id = proposta_id


class ContratoCreditoNaoEncontradoError(DomainError):
    """Contrato de Credito nao encontrado ou fora da fronteira informada."""

    def __init__(self, contrato_id: uuid.UUID) -> None:
        super().__init__(f"Contrato de Credito nao encontrado: {contrato_id}")
        self.contrato_id = contrato_id


class EmprestimoNaoEncontradoError(DomainError):
    """Emprestimo nao encontrado ou fora da fronteira informada."""

    def __init__(self, emprestimo_id: uuid.UUID) -> None:
        super().__init__(f"Emprestimo nao encontrado: {emprestimo_id}")
        self.emprestimo_id = emprestimo_id


class CobrancaCasoNaoEncontradoError(DomainError):
    """Caso de cobranca nao encontrado ou fora da fronteira informada."""

    def __init__(self, caso_id: uuid.UUID) -> None:
        super().__init__(f"Caso de cobranca nao encontrado: {caso_id}")
        self.caso_id = caso_id


class PromessaPagamentoNaoEncontradaError(DomainError):
    """Promessa de pagamento nao encontrada ou fora da fronteira informada."""

    def __init__(self, promessa_id: uuid.UUID) -> None:
        super().__init__(f"Promessa de pagamento nao encontrada: {promessa_id}")
        self.promessa_id = promessa_id


class PagamentoNaoEncontradoError(DomainError):
    """Pagamento oficial nao encontrado ou fora da fronteira informada."""

    def __init__(self, pagamento_id: uuid.UUID) -> None:
        super().__init__(f"Pagamento nao encontrado: {pagamento_id}")
        self.pagamento_id = pagamento_id


class AgendaItemNaoEncontradoError(DomainError):
    """Item de agenda nao encontrado ou fora da fronteira informada."""

    def __init__(self, agenda_item_id: uuid.UUID) -> None:
        super().__init__(f"Item de agenda nao encontrado: {agenda_item_id}")
        self.agenda_item_id = agenda_item_id


class LembreteNaoEncontradoError(DomainError):
    """Lembrete nao encontrado ou fora da fronteira informada."""

    def __init__(self, lembrete_id: uuid.UUID) -> None:
        super().__init__(f"Lembrete nao encontrado: {lembrete_id}")
        self.lembrete_id = lembrete_id


class JobAgendadoNaoEncontradoError(DomainError):
    def __init__(self, job_id: uuid.UUID) -> None:
        super().__init__(f"Job agendado nao encontrado: {job_id}")
        self.job_id = job_id


class NotificacaoNaoEncontradaError(DomainError):
    def __init__(self, notificacao_id: uuid.UUID) -> None:
        super().__init__(f"Notificacao nao encontrada: {notificacao_id}")
        self.notificacao_id = notificacao_id


class TemplateNotificacaoNaoEncontradoError(DomainError):
    def __init__(self, template_id: uuid.UUID) -> None:
        super().__init__(f"Template de notificacao nao encontrado: {template_id}")
        self.template_id = template_id


class RegistroComunicacaoNaoEncontradoError(DomainError):
    """Registro de comunicacao nao encontrado ou fora da fronteira informada."""

    def __init__(self, registro_id: uuid.UUID) -> None:
        super().__init__(f"Registro de comunicacao nao encontrado: {registro_id}")
        self.registro_id = registro_id


class ModalidadeFinanceiraNaoEncontradaError(DomainError):
    """Modalidade financeira nao encontrada ou fora da fronteira informada."""

    def __init__(self, modalidade_id: uuid.UUID) -> None:
        super().__init__(f"Modalidade financeira nao encontrada: {modalidade_id}")
        self.modalidade_id = modalidade_id


class CalendarioFinanceiroNaoEncontradoError(DomainError):
    """Calendario financeiro nao encontrado ou fora da fronteira informada."""

    def __init__(self, calendario_id: uuid.UUID) -> None:
        super().__init__(f"Calendario financeiro nao encontrado: {calendario_id}")
        self.calendario_id = calendario_id


class ConfiguracaoFinanceiraNaoEncontradaError(DomainError):
    """Configuracao financeira nao encontrada ou fora da fronteira informada."""

    def __init__(self, configuracao_id: uuid.UUID) -> None:
        super().__init__(f"Configuracao financeira nao encontrada: {configuracao_id}")
        self.configuracao_id = configuracao_id


class AutenticacaoRecusadaError(DomainError):
    """Autenticacao recusada com mensagem uniforme (IMP-088)."""

    def __init__(self) -> None:
        super().__init__("Autenticacao recusada")


class AcessoNegadoError(DomainError):
    """Principal autenticado nao possui permissao para a operacao (IMP-087)."""

    def __init__(self, operacao: str) -> None:
        super().__init__(f"Acesso negado para operacao: {operacao}")
        self.operacao = operacao


class ContextoOperacionalIncompletoError(DomainError):
    """O proprio Principal nao possui uma unica Carteira operacional."""

    def __init__(self) -> None:
        super().__init__("Contexto operacional corrente indisponivel")


class PerfilNaoEncontradoError(DomainError):
    def __init__(self, perfil_id: uuid.UUID) -> None:
        super().__init__(f"Perfil de Acesso nao encontrado: {perfil_id}")
        self.perfil_id = perfil_id


class PerfilConflitoError(DomainError):
    def __init__(self, motivo: str) -> None:
        super().__init__(motivo)
        self.motivo = motivo


class TransicaoEstadoInvalidaError(DomainError):
    """Transição de estado operacional rejeitada pelo Aggregate (FEATURE-004).

    A regra de negócio é avaliada no Domain (``inativar()``/``reativar()``,
    DOMAIN-017) e lança ``ViolacaoInvarianteError``; a Aplicação a traduz para
    este erro de conflito para que a API responda 409 (estado divergente —
    IMP-036). Não é regra de negócio duplicada: apenas re-enquadramento do
    erro já decidido pelo Aggregate.
    """

    def __init__(self, tenant_id: object, acao: str, motivo: str) -> None:
        super().__init__(f"Transição de estado inválida em {tenant_id} ({acao}): {motivo}")
        self.tenant_id = tenant_id
        self.acao = acao
        self.motivo = motivo


class ConexaoWhatsAppNaoEncontradaError(DomainError):
    """Nenhuma instância existe para o Tenant (IMP-367, PLAN-034).

    "Não existe" é diferente de "existe e não está pareada": a primeira pede
    criar a instância, a segunda pede escanear um QR. Colapsar as duas faria a
    tela oferecer a ação errada.
    """

    def __init__(self, tenant_id: object) -> None:
        super().__init__(f"Nenhuma conexão de WhatsApp para o Tenant {tenant_id}")
        self.tenant_id = tenant_id


class NomeInstanciaInvalidoError(DomainError):
    """Nome de instância que o nosso banco recusaria (IMP-367).

    Existe para ser levantado **antes** de criar a instância no provedor: o
    Evolution aceita nomes que a coluna `instancia_nome` não comporta, e
    descobrir isso no `save` deixaria a instância criada lá fora sem registro
    aqui — inalcançável, porque o token só existia nesta requisição.
    """

    def __init__(self, motivo: str) -> None:
        super().__init__(motivo)
        self.motivo = motivo
