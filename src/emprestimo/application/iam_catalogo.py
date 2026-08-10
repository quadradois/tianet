"""Catalogo fechado de operacoes autorizaveis do backend."""

from emprestimo.domain.platform.permissao import Permissao

CATALOGO_PERMISSOES = (
    Permissao("tenant.criar", "Provisionar Tenants"),
    Permissao("tenant.ler", "Consultar Tenants"),
    Permissao("tenant.atualizar", "Atualizar Tenants"),
    Permissao("tenant.inativar", "Inativar Tenants"),
    Permissao("tenant.reativar", "Reativar Tenants"),
    Permissao("devedor.criar", "Criar Devedores"),
    Permissao("devedor.ler", "Consultar Devedores"),
    Permissao("devedor.atualizar", "Atualizar Devedores"),
    Permissao("devedor.inativar", "Inativar Devedores"),
    Permissao("devedor.reativar", "Reativar Devedores"),
    Permissao("comercial.simulacao.criar", "Criar simulacoes comerciais"),
    Permissao("comercial.proposta.criar", "Criar propostas comerciais"),
    Permissao("comercial.proposta.ler", "Consultar propostas comerciais"),
    Permissao("comercial.proposta.decidir", "Decidir propostas comerciais"),
    Permissao("comercial.proposta.integrar", "Gerar contrato logico comercial"),
    Permissao("contratos.contrato.criar", "Criar contratos de credito"),
    Permissao("contratos.contrato.ler", "Consultar contratos de credito"),
    Permissao("contratos.contrato.assinar", "Formalizar e assinar contratos"),
    Permissao("contratos.contrato.liberar", "Liberar contrato para Motor futuro"),
    Permissao("contratos.contrato.encerrar", "Cancelar ou encerrar contratos"),
    Permissao("motor.emprestimo.criar", "Criar emprestimos no Motor Financeiro"),
    Permissao("motor.emprestimo.ler", "Consultar emprestimos no Motor Financeiro"),
    Permissao("motor.parcela.gerar", "Gerar plano de parcelas no Motor Financeiro"),
    Permissao("motor.parcela.ler", "Consultar parcelas no Motor Financeiro"),
    Permissao("motor.pagamento.registrar", "Registrar pagamentos no Motor Financeiro"),
    Permissao("motor.saldo.ler", "Consultar saldo financeiro"),
    Permissao("motor.memoria.ler", "Consultar memoria de calculo financeira"),
    Permissao("motor.quitacao.executar", "Executar quitacao financeira"),
    Permissao("motor.renegociacao.criar", "Criar renegociacao financeira"),
    Permissao("credencial.redefinir", "Redefinir credenciais"),
    Permissao("perfil.gerir", "Gerir perfis e atribuicoes"),
    Permissao("perfil.ler", "Consultar perfis e permissoes"),
)

PERMISSOES_PLATAFORMA = tuple(
    permissao for permissao in CATALOGO_PERMISSOES if permissao.codigo.startswith("tenant.")
)
PERMISSOES_ADMIN_TENANT = tuple(
    permissao for permissao in CATALOGO_PERMISSOES if permissao not in PERMISSOES_PLATAFORMA
)

CATALOGO_POR_CODIGO = {permissao.codigo: permissao for permissao in CATALOGO_PERMISSOES}
