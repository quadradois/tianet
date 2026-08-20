/**
 * Onde o destino aparece no menu.
 *
 * "principal" e o que o Credor faz: emprestar, ver quem deve, receber.
 * "administracao" e o resto — telas que existem, sao alcancaveis e continuam
 * certificadas, mas nao sao tarefa de todo dia. Nenhuma rota e removida; o que
 * muda e o que ocupa a primeira vista.
 */
export type NavigationGroup = "principal" | "administracao";

export type NavigationDestination = Readonly<{
  grupo: NavigationGroup;
  href: string;
  label: string;
  requiredPermission?: string;
  requiredAnyPermission?: readonly string[];
  /** Exige todas: destino que executa uma cadeia so aparece se ela for possivel. */
  requiredAllPermissions?: readonly string[];
}>;

export const SHELL_NAVIGATION: readonly NavigationDestination[] = [
  {
    grupo: "principal",
    href: "/app",
    label: "Inicio",
    requiredAnyPermission: ["relatorios.operacionais.ler", "agenda.ler", "cobranca.caso.ler"],
  },
  {
    grupo: "principal",
    href: "/app/lancamentos",
    label: "Novo emprestimo",
    requiredAllPermissions: [
      "devedor.criar",
      "comercial.proposta.criar",
      "contratos.contrato.criar",
      "motor.emprestimo.criar",
    ],
  },
  {
    grupo: "principal",
    href: "/app/devedores",
    label: "Devedores",
    requiredPermission: "devedor.ler",
  },
  {
    grupo: "administracao",
    href: "/app/devedores",
    label: "Comercial por devedor",
    requiredAnyPermission: ["comercial.proposta.ler", "comercial.simulacao.criar", "comercial.proposta.criar"],
  },
  {
    grupo: "administracao",
    href: "/app/contratos",
    label: "Contratos",
    requiredAnyPermission: [
      "contratos.contrato.criar",
      "contratos.contrato.ler",
      "contratos.contrato.assinar",
      "contratos.contrato.liberar",
      "contratos.contrato.encerrar",
    ],
  },
  {
    grupo: "principal",
    href: "/app/motor",
    label: "Emprestimos",
    requiredAnyPermission: [
      "motor.emprestimo.criar",
      "motor.emprestimo.ler",
      "motor.parcela.gerar",
      "motor.parcela.ler",
      "motor.pagamento.registrar",
      "motor.saldo.ler",
      "motor.memoria.ler",
      "motor.quitacao.executar",
      "motor.renegociacao.criar",
    ],
  },
  {
    grupo: "principal",
    href: "/app/cobranca",
    label: "Cobranca",
    requiredAnyPermission: [
      "cobranca.caso.ler",
      "cobranca.acao.registrar",
      "cobranca.promessa.registrar",
      "cobranca.promessa.apropriar",
    ],
  },
  {
    grupo: "administracao",
    href: "/app/agenda",
    label: "Agenda",
    requiredAnyPermission: [
      "agenda.ler",
      "agenda.compromisso.gerir",
      "agenda.lembrete.gerir",
      "notificacao.conciliar",
      "comunicacao.registrar",
      "comunicacao.ler",
    ],
  },
  {
    grupo: "administracao",
    href: "/app/relatorios",
    label: "Relatorios",
    requiredPermission: "relatorios.operacionais.ler",
  },
  {
    grupo: "administracao",
    href: "/app/configuracoes-financeiras",
    label: "Configuracoes",
    requiredAnyPermission: [
      "configuracoes_financeiras.configuracao.ler",
      "configuracoes_financeiras.configuracao.gerir",
      "configuracoes_financeiras.configuracao.aprovar",
      "configuracoes_financeiras.configuracao.ativar",
      "configuracoes_financeiras.modalidade.gerir",
      "configuracoes_financeiras.calendario.gerir",
      "configuracoes_financeiras.snapshot.capturar",
    ],
  },
  {
    grupo: "administracao",
    href: "/app/iam",
    label: "IAM",
    requiredAnyPermission: ["perfil.ler", "perfil.gerir"],
  },
  {
    grupo: "administracao",
    href: "/app/automacao",
    label: "Automacao",
    requiredAnyPermission: [
      "automacao.job.consultar",
      "automacao.job.cancelar",
      "automacao.job.retry",
      "notificacao.consultar",
      "notificacao.template.gerir",
      "notificacao.conciliar",
    ],
  },
];

export function navigationByGroup(
  destinations: readonly NavigationDestination[],
  grupo: NavigationGroup,
): readonly NavigationDestination[] {
  return destinations.filter((destination) => destination.grupo === grupo);
}

export function visibleNavigationItems(
  destinations: readonly NavigationDestination[],
  effectivePermissions: readonly string[],
): readonly NavigationDestination[] {
  const granted = new Set(effectivePermissions);
  return destinations.filter((destination) =>
    (destination.requiredPermission === undefined || granted.has(destination.requiredPermission))
    && (destination.requiredAnyPermission === undefined
      || destination.requiredAnyPermission.some((permission) => granted.has(permission)))
    && (destination.requiredAllPermissions === undefined
      || destination.requiredAllPermissions.every((permission) => granted.has(permission))));
}
