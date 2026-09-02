"""Catalogo fechado de operacoes autorizaveis do backend."""

from emprestimo.domain.platform.permissao import Permissao

CATALOGO_PERMISSOES_VERSAO = "1.1.0"

CATALOGO_PERMISSOES = (
    # IMP-351: o endpoint POST /platform/tenants saiu, mas esta permissao NAO.
    # Ela virou o marcador do papel de Administrador da Plataforma — e o que
    # `bootstrap_plataforma`, `autorizacao.py` e `estado.py` consultam para
    # saber quem e a raiz administrativa. Remove-la quebraria os tres.
    Permissao("tenant.criar", "Identificar o Administrador da Plataforma"),
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
    # IMP-360: submeter e decidir sao permissoes distintas. Antes, enviar para
    # analise usava `decidir` — quem submetia podia aprovar. Nao havia
    # segregacao entre propor e decidir, para nenhum operador.
    Permissao("comercial.proposta.submeter", "Submeter propostas comerciais para analise"),
    Permissao("comercial.proposta.decidir", "Decidir propostas comerciais"),
    Permissao("comercial.proposta.integrar", "Gerar contrato logico comercial"),
    Permissao("contratos.contrato.criar", "Criar contratos de credito"),
    Permissao("contratos.contrato.ler", "Consultar contratos de credito"),
    Permissao("contratos.contrato.assinar", "Formalizar e assinar contratos"),
    Permissao("contratos.contrato.liberar", "Liberar contrato para Motor futuro"),
    Permissao("contratos.contrato.encerrar", "Cancelar ou encerrar contratos"),
    Permissao("motor.emprestimo.criar", "Criar emprestimos no Motor Financeiro"),
    Permissao("motor.emprestimo.ler", "Consultar emprestimos no Motor Financeiro"),
    Permissao("motor.pagamento.registrar", "Registrar pagamentos no Motor Financeiro"),
    Permissao("motor.saldo.ler", "Consultar saldo financeiro"),
    Permissao("motor.memoria.ler", "Consultar memoria de calculo financeira"),
    Permissao("motor.quitacao.executar", "Executar quitacao financeira"),
    Permissao("motor.renegociacao.criar", "Criar renegociacao financeira"),
    Permissao("cobranca.caso.ler", "Consultar casos de cobranca operacional"),
    Permissao("cobranca.acao.registrar", "Registrar acoes de cobranca"),
    Permissao("cobranca.promessa.registrar", "Registrar promessas de pagamento"),
    Permissao("cobranca.promessa.apropriar", "Apropriar pagamento em promessa"),
    Permissao("agenda.ler", "Consultar agenda operacional"),
    Permissao("agenda.compromisso.gerir", "Gerir compromissos de agenda"),
    Permissao("agenda.lembrete.gerir", "Gerir lembretes de agenda"),
    Permissao("comunicacao.registrar", "Registrar comunicacao manual"),
    Permissao("comunicacao.ler", "Consultar historico de comunicacao"),
    Permissao("relatorios.operacionais.ler", "Consultar relatorios operacionais"),
    Permissao("configuracoes_financeiras.modalidade.gerir", "Gerir modalidades financeiras"),
    Permissao("configuracoes_financeiras.calendario.gerir", "Gerir calendarios financeiros"),
    Permissao("configuracoes_financeiras.configuracao.gerir", "Gerir configuracoes financeiras"),
    Permissao(
        "configuracoes_financeiras.configuracao.aprovar",
        "Aprovar configuracoes financeiras",
    ),
    Permissao("configuracoes_financeiras.configuracao.ativar", "Ativar configuracoes financeiras"),
    Permissao("configuracoes_financeiras.configuracao.ler", "Consultar configuracoes financeiras"),
    Permissao("configuracoes_financeiras.snapshot.capturar", "Capturar snapshots contratuais"),
    Permissao("automacao.job.consultar", "Consultar jobs de automacao"),
    Permissao("automacao.job.cancelar", "Cancelar jobs de automacao"),
    Permissao("automacao.job.retry", "Repetir jobs de automacao"),
    Permissao("notificacao.consultar", "Consultar notificacoes"),
    Permissao("notificacao.conciliar", "Conciliar notificacoes"),
    Permissao("notificacao.template.gerir", "Gerir templates de notificacao"),
    # IMP-355: ate 2026-08-27 nao havia rota de criacao de Usuario — cada Tenant
    # ficava limitado ao administrador criado pela CLI de bootstrap.
    Permissao("usuario.criar", "Criar Usuarios do Tenant"),
    # IMP-367: ler e gerir separadas porque sao riscos diferentes. Ver o estado
    # da conexao e rotina; conectar gera token novo e desconectar derruba o
    # canal de comunicacao inteiro do Credor.
    Permissao("whatsapp.conexao.ler", "Consultar a conexao de WhatsApp"),
    Permissao("whatsapp.conexao.gerir", "Conectar e desconectar o WhatsApp"),
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
