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
