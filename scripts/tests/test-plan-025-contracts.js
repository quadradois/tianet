#!/usr/bin/env node
'use strict';

const assert = require('assert');
const crypto = require('crypto');
const childProcess = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf8').replace(/\r\n/g, '\n');

const FILES = {
  adr001: 'docs/architecture/adrs/ADR-001-stack-tecnologica-oficial-mvp.md',
  discovery: 'docs/audits/discoveries/frontend-mvp-discovery-sdd.md',
  matrix: 'docs/governance/frontend-mvp-traceability-matrix.md',
  feature11: 'docs/product/platform/features/FEATURE-011-gerir-perfis-e-permissoes.md',
  feature12: 'docs/product/platform/features/FEATURE-012-autorizar-requisicao.md',
  us125: 'docs/product/platform/user-stories/US-125-consultar-contexto-operacional-corrente.md',
  us126: 'docs/product/platform/user-stories/US-126-consultar-catalogo-permissoes.md',
  plan: 'docs/implementation/plans/PLAN-025-frontend-mvp.md',
  backlog: 'docs/implementation/backlogs/PLAN-025-execution-backlog.md',
  report: 'docs/implementation/reports/PLAN-026-frontend-mvp-hardening-contratual-2026-08-12.md',
  scaffoldReport: 'docs/audits/reports/frontend-mvp-imp-284-scaffold-report-2026-08-12.md',
  scaffoldManifest: 'docs/audits/evidence/frontend-mvp-imp-284-protected-baseline.json',
  harnessReport: 'docs/audits/reports/frontend-mvp-imp-285-test-harness-report-2026-08-13.md',
  harnessManifest: 'docs/audits/evidence/frontend-mvp-imp-285-protected-baseline.json',
  foundationReport: 'docs/audits/reports/frontend-mvp-imp-286-design-foundation-report-2026-08-13.md',
  foundationManifest: 'docs/audits/evidence/frontend-mvp-imp-286-protected-baseline.json',
  openapiReport: 'docs/audits/reports/frontend-mvp-imp-287-openapi-client-report-2026-08-13.md',
  openapiManifest: 'docs/audits/evidence/frontend-mvp-imp-287-protected-baseline.json',
  dashboardReport: 'docs/audits/reports/frontend-mvp-imp-290-dashboard-report-2026-08-13.md',
  dashboardManifest: 'docs/audits/evidence/frontend-mvp-imp-290-protected-baseline.json',
  snapshot: 'docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json',
  registry: 'docs/governance/registry/identifier-registry.json',
  packageJson: 'package.json',
};

const docs = Object.fromEntries(Object.entries(FILES).map(([key, rel]) => [key, read(rel)]));
// IMP-304 estende a faixa: correcao pos-certificacao decidida pela DR-002.
const EXPECTED_IMPS = Array.from({ length: 31 }, (_, index) => `IMP-${274 + index}`);
const REQUIRED_FIELDS = [
  'Objetivo',
  'Componentes afetados',
  'Dependencias',
  'Criterios de conclusao',
  'Suite minima',
  'Status',
];
const REQUIRED_GATES = [
  'npm run docs:validate',
  'npm run docs:test',
  'node scripts/tests/test-plan-025-contracts.js',
  'npm run quality:migrations',
  'git diff --check',
  'fable:fable-judge',
];
const SCAFFOLD_FILES = {
  packageJson: 'frontend/package.json',
  packageLock: 'frontend/package-lock.json',
  npmrc: 'frontend/.npmrc',
  tsconfig: 'frontend/tsconfig.json',
  nextConfig: 'frontend/next.config.ts',
  eslintConfig: 'frontend/eslint.config.mjs',
  layout: 'frontend/src/app/layout.tsx',
  page: 'frontend/src/app/page.tsx',
  globals: 'frontend/src/app/globals.css',
  readme: 'frontend/README.md',
  workflow: '.github/workflows/quality.yml',
  gitignore: '.gitignore',
};
const SCAFFOLD_VERSIONS = {
  next: '16.3.0',
  react: '19.2.8',
  'react-dom': '19.2.8',
  typescript: '5.9.3',
  eslint: '9.39.5',
  'eslint-config-next': '16.3.0',
  '@types/node': '20.19.43',
  '@types/react': '19.2.18',
  '@types/react-dom': '19.2.4',
};
const HARNESS_FILES = {
  packageJson: 'frontend/package.json',
  unitConfig: 'frontend/vitest.unit.config.ts',
  componentConfig: 'frontend/vitest.component.config.ts',
  contractConfig: 'frontend/vitest.contract.config.ts',
  playwrightConfig: 'frontend/playwright.config.ts',
  unitSmoke: 'frontend/tests/unit/harness.test.ts',
  componentSmoke: 'frontend/tests/component/harness.test.tsx',
  componentSetup: 'frontend/tests/component/setup.ts',
  mswServer: 'frontend/tests/mocks/server.ts',
  contractSmoke: 'frontend/tests/contract/openapi-snapshot.test.ts',
  e2eSmoke: 'frontend/tests/e2e/scaffold.spec.ts',
  infrastructureSmoke: 'frontend/tests/infrastructure/real-stack-smoke.mjs',
  toolchainCheck: 'frontend/tests/toolchain-check.mjs',
  workflow: '.github/workflows/quality.yml',
  gitignore: 'frontend/.gitignore',
};
const HARNESS_VERSIONS = {
  '@playwright/test': '1.62.1',
  '@testing-library/dom': '10.4.1',
  '@testing-library/jest-dom': '7.0.1',
  '@testing-library/react': '16.3.2',
  '@testing-library/user-event': '14.6.4',
  jsdom: '30.0.1',
  msw: '2.15.0',
  vitest: '4.1.10',
};
const FOUNDATION_FILES = {
  componentsJson: 'frontend/components.json',
  postcssConfig: 'frontend/postcss.config.mjs',
  packageJson: 'frontend/package.json',
  globals: 'frontend/src/app/globals.css',
  page: 'frontend/src/app/page.tsx',
  layout: 'frontend/src/app/layout.tsx',
  utils: 'frontend/src/lib/utils.ts',
  button: 'frontend/src/components/ui/button.tsx',
  alert: 'frontend/src/components/ui/alert.tsx',
  card: 'frontend/src/components/ui/card.tsx',
  dialog: 'frontend/src/components/ui/dialog.tsx',
  input: 'frontend/src/components/ui/input.tsx',
  label: 'frontend/src/components/ui/label.tsx',
  skeleton: 'frontend/src/components/ui/skeleton.tsx',
  destructiveDialog: 'frontend/src/components/foundation/destructive-dialog-demo.tsx',
  feedback: 'frontend/src/components/foundation/feedback-state.tsx',
  showcase: 'frontend/src/components/foundation/foundation-showcase.tsx',
  overflow: 'frontend/src/components/foundation/overflow-region.tsx',
  componentTest: 'frontend/tests/component/foundation.test.tsx',
  e2eTest: 'frontend/tests/e2e/foundation.spec.ts',
  axeTest: 'frontend/tests/e2e/foundation-a11y.spec.ts',
  playwrightConfig: 'frontend/playwright.config.ts',
  workflow: '.github/workflows/quality.yml',
  gitignore: 'frontend/.gitignore',
};
const FOUNDATION_DEPENDENCIES = {
  '@radix-ui/react-dialog': '1.1.23',
  '@radix-ui/react-slot': '1.3.3',
  'class-variance-authority': '0.7.1',
  clsx: '2.1.1',
  'tailwind-merge': '3.6.0',
};
const FOUNDATION_DEV_DEPENDENCIES = {
  '@axe-core/playwright': '4.13.0',
  '@tailwindcss/postcss': '4.3.3',
  postcss: '8.5.26',
  tailwindcss: '4.3.3',
};
const OPENAPI_VERSIONS = {
  'openapi-fetch': '0.17.0',
  'openapi-typescript': '7.13.0',
  'server-only': '0.0.1',
};
const BFF_VERSIONS = { jose: '6.2.8' };
const OPENAPI_FILES = {
  generated: 'frontend/src/lib/api/openapi.generated.ts',
  client: 'frontend/src/lib/api/client.server.ts',
  codegen: 'frontend/scripts/openapi-codegen.mjs',
  contractTest: 'frontend/tests/contract/openapi-client.test.ts',
  packageJson: 'frontend/package.json',
  workflow: '.github/workflows/quality.yml',
  readme: 'frontend/README.md',
  scopeScript: 'scripts/tests/test-imp-287-scope.js',
};
const BFF_FILES = {
  session: 'frontend/src/lib/bff/session.server.ts',
  backend: 'frontend/src/lib/bff/backend.server.ts',
  loginRoute: 'frontend/src/app/api/auth/login/route.ts',
  logoutRoute: 'frontend/src/app/api/auth/logout/route.ts',
  config: 'frontend/vitest.bff.config.ts',
  sessionTest: 'frontend/tests/bff/session.test.ts',
  bffTest: 'frontend/tests/bff/bff.test.ts',
  envExample: 'frontend/.env.example',
  report: 'docs/audits/reports/frontend-mvp-imp-288-session-bff-report-2026-08-13.md',
  manifest: 'docs/audits/evidence/frontend-mvp-imp-288-protected-baseline.json',
  scopeScript: 'scripts/tests/test-imp-288-scope.js',
  packageJson: 'frontend/package.json',
  client: 'frontend/src/lib/api/client.server.ts',
  workflow: '.github/workflows/quality.yml',
};
const SHELL_FILES = {
  session: 'frontend/src/lib/bff/session.server.ts',
  backend: 'frontend/src/lib/bff/backend.server.ts',
  context: 'frontend/src/lib/bff/context.server.ts',
  bootstrapRoute: 'frontend/src/app/api/auth/bootstrap/route.ts',
  loginForm: 'frontend/src/components/auth/login-form.client.tsx',
  logoutButton: 'frontend/src/components/auth/logout-button.client.tsx',
  recovery: 'frontend/src/components/auth/session-recovery.client.tsx',
  appShell: 'frontend/src/components/shell/app-shell.tsx',
  contextSummary: 'frontend/src/components/shell/context-summary.tsx',
  navigation: 'frontend/src/components/shell/navigation.tsx',
  navigationPolicy: 'frontend/src/lib/shell/navigation-policy.ts',
  appLayout: 'frontend/src/app/app/layout.tsx',
  loginPage: 'frontend/src/app/login/page.tsx',
  notFound: 'frontend/src/app/not-found.tsx',
  unitTest: 'frontend/tests/unit/navigation-policy.test.ts',
  componentTest: 'frontend/tests/component/session-shell.test.tsx',
  bffTest: 'frontend/tests/bff/context.test.ts',
  contractTest: 'frontend/tests/contract/session-shell.test.ts',
  e2eTest: 'frontend/tests/session-e2e/session-shell.spec.ts',
  axeTest: 'frontend/tests/session-e2e/session-shell-a11y.spec.ts',
  fixture: 'frontend/tests/session-e2e/backend-fixture.mjs',
  playwrightConfig: 'frontend/playwright.session.config.ts',
  report: 'docs/audits/reports/frontend-mvp-imp-289-authenticated-shell-report-2026-08-13.md',
  manifest: 'docs/audits/evidence/frontend-mvp-imp-289-protected-baseline.json',
  scopeScript: 'scripts/tests/test-imp-289-scope.js',
  packageJson: 'frontend/package.json',
  workflow: '.github/workflows/quality.yml',
  backlog: 'docs/implementation/backlogs/PLAN-025-execution-backlog.md',
};
const DASHBOARD_FILES = {
  component: 'frontend/src/components/dashboard/dashboard.tsx',
  currentContext: 'frontend/src/lib/bff/current-context.server.ts',
  loader: 'frontend/src/lib/bff/dashboard.server.ts',
  policy: 'frontend/src/lib/dashboard/dashboard-policy.ts',
  page: 'frontend/src/app/app/page.tsx',
  navigationPolicy: 'frontend/src/lib/shell/navigation-policy.ts',
  unitTest: 'frontend/tests/unit/dashboard-policy.test.ts',
  componentTest: 'frontend/tests/component/dashboard.test.tsx',
  bffTest: 'frontend/tests/bff/dashboard.test.ts',
  contractTest: 'frontend/tests/contract/dashboard.test.ts',
  e2eTest: 'frontend/tests/dashboard-e2e/dashboard.spec.ts',
  axeTest: 'frontend/tests/dashboard-e2e/dashboard-a11y.spec.ts',
  fixture: 'frontend/tests/dashboard-e2e/backend-fixture.mjs',
  playwrightConfig: 'frontend/playwright.dashboard.config.ts',
  report: 'docs/audits/reports/frontend-mvp-imp-290-dashboard-report-2026-08-13.md',
  manifest: 'docs/audits/evidence/frontend-mvp-imp-290-protected-baseline.json',
  scopeScript: 'scripts/tests/test-imp-290-scope.js',
  packageJson: 'frontend/package.json',
  workflow: '.github/workflows/quality.yml',
  plan: 'docs/implementation/plans/PLAN-025-frontend-mvp.md',
  backlog: 'docs/implementation/backlogs/PLAN-025-execution-backlog.md',
  discovery: 'docs/audits/discoveries/frontend-mvp-discovery-sdd.md',
  matrix: 'docs/governance/frontend-mvp-traceability-matrix.md',
};
const DEVEDORES_FILES = {
  component: 'frontend/src/components/devedores/devedores.tsx',
  form: 'frontend/src/components/devedores/devedor-form.client.tsx',
  statusDialog: 'frontend/src/components/devedores/devedor-status-dialog.client.tsx',
  loader: 'frontend/src/lib/bff/devedores.server.ts',
  policy: 'frontend/src/lib/devedores/devedores-policy.ts',
  listPage: 'frontend/src/app/app/devedores/page.tsx',
  detailPage: 'frontend/src/app/app/devedores/[devedorId]/page.tsx',
  actions: 'frontend/src/app/app/devedores/actions.ts',
  unitTest: 'frontend/tests/unit/devedores-policy.test.ts',
  componentTest: 'frontend/tests/component/devedores.test.tsx',
  bffTest: 'frontend/tests/bff/devedores.test.ts',
  contractTest: 'frontend/tests/contract/devedores.test.ts',
  e2eTest: 'frontend/tests/devedores-e2e/devedores.spec.ts',
  axeTest: 'frontend/tests/devedores-e2e/devedores-a11y.spec.ts',
  fixture: 'frontend/tests/devedores-e2e/backend-fixture.mjs',
  playwrightConfig: 'frontend/playwright.devedores.config.ts',
  report: 'docs/audits/reports/frontend-mvp-imp-291-devedores-report-2026-08-14.md',
  manifest: 'docs/audits/evidence/frontend-mvp-imp-291-protected-baseline.json',
  scopeScript: 'scripts/tests/test-imp-291-scope.js',
  packageJson: 'frontend/package.json',
  workflow: '.github/workflows/quality.yml',
  navigationPolicy: 'frontend/src/lib/shell/navigation-policy.ts',
  plan: 'docs/implementation/plans/PLAN-025-frontend-mvp.md',
  backlog: 'docs/implementation/backlogs/PLAN-025-execution-backlog.md',
  discovery: 'docs/audits/discoveries/frontend-mvp-discovery-sdd.md',
  matrix: 'docs/governance/frontend-mvp-traceability-matrix.md',
};
const COMERCIAL_FILES = {
  component: 'frontend/src/components/comercial/comercial.tsx',
  jsonForm: 'frontend/src/components/comercial/comercial-json-form.client.tsx',
  decisionDialog: 'frontend/src/components/comercial/proposta-decision-dialog.client.tsx',
  loader: 'frontend/src/lib/bff/comercial.server.ts',
  policy: 'frontend/src/lib/comercial/comercial-policy.ts',
  devedorComercialPage: 'frontend/src/app/app/devedores/[devedorId]/comercial/page.tsx',
  propostaPage: 'frontend/src/app/app/comercial/propostas/[propostaId]/page.tsx',
  actions: 'frontend/src/app/app/comercial/actions.ts',
  unitTest: 'frontend/tests/unit/comercial-policy.test.ts',
  componentTest: 'frontend/tests/component/comercial.test.tsx',
  bffTest: 'frontend/tests/bff/comercial.test.ts',
  contractTest: 'frontend/tests/contract/comercial.test.ts',
  e2eTest: 'frontend/tests/comercial-e2e/comercial.spec.ts',
  axeTest: 'frontend/tests/comercial-e2e/comercial-a11y.spec.ts',
  fixture: 'frontend/tests/comercial-e2e/backend-fixture.mjs',
  playwrightConfig: 'frontend/playwright.comercial.config.ts',
  report: 'docs/audits/reports/frontend-mvp-imp-292-comercial-report-2026-08-14.md',
  manifest: 'docs/audits/evidence/frontend-mvp-imp-292-protected-baseline.json',
  scopeScript: 'scripts/tests/test-imp-292-scope.js',
  packageJson: 'frontend/package.json',
  workflow: '.github/workflows/quality.yml',
  navigationPolicy: 'frontend/src/lib/shell/navigation-policy.ts',
  devedoresComponent: 'frontend/src/components/devedores/devedores.tsx',
  plan: 'docs/implementation/plans/PLAN-025-frontend-mvp.md',
  backlog: 'docs/implementation/backlogs/PLAN-025-execution-backlog.md',
  discovery: 'docs/audits/discoveries/frontend-mvp-discovery-sdd.md',
  matrix: 'docs/governance/frontend-mvp-traceability-matrix.md',
};
const CONTRATOS_FILES = {
  loader: 'frontend/src/lib/bff/contratos.server.ts',
  policy: 'frontend/src/lib/contratos/contratos-policy.ts',
  component: 'frontend/src/components/contratos/contratos.tsx',
  decisionDialog: 'frontend/src/components/contratos/contrato-decision-dialog.client.tsx',
  listPage: 'frontend/src/app/app/contratos/page.tsx',
  detailPage: 'frontend/src/app/app/contratos/[contratoId]/page.tsx',
  actions: 'frontend/src/app/app/contratos/actions.ts',
  unitTest: 'frontend/tests/unit/contratos-policy.test.ts',
  componentTest: 'frontend/tests/component/contratos.test.tsx',
  bffTest: 'frontend/tests/bff/contratos.test.ts',
  contractTest: 'frontend/tests/contract/contratos.test.ts',
  e2eTest: 'frontend/tests/contratos-e2e/contratos.spec.ts',
  axeTest: 'frontend/tests/contratos-e2e/contratos-a11y.spec.ts',
  fixture: 'frontend/tests/contratos-e2e/backend-fixture.mjs',
  playwrightConfig: 'frontend/playwright.contratos.config.ts',
  report: 'docs/audits/reports/frontend-mvp-imp-293-contratos-report-2026-08-14.md',
  manifest: 'docs/audits/evidence/frontend-mvp-imp-293-protected-baseline.json',
  scopeScript: 'scripts/tests/test-imp-293-scope.js',
  packageJson: 'frontend/package.json',
  workflow: '.github/workflows/quality.yml',
  navigationPolicy: 'frontend/src/lib/shell/navigation-policy.ts',
  comercialComponent: 'frontend/src/components/comercial/comercial.tsx',
  propostaPage: 'frontend/src/app/app/comercial/propostas/[propostaId]/page.tsx',
  plan: 'docs/implementation/plans/PLAN-025-frontend-mvp.md',
  backlog: 'docs/implementation/backlogs/PLAN-025-execution-backlog.md',
  discovery: 'docs/audits/discoveries/frontend-mvp-discovery-sdd.md',
  matrix: 'docs/governance/frontend-mvp-traceability-matrix.md',
};
const MOTOR_FILES = {
  loader: 'frontend/src/lib/bff/motor.server.ts',
  policy: 'frontend/src/lib/motor/motor-policy.ts',
  component: 'frontend/src/components/motor/motor.tsx',
  commandDialog: 'frontend/src/components/motor/motor-command-dialog.client.tsx',
  listPage: 'frontend/src/app/app/motor/page.tsx',
  detailPage: 'frontend/src/app/app/motor/[emprestimoId]/page.tsx',
  actions: 'frontend/src/app/app/motor/actions.ts',
  unitTest: 'frontend/tests/unit/motor-policy.test.ts',
  componentTest: 'frontend/tests/component/motor.test.tsx',
  bffTest: 'frontend/tests/bff/motor.test.ts',
  contractTest: 'frontend/tests/contract/motor.test.ts',
  e2eTest: 'frontend/tests/motor-e2e/motor.spec.ts',
  axeTest: 'frontend/tests/motor-e2e/motor-a11y.spec.ts',
  fixture: 'frontend/tests/motor-e2e/backend-fixture.mjs',
  playwrightConfig: 'frontend/playwright.motor.config.ts',
  report: 'docs/audits/reports/frontend-mvp-imp-294-motor-report-2026-08-14.md',
  manifest: 'docs/audits/evidence/frontend-mvp-imp-294-protected-baseline.json',
  scopeScript: 'scripts/tests/test-imp-295-scope.js',
  packageJson: 'frontend/package.json',
  workflow: '.github/workflows/quality.yml',
  navigationPolicy: 'frontend/src/lib/shell/navigation-policy.ts',
  navigationTest: 'frontend/tests/unit/navigation-policy.test.ts',
  contratosComponent: 'frontend/src/components/contratos/contratos.tsx',
  contratoPage: 'frontend/src/app/app/contratos/[contratoId]/page.tsx',
  plan: 'docs/implementation/plans/PLAN-025-frontend-mvp.md',
  backlog: 'docs/implementation/backlogs/PLAN-025-execution-backlog.md',
  discovery: 'docs/audits/discoveries/frontend-mvp-discovery-sdd.md',
  matrix: 'docs/governance/frontend-mvp-traceability-matrix.md',
  openapi: 'docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json',
};
const COBRANCA_FILES = {
  loader: 'frontend/src/lib/bff/cobranca.server.ts',
  policy: 'frontend/src/lib/cobranca/cobranca-policy.ts',
  component: 'frontend/src/components/cobranca/cobranca.tsx',
  actionForm: 'frontend/src/components/cobranca/cobranca-command-dialog.client.tsx',
  page: 'frontend/src/app/app/cobranca/page.tsx',
  actions: 'frontend/src/app/app/cobranca/actions.ts',
  unitTest: 'frontend/tests/unit/cobranca-policy.test.ts',
  componentTest: 'frontend/tests/component/cobranca.test.tsx',
  bffTest: 'frontend/tests/bff/cobranca.test.ts',
  contractTest: 'frontend/tests/contract/cobranca.test.ts',
  e2eTest: 'frontend/tests/cobranca-e2e/cobranca.spec.ts',
  axeTest: 'frontend/tests/cobranca-e2e/cobranca-a11y.spec.ts',
  fixture: 'frontend/tests/cobranca-e2e/backend-fixture.mjs',
  playwrightConfig: 'frontend/playwright.cobranca.config.ts',
  report: 'docs/audits/reports/frontend-mvp-imp-295-cobranca-report-2026-08-14.md',
  manifest: 'docs/audits/evidence/frontend-mvp-imp-295-protected-baseline.json',
  scopeScript: 'scripts/tests/test-imp-295-scope.js',
  packageJson: 'frontend/package.json',
  workflow: '.github/workflows/quality.yml',
  navigationPolicy: 'frontend/src/lib/shell/navigation-policy.ts',
  navigationTest: 'frontend/tests/unit/navigation-policy.test.ts',
  plan: 'docs/implementation/plans/PLAN-025-frontend-mvp.md',
  backlog: 'docs/implementation/backlogs/PLAN-025-execution-backlog.md',
  discovery: 'docs/audits/discoveries/frontend-mvp-discovery-sdd.md',
  matrix: 'docs/governance/frontend-mvp-traceability-matrix.md',
  openapi: 'docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json',
};
const AGENDA_FILES = {
  loader: 'frontend/src/lib/bff/agenda-comunicacao.server.ts',
  policy: 'frontend/src/lib/agenda/agenda-policy.ts',
  component: 'frontend/src/components/agenda/agenda-comunicacao.tsx',
  commandDialog: 'frontend/src/components/agenda/agenda-command-dialog.client.tsx',
  page: 'frontend/src/app/app/agenda/page.tsx',
  actions: 'frontend/src/app/app/agenda/actions.ts',
  unitTest: 'frontend/tests/unit/agenda-policy.test.ts',
  componentTest: 'frontend/tests/component/agenda-comunicacao.test.tsx',
  bffTest: 'frontend/tests/bff/agenda-comunicacao.test.ts',
  contractTest: 'frontend/tests/contract/agenda-comunicacao.test.ts',
  e2eTest: 'frontend/tests/agenda-e2e/agenda-comunicacao.spec.ts',
  axeTest: 'frontend/tests/agenda-e2e/agenda-comunicacao-a11y.spec.ts',
  fixture: 'frontend/tests/agenda-e2e/backend-fixture.mjs',
  playwrightConfig: 'frontend/playwright.agenda.config.ts',
  report: 'docs/audits/reports/frontend-mvp-imp-296-agenda-comunicacao-report-2026-08-14.md',
  manifest: 'docs/audits/evidence/frontend-mvp-imp-296-protected-baseline.json',
  scopeScript: 'scripts/tests/test-imp-296-scope.js',
  packageJson: 'frontend/package.json',
  workflow: '.github/workflows/quality.yml',
  navigationPolicy: 'frontend/src/lib/shell/navigation-policy.ts',
  navigationTest: 'frontend/tests/unit/navigation-policy.test.ts',
  plan: 'docs/implementation/plans/PLAN-025-frontend-mvp.md',
  backlog: 'docs/implementation/backlogs/PLAN-025-execution-backlog.md',
  discovery: 'docs/audits/discoveries/frontend-mvp-discovery-sdd.md',
  matrix: 'docs/governance/frontend-mvp-traceability-matrix.md',
  openapi: 'docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json',
};
const BFF_ERROR_SANITIZATION_FILES = {
  report: 'docs/audits/reports/frontend-mvp-bff-error-sanitization-report-2026-08-14.md',
  manifest: 'docs/audits/evidence/frontend-mvp-bff-error-sanitization-protected-baseline.json',
  scopeScript: 'scripts/tests/test-bff-error-sanitization-scope.js',
  workflow: '.github/workflows/quality.yml',
  testPlan: 'scripts/tests/test-plan-025-contracts.js',
  plan: 'docs/implementation/plans/PLAN-025-frontend-mvp.md',
  backlog: 'docs/implementation/backlogs/PLAN-025-execution-backlog.md',
  devedoresLoader: 'frontend/src/lib/bff/devedores.server.ts',
  devedoresTest: 'frontend/tests/bff/devedores.test.ts',
  comercialLoader: 'frontend/src/lib/bff/comercial.server.ts',
  comercialTest: 'frontend/tests/bff/comercial.test.ts',
  contratosLoader: 'frontend/src/lib/bff/contratos.server.ts',
  contratosTest: 'frontend/tests/bff/contratos.test.ts',
  motorLoader: 'frontend/src/lib/bff/motor.server.ts',
  motorTest: 'frontend/tests/bff/motor.test.ts',
  cobrancaLoader: 'frontend/src/lib/bff/cobranca.server.ts',
  cobrancaTest: 'frontend/tests/bff/cobranca.test.ts',
  agendaLoader: 'frontend/src/lib/bff/agenda-comunicacao.server.ts',
};
const RELATORIOS_FILES = {
  loader: 'frontend/src/lib/bff/relatorios.server.ts',
  policy: 'frontend/src/lib/relatorios/relatorios-policy.ts',
  component: 'frontend/src/components/relatorios/relatorios.tsx',
  page: 'frontend/src/app/app/relatorios/page.tsx',
  loading: 'frontend/src/app/app/relatorios/loading.tsx',
  unitTest: 'frontend/tests/unit/relatorios-policy.test.ts',
  componentTest: 'frontend/tests/component/relatorios.test.tsx',
  bffTest: 'frontend/tests/bff/relatorios.test.ts',
  contractTest: 'frontend/tests/contract/relatorios.test.ts',
  e2eTest: 'frontend/tests/relatorios-e2e/relatorios.spec.ts',
  axeTest: 'frontend/tests/relatorios-e2e/relatorios-a11y.spec.ts',
  fixture: 'frontend/tests/relatorios-e2e/backend-fixture.mjs',
  playwrightConfig: 'frontend/playwright.relatorios.config.ts',
  report: 'docs/audits/reports/frontend-mvp-imp-297-relatorios-report-2026-08-14.md',
  manifest: 'docs/audits/evidence/frontend-mvp-imp-297-protected-baseline.json',
  scopeScript: 'scripts/tests/test-imp-297-scope.js',
  packageJson: 'frontend/package.json',
  workflow: '.github/workflows/quality.yml',
  navigationPolicy: 'frontend/src/lib/shell/navigation-policy.ts',
  navigationTest: 'frontend/tests/unit/navigation-policy.test.ts',
  plan: 'docs/implementation/plans/PLAN-025-frontend-mvp.md',
  backlog: 'docs/implementation/backlogs/PLAN-025-execution-backlog.md',
  discovery: 'docs/audits/discoveries/frontend-mvp-discovery-sdd.md',
  matrix: 'docs/governance/frontend-mvp-traceability-matrix.md',
  openapi: 'docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json',
};
const CONFIGURACOES_FILES = {
  loader: 'frontend/src/lib/bff/configuracoes-financeiras.server.ts',
  policy: 'frontend/src/lib/configuracoes-financeiras/configuracoes-policy.ts',
  component: 'frontend/src/components/configuracoes-financeiras/configuracoes-financeiras.tsx',
  actionForm: 'frontend/src/components/configuracoes-financeiras/configuracoes-actions.client.tsx',
  page: 'frontend/src/app/app/configuracoes-financeiras/page.tsx',
  loading: 'frontend/src/app/app/configuracoes-financeiras/loading.tsx',
  actions: 'frontend/src/app/app/configuracoes-financeiras/actions.ts',
  unitTest: 'frontend/tests/unit/configuracoes-policy.test.ts',
  componentTest: 'frontend/tests/component/configuracoes-financeiras.test.tsx',
  bffTest: 'frontend/tests/bff/configuracoes-financeiras.test.ts',
  contractTest: 'frontend/tests/contract/configuracoes-financeiras.test.ts',
  e2eTest: 'frontend/tests/configuracoes-e2e/configuracoes.spec.ts',
  axeTest: 'frontend/tests/configuracoes-e2e/configuracoes-a11y.spec.ts',
  fixture: 'frontend/tests/configuracoes-e2e/backend-fixture.mjs',
  playwrightConfig: 'frontend/playwright.configuracoes.config.ts',
  report: 'docs/audits/reports/frontend-mvp-imp-298-configuracoes-report-2026-08-14.md',
  manifest: 'docs/audits/evidence/frontend-mvp-imp-298-protected-baseline.json',
  scopeScript: 'scripts/tests/test-imp-298-scope.js',
  packageJson: 'frontend/package.json',
  workflow: '.github/workflows/quality.yml',
  navigationPolicy: 'frontend/src/lib/shell/navigation-policy.ts',
  navigationTest: 'frontend/tests/unit/navigation-policy.test.ts',
  plan: 'docs/implementation/plans/PLAN-025-frontend-mvp.md',
  backlog: 'docs/implementation/backlogs/PLAN-025-execution-backlog.md',
  discovery: 'docs/audits/discoveries/frontend-mvp-discovery-sdd.md',
  matrix: 'docs/governance/frontend-mvp-traceability-matrix.md',
  openapi: 'docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json',
};
const IAM_FILES = {
  loader: 'frontend/src/lib/bff/iam.server.ts',
  policy: 'frontend/src/lib/iam/iam-policy.ts',
  component: 'frontend/src/components/iam/iam-admin.tsx',
  actionForm: 'frontend/src/components/iam/iam-actions.client.tsx',
  page: 'frontend/src/app/app/iam/page.tsx',
  loading: 'frontend/src/app/app/iam/loading.tsx',
  actions: 'frontend/src/app/app/iam/actions.ts',
  unitTest: 'frontend/tests/unit/iam-policy.test.ts',
  componentTest: 'frontend/tests/component/iam.test.tsx',
  bffTest: 'frontend/tests/bff/iam.test.ts',
  contractTest: 'frontend/tests/contract/iam.test.ts',
  e2eTest: 'frontend/tests/iam-e2e/iam.spec.ts',
  axeTest: 'frontend/tests/iam-e2e/iam-a11y.spec.ts',
  fixture: 'frontend/tests/iam-e2e/backend-fixture.mjs',
  playwrightConfig: 'frontend/playwright.iam.config.ts',
  report: 'docs/audits/reports/frontend-mvp-imp-299-iam-report-2026-08-14.md',
  manifest: 'docs/audits/evidence/frontend-mvp-imp-299-protected-baseline.json',
  scopeScript: 'scripts/tests/test-imp-299-scope.js',
  packageJson: 'frontend/package.json',
  workflow: '.github/workflows/quality.yml',
  navigationPolicy: 'frontend/src/lib/shell/navigation-policy.ts',
  navigationTest: 'frontend/tests/unit/navigation-policy.test.ts',
  plan: 'docs/implementation/plans/PLAN-025-frontend-mvp.md',
  backlog: 'docs/implementation/backlogs/PLAN-025-execution-backlog.md',
  discovery: 'docs/audits/discoveries/frontend-mvp-discovery-sdd.md',
  matrix: 'docs/governance/frontend-mvp-traceability-matrix.md',
  openapi: 'docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json',
};
const AUTOMACAO_FILES = {
  loader: 'frontend/src/lib/bff/automacao.server.ts',
  policy: 'frontend/src/lib/automacao/automacao-policy.ts',
  component: 'frontend/src/components/automacao/automacao.tsx',
  actionForm: 'frontend/src/components/automacao/automacao-actions.client.tsx',
  page: 'frontend/src/app/app/automacao/page.tsx',
  loading: 'frontend/src/app/app/automacao/loading.tsx',
  actions: 'frontend/src/app/app/automacao/actions.ts',
  unitTest: 'frontend/tests/unit/automacao-policy.test.ts',
  componentTest: 'frontend/tests/component/automacao.test.tsx',
  bffTest: 'frontend/tests/bff/automacao.test.ts',
  contractTest: 'frontend/tests/contract/automacao.test.ts',
  e2eTest: 'frontend/tests/automacao-e2e/automacao.spec.ts',
  axeTest: 'frontend/tests/automacao-e2e/automacao-a11y.spec.ts',
  fixture: 'frontend/tests/automacao-e2e/backend-fixture.mjs',
  playwrightConfig: 'frontend/playwright.automacao.config.ts',
  report: 'docs/audits/reports/frontend-mvp-imp-300-automacao-report-2026-08-14.md',
  manifest: 'docs/audits/evidence/frontend-mvp-imp-300-protected-baseline.json',
  scopeScript: 'scripts/tests/test-imp-300-scope.js',
  packageJson: 'frontend/package.json',
  workflow: '.github/workflows/quality.yml',
  navigationPolicy: 'frontend/src/lib/shell/navigation-policy.ts',
  navigationTest: 'frontend/tests/unit/navigation-policy.test.ts',
  plan: 'docs/implementation/plans/PLAN-025-frontend-mvp.md',
  backlog: 'docs/implementation/backlogs/PLAN-025-execution-backlog.md',
  discovery: 'docs/audits/discoveries/frontend-mvp-discovery-sdd.md',
  matrix: 'docs/governance/frontend-mvp-traceability-matrix.md',
  openapi: 'docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json',
};
const JORNADAS_FILES = {
  playwrightConfig: 'frontend/playwright.jornadas.config.ts',
  e2eTest: 'frontend/tests/jornadas-e2e/jornadas-compostas.spec.ts',
  realStack: 'frontend/tests/jornadas-e2e/real-stack.mjs',
  seed: 'frontend/tests/jornadas-e2e/seed_integrated.py',
  report: 'docs/audits/reports/frontend-mvp-imp-301-jornadas-compostas-report-2026-08-14.md',
  manifest: 'docs/audits/evidence/frontend-mvp-imp-301-protected-baseline.json',
  scopeScript: 'scripts/tests/test-imp-301-scope.js',
  packageJson: 'frontend/package.json',
  workflow: '.github/workflows/quality.yml',
  plan: 'docs/implementation/plans/PLAN-025-frontend-mvp.md',
  backlog: 'docs/implementation/backlogs/PLAN-025-execution-backlog.md',
  discovery: 'docs/audits/discoveries/frontend-mvp-discovery-sdd.md',
  matrix: 'docs/governance/frontend-mvp-traceability-matrix.md',
};
const CERTIFICATION_FILES = {
  certificationScript: 'frontend/tests/certification/ui-security-boundaries.mjs',
  report: 'docs/audits/reports/frontend-mvp-imp-302-ui-security-boundaries-report-2026-08-14.md',
  manifest: 'docs/audits/evidence/frontend-mvp-imp-302-protected-baseline.json',
  scopeScript: 'scripts/tests/test-imp-302-scope.js',
  packageJson: 'frontend/package.json',
  workflow: '.github/workflows/quality.yml',
  plan: 'docs/implementation/plans/PLAN-025-frontend-mvp.md',
  backlog: 'docs/implementation/backlogs/PLAN-025-execution-backlog.md',
  discovery: 'docs/audits/discoveries/frontend-mvp-discovery-sdd.md',
  matrix: 'docs/governance/frontend-mvp-traceability-matrix.md',
};
const FINAL_READINESS_FILES = {
  report: 'docs/audits/reports/frontend-mvp-final-readiness-report-2026-08-14.md',
  manifest: 'docs/audits/evidence/frontend-mvp-imp-303-protected-baseline.json',
  scopeScript: 'scripts/tests/test-imp-304-scope.js',
  workflow: '.github/workflows/quality.yml',
  plan: 'docs/implementation/plans/PLAN-025-frontend-mvp.md',
  backlog: 'docs/implementation/backlogs/PLAN-025-execution-backlog.md',
  discovery: 'docs/audits/discoveries/frontend-mvp-discovery-sdd.md',
  matrix: 'docs/governance/frontend-mvp-traceability-matrix.md',
  openapi: 'docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json',
};
function assertText(doc, text, context) {
  assert.ok(doc.includes(text), `${context}: contrato ausente: ${text}`);
}

function assertNormalizedText(doc, text, context) {
  const normalizedDoc = doc.replace(/\s+/g, ' ').trim();
  const normalizedText = text.replace(/\s+/g, ' ').trim();
  assert.ok(normalizedDoc.includes(normalizedText), `${context}: contrato ausente: ${text}`);
}

function readScaffold() {
  const source = Object.fromEntries(Object.entries(SCAFFOLD_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
  const sourceRoot = path.join(ROOT, 'frontend', 'src');
  const pending = [sourceRoot];
  const implementationFiles = [];
  while (pending.length) {
    const current = pending.pop();
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const absolute = path.join(current, entry.name);
      if (entry.isDirectory()) pending.push(absolute);
      else if (/\.(?:js|jsx|ts|tsx|css|mjs|cjs)$/.test(entry.name)) implementationFiles.push(absolute);
    }
  }
  source.implementation = implementationFiles
    .filter((file) => {
      const normalized = file.replace(/\\/g, '/');
      return !normalized.includes('/src/lib/api/')
        && !normalized.includes('/src/lib/bff/')
        && !normalized.includes('/src/lib/shell/')
        && !normalized.includes('/src/app/api/')
        && !normalized.includes('/src/app/app/')
        && !normalized.includes('/src/app/login/')
        && !normalized.includes('/src/app/session/')
        && !normalized.includes('/src/components/auth/')
        && !normalized.includes('/src/components/dashboard/')
        && !normalized.includes('/src/lib/dashboard/')
        && !normalized.includes('/src/components/devedores/')
        && !normalized.includes('/src/lib/devedores/')
        && !normalized.includes('/src/components/comercial/')
        && !normalized.includes('/src/lib/comercial/')
        && !normalized.includes('/src/components/contratos/')
        && !normalized.includes('/src/lib/contratos/')
        && !normalized.includes('/src/components/motor/')
        && !normalized.includes('/src/lib/motor/')
        && !normalized.includes('/src/components/cobranca/')
        && !normalized.includes('/src/lib/cobranca/')
        && !normalized.includes('/src/components/agenda/')
        && !normalized.includes('/src/lib/agenda/')
        && !normalized.includes('/src/components/iam/')
        && !normalized.includes('/src/lib/iam/')
        && !normalized.includes('/src/components/automacao/')
        && !normalized.includes('/src/lib/automacao/')
        && !normalized.includes('/src/components/shell/')
        && !normalized.includes('/src/components/lancamento/')
        && !normalized.includes('/src/lib/lancamento/')
        && !normalized.includes('/src/app/app/contratos/');
    })
    .sort()
    .map((file) => fs.readFileSync(file, 'utf8'))
    .join('\n');
  source.implementationPaths = implementationFiles.map((file) => path.relative(sourceRoot, file).replace(/\\/g, '/'));
  return source;
}

function readHarness() {
  return Object.fromEntries(Object.entries(HARNESS_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readFoundation() {
  const source = Object.fromEntries(Object.entries(FOUNDATION_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
  const sourceRoot = path.join(ROOT, 'frontend', 'src');
  const pending = [sourceRoot];
  const implementationFiles = [];
  while (pending.length) {
    const current = pending.pop();
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const absolute = path.join(current, entry.name);
      if (entry.isDirectory()) pending.push(absolute);
      else if (/\.(?:ts|tsx|css)$/.test(entry.name)) implementationFiles.push(absolute);
    }
  }
  source.implementation = implementationFiles
    .filter((file) => {
      const normalized = file.replace(/\\/g, '/');
      return !normalized.includes('/src/lib/api/')
        && !normalized.includes('/src/lib/bff/')
        && !normalized.includes('/src/lib/shell/')
        && !normalized.includes('/src/app/api/')
        && !normalized.includes('/src/app/app/')
        && !normalized.includes('/src/app/login/')
        && !normalized.includes('/src/app/session/')
        && !normalized.includes('/src/components/auth/')
        && !normalized.includes('/src/components/dashboard/')
        && !normalized.includes('/src/lib/dashboard/')
        && !normalized.includes('/src/components/devedores/')
        && !normalized.includes('/src/lib/devedores/')
        && !normalized.includes('/src/components/comercial/')
        && !normalized.includes('/src/lib/comercial/')
        && !normalized.includes('/src/components/contratos/')
        && !normalized.includes('/src/lib/contratos/')
        && !normalized.includes('/src/components/motor/')
        && !normalized.includes('/src/lib/motor/')
        && !normalized.includes('/src/components/cobranca/')
        && !normalized.includes('/src/lib/cobranca/')
        && !normalized.includes('/src/components/agenda/')
        && !normalized.includes('/src/lib/agenda/')
        && !normalized.includes('/src/components/iam/')
        && !normalized.includes('/src/lib/iam/')
        && !normalized.includes('/src/components/automacao/')
        && !normalized.includes('/src/lib/automacao/')
        && !normalized.includes('/src/components/shell/')
        && !normalized.includes('/src/components/lancamento/')
        && !normalized.includes('/src/lib/lancamento/')
        && !normalized.includes('/src/app/app/contratos/');
    })
    .sort()
    .map((file) => fs.readFileSync(file, 'utf8'))
    .join('\n');
  source.implementationPaths = implementationFiles
    .filter((file) => {
      const normalized = file.replace(/\\/g, '/');
      return !normalized.includes('/src/lib/api/')
        && !normalized.includes('/src/lib/bff/')
        && !normalized.includes('/src/lib/shell/')
        && !normalized.includes('/src/app/api/')
        && !normalized.includes('/src/app/app/')
        && !normalized.includes('/src/app/login/')
        && !normalized.includes('/src/app/session/')
        && !normalized.includes('/src/components/auth/')
        && !normalized.includes('/src/components/dashboard/')
        && !normalized.includes('/src/lib/dashboard/')
        && !normalized.includes('/src/components/devedores/')
        && !normalized.includes('/src/lib/devedores/')
        && !normalized.includes('/src/components/comercial/')
        && !normalized.includes('/src/lib/comercial/')
        && !normalized.includes('/src/components/contratos/')
        && !normalized.includes('/src/lib/contratos/')
        && !normalized.includes('/src/components/motor/')
        && !normalized.includes('/src/lib/motor/')
        && !normalized.includes('/src/components/cobranca/')
        && !normalized.includes('/src/lib/cobranca/')
        && !normalized.includes('/src/components/agenda/')
        && !normalized.includes('/src/lib/agenda/')
        && !normalized.includes('/src/components/iam/')
        && !normalized.includes('/src/lib/iam/')
        && !normalized.includes('/src/components/automacao/')
        && !normalized.includes('/src/lib/automacao/')
        && !normalized.includes('/src/components/shell/')
        && !normalized.includes('/src/components/lancamento/')
        && !normalized.includes('/src/lib/lancamento/')
        && !normalized.includes('/src/app/app/contratos/');
    })
    .map((file) => path.relative(sourceRoot, file).replace(/\\/g, '/'));
  return source;
}

function readOpenapiClient() {
  return Object.fromEntries(Object.entries(OPENAPI_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readBff() {
  return Object.fromEntries(Object.entries(BFF_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readShell() {
  return Object.fromEntries(Object.entries(SHELL_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readDashboard() {
  return Object.fromEntries(Object.entries(DASHBOARD_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readDevedores() {
  return Object.fromEntries(Object.entries(DEVEDORES_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readComercial() {
  return Object.fromEntries(Object.entries(COMERCIAL_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readContratos() {
  return Object.fromEntries(Object.entries(CONTRATOS_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readMotor() {
  return Object.fromEntries(Object.entries(MOTOR_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readCobranca() {
  return Object.fromEntries(Object.entries(COBRANCA_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readAgendaComunicacao() {
  return Object.fromEntries(Object.entries(AGENDA_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readFormatoBrasileiro() {
  return {
    modulo: read('frontend/src/lib/formato/brasileiro.ts'),
    teste: read('frontend/tests/unit/formato-brasileiro.test.ts'),
  };
}

function readBffErrorSanitization() {
  return Object.fromEntries(Object.entries(BFF_ERROR_SANITIZATION_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readRelatorios() {
  return Object.fromEntries(Object.entries(RELATORIOS_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readConfiguracoes() {
  return Object.fromEntries(Object.entries(CONFIGURACOES_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readIam() {
  return Object.fromEntries(Object.entries(IAM_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readAutomacao() {
  return Object.fromEntries(Object.entries(AUTOMACAO_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readJornadas() {
  return Object.fromEntries(Object.entries(JORNADAS_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readCertification() {
  return Object.fromEntries(Object.entries(CERTIFICATION_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function readFinalReadiness() {
  return Object.fromEntries(Object.entries(FINAL_READINESS_FILES).map(([key, rel]) => {
    const absolute = path.join(ROOT, rel);
    assert.ok(fs.existsSync(absolute), `${rel} ausente`);
    return [key, read(rel)];
  }));
}

function impBlocks(backlog) {
  const headings = [...backlog.matchAll(/^### (IMP-(\d{3})) -/gm)];
  return headings.map((heading, index) => {
    const next = index + 1 < headings.length ? headings[index + 1].index : backlog.indexOf('\n---', heading.index);
    const end = next === -1 ? backlog.length : next;
    return {
      id: heading[1],
      number: Number(heading[2]),
      text: backlog.slice(heading.index, end),
    };
  });
}

function certifiedOperationCount(matrix) {
  const section = matrix.split('# 3. Matriz de superficies')[1].split('\n---')[0];
  return section
    .split('\n')
    .filter((line) => line.startsWith('|') && !line.startsWith('|---'))
    .map((line) => line.split('|').map((cell) => cell.trim())[7])
    .filter((cell) => /^\d+$/.test(cell ?? ''))
    .map(Number)
    .reduce((total, value) => total + value, 0);
}

const contracts = {
  filesAndRegistry(source) {
    assertText(source.plan, '# PLAN-025 - Frontend MVP Transversal', 'PLAN H1');
    assertText(source.backlog, '# PLAN-025-EXEC - Backlog do Frontend MVP Transversal', 'backlog H1');
    assertText(source.us125, '**ID:** US-125', 'US-125');
    assertText(source.us126, '**ID:** US-126', 'US-126');
    assertText(source.report, '**ID:** PLAN-026', 'relatorio PLAN-026');
    const registry = JSON.parse(source.registry);
    assert.ok(registry.namespaces.PLAN.ultimo >= 26, 'Registry deve incluir PLAN-026');
    assert.ok(registry.namespaces.US.ultimo >= 126, 'Registry deve incluir US-126');
  },

  productDecision(source) {
    assertText(source.feature11, '**Versão:** 1.1.0', 'FEATURE-011 versionada');
    assertText(source.feature11, 'US-126', 'FEATURE-011 complementada');
    assertText(source.feature12, '**Versão:** 1.1.0', 'FEATURE-012 versionada');
    assertText(source.feature12, 'US-125', 'FEATURE-012 complementada');
    assertText(source.plan, 'Nao sera criada Capability chamada Frontend', 'sem Capability Frontend');
    assertText(source.plan, 'nao emitir Capability Frontend, EPIC tecnico ou nova Feature', 'sem artefato artificial');
    assert.ok(!/\bEPIC-011\b/.test(`${source.plan}\n${source.matrix}`), 'nao deve emitir EPIC-011');
    assert.ok(!/\bFEATURE-046\b/.test(`${source.plan}\n${source.matrix}`), 'nao deve emitir FEATURE-046');
  },

  matrix(source) {
    assert.strictEqual(certifiedOperationCount(source.matrix), 106, 'matriz deve somar 106 operacoes certificadas');
    assertText(source.matrix, '`GET /iam/contexto-atual` | 1 |', 'endpoint certificado contexto');
    assertText(source.matrix, '`GET /iam/permissoes` | 1 |', 'endpoint certificado catalogo');
    assert.ok(!source.matrix.includes('**desejado:**'), 'matriz nao pode manter endpoint implementado como desejado');
    for (const token of ['Product', 'EPIC', 'Feature', 'User Stories', 'Permissao RBAC', 'Cenario Playwright']) {
      assertText(source.matrix, token, 'cabecalho da matriz');
    }
    for (const status of ['400', '401', '403', '404', '409', '422', '5xx']) {
      assertText(source.matrix, `| ${status} |`, 'matriz de erros');
    }
  },

  gaps(source) {
    for (let number = 1; number <= 7; number += 1) {
      const marker = `## Lacuna ${number} -`;
      const start = source.plan.indexOf(marker);
      assert.ok(start >= 0, `${marker} ausente`);
      const next = source.plan.indexOf('\n## Lacuna ', start + marker.length);
      const block = source.plan.slice(start, next === -1 ? source.plan.indexOf('\n---', start) : next);
      assertText(block, '**Decisao:**', `lacuna ${number}`);
      assertText(block, '**Contrato desejado:**', `lacuna ${number}`);
      assertText(block, '**Teste antes da correcao:**', `lacuna ${number}`);
      assertText(block, '**Pacote:**', `lacuna ${number}`);
      assertText(block, '**Impacto:**', `lacuna ${number}`);
    }
    assertText(source.plan, 'IMP-276..IMP-283 foram executados', 'execucao do hardening');
  },

  backlog(source) {
    const blocks = impBlocks(source.backlog);
    assert.deepStrictEqual(blocks.map((block) => block.id), EXPECTED_IMPS, 'faixa IMP-274..IMP-304 deve estar completa e ordenada');
    for (const block of blocks) {
      for (const field of REQUIRED_FIELDS) assertText(block.text, `**${field}:**`, `${block.id} campo`);
      assert.match(block.text, /\*\*Status:\*\* (?:Planejado|Concluido)\./, `${block.id} status invalido`);
      const dependency = block.text.match(/^- \*\*Dependencias:\*\* (.+)$/m)?.[1] ?? '';
      for (const match of dependency.matchAll(/IMP-(\d{3})(?:\.\.IMP-(\d{3}))?/g)) {
        const first = Number(match[1]);
        const last = Number(match[2] ?? match[1]);
        assert.ok(first >= 274 && last <= 303, `${block.id} depende de IMP fora do PLAN-025`);
        assert.ok(last < block.number, `${block.id} depende de item futuro: ${match[0]}`);
      }
    }
    for (let number = 276; number <= 283; number += 1) {
      const block = blocks.find((item) => item.number === number);
      assertText(block.text, '**Status:** Concluido.', `IMP-${number} concluido`);
    }
    for (const number of [274, 275]) {
      const block = blocks.find((item) => item.number === number);
      assertNormalizedText(
        block.text,
        'fotografia historica anterior ao hardening, com 105 operacoes e os dois endpoints IAM apenas desejados',
        `IMP-${number} baseline historico`,
      );
      assertNormalizedText(
        block.text,
        'estado final apos IMP-283, com 107 operacoes e os dois endpoints IAM certificados',
        `IMP-${number} contrato final`,
      );
      assert.doesNotMatch(
        block.text.replace(/\s+/g, ' '),
        /estado (?:final|corrente)[^.;]*105 operacoes/i,
        `IMP-${number} nao pode tratar 105 como estado final ou corrente`,
      );
    }
    const scaffold = blocks.find((item) => item.number === 284);
    assertText(scaffold.text, '**Status:** Concluido.', 'IMP-284 concluido');
    const harness = blocks.find((item) => item.number === 285);
    assertText(harness.text, '**Status:** Concluido.', 'IMP-285 concluido');
    const design = blocks.find((item) => item.number === 286);
    assertText(design.text, '**Status:** Concluido.', 'IMP-286 concluido');
    const openapiClient = blocks.find((item) => item.number === 287);
    assertText(openapiClient.text, '**Status:** Concluido.', 'IMP-287 concluido');
    const bff = blocks.find((item) => item.number === 288);
    assertText(bff.text, '**Status:** Concluido.', 'IMP-288 concluido');
    const shell = blocks.find((item) => item.number === 289);
    assertText(shell.text, '**Status:** Concluido.', 'IMP-289 concluido');
    const dashboard = blocks.find((item) => item.number === 290);
    assertText(dashboard.text, '**Status:** Concluido.', 'IMP-290 concluido');
  },

  hardening(source) {
    const snapshot = JSON.parse(source.snapshot);
    const operations = Object.values(snapshot.paths).reduce(
      (total, pathItem) => total + Object.keys(pathItem).filter((method) => ['get', 'post', 'put', 'patch', 'delete'].includes(method)).length,
      0,
    );
    // O pino acompanha o snapshot vivo, que por contrato deve bater byte a byte
    // com o runtime. A matriz soma 105 e o contrato 106: PLAN-027/IMP-306
    // acrescentou POST /credit/carteiras/{id}/lancamentos, que ainda nao tem
    // jornada frontend propria, e a DR-004 tirou as duas operacoes de plano de
    // parcelas dos dois lados.
    assert.strictEqual(operations, 107, 'snapshot deve conter 107 operacoes');
    assert.strictEqual(Object.keys(snapshot.components.schemas).length, 135, 'snapshot deve conter 135 schemas');
    assert.ok(snapshot.paths['/iam/contexto-atual']?.get, 'snapshot deve publicar contexto atual');
    assert.ok(snapshot.paths['/iam/permissoes']?.get, 'snapshot deve publicar catalogo IAM');
    const snapshotHash = crypto.createHash('sha256').update(Buffer.from(source.snapshot, 'utf8')).digest('hex');
    assertText(source.report, snapshotHash, 'hash calculado do snapshot');
    assertText(source.report, 'IMP-284 continua **bloqueado**', 'decisao do scaffold');
  },

  gates(source) {
    for (const gate of REQUIRED_GATES) {
      assertText(source.plan, gate, 'gate PLAN');
      assertText(source.backlog, gate, 'gate backlog');
    }
    const packageJson = JSON.parse(source.packageJson);
    assertText(packageJson.scripts['docs:test'], 'node scripts/tests/test-plan-025-contracts.js', 'integracao docs:test');
  },

  scaffold(source = readScaffold()) {
    const packageJson = JSON.parse(source.packageJson);
    assert.strictEqual(packageJson.private, true, 'frontend deve ser pacote privado');
    assert.strictEqual(packageJson.type, 'module', 'configs TypeScript/ESM devem carregar sem warning');
    assert.strictEqual(packageJson.packageManager, 'npm@11.17.0', 'npm deve estar fixado');
    assert.strictEqual(packageJson.engines?.node, '24.19.0', 'Node.js LTS deve estar fixado');
    assert.strictEqual(packageJson.engines?.npm, '11.17.0', 'npm deve estar fixado no engines');
    for (const script of ['dev', 'lint', 'typecheck', 'build', 'start']) {
      assert.ok(packageJson.scripts?.[script], `script frontend ausente: ${script}`);
    }
    for (const artifact of ['playwright-report', 'test-results', 'coverage', 'blob-report']) {
      assertText(packageJson.scripts.lint, `--ignore-pattern ${artifact}`, `lint deve ignorar artifact ${artifact}`);
    }

    assert.deepStrictEqual(
      Object.keys(packageJson.dependencies ?? {}).sort(),
      ['next', 'react', 'react-dom', 'openapi-fetch', 'server-only', ...Object.keys(FOUNDATION_DEPENDENCIES), ...Object.keys(BFF_VERSIONS)].sort(),
    );
    assert.deepStrictEqual(
      Object.keys(packageJson.devDependencies ?? {}).sort(),
      [
        '@types/node',
        '@types/react',
        '@types/react-dom',
        'eslint',
        'eslint-config-next',
        'typescript',
        ...Object.keys(HARNESS_VERSIONS),
        ...Object.keys(FOUNDATION_DEV_DEPENDENCIES),
        'openapi-typescript',
      ].sort(),
    );
    for (const [name, version] of Object.entries(SCAFFOLD_VERSIONS)) {
      const actual = packageJson.dependencies?.[name] ?? packageJson.devDependencies?.[name];
      assert.strictEqual(actual, version, `${name} deve usar versao exata ${version}`);
    }
    assert.ok(!packageJson.overrides, 'peer overrides nao sao permitidos');
    assertNormalizedText(source.npmrc, 'engine-strict=true', 'toolchain deve falhar fechado');

    const packageLock = JSON.parse(source.packageLock);
    assert.strictEqual(packageLock.lockfileVersion, 3, 'lockfile frontend deve ser v3');
    assert.strictEqual(packageLock.packages?.['']?.name, packageJson.name, 'lockfile deve pertencer ao frontend');
    for (const [name, version] of Object.entries(SCAFFOLD_VERSIONS)) {
      const actual = packageLock.packages?.['']?.dependencies?.[name]
        ?? packageLock.packages?.['']?.devDependencies?.[name];
      assert.strictEqual(actual, version, `lockfile deve fixar ${name}`);
    }

    const tsconfig = JSON.parse(source.tsconfig);
    assert.strictEqual(tsconfig.compilerOptions?.strict, true, 'TypeScript strict obrigatorio');
    assert.strictEqual(tsconfig.compilerOptions?.allowJs, false, 'JavaScript sem check nao pode contornar o typecheck');
    assert.strictEqual(tsconfig.compilerOptions?.noUncheckedIndexedAccess, true, 'noUncheckedIndexedAccess obrigatorio');
    assert.strictEqual(tsconfig.compilerOptions?.exactOptionalPropertyTypes, true, 'exactOptionalPropertyTypes obrigatorio');
    assert.strictEqual(tsconfig.compilerOptions?.noEmit, true, 'typecheck nao pode emitir arquivos');

    assert.match(source.layout, /import\s+['\"]\.\/globals\.css['\"]/, 'layout importa CSS minimo');
    assertText(source.layout, 'export default function RootLayout', 'App Router layout');
    assertText(source.page, 'export default function Home', 'App Router page');
    assert.ok(!fs.existsSync(path.join(ROOT, 'frontend/pages')), 'Pages Router nao pode existir');
    assert.ok(!fs.existsSync(path.join(ROOT, 'frontend/pages')), 'Pages Router nao pode existir');

    const implementation = [source.implementation, source.nextConfig].join('\n');
    for (const forbidden of [
      /['\"]use server['\"]/i,
      /\bfetch\s*\(/i,
      /\/auth\//i,
      /\/iam\//i,
      /\/credit\//i,
      /\b(?:juros|mora|multa|amortiza|saldo|quitacao|renegocia)\w*/i,
    ]) assert.doesNotMatch(implementation, forbidden, `scaffold contem superficie antecipada: ${forbidden}`);
    assert.doesNotMatch(source.layout, /['\"]use client['\"]/, 'layout deve permanecer Server Component');
    assert.doesNotMatch(source.page, /['\"]use client['\"]/, 'pagina deve permanecer Server Component');
    assertNormalizedText(source.readme, 'Server Components por padrao', 'boundary RSC');
    assertNormalizedText(source.readme, 'o IMP-288 cria sessao JWE e transporte autenticado server-only', 'boundary BFF');
    assertNormalizedText(source.readme, 'shadcn/ui e tokens semanticos materializados no IMP-286', 'boundary shadcn');
    assertNormalizedText(source.readme, 'o cliente OpenAPI e gerado exclusivamente do snapshot certificado', 'boundary OpenAPI');
    assertNormalizedText(source.workflow, 'working-directory: frontend', 'CI frontend isolada');
    assertNormalizedText(source.workflow, 'node-version: "24.19.0"', 'CI Node fixado');
    assertText(source.workflow, 'node tests/toolchain-check.mjs', 'CI deve verificar toolchain multiplataforma');
    for (const command of ['npm ci --ignore-scripts', 'npm run lint', 'npm run typecheck', 'npm run build']) {
      assertText(source.workflow, command, `CI frontend: ${command}`);
    }
    for (const ignored of ['/frontend/node_modules/', '/frontend/.next/', '/frontend/.env*']) {
      assertText(source.gitignore, ignored, `gitignore frontend: ${ignored}`);
    }
  },

  scaffoldEvidence(source) {
    assertText(source.adr001, '> **Versão:** 1.2.0', 'versao corrente do ADR-001');
    assertText(source.adr001, 'Next.js App Router', 'adendo Next.js do ADR-001');
    assertText(source.adr001, 'Autoridade do adendo 1.1.0', 'autoridade do adendo ADR-001');
    assertText(source.scaffoldReport, '**Status:** IMP-284 concluido; IMP-285 nao iniciado', 'status do relatorio IMP-284');
    assertText(source.scaffoldReport, '26 de 26 casos', 'evidencia GREEN do scaffold');
    assertText(source.scaffoldReport, '107 operacoes, 133 schemas', 'OpenAPI preservado no relatorio');
    assertText(source.scaffoldReport, '37 arquivos comparados ao manifesto inicial; 0 divergencia', 'prova de escopo');
    assertText(source.scaffoldReport, 'fable:fable-judge', 'gate para IMP-285');
    const manifest = JSON.parse(source.scaffoldManifest);
    assert.strictEqual(Object.keys(manifest.files).length, 37, 'manifesto deve listar 37 arquivos protegidos');
    assert.strictEqual(manifest.head, 'e48cb72ee4f62428491e8b8c19a569611d83fca8', 'HEAD do baseline');
  },

  harness(source = readHarness()) {
    const harnessSource = Object.values(source).join('\n');
    assert.doesNotMatch(harnessSource, /\.(?:skip|only|todo)\s*\(/, 'harness nao pode conter skip, only ou todo');
    const packageJson = JSON.parse(source.packageJson);
    assert.deepStrictEqual(
      Object.keys(packageJson.dependencies ?? {}).sort(),
      ['next', 'react', 'react-dom', 'openapi-fetch', 'server-only', ...Object.keys(FOUNDATION_DEPENDENCIES), ...Object.keys(BFF_VERSIONS)].sort(),
      'harness nao pode antecipar dependencias runtime de IMP futuro',
    );
    assert.deepStrictEqual(
      Object.keys(packageJson.devDependencies ?? {}).sort(),
      [
        '@types/node',
        '@types/react',
        '@types/react-dom',
        'eslint',
        'eslint-config-next',
        'typescript',
        ...Object.keys(HARNESS_VERSIONS),
        ...Object.keys(FOUNDATION_DEV_DEPENDENCIES),
        'openapi-typescript',
      ].sort(),
      'harness nao pode antecipar dependencias de IMP futuro',
    );
    for (const [name, version] of Object.entries(HARNESS_VERSIONS)) {
      assert.strictEqual(packageJson.devDependencies?.[name], version, `${name} deve usar versao exata ${version}`);
    }
    for (const script of ['test:unit', 'test:component', 'test:contract', 'test:e2e', 'test:infrastructure', 'test:harness']) {
      assert.ok(packageJson.scripts?.[script], `script de harness ausente: ${script}`);
    }
    assertText(source.unitConfig, 'environment: "node"', 'Vitest unitario isolado');
    assertText(source.unitConfig, 'passWithNoTests: false', 'unit nao aceita zero testes');
    assertText(source.componentConfig, 'environment: "jsdom"', 'Vitest componente em jsdom');
    assertText(source.componentConfig, 'passWithNoTests: false', 'component nao aceita zero testes');
    assertText(source.contractConfig, 'environment: "node"', 'Vitest contrato isolado');
    assertText(source.contractConfig, 'passWithNoTests: false', 'contract nao aceita zero testes');
    assertText(source.unitSmoke, 'it(', 'unit smoke deve conter teste observavel');
    assertText(source.componentSmoke, 'it(', 'component smoke deve conter teste observavel');
    assertText(source.contractSmoke, 'it(', 'contract smoke deve conter teste observavel');
    assertText(source.e2eSmoke, 'test(', 'E2E smoke deve conter teste observavel');
    assertText(source.componentSetup, 'onUnhandledRequest: "error"', 'MSW deve falhar fechado');
    assertText(source.componentSetup, 'server.resetHandlers()', 'MSW deve limpar handlers');
    assertText(source.componentSetup, 'server.close()', 'MSW deve encerrar lifecycle');
    assertText(source.componentSmoke, 'userEvent.setup()', 'componente deve testar interacao real');
    assertText(source.componentSmoke, 'render(<Home />)', 'componente deve renderizar placeholder existente');
    assertText(source.componentSmoke, 'msw.harness.invalid/lifecycle', 'MSW deve usar recurso tecnico, nao backend ficticio');
    assert.ok(!source.componentSmoke.includes('/health'), 'MSW nao pode antecipar endpoint backend');
    assertText(source.componentSmoke, 'fetch("http://msw.harness.invalid/unhandled")', 'MSW deve testar request inesperada');
    assertText(source.componentSmoke, '.rejects.toThrow()', 'request inesperada deve falhar observavelmente');
    assertText(source.contractSmoke, 'frontend-mvp-backend-openapi.json', 'contrato deve ler snapshot oficial');
    assertText(source.contractSmoke, '107', 'contrato deve validar 107 operacoes');
    assertText(source.contractSmoke, '135', 'contrato deve validar 135 schemas');
    assert.ok(!/\sas\s+Record</.test(source.contractSmoke), 'contrato nao pode contornar narrowing com cast manual');
    assertText(source.playwrightConfig, 'reuseExistingServer: false', 'Playwright nao pode reutilizar servidor');
    assertText(source.playwrightConfig, 'screenshot: "only-on-failure"', 'screenshot diagnostica');
    assertText(source.e2eSmoke, 'getByRole("heading", { name: "TiaNet" })', 'E2E deve observar placeholder');
    assertText(source.e2eSmoke, 'page.on("console"', 'smoke E2E deve falhar por console error');
    assertText(source.infrastructureSmoke, 'postgres:16', 'infra deve subir PostgreSQL real descartavel');
    assertText(source.infrastructureSmoke, 'emprestimo.presentation.api.main:app', 'infra deve subir FastAPI real');
    // IMP-343: o literal 'health.status, "healthy"' deixou de valer quando o
    // /health passou a somar o worker aos checks — a stack de smoke nao sobe
    // worker, entao o status legitimo virou 'degraded'. A intencao da regra
    // continua: o smoke observa readiness REAL e nao aceita qualquer status.
    assertText(source.infrastructureSmoke, 'health.checks.database, "healthy"', 'infra deve observar readiness real do banco');
    assertText(source.infrastructureSmoke, 'STATUS_PRONTO.includes(health.status)', 'infra deve restringir o status aceito na readiness');
    // IMP-343: o smoke subia a API contra banco sem schema e chamava de ready.
    // Migrar antes de servir e o que qualquer ambiente real faz; sem isto, o
    // smoke volta a provar menos do que afirma.
    assertText(source.infrastructureSmoke, '"alembic", "upgrade", "head"', 'infra deve migrar antes de servir');
    assertText(source.toolchainCheck, 'v24.19.0', 'check multiplataforma de Node');
    assertText(source.toolchainCheck, '11.17.0', 'check multiplataforma de npm');
    for (const ignored of ['/test-results/', '/playwright-report/', '/coverage/']) {
      assertText(source.gitignore, ignored, `artifact deve ser ignorado: ${ignored}`);
    }
    for (const command of [
      'npm install --global npm@11.17.0 --ignore-scripts',
      'npm run test:unit',
      'npm run test:component',
      'npm run test:contract',
      'npx playwright install --with-deps chromium',
      'npm run test:e2e',
    ]) assertText(source.workflow, command, `CI harness: ${command}`);
    assertText(source.workflow, 'windows-latest', 'CI deve validar runner Windows');
    assertText(source.workflow, 'actions/upload-artifact@v4', 'CI deve publicar diagnosticos');
    assertText(source.workflow, 'node frontend/tests/infrastructure/real-stack-smoke.mjs', 'CI deve observar FastAPI/PostgreSQL reais');
  },

  harnessEvidence(source) {
    assertText(source.harnessReport, '**Status:** IMP-285 concluido; IMP-286 nao iniciado', 'status relatorio IMP-285');
    assertNormalizedText(source.harnessReport, '26 de 27 casos', 'evidencia RED do harness');
    assertNormalizedText(source.harnessReport, 'execucao remota nao foi observada', 'fronteira honesta de CI');
    assertText(source.harnessReport, 'PostgreSQL 16 descartavel', 'banco real observado');
    assertText(source.harnessReport, 'aplicacao FastAPI real', 'servidor real observado');
    assertText(source.harnessReport, 'fable:fable-judge', 'gate do IMP-286');
    const manifest = JSON.parse(source.harnessManifest);
    assert.strictEqual(Object.keys(manifest.files).length, 59, 'baseline IMP-285 deve conter 59 caminhos');
    assert.strictEqual(manifest.predecessor.sha256, '72fcb868bf1cf0d9fa3fd86d53804bdfad783e5eb4bcdc8b4617e246d59b5e02');
    assert.ok(manifest.allowedNewPaths.every((item) => !item.endsWith('/')), 'allowlist nova deve usar somente paths exatos');
    for (const forbidden of ['src/', 'migrations/', 'tests/', 'docs/product/', 'docs/governance/registry/', 'docs/governance/contracts/openapi/']) {
      assert.ok(!manifest.mutableBaselinePaths.some((item) => item.startsWith(forbidden)), `mutable nao pode incluir ${forbidden}`);
      assert.ok(!manifest.allowedNewPaths.some((item) => item.startsWith(forbidden)), `novo nao pode incluir ${forbidden}`);
    }
  },

  foundationEvidence(source) {
    assertText(source.discovery, '**Vers?o:** 3.2.0', 'Discovery vivo preserva historico da foundation');
    assertText(source.foundationReport, '**Status:** IMP-286 concluido; IMP-287 nao iniciado e sob gate adversarial', 'status relatorio IMP-286');
    assertNormalizedText(source.foundationReport, '37 de 38 casos passaram', 'evidencia RED da foundation');
    assertText(source.foundationReport, '`frontend/components.json ausente`', 'motivo RED esperado');
    assertNormalizedText(source.foundationReport, 'execucao remota nao foi observada', 'fronteira honesta de CI');
    assertNormalizedText(source.foundationReport, 'screenshots sao diagnosticos deterministas', 'fronteira da evidencia visual');
    assertText(source.foundationReport, 'IMP-287 continua Planejado', 'gate do IMP-287');

    const manifest = JSON.parse(source.foundationManifest);
    assert.strictEqual(Object.keys(manifest.files).length, 74, 'baseline IMP-286 deve conter 74 paths');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 14, 'mutable IMP-286 deve ser exato');
    assert.strictEqual(manifest.allowedNewPaths.length, 23, 'allowlist IMP-286 deve ser exata');
    assert.strictEqual(manifest.predecessor.sha256, 'aad63efd04a284ef2417a49a1b13bbd02acaab6bd5cba0b208c1e3299ef660a2');
    for (const list of [manifest.mutableBaselinePaths, manifest.allowedNewPaths]) {
      assert.ok(list.every((item) => !item.endsWith('/')), 'manifesto IMP-286 nao aceita diretorio');
      for (const forbidden of ['src/', 'migrations/', 'tests/', 'docs/product/', 'docs/governance/registry/', 'docs/governance/contracts/openapi/']) {
        assert.ok(!list.some((item) => item.startsWith(forbidden)), `manifesto IMP-286 nao pode incluir ${forbidden}`);
      }
    }

    for (const [relative, width, minimumHeight, expectedHash] of [
      ['docs/audits/evidence/frontend-mvp-imp-286-foundation-desktop.png', 1440, 900, '1c830b1f19c316fa326047d5b328a9a172581175eb07003647415bfe52c0775d'],
      ['docs/audits/evidence/frontend-mvp-imp-286-foundation-mobile.png', 390, 844, 'edd3bbed6288e84dc69d01a7b13d070070627730ad78728fbb0992867f4528a8'],
    ]) {
      const image = fs.readFileSync(path.join(ROOT, relative));
      assert.deepStrictEqual([...image.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10], `${relative} deve ser PNG`);
      assert.strictEqual(image.readUInt32BE(16), width, `${relative} deve preservar largura governada`);
      assert.ok(image.readUInt32BE(20) >= minimumHeight, `${relative} deve preservar altura minima governada`);
      const actualHash = crypto.createHash('sha256').update(image).digest('hex');
      assert.strictEqual(actualHash, expectedHash, `${relative} deve preservar SHA-256 observado`);
      assertText(source.foundationReport, expectedHash, `${relative} deve ter SHA publicado`);
    }
  },

  foundation(source = readFoundation()) {
    const packageJson = JSON.parse(source.packageJson);
    for (const [name, version] of Object.entries(FOUNDATION_DEPENDENCIES)) {
      assert.strictEqual(packageJson.dependencies?.[name], version, `${name} deve usar versao exata ${version}`);
    }
    for (const [name, version] of Object.entries(FOUNDATION_DEV_DEPENDENCIES)) {
      assert.strictEqual(packageJson.devDependencies?.[name], version, `${name} deve usar versao exata ${version}`);
    }
    for (const script of ['test:a11y', 'test:visual']) {
      assert.ok(packageJson.scripts?.[script], `script foundation ausente: ${script}`);
    }
    const allVersions = [...Object.values(packageJson.dependencies ?? {}), ...Object.values(packageJson.devDependencies ?? {})];
    assert.ok(allVersions.every((version) => !/^[~^*]|\b(?:latest|next)\b/.test(version)), 'foundation exige pins exatos');
    for (const forbidden of ['react-hook-form', 'zod', '@tanstack/react-query', 'swr']) {
      assert.ok(!packageJson.dependencies?.[forbidden] && !packageJson.devDependencies?.[forbidden], `IMP futuro antecipado: ${forbidden}`);
    }

    const components = JSON.parse(source.componentsJson);
    assert.strictEqual(components.rsc, true, 'shadcn deve preservar Server Components');
    assert.strictEqual(components.tsx, true, 'shadcn deve gerar TSX');
    assert.strictEqual(components.tailwind?.cssVariables, true, 'shadcn deve usar CSS variables');
    assert.strictEqual(components.tailwind?.css, 'src/app/globals.css', 'shadcn deve apontar para o CSS governado');
    assert.strictEqual(components.aliases?.components, '@/components', 'alias shadcn de componentes');
    assertText(source.postcssConfig, '"@tailwindcss/postcss": {}', 'PostCSS oficial Tailwind v4');
    assertText(source.globals, '@import "tailwindcss"', 'Tailwind CSS-first');
    for (const token of [
      '--background:', '--foreground:', '--card:', '--muted:', '--border:', '--input:', '--ring:',
      '--primary:', '--destructive:', '--success:', '--warning:', '--information:', '--font-sans:',
      '--space-', '--size-', '--radius-', '--shadow-', '--focus-', '--motion-',
    ]) assertText(source.globals, token, `token semantico ${token}`);
    for (const behavior of ['prefers-reduced-motion', ':focus-visible', 'forced-colors']) {
      assertText(source.globals, behavior, `comportamento acessivel ${behavior}`);
    }

    assertText(source.button, 'cva(', 'Button deve usar variantes explicitas');
    assertText(source.button, 'VariantProps', 'Button deve expor variantes tipadas');
    assert.doesNotMatch(source.button, /(?:isDestructive|isPending|isLoading)\??:/, 'Button nao pode proliferar modos booleanos');
    for (const state of [
      'LoadingState', 'EmptyState', 'ErrorState', 'SuccessState', 'PermissionDeniedState', 'NotFoundState',
    ]) assertText(source.feedback, state, `estado explicito ${state}`);
    assertText(source.feedback, 'aria-live="polite"', 'estado assincrono deve usar live region');
    assertText(source.feedback, 'role="alert"', 'erro deve ser anunciado');
    assertText(source.overflow, 'tabIndex={0}', 'overflow deve ser navegavel por teclado');
    assertText(source.overflow, 'aria-label', 'overflow deve ter nome acessivel');
    assertText(source.destructiveDialog, 'Dialog', 'acao destrutiva deve usar Dialog acessivel');
    assertText(source.showcase, 'PendingButton', 'pending deve ser variante explicita, nao boolean soup');
    assertText(source.page, 'FoundationShowcase', 'rota raiz deve ser somente showcase tecnico');
    assertText(source.layout, 'Pular para o conteudo', 'layout deve oferecer skip link');

    const componentSources = [source.button, source.alert, source.card, source.dialog, source.input, source.label, source.skeleton, source.feedback, source.showcase, source.overflow].join('\n');
    assert.doesNotMatch(componentSources, /#[0-9a-f]{3,8}\b/i, 'componentes nao podem conter cores hardcoded');
    assert.doesNotMatch(source.implementation, /\bfetch\s*\(|\/auth\/|\/iam\/|\/credit\/|\b(?:juros|mora|multa|amortiza|saldo|quitacao|renegocia)\w*/i, 'foundation nao pode antecipar API/auth/financeiro');
    const clientFiles = source.implementationPaths.filter((relative) => {
      const absolute = path.join(ROOT, 'frontend', 'src', relative);
      return /['"]use client['"]/.test(fs.readFileSync(absolute, 'utf8'));
    }).sort();
    assert.deepStrictEqual(
      clientFiles,
      ['components/configuracoes-financeiras/configuracoes-actions.client.tsx', 'components/foundation/destructive-dialog-demo.tsx', 'components/ui/dialog.tsx', 'components/ui/sheet.tsx'],
      'Client Components devem ficar limitados ao dialogo interativo',
    );

    assertText(source.componentTest, 'userEvent.setup()', 'component test deve exercitar interacao real');
    assertText(source.componentTest, 'getByRole', 'component test deve consultar semantica');
    assertText(source.axeTest, 'AxeBuilder', 'axe deve executar no Chromium real');
    assertText(source.axeTest, 'critical', 'axe deve bloquear impacto critico');
    assertText(source.axeTest, 'serious', 'axe deve bloquear impacto serio');
    assertText(source.e2eTest, '1440', 'evidencia desktop deve ser governada');
    assertText(source.e2eTest, '390', 'evidencia mobile deve ser governada');
    assertText(source.e2eTest, 'testInfo.attach', 'screenshots devem ser artifacts diagnosticos');
    assertText(source.e2eTest, 'reducedMotion', 'motion reduzido deve ser observado');
    assert.strictEqual(
      (source.e2eTest.match(/await expect\(dialog\)\.toBeHidden\(\)/g) ?? []).length,
      2,
      'os dois fechamentos de Dialog devem aguardar estado oculto',
    );
    assert.strictEqual(
      (source.e2eTest.match(/await expect\(dialog\)\.toBeHidden\(\);\s+await expect\(trigger\)\.toBeFocused\(\);/g) ?? []).length,
      2,
      'os dois fechamentos de Dialog devem observar retorno de foco antes de continuar',
    );
    for (const browserTest of [source.e2eTest, source.axeTest]) {
      assertText(browserTest, 'page.on("console"', 'foundation deve falhar por console error');
      assertText(browserTest, 'page.on("pageerror"', 'foundation deve falhar por pageerror');
    }
    assertText(source.playwrightConfig, 'reuseExistingServer: false', 'servidor visual nao pode ser reutilizado');
    assertText(source.workflow, 'npm run test:a11y', 'CI deve executar axe');
    assertText(source.workflow, 'npm run test:visual', 'CI deve gerar screenshots foundation');
    for (const ignored of ['/test-results/', '/playwright-report/', '/coverage/', '/blob-report/']) {
      assertText(source.gitignore, ignored, `artifact deve ser ignorado: ${ignored}`);
    }
  },

  openapiClient(source = readOpenapiClient()) {
    const packageJson = JSON.parse(source.packageJson);
    assert.strictEqual(packageJson.dependencies?.['openapi-fetch'], OPENAPI_VERSIONS['openapi-fetch']);
    assert.strictEqual(packageJson.dependencies?.['server-only'], OPENAPI_VERSIONS['server-only']);
    assert.strictEqual(packageJson.devDependencies?.['openapi-typescript'], OPENAPI_VERSIONS['openapi-typescript']);
    assert.strictEqual(packageJson.scripts?.['api:generate'], 'node scripts/openapi-codegen.mjs --write');
    assert.strictEqual(packageJson.scripts?.['api:check'], 'node scripts/openapi-codegen.mjs --check');
    assertText(packageJson.scripts?.['test:contract'] ?? '', 'npm run api:check', 'contract roda drift check');
    assertText(packageJson.scripts?.['test:contract'] ?? '', 'npm run typecheck', 'contract executa negativos de tipo');

    assertText(source.generated, 'export interface paths', 'paths gerados do OpenAPI');
    assertText(source.generated, 'export interface components', 'components gerados do OpenAPI');
    assertText(source.generated, 'This file was auto-generated by IMP-287. Do not edit manually.', 'header gerado');
    assertText(
      source.generated,
      '23d8d91f5f5890ef5ca010d1fc45a458458e5028042c80e7e15dbf82052af76a',
      'SHA governado no gerado',
    );
    assertText(source.generated, 'AuthLoginRequest:', 'AuthLoginRequest gerado');
    assertText(source.generated, 'AuthRefreshRequest:', 'AuthRefreshRequest gerado');
    assertText(source.generated, 'ContextoOperacionalResponse:', 'contexto gerado');
    assertText(source.generated, 'PermissoesCatalogoResponse:', 'catalogo gerado');
    assertText(source.generated, 'ErroResponse:', 'erro gerado');

    assert.match(source.client, /^import "server-only";/, 'cliente deve ser fail-closed no servidor');
    assertText(source.client, 'createClient<paths>({ ...options, baseUrl })', 'factory preserva paths gerados');
    assertText(source.client, 'import type { paths } from "./openapi.generated"', 'cliente importa paths gerados');
    assert.doesNotMatch(source.client, /\b(?:Authorization|Bearer|cookie|refresh|Idempotency-Key|correlation|ApiProblem|process\.env|NEXT_PUBLIC_|fetch\s*\()/i, 'cliente nao antecipa IMP-288');
    assert.doesNotMatch(source.client, /\bany\b|\sas\s|@ts-(?:ignore|expect-error)|<unknown>/, 'cliente nao contorna tipos');
    assert.doesNotMatch(source.client, /\b(?:interface|type)\s+(?:Auth|Contexto|Permissao|Erro)/, 'cliente nao duplica schemas');

    assertText(source.codegen, 'EXPECTED_SNAPSHOT_SHA256', 'codegen fixa hash do snapshot');
    assertText(source.codegen, 'alphabetize: true', 'codegen alfabetizado');
    assertText(source.codegen, 'immutable: true', 'codegen imutavel');
    assertText(source.codegen, 'canonicalizeLineEndings(actual) !== expected', 'check neutraliza EOL de checkout Windows');
    assertText(source.codegen, 'mode !== "--write" && mode !== "--check"', 'modos write/check separados');
    assert.doesNotMatch(source.codegen, /https?:\/\//, 'codegen nao usa fonte remota');

    for (const text of ['AuthLoginRequest', 'AuthRefreshRequest', 'ContextoOperacionalResponse', 'PermissoesCatalogoResponse', 'ErroResponse']) {
      assertText(source.contractTest, text, `teste contratual cobre ${text}`);
    }
    for (const text of ['toHaveLength(63)', 'required).toBe(true)', 'minLength: 1, maxLength: 255', 'toBe(107)', 'toHaveLength(135)']) {
      assertText(source.contractTest, text, `teste contratual cobre ${text}`);
    }
    assertText(source.workflow, 'npm run api:check', 'CI bloqueia drift OpenAPI');
    assertText(source.workflow, 'fetch-depth: 0', 'CI disponibiliza o commit-base do escopo');
    assertText(source.scopeScript, '`${manifest.head}...HEAD`', 'scope inclui delta commitado desde o baseline');
    assertText(source.scopeScript, '...worktreePaths', 'scope inclui mudancas locais ainda nao commitadas');
    assert.doesNotMatch(source.workflow, /node scripts\/tests\/test-imp-28[4-7]-scope\.js/, 'CI nao executa gate historico obsoleto');
  },

  openapiEvidence(source) {
    assertText(source.plan, '**Versao:** 3.1.0', 'PLAN versionado apos IMP-298');
    assertText(source.plan, 'Frontend MVP concluido localmente', 'status PLAN corrente');
    assertText(source.backlog, '**Versao:** 3.1.0', 'backlog versionado apos IMP-298');
    assertText(source.backlog, '### IMP-287 - Gerar cliente OpenAPI e gate de drift', 'IMP-287 no backlog');
    assertText(source.backlog, '- **Status:** Concluido.', 'IMP concluido no backlog');
    const imp288 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-288');
    assertText(imp288?.text ?? '', '- **Status:** Concluido.', 'IMP-288 concluido');
    const imp289 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-289');
    assertText(imp289?.text ?? '', '- **Status:** Concluido.', 'IMP-289 concluido');
    assertText(source.discovery, '**Vers?o:** 3.2.0', 'Discovery versionado apos IMP-298');
    assertText(source.discovery, '107 operações e conjuntos obrigatórios', 'Discovery corrente usa 107');
    assertText(source.discovery, 'fotografia histórica pré-hardening', 'Discovery preserva baseline 105');
    assertText(source.discovery, 'fotografia histórica pré-scaffold', 'Discovery rotula ausencia de frontend como historica');
    assert.doesNotMatch(source.discovery, /Não existe aplicação frontend[\s\S]{0,180}estado\s+atual/, 'Discovery nao pode negar o frontend corrente');
    assertText(source.plan, '`npm run api:check` com comparacao de bytes canonicos LF', 'PLAN descreve o check implementado');
    assert.doesNotMatch(source.plan, /openapi-typescript --check/, 'PLAN nao promete flag vendor nao executada');
    assertText(source.matrix, '**Versao:** 3.9.0', 'matriz versionada apos IMP-298');
    assertText(source.openapiReport, 'RED: 53 de 54', 'relatorio preserva RED');
    assertText(source.openapiReport, 'fable:fable-judge', 'relatorio exige judge antes do IMP-288');

    const manifest = JSON.parse(source.openapiManifest);
    const predecessorPath = path.join(ROOT, manifest.predecessor.path);
    const predecessorHash = crypto.createHash('sha256').update(fs.readFileSync(predecessorPath)).digest('hex');
    assert.strictEqual(manifest.predecessor.sha256, predecessorHash, 'manifesto IMP-287 encadeia IMP-286');
    assert.strictEqual(Object.keys(manifest.files).length, 97, 'baseline IMP-287 deve conter 97 paths');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 9, 'allowlist mutavel IMP-287 exata');
    assert.strictEqual(manifest.allowedNewPaths.length, 7, 'allowlist nova IMP-287 exata');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist nova usa paths exatos');
    for (const forbidden of ['src/', 'migrations/', 'tests/', 'docs/product/', 'docs/governance/registry/', 'docs/governance/contracts/openapi/']) {
      assert.ok(!manifest.mutableBaselinePaths.some((relative) => relative.startsWith(forbidden)), `mutable nao inclui ${forbidden}`);
      assert.ok(!manifest.allowedNewPaths.some((relative) => relative.startsWith(forbidden)), `novo nao inclui ${forbidden}`);
    }
  },

  bff(source = readBff()) {
    const packageJson = JSON.parse(source.packageJson);
    assert.strictEqual(packageJson.dependencies?.jose, BFF_VERSIONS.jose, 'jose deve usar versao exata');
    assertText(packageJson.scripts?.['test:bff'] ?? '', 'vitest.bff.config.ts', 'script BFF dedicado');
    assertText(packageJson.scripts?.['test:harness'] ?? '', 'npm run test:bff', 'harness inclui BFF');
    assert.doesNotMatch(source.envExample, /^NEXT_PUBLIC_[A-Z0-9_]*=/m, 'segredo nao pode ser NEXT_PUBLIC');
    for (const module of [source.session, source.backend, source.client]) {
      assert.match(module, /^import "server-only";/, 'modulo sensivel deve importar server-only');
      assert.doesNotMatch(module, /\blocalStorage\b|\bsessionStorage\b|\bindexedDB\b|NEXT_PUBLIC_/i, 'token nao pode chegar ao browser');
      assert.doesNotMatch(
        module,
        /:\s*any\b|\bas\s+any\b|<any>|@ts-(?:ignore|expect-error)/,
        'BFF nao contorna tipos',
      );
    }
    assertText(source.session, 'new EncryptJWT', 'sessao usa JWE madura');
    assertText(source.session, 'A256GCM', 'sessao usa AEAD A256GCM');
    for (const token of ['httpOnly: true', 'sameSite: "lax"', 'secure: config.production', 'path: "/"']) {
      assertText(source.session, token, `cookie governa ${token}`);
    }
    assertText(source.session, 'FRONTEND_SESSION_KEY', 'secret server-only obrigatorio');
    assert.doesNotMatch(source.session, /(?:secret|key)\s*[:=]\s*["'][^"']{8,}["']/i, 'secret nao pode ter default');
    assertText(source.session, 'origin !== config.origin', 'Origin exata');
    assertText(source.session, 'csrf !== CSRF_HEADER_VALUE', 'CSRF fail-closed');
    assertText(source.backend, 'createHash("sha256")', 'single-flight nao usa refresh bruto como chave');
    assertText(source.backend, 'finally', 'single-flight limpa estado transitorio');
    assertText(source.backend, 'this.active.size >= this.maximum', 'single-flight possui limite');
    assertText(source.backend, 'IDEMPOTENCY_PATTERN.test(key)', 'retry de mutacao exige idempotencia valida');
    assertText(source.backend, 'new URL(request.url).origin !== new URL(backendUrl).origin', 'Bearer fica restrito ao backend governado');
    assertText(source.backend, 'original.clone()', 'retry preserva request clonado');
    assertText(source.backend, 'if (firstResponse.status !== 401)', 'refresh apenas em 401');
    assertText(source.backend, 'if (replayResponse.status === 401)', 'segundo 401 encerra sessao');
    assertText(source.backend, 'X-Correlation-ID', 'correlation propagada');
    assertNormalizedText(
      source.backend,
      `function responseCorrelationId(response: Response, fallbackCorrelationId: string): string {
        const receivedCorrelation = response.headers.get("X-Correlation-ID");
        return receivedCorrelation && CORRELATION_PATTERN.test(receivedCorrelation)
          ? receivedCorrelation
          : fallbackCorrelationId;
      }`,
      'correlation de resposta aceita backend valido e preserva fallback outbound',
    );
    assert.doesNotMatch(
      source.backend,
      /correlationId\(result\.response\.headers\.get\("X-Correlation-ID"\)\s*\?\?\s*requestCorrelation\)/,
      'resposta 2xx nao pode gerar terceiro correlation ID',
    );
    assert.strictEqual(
      (source.backend.match(/responseCorrelationId\(result\.response, requestCorrelation\)/g) ?? []).length,
      2,
      'login e logout reutilizam o helper de correlation de resposta',
    );
    assertText(
      source.backend,
      'const selectedCorrelationId = responseCorrelationId(response, fallbackCorrelationId);',
      'tratamento de erro reutiliza o helper de correlation de resposta',
    );
    assertText(
      source.backend,
      'Response.json({ authenticated: true, correlationId: returnedCorrelation }, { status: 200, headers: responseHeaders(returnedCorrelation) })',
      'login usa o mesmo correlation no header e corpo publico',
    );
    assertText(
      source.backend,
      'new Response(null, { status: 204, headers: responseHeaders(returnedCorrelation) })',
      'logout usa o correlation selecionado no header',
    );
    assertText(source.bffTest, 'login 200 com correlation backend $label', 'suite cobre correlation de login valido, invalido e ausente');
    assertText(source.bffTest, 'logout 2xx com correlation backend $label', 'suite cobre correlation de logout valido, invalido e ausente');
    const correlationCases = source.bffTest.match(
      /const RESPONSE_CORRELATION_CASES = \[([\s\S]*?)\] as const;/,
    );
    assert.ok(correlationCases, 'fixture parametrizada de correlation deve existir');
    const expectedCorrelationCases = `const RESPONSE_CORRELATION_CASES = [
      { label: "valido", backendCorrelation: "corr-backend-valid-288", expected: "corr-backend-valid-288" },
      { label: "invalido", backendCorrelation: "correlation invalido", expected: CORRELATION },
      { label: "ausente", backendCorrelation: undefined, expected: CORRELATION },
    ] as const;`;
    assert.strictEqual(
      correlationCases[0].replace(/\s+/g, ' ').trim(),
      expectedCorrelationCases.replace(/\s+/g, ' ').trim(),
      'fixture de correlation deve preservar os tres tuples semanticos exatos e sua ordem',
    );
    const correlationLabels = [...correlationCases[1].matchAll(/label: "([^"]+)"/g)]
      .map((match) => match[1]);
    assert.deepStrictEqual(
      correlationLabels,
      ['valido', 'invalido', 'ausente'],
      'fixture de correlation deve conter exatamente valido, invalido e ausente',
    );
    assert.strictEqual(
      (source.bffTest.match(/it\.each\(RESPONSE_CORRELATION_CASES\)\(/g) ?? []).length,
      2,
      'login e logout devem executar a fixture completa de correlation',
    );
    assert.doesNotMatch(
      source.bffTest,
      /it\.each\(RESPONSE_CORRELATION_CASES\s*\./,
      'parametrizacao de correlation nao pode reduzir ou transformar a fixture',
    );
    assertText(source.backend, 'class ApiProblem', 'ApiProblem tipado');
    for (const field of ['status: number', 'codigo: string', 'mensagem: string', 'correlationId: string']) {
      assertText(source.backend, field, `ApiProblem preserva ${field}`);
    }
    assertText(source.backend, 'status === 404', '404 neutralizado');
    assert.doesNotMatch(source.backend, /Response\.json\(\{[^}]*?(?:accessToken|refreshToken)/s, 'BFF nao serializa token');
    assert.doesNotMatch(
      [source.session, source.backend, source.loginRoute, source.logoutRoute].join('\n'),
      /\b(?:juros|mora|multa|amortiza|saldo|quitacao|renegocia)\w*/i,
      'BFF nao calcula regra financeira',
    );
    assertText(source.loginRoute, 'await cookies()', 'login usa cookies assincronos App Router');
    assertText(source.logoutRoute, 'await cookies()', 'logout usa cookies assincronos App Router');
    assert.ok(!fs.existsSync(path.join(ROOT, 'frontend/src/app/api/auth/refresh/route.ts')), 'refresh nao pode ser superficie publica');
    const routeFiles = [];
    const routeRoot = path.join(ROOT, 'frontend/src/app/api');
    const pending = [routeRoot];
    while (pending.length) {
      const current = pending.pop();
      for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
        const absolute = path.join(current, entry.name);
        if (entry.isDirectory()) pending.push(absolute);
        else if (entry.name === 'route.ts') routeFiles.push(path.relative(ROOT, absolute).replace(/\\/g, '/'));
      }
    }
    assert.deepStrictEqual(routeFiles.sort(), [
      'frontend/src/app/api/auth/bootstrap/route.ts',
      'frontend/src/app/api/auth/login/route.ts',
      'frontend/src/app/api/auth/logout/route.ts',
    ]);
    for (const testSource of [source.sessionTest, source.bffTest]) {
      assert.doesNotMatch(testSource, /\.skip\b|\.todo\b|\.only\b/, 'BFF nao aceita testes ignorados');
    }
    for (const text of ['single-flight', 'Idempotency-Key', 'Origin', 'CSRF', '404', 'timeout']) {
      assertText(source.bffTest + source.sessionTest, text, `suite BFF cobre ${text}`);
    }
    assertText(source.workflow, 'npm run test:bff', 'CI executa suite BFF');
    assert.doesNotMatch(source.workflow, /node scripts\/tests\/test-imp-287-scope\.js/, 'CI nao executa gate historico obsoleto');
    assertText(source.scopeScript, '`${manifest.head}...HEAD`', 'scope suporta checkout limpo');
    assertText(source.scopeScript, '...worktreePaths', 'scope inclui worktree local');
    const manifest = JSON.parse(source.manifest);
    const predecessorPath = path.join(ROOT, manifest.predecessor.path);
    const predecessorHash = crypto.createHash('sha256').update(fs.readFileSync(predecessorPath)).digest('hex');
    assert.strictEqual(manifest.predecessor.sha256, predecessorHash, 'manifesto IMP-288 encadeia IMP-287');
    assert.strictEqual(Object.keys(manifest.files).length, 104, 'baseline IMP-288 possui 104 paths');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 11, 'allowlist mutavel IMP-288 exata');
    assert.strictEqual(manifest.allowedNewPaths.length, 12, 'allowlist nova IMP-288 exata');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist IMP-288 usa paths exatos');
    for (const forbidden of ['src/', 'migrations/', 'tests/', 'docs/product/', 'docs/governance/registry/', 'docs/governance/contracts/openapi/']) {
      assert.ok(!manifest.mutableBaselinePaths.some((relative) => relative.startsWith(forbidden)), `mutable IMP-288 nao inclui ${forbidden}`);
      assert.ok(!manifest.allowedNewPaths.some((relative) => relative.startsWith(forbidden)), `novo IMP-288 nao inclui ${forbidden}`);
    }
    assertText(source.report, '67/68', 'relatorio preserva RED canonico');
    assertText(source.report, 'processo/isolate Next', 'relatorio limita single-flight');
    assertText(source.report, 'execução remota não foi observada', 'relatorio nao inventa CI remota');
    assertText(docs.plan, '**Versao:** 3.1.0', 'PLAN corrente apos IMP-298');
    assertText(docs.backlog, '**Versao:** 3.1.0', 'backlog corrente apos IMP-298');
    assertText(docs.discovery, '**Vers?o:** 3.2.0', 'Discovery corrente apos IMP-298');
    assertText(docs.matrix, '**Versao:** 3.9.0', 'matriz corrente apos IMP-298');
  },

  dashboard(source = readDashboard()) {
    const packageJson = JSON.parse(source.packageJson);
    const manifest = JSON.parse(source.manifest);
    const combined = [source.component, source.loader, source.policy, source.page].join('\n');
    const fourPaths = [
      '/credit/carteiras/{carteira_id}/relatorios/resumo',
      '/credit/carteiras/{carteira_id}/relatorios/vencimentos',
      '/credit/agenda',
      '/credit/cobrancas/casos',
    ];
    assert.match(source.loader, /^import "server-only";/, 'loader Dashboard deve ser server-only');
    assertText(source.currentContext, 'cache(async () =>', 'contexto deve ser memoizado por request');
    assertText(source.currentContext, 'loadOperationalContext(await cookies()', 'contexto vem do proprio Principal');
    for (const endpoint of fourPaths) assertText(source.loader, endpoint, `loader usa ${endpoint}`);
    for (const permission of ['relatorios.operacionais.ler', 'agenda.ler', 'cobranca.caso.ler']) {
      assertText(source.policy + source.loader, permission, `RBAC exato ${permission}`);
    }
    assertText(source.loader, 'carteiraId = context.carteira_padrao.id', 'Carteira vem do contexto US-125');
    assertText(source.loader, 'cache: "no-store"', 'Dashboard nao reutiliza resposta entre sessoes');
    assertText(source.loader, 'Promise<DashboardSectionResult', 'secoes iniciam como Promises independentes');
    assertText(source.loader, 'value.data_referencia === referenceDate', 'relatorios ecoam a data solicitada');
    assertText(source.loader, 'result.response.status !== 200', 'somente 200 e sucesso contratual');
    assertText(source.loader, 'requiredNullableUuid(item, "emprestimo_id")', 'campos nullable obrigatorios permanecem presentes');
    assertText(source.loader, 'requiredNullableDateTime(item, "atualizado_em")', 'agenda exige atualizado_em nullable');
    assertText(source.loader, 'calendarPartsAreValid(year, month, day)', 'date-time nao normaliza dia impossivel');
    assert.doesNotMatch(source.loader, /problem\.status === 403[^\n]*denied/, '403 backend nao pode perder correlation como preflight RBAC');
    assert.doesNotMatch(source.loader, /response\.json\(|result\.error/, 'loader nao revela body de erro backend');
    assertText(source.policy, 'America/Sao_Paulo', 'data civil possui timezone explicito');
    assertText(source.policy, 'firstInstantOfCivilDate', 'janela deriva limite civil da zona IANA');
    assertText(source.policy, 'timeZoneName: "longOffset"', 'offset vigente e derivado da base IANA');
    assertText(source.unitTest, '2018-11-04T01:00:00.000-02:00', 'teste cobre transicao historica de horario de verao');
    assertText(source.unitTest, '0100-01-01', 'teste cobre limite inferior nao suportado');
    assertText(source.unitTest, '9999-12-31', 'teste cobre limite superior nao suportado');
    assertText(source.policy, 'calendarDateIsValid(raw)', 'periodo rejeita data de calendario invalida');
    assertText(source.page, 'query.data_referencia', 'periodo e estado canonico da URL');
    assertText(source.page, 'redirect(`/app?data_referencia=', 'URL ausente e canonicalizada');
    assert.doesNotMatch(source.page, /query\.(?:tenant_id|carteira_id)/, 'browser nao seleciona Tenant/Carteira');
    assert.doesNotMatch(source.component + source.page, /['"]use client['"]/, 'Dashboard permanece server-first');
    assert.doesNotMatch(source.component + source.page, /accessToken|refreshToken|Authorization|Bearer|localStorage|sessionStorage/, 'Dashboard nao recebe token ou storage do browser');
    assert.doesNotMatch(source.policy, /startsWith|permission\.\*|includes\(permission\)/, 'RBAC nao aceita prefixo ou wildcard');
    assert.doesNotMatch(combined, /["']\/(?:dashboard|devedores)|\.(?:POST|PUT|PATCH|DELETE)\(/i, 'IMP-290 nao antecipa rota/comando');
    // A regra e "Dashboard nao CALCULA regra financeira". Padrao de calculo fica
    // proibido nas tres camadas — e o que a mutacao do IMP-290 exercita.
    assert.doesNotMatch([source.component, source.loader, source.page].join('\n'), /\.reduce\(|parseFloat\(|parseInt\(|Math\.(?:round|floor|ceil)/i, 'Dashboard nao calcula regra financeira');
    // Vocabulario financeiro continua proibido no caminho de dados (loader e
    // pagina), onde nomear o conceito antecede derivar o valor. No componente,
    // que so renderiza numero vindo do backend, o rotulo e permitido: proibir a
    // palavra ali era falso positivo — impedia exibir "Projecao de juros" mesmo
    // com o valor calculado pelo Motor. Refinado pelo IMP-344.
    assert.doesNotMatch([source.loader, source.page].join('\n'), /\bpercentual\b|\b(?:juros|mora|multa|amortiza|saldo|quitacao|renegocia)\w*/i, 'loader e pagina do Dashboard nao derivam valor financeiro');
    for (const marker of ['Carregando', 'Nenhum', 'Sem permissao', 'Nao foi possivel carregar', 'overflow']) {
      assertText(source.component + source.componentTest + source.e2eTest, marker, `estado Dashboard ${marker}`);
    }
    assertText(source.component, 'Correlation ID:', 'falha publica correlation segura');
    assertText(source.component, 'Dados nao encontrados ou indisponiveis.', '404 permanece neutro');
    // O rotulo virou "Inicio" no PLAN-029 IMP-318: "Dashboard" e palavra de
    // quem constroi o sistema, nao de quem empresta o proprio dinheiro. O que o
    // gate protege continua sendo o mesmo — a navegacao aponta para a rota que
    // existe, e nao para uma futura.
    assertText(source.navigationPolicy, 'label: "Inicio"', 'navegacao aponta para a tela inicial existente');
    assertText(source.navigationPolicy, 'grupo: "principal"', 'navegacao separa dia a dia de administracao');
    assert.doesNotMatch(source.navigationPolicy, /href:\s*["']\/(?:dashboard|credit)/, 'navegacao nao antecipa rota futura');
    assertText(packageJson.scripts?.['test:dashboard'] ?? '', 'playwright.dashboard.config.ts', 'script Playwright Dashboard dedicado');
    assertText(packageJson.scripts?.['test:harness'] ?? '', 'npm run test:dashboard', 'harness inclui Dashboard');
    assertText(source.workflow, 'npm run test:dashboard', 'CI executa Dashboard');
    assert.doesNotMatch(source.workflow, /node scripts\/tests\/test-imp-28[4-9]-scope\.js/, 'CI nao executa scope historico');
    assertText(source.playwrightConfig, 'reuseExistingServer: false', 'Dashboard nao reutiliza servidores');
    // O build deixou de ser refeito por config (PLAN-032 §9.5): treze builds no
    // mesmo .next/ eram desperdicio e corrida. A INTENCAO da regra continua a
    // mesma — a suite roda contra build de producao, nunca contra `next dev` —
    // e agora e verificada em duas partes.
    assertText(source.playwrightConfig, 'npm run start', 'Dashboard usa servidor de producao');
    assertText(source.playwrightConfig, 'require-build.mjs', 'Dashboard exige build atual antes de subir');
    assert.doesNotMatch(source.playwrightConfig, /npm run dev/, 'Dashboard nao usa servidor de desenvolvimento');
    assertText(source.playwrightConfig, 'viewport: { height: 900, width: 1440 }', 'viewport Dashboard desktop');
    assertText(source.playwrightConfig, 'viewport: { height: 844, width: 390 }', 'viewport Dashboard mobile');
    assertText(source.axeTest, 'AxeBuilder', 'axe executa no browser real');
    assertText(source.axeTest, 'page.keyboard.press("Tab")', 'teclado real observado');
    assertText(source.e2eTest, 'requests.every', 'browser nao chama backend diretamente');
    assertText(source.bffTest, 'sem fabricar vazio', 'resposta malformada nao vira empty state');
    assertText(source.bffTest, 'aceita somente 200 e rejeita payload estruturalmente incompleto', 'BFF cobre status exato e schema requerido');
    assertText(source.bffTest, '2026-02-30T12:00:00Z', 'BFF rejeita date-time com calendario impossivel');
    assertText(source.bffTest, 'acesso_negado', '403 backend permanece problema correlacionado');
    assertText(source.matrix, 'a composicao visual pertence ao PLAN-025, nao ao escopo Product de FEATURE-031', 'matriz separa composicao tecnica do escopo Product');
    for (const testSource of [source.unitTest, source.componentTest, source.bffTest, source.contractTest, source.e2eTest, source.axeTest]) {
      assert.doesNotMatch(testSource, /\.skip\b|\.todo\b|\.only\b/, 'suite IMP-290 nao aceita testes ignorados');
    }
    assert.strictEqual(manifest.baselineCount, 150, 'baseline IMP-290 exato');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 15, 'mutaveis IMP-290 exatos');
    assert.strictEqual(manifest.protectedBaselineCount, 135, 'protegidos IMP-290 exatos');
    assert.strictEqual(manifest.allowedNewPaths.length, 19, 'novos IMP-290 exatos');
    assert.strictEqual(manifest.expectedFinalCount, 169, 'inventario IMP-290 exato');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist IMP-290 usa paths exatos');
    assert.ok(!manifest.mutableBaselinePaths.includes('frontend/package-lock.json'), 'lockfile fica imutavel');
    assert.ok(!manifest.mutableBaselinePaths.some((relative) => relative.startsWith('docs/product/')), 'Product fica imutavel');
    assertText(source.scopeScript, '`${manifest.head}...HEAD`', 'scope suporta checkout limpo');
    assertText(source.scopeScript, '...worktreePaths', 'scope inclui worktree local');
    for (const [name, width, height] of [
      ['dashboard-desktop', 1440, 900],
      ['dashboard-mobile', 390, 844],
      ['dashboard-states-desktop', 1440, 900],
      ['dashboard-states-mobile', 390, 844],
    ]) {
      const relative = `docs/audits/evidence/frontend-mvp-imp-290-${name}.png`;
      const bytes = fs.readFileSync(path.join(ROOT, relative));
      assert.deepStrictEqual([...bytes.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10], `${name} deve ser PNG`);
      assert.strictEqual(bytes.readUInt32BE(16), width, `${name} largura governada`);
      assert.strictEqual(bytes.readUInt32BE(20), height, `${name} altura governada`);
      assertText(source.report, crypto.createHash('sha256').update(bytes).digest('hex'), `relatorio publica SHA ${name}`);
    }
    assertText(source.plan, '**Versao:** 3.1.0', 'PLAN vivo pos-IMP-298');
    assertText(source.backlog, '**Versao:** 3.1.0', 'backlog vivo pos-IMP-298');
    assertText(source.discovery, '**Vers?o:** 3.2.0', 'Discovery vivo pos-IMP-298');
    assertText(source.matrix, '**Versao:** 3.9.0', 'matriz viva pos-IMP-298');
    const imp290 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-290');
    const imp291 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-291');
    assertText(imp290?.text ?? '', '- **Status:** Concluido.', 'IMP-290 deve estar concluido');
    const imp292 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-292');
    const imp293 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-293');
    assertText(imp291?.text ?? '', '- **Status:** Concluido.', 'IMP-291 deve estar concluido no estado corrente');
    assertText(imp292?.text ?? '', '- **Status:** Concluido.', 'IMP-292 deve estar concluido no estado corrente');
    assertText(imp293?.text ?? '', '- **Status:** Concluido.', 'IMP-293 deve estar concluido');
    const imp294 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-294');
    assertText(imp294?.text ?? '', '- **Status:** Concluido.', 'IMP-294 deve estar concluido no estado corrente');
    const imp295 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-295');
    assertText(imp295?.text ?? '', '- **Status:** Concluido.', 'IMP-295 deve estar concluido no estado corrente');
    const imp296 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-296');
    assertText(imp296?.text ?? '', '- **Status:** Concluido.', 'IMP-296 deve estar concluido');
    assertText(source.report, '106/107', 'relatorio preserva RED canonico');
    assertText(source.report, 'CI Linux/Windows: configurada, mas a execucao remota nao foi observada', 'relatorio nao inventa CI remota');
    assertText(source.report, 'IMP-291 continua bloqueado', 'relatorio mantem IMP-291 sob judge');
  },

  shell(source = readShell()) {
    const packageJson = JSON.parse(source.packageJson);
    assertText(packageJson.scripts?.['test:session'] ?? '', 'playwright.session.config.ts', 'script de sessao dedicado');
    assertText(packageJson.scripts?.['test:harness'] ?? '', 'npm run test:session', 'harness inclui sessao/contexto');
    assert.match(source.context, /^import "server-only";/, 'contexto deve ser server-only');
    assertText(source.context, 'client.GET("/iam/contexto-atual"', 'loader usa endpoint certificado');
    assertText(source.context, 'unsealSession(encrypted', 'loader abre JWE somente no servidor');
    assertText(source.context, 'isOperationalContext', 'resposta 200 possui narrowing runtime');
    assertText(source.context, 'status: 502', 'resposta malformada falha fechada');
    assertText(source.context, 'assertTrustedMutation(request, dependencies.config)', 'bootstrap valida Origin/CSRF');
    assertText(source.context, 'createCookieAuthenticatedFetch(cookies, dependencies, requestCorrelation)', 'bootstrap persiste refresh fora do render');
    assert.doesNotMatch(source.context, /[?&](?:usuario_id|tenant_id|carteira_id)=|body:\s*\{[^}]*?(?:usuario_id|tenant_id|carteira_id)/s, 'contexto nao aceita IDs arbitrarios');
    assert.doesNotMatch(source.context, /\/iam\/permissoes/, 'shell nao consulta catalogo administrativo');
    assert.doesNotMatch(source.appLayout, /['"]use client['"]/, 'layout autenticado permanece Server Component');
    assertText(source.appLayout, 'currentOperationalContext()', 'layout consulta contexto memoizado no servidor');
    assertText(source.appLayout, '? "/login" : "/session/recover"', '401 usa recovery unico entre montagens');
    assertText(source.appLayout, 'Nenhuma Carteira alternativa foi escolhida', '409 nao fabrica Carteira');
    assertText(source.loginForm, 'fetch("/api/auth/login"', 'login chama BFF same-origin');
    for (const field of ['email:', 'segredo:']) assertText(source.loginForm, field, `login publico usa ${field}`);
    assert.doesNotMatch(source.loginForm, /identificador_institucional|Instituicao|organization/, 'login publico nao coleta Instituicao');
    assertText(source.backend, 'type AuthLoginRequest', 'BFF preserva contrato backend AuthLoginRequest');
    assertText(source.backend, 'type BrowserLoginRequest', 'BFF separa contrato publico do contrato backend');
    assertText(source.backend, 'identificador_institucional: dependencies.config.loginTenantIdentifier', 'BFF deriva Instituicao server-only');
    assertText(source.session, 'FRONTEND_LOGIN_TENANT_IDENTIFICADOR', 'config server-only define Instituicao do login backend');
    assertText(source.loginForm, 'router.replace("/app")', 'pos-login usa destino fixo');
    assert.doesNotMatch(source.loginForm, /(?:returnUrl|redirectTo|nextUrl|localStorage|sessionStorage|access_token|refresh_token)/, 'login nao aceita redirect arbitrario nem expoe token');
    assertText(source.logoutButton, 'fetch("/api/auth/logout"', 'logout chama BFF same-origin');
    assertText(source.logoutButton, 'router.replace("/login")', 'logout remove PII apos encerramento local');
    assert.doesNotMatch(source.logoutButton, /!response\.ok|response\.status\s*!==\s*401/, 'erro remoto nao pode manter shell apos cookie local limpo');
    assertText(source.recovery, 'fetch("/api/auth/bootstrap"', 'recovery chama bootstrap exato');
    assertText(source.recovery, 'started.current', 'recovery nao cria loop');
    assertText(source.context, 'recoveryAttemptCookieName(dependencies.config)', 'BFF grava tentativa efemera server-only');
    assertText(source.context, 'httpOnly: true', 'marcador de recovery nao e exposto ao browser');
    assertText(source.appLayout, 'cookieStore.get(recoveryAttemptCookieName(dependencies.config))', 'layout impede nova montagem de recovery');
    assertText(source.navigationPolicy, 'new Set(effectivePermissions)', 'permissoes efetivas formam conjunto exato');
    assertText(source.navigationPolicy, 'granted.has(destination.requiredPermission)', 'guard usa igualdade exata');
    assert.doesNotMatch(source.navigationPolicy, /startsWith|includes\(destination\.requiredPermission\)|permission\.\*|\/dashboard|href:\s*["']\/devedores|\/credit/, 'guard nao usa prefixo/wildcard nem antecipa jornada');
    assertText(source.contextSummary, 'context.tenant.nome', 'shell apresenta Tenant do backend');
    assertText(source.contextSummary, 'context.carteira_padrao.nome', 'shell apresenta Carteira do backend');
    assertText(source.contextSummary, 'context.perfil?.nome ?? "Sem perfil ativo"', 'perfil nulo nao concede acesso');
    assertText(source.context, 'contextMatchesSession(payload, session)', 'contexto deve corresponder ao Usuario e Tenant da sessao');
    assertText(source.context, 'value.perfil !== null || value.permissoes.length === 0', 'perfil nulo nao pode publicar permissao efetiva');
    assertText(source.context, 'response.status !== 401 && response.status !== 409', 'contexto rejeita status nao certificado');
    assertText(source.bootstrapRoute, 'handleContextBootstrap', 'Route Handler bootstrap e especifico');
    assert.doesNotMatch([source.loginForm, source.logoutButton, source.recovery, source.appShell].join('\n'), /\/iam\/|\/credit\/|NEXT_PUBLIC_|accessToken|refreshToken/, 'Client Components nao recebem API backend ou tokens');
    assert.doesNotMatch([source.context, source.loginForm, source.logoutButton, source.recovery, source.appShell].join('\n'), /:\s*any\b|\bas\s+any\b|<any>|@ts-(?:ignore|expect-error)|\b(?:juros|mora|multa|amortiza|saldo|quitacao|renegocia)\w*/i, 'shell nao contorna tipos nem calcula regra financeira');
    assertText(source.unitTest, 'igualdade exata', 'unit cobre permissao exata');
    assertText(source.componentTest, 'envia somente credenciais', 'component cobre body publico de login');
    assertText(source.componentTest, 'queryByRole("textbox", { name: "Instituicao" })', 'component garante remocao do campo Instituicao');
    assertText(source.componentTest, 'identificador_institucional', 'component rejeita identificador institucional no body publico');
    assertText(source.componentTest, 'Sem perfil ativo', 'component cobre perfil nulo');
    for (const marker of ['proprio Principal', 'resposta 200 malformada', 'Usuario ou Tenant diferente', 'status nao certificado', 'sanitiza 500', 'timeout do contexto', '409 de contexto incompleto', 'um refresh', 'Origin hostil', 'sem cookie']) assertText(source.bffTest, marker, `BFF contexto cobre ${marker}`);
    assertText(source.contractTest, '["200", "401", "409", "500"]', 'contract nao inventa status do contexto');
    assertText(source.e2eTest, 'browserRequests.every', 'E2E rejeita browser direto ao backend');
    assertText(source.e2eTest, 'localStorage.length', 'E2E rejeita token em storage');
    assertText(source.e2eTest, '401 dispara um bootstrap controlado', 'E2E cobre recovery 401');
    assertText(source.e2eTest, '401 repetido executa no maximo um bootstrap', 'E2E impede loop de recovery entre montagens');
    assertText(source.e2eTest, '5xx mostra estado seguro e correlation', 'E2E cobre falha tecnica correlacionada');
    assertText(source.e2eTest, '409 nao fabrica Carteira alternativa', 'E2E cobre 409');
    assertText(source.e2eTest, '404 permanece neutro', 'E2E cobre 404 neutro');
    assertText(source.axeTest, 'AxeBuilder', 'axe executa no browser real');
    assertText(source.axeTest, 'page.keyboard.press("Tab")', 'teclado real observado');
    for (const testSource of [source.unitTest, source.componentTest, source.bffTest, source.contractTest, source.e2eTest, source.axeTest]) assert.doesNotMatch(testSource, /\.skip\b|\.todo\b|\.only\b/, 'suite IMP-289 nao aceita testes ignorados');
    assertText(source.playwrightConfig, 'reuseExistingServer: false', 'servidores de sessao nao sao reutilizados');
    assertText(source.playwrightConfig, 'viewport: { height: 900, width: 1440 }', 'viewport desktop governado');
    assertText(source.playwrightConfig, 'viewport: { height: 844, width: 390 }', 'viewport mobile governado');
    assertText(source.playwrightConfig, 'FRONTEND_BACKEND_URL', 'fixture backend e server-only');
    assertText(source.fixture, '/iam/contexto-atual', 'fixture real implementa contexto');
    assertText(source.workflow, 'npm run test:session', 'CI executa shell/contexto');
    assert.doesNotMatch(source.workflow, /node scripts\/tests\/test-imp-28[4-9]-scope\.js/, 'CI nao executa scope historico');
    const manifest = JSON.parse(source.manifest);
    const predecessorPath = path.join(ROOT, manifest.predecessor.path);
    assert.strictEqual(crypto.createHash('sha256').update(fs.readFileSync(predecessorPath)).digest('hex'), manifest.predecessor.sha256, 'manifesto IMP-289 encadeia IMP-288');
    assert.strictEqual(Object.keys(manifest.files).length, 116, 'baseline IMP-289 possui 116 paths');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 13, 'allowlist mutavel IMP-289 exata');
    assert.strictEqual(manifest.allowedNewPaths.length, 34, 'allowlist nova IMP-289 exata');
    assert.strictEqual(manifest.expectedFinalCount, 150, 'inventario final IMP-289 exato');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist IMP-289 usa paths exatos');
    assert.ok(!manifest.mutableBaselinePaths.includes('frontend/package-lock.json'), 'lockfile fica imutavel');
    for (const imageName of ['login-desktop', 'login-mobile', 'shell-desktop', 'shell-mobile']) {
      const relative = `docs/audits/evidence/frontend-mvp-imp-289-${imageName}.png`;
      const bytes = fs.readFileSync(path.join(ROOT, relative));
      assert.strictEqual(bytes.subarray(1, 4).toString('ascii'), 'PNG', `${imageName} deve ser PNG`);
      assertText(source.report, crypto.createHash('sha256').update(bytes).digest('hex'), `relatorio publica SHA ${imageName}`);
    }
    assertText(source.report, '90/91', 'relatorio preserva RED canonico');
    assertText(source.report, 'CI remota Linux/Windows nao foi observada', 'relatorio nao inventa CI remota');
    assertText(source.report, 'IMP-290 permanece bloqueado', 'relatorio mantem proximo IMP sob judge');
    const imp289 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-289');
    const imp290 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-290');
    const imp291 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-291');
    const imp292 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-292');
    const imp293 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-293');
    assertText(imp289?.text ?? '', '- **Status:** Concluido.', 'IMP-289 deve estar concluido');
    assertText(imp290?.text ?? '', '- **Status:** Concluido.', 'IMP-290 deve estar concluido no estado corrente');
    assertText(imp291?.text ?? '', '- **Status:** Concluido.', 'IMP-291 deve estar concluido no estado corrente');
    assertText(imp292?.text ?? '', '- **Status:** Concluido.', 'IMP-292 deve estar concluido no estado corrente');
    assertText(imp293?.text ?? '', '- **Status:** Concluido.', 'IMP-293 deve estar concluido');
    const imp294 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-294');
    assertText(imp294?.text ?? '', '- **Status:** Concluido.', 'IMP-294 deve estar concluido no estado corrente');
    const imp295 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-295');
    assertText(imp295?.text ?? '', '- **Status:** Concluido.', 'IMP-295 deve estar concluido no estado corrente');
    const imp296 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-296');
    assertText(imp296?.text ?? '', '- **Status:** Concluido.', 'IMP-296 deve estar concluido');
  },

  devedores(source = readDevedores()) {
    assert.match(source.loader, /^import "server-only";/, 'loader Devedores deve ser server-only');
    assertText(source.navigationPolicy, 'href: "/app/devedores"', 'navegacao Devedores sob shell autenticado');
    assertText(source.navigationPolicy, 'requiredPermission: "devedor.ler"', 'navegacao Devedores exige devedor.ler exato');
    assertText(source.packageJson, '"test:devedores"', 'package expoe gate Devedores');
    assertText(source.workflow, 'npm run test:devedores', 'CI executa gate Devedores');
    assertText(source.loader, 'context.carteira_padrao.id', 'BFF usa somente Carteira propria do contexto');
    assert.doesNotMatch(source.loader + source.listPage + source.detailPage + source.actions, /searchParams\.(?:tenant_id|carteira_id)|query\.(?:tenant_id|carteira_id)|formData\.get\(["'](?:tenant_id|carteira_id)["']\)/, 'Devedores nao aceita Tenant/Carteira do browser');
    for (const permission of ['devedor.ler', 'devedor.criar', 'devedor.atualizar', 'devedor.inativar', 'devedor.reativar']) {
      assertText(source.policy + source.loader + source.unitTest + source.bffTest, permission, `permissao Devedores ${permission}`);
    }
    assert.doesNotMatch(source.policy, /startsWith|includes\(permission\)|permission\.\*|\*/, 'RBAC Devedores nao usa prefixo/wildcard');
    for (const endpoint of [
      '/credit/carteiras/{carteira_id}/devedores',
      '/credit/carteiras/{carteira_id}/devedores/{devedor_id}',
      '/credit/carteiras/{carteira_id}/devedores/{devedor_id}/historico',
      '/credit/carteiras/{carteira_id}/devedores/{devedor_id}/inativar',
      '/credit/carteiras/{carteira_id}/devedores/{devedor_id}/reativar',
    ]) {
      assertText(source.loader + source.contractTest, endpoint, `endpoint oficial Devedores ${endpoint}`);
    }
    assertText(source.loader + source.bffTest, 'Idempotency-Key', 'comandos Devedores enviam Idempotency-Key');
    assertText(source.loader + source.component + source.bffTest, 'Correlation ID', 'erros Devedores mostram correlation seguro');
    assert.doesNotMatch(source.component + source.form + source.statusDialog + source.listPage + source.detailPage, /accessToken|refreshToken|Authorization|Bearer|localStorage|sessionStorage/, 'Devedores nao expoe tokens no browser');
    assert.doesNotMatch(source.component + source.loader + source.policy, /\.reduce\(|parseFloat\(|parseInt\(|Math\.(?:round|floor|ceil)|\b(?:juros|mora|multa|amortiza|saldo|quitacao|renegocia|parcela|pagamento|emprestimo)\w*/i, 'Devedores nao calcula regra financeira');
    assertText(source.component, '/app/devedores/${item.id}/comercial', 'Devedores oferece entrada Comercial governada');
    assert.doesNotMatch(source.component, /\/(?:agenda|comunicacoes|cobranca|relatorios|configuracoes)\b/, 'Devedores nao antecipa jornadas futuras apos Motor');
    for (const marker of ['loading', 'empty', 'denied', '404', '409', '422', 'overflow']) {
      assertText(source.component + source.componentTest + source.e2eTest, marker, `estado Devedores ${marker}`);
    }
    const packageJson = JSON.parse(source.packageJson);
    assertText(packageJson.scripts?.['test:devedores'] ?? '', 'playwright.devedores.config.ts', 'script Playwright Devedores dedicado');
    assertText(packageJson.scripts?.['test:harness'] ?? '', 'npm run test:devedores', 'harness inclui Devedores');
    const manifest = JSON.parse(source.manifest);
    assert.strictEqual(manifest.baselineCount, 169, 'baseline IMP-291 exato');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 15, 'mutaveis IMP-291 exatos');
    assert.strictEqual(manifest.protectedBaselineCount, 154, 'protegidos IMP-291 exatos');
    assert.strictEqual(manifest.allowedNewPaths.length, 23, 'novos IMP-291 exatos');
    assert.strictEqual(manifest.expectedFinalCount, 192, 'inventario IMP-291 exato');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist IMP-291 usa paths exatos');
    assert.ok(!manifest.mutableBaselinePaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-291 nao libera backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.allowedNewPaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-291 nao cria backend/Product/Registry/OpenAPI');
    for (const [suffix, width, height] of [
      ['devedores-list-desktop', 1440, 900],
      ['devedores-list-mobile', 390, 844],
      ['devedor-detail-desktop', 1440, 900],
      ['devedor-form-mobile', 390, 844],
    ]) {
      const relative = `docs/audits/evidence/frontend-mvp-imp-291-${suffix}.png`;
      const bytes = fs.readFileSync(path.join(ROOT, relative));
      assert.strictEqual(bytes.readUInt32BE(16), width, `${suffix} largura`);
      assert.strictEqual(bytes.readUInt32BE(20), height, `${suffix} altura`);
      assertText(source.report, crypto.createHash('sha256').update(bytes).digest('hex'), `relatorio publica SHA ${suffix}`);
    }
    assertText(source.plan, '**Versao:** 3.1.0', 'PLAN vivo pos-IMP-298');
    assertText(source.backlog, '**Versao:** 3.1.0', 'backlog vivo pos-IMP-298');
    assertText(source.discovery, '**Vers?o:** 3.2.0', 'Discovery vivo pos-IMP-298');
    assertText(source.matrix, '**Versao:** 3.9.0', 'matriz viva pos-IMP-298');
    const imp291 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-291');
    const imp292 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-292');
    const imp293 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-293');
    assertText(imp291?.text ?? '', '- **Status:** Concluido.', 'IMP-291 deve estar concluido');
    assertText(imp292?.text ?? '', '- **Status:** Concluido.', 'IMP-292 deve estar concluido');
    assertText(imp293?.text ?? '', '- **Status:** Concluido.', 'IMP-293 deve estar concluido');
  },

  comercial(source = readComercial()) {
    assert.match(source.loader, /^import "server-only";/, 'loader Comercial deve ser server-only');
    assertText(source.navigationPolicy, 'href: "/app/devedores"', 'Comercial parte da jornada de Devedores ativos');
    assertText(source.devedoresComponent, '/app/devedores/${item.id}/comercial', 'Devedor ativo oferece entrada para Comercial');
    assertText(source.packageJson, '"test:comercial"', 'package expoe gate Comercial');
    assertText(source.workflow, 'npm run test:comercial', 'CI executa gate Comercial');
    assertText(source.loader, 'context.carteira_padrao.id', 'BFF Comercial usa somente Carteira propria');
    assert.doesNotMatch(source.loader + source.devedorComercialPage + source.propostaPage + source.actions, /searchParams\.(?:tenant_id|carteira_id)|query\.(?:tenant_id|carteira_id)|formData\.get\(["'](?:tenant_id|carteira_id)["']\)/, 'Comercial nao aceita Tenant/Carteira do browser');
    for (const permission of [
      'comercial.simulacao.criar',
      'comercial.proposta.criar',
      'comercial.proposta.ler',
      'comercial.proposta.decidir',
      'comercial.proposta.integrar',
    ]) {
      assertText(source.policy + source.loader + source.unitTest + source.bffTest, permission, `permissao Comercial ${permission}`);
    }
    assert.doesNotMatch(source.policy, /startsWith|includes\(permission\)|permission\.\*|\*/, 'RBAC Comercial nao usa prefixo/wildcard');
    for (const endpoint of [
      '/credit/carteiras/{carteira_id}/devedores/{devedor_id}/simulacoes-comerciais',
      '/credit/simulacoes-comerciais/{simulacao_id}',
      '/credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais',
      '/credit/propostas-comerciais/{proposta_id}',
      '/credit/propostas-comerciais/{proposta_id}/enviar-para-analise',
      '/credit/propostas-comerciais/{proposta_id}/aprovar',
      '/credit/propostas-comerciais/{proposta_id}/recusar',
      '/credit/propostas-comerciais/{proposta_id}/cancelar',
      '/credit/propostas-comerciais/{proposta_id}/expirar',
      '/credit/propostas-comerciais/{proposta_id}/contrato-logico',
    ]) {
      assertText(source.loader + source.contractTest, endpoint, `endpoint oficial Comercial ${endpoint}`);
    }
    assertText(source.loader, 'export async function getCommercialSimulation', 'BFF consulta simulacao comercial por ID');
    assertText(source.propostaPage, 'getCommercialSimulation', 'detalhe de proposta consulta simulacao vinculada');
    assertText(source.component, 'Simulacao comercial vinculada', 'UI apresenta consulta read-only da simulacao vinculada');
    assertText(source.bffTest, 'consulta simulacao por ID usando endpoint oficial', 'suite BFF cobre consulta de simulacao por ID');
    assertText(source.loader + source.bffTest + source.contractTest, 'Idempotency-Key', 'Comercial envia Idempotency-Key exigida pelo OpenAPI certificado');
    assertText(source.loader + source.component + source.bffTest, 'Correlation ID', 'erros Comercial mostram correlation seguro');
    assert.doesNotMatch(source.component + source.jsonForm + source.decisionDialog + source.devedorComercialPage + source.propostaPage, /accessToken|refreshToken|Authorization|Bearer|localStorage|sessionStorage/, 'Comercial nao expoe tokens no browser');
    assert.doesNotMatch(source.component + source.loader, /\.reduce\(|parseFloat\(|parseInt\(|Math\.(?:round|floor|ceil)|\b(?:juros|mora|multa|amortiza|saldo|quitacao|renegocia|parcela|pagamento|emprestimo)\w*/i, 'Comercial nao calcula regra financeira nem antecipa Motor');
    assert.doesNotMatch(source.component + source.propostaPage, /\/app\/(?:motor|pagamentos)\b|criar Emprestimo|assinar credito|liberar credito/i, 'Comercial nao cria Motor/pagamentos diretamente');
    for (const marker of ['loading', 'empty', 'denied', '404', '409', '422', 'overflow', 'contrato logico']) {
      assertText(source.component + source.componentTest + source.e2eTest, marker, `estado Comercial ${marker}`);
    }
    assertText(source.report, 'trilha de decisoes detalhada nao possui endpoint no OpenAPI', 'relatorio registra lacuna de trilha');
    assertText(source.report, 'filtro por periodo nao possui contrato no OpenAPI Comercial', 'relatorio registra lacuna de periodo');
    assertText(source.report, 'Idempotency-Key nao e publicada no OpenAPI Comercial', 'relatorio registra fronteira de idempotencia');
    const packageJson = JSON.parse(source.packageJson);
    assertText(packageJson.scripts?.['test:comercial'] ?? '', 'playwright.comercial.config.ts', 'script Playwright Comercial dedicado');
    assertText(packageJson.scripts?.['test:harness'] ?? '', 'npm run test:comercial', 'harness inclui Comercial');
    const manifest = JSON.parse(source.manifest);
    assert.strictEqual(manifest.baselineCount, 192, 'baseline IMP-292 exato');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 15, 'mutaveis IMP-292 exatos');
    assert.strictEqual(manifest.protectedBaselineCount, 177, 'protegidos IMP-292 exatos');
    assert.strictEqual(manifest.allowedNewPaths.length, 23, 'novos IMP-292 exatos');
    assert.strictEqual(manifest.expectedFinalCount, 215, 'inventario IMP-292 exato');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist IMP-292 usa paths exatos');
    assert.ok(!manifest.mutableBaselinePaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-292 nao libera backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.allowedNewPaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-292 nao cria backend/Product/Registry/OpenAPI');
    for (const [suffix, width, height] of [
      ['comercial-list-desktop', 1440, 900],
      ['comercial-list-mobile', 390, 844],
      ['proposta-detail-desktop', 1440, 900],
      ['proposta-flow-mobile', 390, 844],
    ]) {
      const relative = `docs/audits/evidence/frontend-mvp-imp-292-${suffix}.png`;
      const bytes = fs.readFileSync(path.join(ROOT, relative));
      assert.strictEqual(bytes.readUInt32BE(16), width, `${suffix} largura`);
      assert.strictEqual(bytes.readUInt32BE(20), height, `${suffix} altura`);
      assertText(source.report, crypto.createHash('sha256').update(bytes).digest('hex'), `relatorio publica SHA ${suffix}`);
    }
    assertText(source.plan, '**Versao:** 3.1.0', 'PLAN vivo pos-IMP-298');
    assertText(source.backlog, '**Versao:** 3.1.0', 'backlog vivo pos-IMP-298');
    assertText(source.discovery, '**Vers?o:** 3.2.0', 'Discovery vivo pos-IMP-298');
    assertText(source.matrix, '**Versao:** 3.9.0', 'matriz viva pos-IMP-298');
    const imp292 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-292');
    const imp293 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-293');
    assertText(imp292?.text ?? '', '- **Status:** Concluido.', 'IMP-292 deve estar concluido');
    assertText(imp293?.text ?? '', '- **Status:** Concluido.', 'IMP-293 deve estar concluido');
  },

  contratos(source = readContratos()) {
    assert.match(source.loader, /^import "server-only";/, 'loader Contratos deve ser server-only');
    assertText(source.packageJson, '"test:contratos"', 'package expoe gate Contratos');
    assertText(source.workflow, 'npm run test:contratos', 'CI executa gate Contratos');
    assertText(source.navigationPolicy, 'href: "/app/contratos"', 'navegacao Contratos sob shell autenticado');
    assertText(source.comercialComponent, '/app/contratos?proposta_id=${item.id}', 'Comercial aprovado oferece ponte para Contratos');
    assertText(source.loader, 'context.carteira_padrao.id', 'BFF Contratos usa somente Carteira propria');
    assert.doesNotMatch(source.loader + source.listPage + source.detailPage + source.actions, /searchParams\.(?:tenant_id|carteira_id)|query\.(?:tenant_id|carteira_id)|formData\.get\(["'](?:tenant_id|carteira_id)["']\)/, 'Contratos nao aceita Tenant/Carteira do browser');
    for (const permission of [
      'contratos.contrato.criar',
      'contratos.contrato.ler',
      'contratos.contrato.assinar',
      'contratos.contrato.liberar',
      'contratos.contrato.encerrar',
    ]) {
      assertText(source.policy + source.loader + source.unitTest + source.bffTest, permission, `permissao Contratos ${permission}`);
    }
    assert.doesNotMatch(source.policy, /startsWith|includes\(permission\)|permission\.\*|\*/, 'RBAC Contratos nao usa prefixo/wildcard');
    for (const endpoint of [
      '/credit/carteiras/{carteira_id}/contratos',
      '/credit/contratos/{contrato_id}',
      '/credit/contratos/{contrato_id}/historico',
      '/credit/contratos/{contrato_id}/assinar',
      '/credit/contratos/{contrato_id}/liberar-para-motor',
      '/credit/contratos/{contrato_id}/cancelar',
      '/credit/contratos/{contrato_id}/encerrar',
    ]) {
      assertText(source.loader + source.contractTest, endpoint, `endpoint oficial Contratos ${endpoint}`);
    }
    assertText(source.loader + source.bffTest + source.contractTest, 'Idempotency-Key', 'Contratos envia Idempotency-Key exigida pelo OpenAPI certificado');
    const implementationSurface = [
      source.loader,
      source.actions,
      source.decisionDialog,
      source.listPage,
      source.detailPage,
    ].join('\n');
    assert.doesNotMatch(
      implementationSurface,
      /\/credit\/contratos\/\{contrato_id\}\/emprestimos|\/emprestimos\b|\/app\/(?:pagamentos|emprestimos)\b|Pagamento idempotente/i,
      'Contratos nao cria Motor/pagamentos diretamente',
    );
    assertText(source.component, '/app/motor?contrato_id=', 'Contratos oferece ponte governada para Motor apos IMP-294');
    assert.doesNotMatch(source.component + source.decisionDialog + source.listPage + source.detailPage, /accessToken|refreshToken|Authorization|Bearer|localStorage|sessionStorage/, 'Contratos nao expoe tokens no browser');
    assert.doesNotMatch(source.component + source.loader, /\.reduce\(|parseFloat\(|parseInt\(|Math\.(?:round|floor|ceil)/, 'Contratos nao calcula regra financeira');
    for (const marker of ['loading', 'empty', 'denied', '404', '409', 'overflow', 'Historico contratual', 'Liberar para Motor nao cria Emprestimo']) {
      assertText(source.component + source.componentTest + source.e2eTest, marker, `estado Contratos ${marker}`);
    }
    assertText(source.component, 'Contrato nao encontrado ou indisponivel.', 'UI Contratos preserva 404 neutro');
    assertText(source.loader, 'Contrato nao encontrado ou indisponivel.', 'BFF Contratos preserva 404 neutro');
    assertText(source.report, 'As 8 operacoes de Contratos nao publicam `Idempotency-Key`', 'relatorio registra fronteira de idempotencia');
    assertText(source.report, 'Nenhum Motor, pagamento, Emprestimo, Parcela', 'relatorio registra fronteira Motor');
    const packageJson = JSON.parse(source.packageJson);
    assertText(packageJson.scripts?.['test:contratos'] ?? '', 'playwright.contratos.config.ts', 'script Playwright Contratos dedicado');
    assertText(packageJson.scripts?.['test:harness'] ?? '', 'npm run test:contratos', 'harness inclui Contratos');
    const manifest = JSON.parse(source.manifest);
    assert.strictEqual(manifest.baselineCount, 215, 'baseline IMP-293 exato');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 11, 'mutaveis IMP-293 exatos');
    assert.strictEqual(manifest.protectedBaselineCount, 204, 'protegidos IMP-293 exatos');
    assert.strictEqual(manifest.allowedNewPaths.length, 22, 'novos IMP-293 exatos');
    assert.strictEqual(manifest.expectedFinalCount, 237, 'inventario IMP-293 exato');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist IMP-293 usa paths exatos');
    assert.ok(!manifest.mutableBaselinePaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-293 nao libera backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.allowedNewPaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-293 nao cria backend/Product/Registry/OpenAPI');
    for (const [suffix, width, height] of [
      ['contratos-list-desktop', 1440, 900],
      ['contratos-list-mobile', 390, 844],
      ['contrato-detail-desktop', 1440, 900],
      ['contrato-flow-mobile', 390, 844],
    ]) {
      const relative = `docs/audits/evidence/frontend-mvp-imp-293-${suffix}.png`;
      const bytes = fs.readFileSync(path.join(ROOT, relative));
      assert.strictEqual(bytes.readUInt32BE(16), width, `${suffix} largura`);
      assert.strictEqual(bytes.readUInt32BE(20), height, `${suffix} altura`);
      assertText(source.report, crypto.createHash('sha256').update(bytes).digest('hex'), `relatorio publica SHA ${suffix}`);
    }
    assertText(source.plan, '**Versao:** 3.1.0', 'PLAN vivo pos-IMP-298');
    assertText(source.backlog, '**Versao:** 3.1.0', 'backlog vivo pos-IMP-298');
    assertText(source.discovery, '**Vers?o:** 3.2.0', 'Discovery vivo pos-IMP-298');
    assertText(source.matrix, '**Versao:** 3.9.0', 'matriz viva pos-IMP-298');
    const imp293 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-293');
    const imp294 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-294');
    assertText(imp293?.text ?? '', '- **Status:** Concluido.', 'IMP-293 deve estar concluido');
    assertText(imp294?.text ?? '', '- **Status:** Concluido.', 'IMP-294 deve estar concluido');
    const imp295 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-295');
    assertText(imp295?.text ?? '', '- **Status:** Concluido.', 'IMP-295 deve estar concluido no estado corrente');
    const imp296 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-296');
    assertText(imp296?.text ?? '', '- **Status:** Concluido.', 'IMP-296 deve estar concluido');
  },

  motor(source = readMotor()) {
    assert.match(source.loader, /^import "server-only";/, 'loader Motor deve ser server-only');
    assertText(source.packageJson, '"test:motor"', 'package expoe gate Motor');
    assertText(source.workflow, 'npm run test:motor', 'CI executa gate Motor');
    assertText(source.navigationPolicy, 'href: "/app/motor"', 'navegacao Motor sob shell autenticado');
    assertText(source.contratosComponent + source.contratoPage, '/app/motor?contrato_id=', 'Contratos liberado oferece ponte para Motor');
    assertText(source.loader, 'context.carteira_padrao.id', 'BFF Motor usa somente Carteira propria');
    assert.doesNotMatch(source.loader + source.listPage + source.detailPage + source.actions, /searchParams\.(?:tenant_id|carteira_id)|query\.(?:tenant_id|carteira_id)|formData\.get\(["'](?:tenant_id|carteira_id)["']\)/, 'Motor nao aceita Tenant/Carteira do browser');
    for (const permission of [
      'motor.emprestimo.criar',
      'motor.emprestimo.ler',
      'motor.parcela.gerar',
      'motor.parcela.ler',
      'motor.pagamento.registrar',
      'motor.saldo.ler',
      'motor.memoria.ler',
      'motor.quitacao.executar',
      'motor.renegociacao.criar',
    ]) {
      assertText(source.policy + source.loader + source.unitTest + source.bffTest, permission, `permissao Motor ${permission}`);
    }
    assert.doesNotMatch(source.policy, /startsWith|includes\(permission\)|permission\.\*|["']motor\.[^"']*\*[^"']*["']/, 'RBAC Motor nao usa prefixo/wildcard');
    for (const endpoint of [
      '/credit/contratos/{contrato_id}/emprestimos',
      '/credit/carteiras/{carteira_id}/emprestimos',
      '/credit/emprestimos/{emprestimo_id}',
      '/credit/emprestimos/{emprestimo_id}/parcelas',
      '/credit/emprestimos/{emprestimo_id}/pagamentos',
      '/credit/emprestimos/{emprestimo_id}/saldo',
      '/credit/emprestimos/{emprestimo_id}/memoria-calculo',
      '/credit/emprestimos/{emprestimo_id}/quitacao',
      '/credit/emprestimos/{emprestimo_id}/renegociacoes',
    ]) {
      assertText(source.loader + source.contractTest, endpoint, `endpoint oficial Motor ${endpoint}`);
    }
    for (const required of [
      '/credit/contratos/{contrato_id}/emprestimos',
      '/credit/emprestimos/{emprestimo_id}/pagamentos',
      '/credit/emprestimos/{emprestimo_id}/quitacao',
      '/credit/emprestimos/{emprestimo_id}/renegociacoes',
    ]) {
      assertText(source.loader + source.bffTest + source.contractTest, `Idempotency-Key:${required}`, `Idempotency-Key obrigatoria em ${required}`);
    }
    assertText(source.loader + source.bffTest + source.contractTest, 'sem-idempotency:/credit/emprestimos/{emprestimo_id}/parcelas', 'parcelas nao inventa Idempotency-Key ausente no OpenAPI');
    assert.doesNotMatch(source.component + source.commandDialog + source.listPage + source.detailPage, /accessToken|refreshToken|Authorization|Bearer|localStorage|sessionStorage/, 'Motor nao expoe tokens no browser');
    assert.doesNotMatch(source.component + source.commandDialog + source.loader + source.policy, /\.reduce\(|parseFloat\(|parseInt\(|Math\.(?:round|floor|ceil)|Intl\.NumberFormat|toFixed\(|\+\s*(?:principal|juros|encargos|saldo|total|valor)|(?:principal|juros|encargos|saldo|total|valor)\s*\+/, 'Motor nao calcula ou formata valor financeiro localmente');
    // Vocabulario do Credor, e nao da certificacao (PLAN-029 IMP-315).
    //
    // 'loading' saiu da lista: o Motor nao tem estado de carregamento. O marker
    // era satisfeito por um <span class="sr-only">loading empty denied 404 409
    // 422 overflow</span> que existia so para o grep passar — e era lido em voz
    // alta por leitor de tela. Removido o span, o marker nao tinha o que
    // afirmar. Criar um estado de carregamento de verdade para o Motor fica
    // como trabalho proprio; ate la, a lista nao finge que ele existe.
    for (const marker of ['empty', 'Sem permissao', '404', '409', '422', 'overflow', 'Como a conta foi feita', 'Pagamento idempotente', 'Valor para quitar hoje', 'Renegociar condicoes']) {
      assertText(source.component + source.componentTest + source.e2eTest, marker, `estado Motor ${marker}`);
    }
    assertText(source.component, 'Emprestimo nao encontrado ou indisponivel.', 'UI Motor preserva 404 neutro');
    assertText(source.loader, 'Emprestimo nao encontrado ou indisponivel.', 'BFF Motor preserva 404 neutro');
    const packageJson = JSON.parse(source.packageJson);
    assertText(packageJson.scripts?.['test:motor'] ?? '', 'playwright.motor.config.ts', 'script Playwright Motor dedicado');
    assertText(packageJson.scripts?.['test:harness'] ?? '', 'npm run test:motor', 'harness inclui Motor');
    const manifest = JSON.parse(source.manifest);
    assert.strictEqual(manifest.baselineCount, 237, 'baseline IMP-294 exato');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 11, 'mutaveis IMP-294 exatos');
    assert.strictEqual(manifest.protectedBaselineCount, 226, 'protegidos IMP-294 exatos');
    assert.strictEqual(manifest.allowedNewPaths.length, 22, 'novos IMP-294 exatos');
    assert.strictEqual(manifest.expectedFinalCount, 259, 'inventario IMP-294 exato');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist IMP-294 usa paths exatos');
    assert.ok(!manifest.mutableBaselinePaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-294 nao libera backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.allowedNewPaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-294 nao cria backend/Product/Registry/OpenAPI');
    for (const [suffix, width, height] of [
      ['motor-list-desktop', 1440, 900],
      ['motor-list-mobile', 390, 844],
      ['emprestimo-detail-desktop', 1440, 900],
      ['pagamento-flow-mobile', 390, 844],
    ]) {
      const relative = `docs/audits/evidence/frontend-mvp-imp-294-${suffix}.png`;
      const bytes = fs.readFileSync(path.join(ROOT, relative));
      assert.strictEqual(bytes.readUInt32BE(16), width, `${suffix} largura`);
      assert.strictEqual(bytes.readUInt32BE(20), height, `${suffix} altura`);
      assertText(source.report, crypto.createHash('sha256').update(bytes).digest('hex'), `relatorio publica SHA ${suffix}`);
    }
    assertText(source.plan, '**Versao:** 3.1.0', 'PLAN final IMP-298');
    assertText(source.backlog, '**Versao:** 3.1.0', 'backlog final IMP-298');
    assertText(source.discovery, '3.2.0', 'Discovery final IMP-298');
    assertText(source.matrix, '**Versao:** 3.9.0', 'matriz final IMP-298');
    const imp294 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-294');
    const imp295 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-295');
    assertText(imp294?.text ?? '', '- **Status:** Concluido.', 'IMP-294 deve estar concluido');
    assertText(imp295?.text ?? '', '- **Status:** Concluido.', 'IMP-295 deve estar concluido no estado corrente');
  },

  cobranca(source = readCobranca()) {
    assert.match(source.loader, /^import "server-only";/, 'loader Cobranca deve ser server-only');
    assertText(source.packageJson, '"test:cobranca"', 'package expoe gate Cobranca');
    assertText(source.workflow, 'npm run test:cobranca', 'CI executa gate Cobranca');
    assertText(source.navigationPolicy, 'href: "/app/cobranca"', 'navegacao Cobranca sob shell autenticado');
    assertText(source.loader, 'context.carteira_padrao.id', 'BFF Cobranca usa somente Carteira propria');
    assert.doesNotMatch(source.loader + source.page + source.actions, /searchParams\.(?:tenant_id|carteira_id)|query\.(?:tenant_id|carteira_id)|formData\.get\(["'](?:tenant_id|carteira_id)["']\)/, 'Cobranca nao aceita Tenant/Carteira do browser');
    for (const permission of [
      'cobranca.caso.ler',
      'cobranca.acao.registrar',
      'cobranca.promessa.registrar',
      'cobranca.promessa.apropriar',
    ]) {
      assertText(source.policy + source.loader + source.unitTest + source.bffTest + source.navigationTest, permission, `permissao Cobranca ${permission}`);
    }
    assert.doesNotMatch(source.policy, /startsWith|includes\(permission\)|permission\.\*|["']cobranca\.[^"']*\*[^"']*["']/, 'RBAC Cobranca nao usa prefixo/wildcard');
    for (const endpoint of [
      '/credit/cobrancas/casos',
      '/credit/cobrancas/casos/{cobranca_caso_id}/acoes',
      '/credit/cobrancas/casos/{cobranca_caso_id}/promessas',
      '/credit/cobrancas/promessas/{promessa_id}/apropriacoes',
    ]) {
      assertText(source.loader + source.contractTest, endpoint, `endpoint oficial Cobranca ${endpoint}`);
    }
    assertText(source.loader + source.bffTest + source.contractTest, 'sem-idempotency:/credit/cobrancas/casos', 'fila de Cobranca nao inventa Idempotency-Key');
    for (const required of [
      '/credit/cobrancas/casos/{cobranca_caso_id}/acoes',
      '/credit/cobrancas/casos/{cobranca_caso_id}/promessas',
      '/credit/cobrancas/promessas/{promessa_id}/apropriacoes',
    ]) {
      assertText(source.loader + source.bffTest + source.contractTest, `Idempotency-Key:${required}`, `Idempotency-Key obrigatoria em ${required}`);
    }
    assert.doesNotMatch(source.component + source.actionForm + source.page, /accessToken|refreshToken|Authorization|Bearer|localStorage|sessionStorage/, 'Cobranca nao expoe tokens no browser');
    assert.doesNotMatch(source.component + source.actionForm + source.loader + source.policy, /\.reduce\(|parseFloat\(|parseInt\(|Math\.(?:round|floor|ceil)|Intl\.NumberFormat|toFixed\(|\+\s*(?:saldo|total|valor|pendente|declarado)|(?:saldo|total|valor|pendente|declarado)\s*\+/, 'Cobranca nao calcula saldo ou promessa localmente');
    assert.doesNotMatch(source.component + source.actionForm + source.page + source.actions + source.loader, /\/app\/(?:agenda|comunicacoes|relatorios|configuracoes)\b|\/credit\/(?:agenda|comunicacoes|relatorios)\b/i, 'Cobranca nao antecipa Agenda/Comunicacao/Relatorios');
    for (const marker of ['loading', 'empty', 'denied', '404', 'Erro', 'overflow', 'Promessa declaratoria', 'Pagamento oficial apropriado', 'Valor declarado']) {
      assertText(source.component + source.componentTest + source.e2eTest, marker, `estado Cobranca ${marker}`);
    }
    for (const marker of ['409', '422']) {
      assertText(source.bffTest + source.contractTest, marker, `status Cobranca ${marker}`);
    }
    assertText(source.component, 'Caso de cobranca nao encontrado ou indisponivel.', 'UI Cobranca preserva 404 neutro');
    assertText(source.loader, 'Caso de cobranca nao encontrado ou indisponivel.', 'BFF Cobranca preserva 404 neutro');
    const packageJson = JSON.parse(source.packageJson);
    assertText(packageJson.scripts?.['test:cobranca'] ?? '', 'playwright.cobranca.config.ts', 'script Playwright Cobranca dedicado');
    assertText(packageJson.scripts?.['test:harness'] ?? '', 'npm run test:cobranca', 'harness inclui Cobranca');
    const manifest = JSON.parse(source.manifest);
    assert.strictEqual(manifest.baselineCount, 259, 'baseline IMP-295 exato');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 12, 'mutaveis IMP-295 exatos');
    assert.strictEqual(manifest.protectedBaselineCount, 247, 'protegidos IMP-295 exatos');
    assert.strictEqual(manifest.allowedNewPaths.length, 21, 'novos IMP-295 exatos');
    assert.strictEqual(manifest.expectedFinalCount, 280, 'inventario IMP-295 exato');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist IMP-295 usa paths exatos');
    assert.ok(!manifest.mutableBaselinePaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-295 nao libera backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.allowedNewPaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-295 nao cria backend/Product/Registry/OpenAPI');
    for (const [suffix, width, height] of [
      ['cobranca-list-desktop', 1440, 900],
      ['cobranca-list-mobile', 390, 844],
      ['cobranca-action-desktop', 1440, 900],
      ['cobranca-promessa-mobile', 390, 844],
    ]) {
      const relative = `docs/audits/evidence/frontend-mvp-imp-295-${suffix}.png`;
      const bytes = fs.readFileSync(path.join(ROOT, relative));
      assert.strictEqual(bytes.readUInt32BE(16), width, `${suffix} largura`);
      assert.strictEqual(bytes.readUInt32BE(20), height, `${suffix} altura`);
      assertText(source.report, crypto.createHash('sha256').update(bytes).digest('hex'), `relatorio publica SHA ${suffix}`);
    }
    assertText(source.plan, '**Versao:** 3.1.0', 'PLAN final IMP-298');
    assertText(source.backlog, '**Versao:** 3.1.0', 'backlog final IMP-298');
    assertText(source.discovery, '3.2.0', 'Discovery final IMP-298');
    assertText(source.matrix, '**Versao:** 3.9.0', 'matriz final IMP-298');
    const imp295 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-295');
    const imp296 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-296');
    assertText(imp295?.text ?? '', '- **Status:** Concluido.', 'IMP-295 deve estar concluido');
    assertText(imp296?.text ?? '', '- **Status:** Concluido.', 'IMP-296 deve estar concluido');
  },

  agendaComunicacao(source = readAgendaComunicacao()) {
    assert.match(source.loader, /^import "server-only";/, 'loader Agenda/Comunicacao deve ser server-only');
    assertText(source.packageJson, '"test:agenda"', 'package expoe gate Agenda/Comunicacao');
    assertText(source.workflow, 'npm run test:agenda', 'CI executa gate Agenda/Comunicacao');
    assertText(source.navigationPolicy, 'href: "/app/agenda"', 'navegacao Agenda/Comunicacao sob shell autenticado');
    assertText(source.loader, 'context.carteira_padrao.id', 'BFF Agenda/Comunicacao usa somente Carteira propria');
    assert.doesNotMatch(source.loader + source.page + source.actions, /searchParams\.(?:tenant_id|carteira_id)|query\.(?:tenant_id|carteira_id)|formData\.get\(["'](?:tenant_id|carteira_id)["']\)/, 'Agenda/Comunicacao nao aceita Tenant/Carteira do browser');
    for (const permission of ['agenda.ler', 'agenda.compromisso.gerir', 'agenda.lembrete.gerir', 'notificacao.conciliar', 'comunicacao.registrar', 'comunicacao.ler']) {
      assertText(source.policy + source.loader + source.unitTest + source.bffTest + source.navigationTest, permission, `permissao Agenda/Comunicacao ${permission}`);
    }
    assert.doesNotMatch(source.policy, /startsWith|includes\(permission\)|permission\.\*|["'](?:agenda|comunicacao|notificacao)\.[^"']*\*[^"']*["']/, 'RBAC Agenda/Comunicacao nao usa prefixo/wildcard');
    for (const endpoint of [
      '/credit/agenda',
      '/credit/carteiras/{carteira_id}/devedores/{devedor_id}/agenda/compromissos',
      '/credit/agenda/compromissos/{agenda_item_id}/lembretes',
      '/credit/agenda/compromissos/{agenda_item_id}/reagendar',
      '/credit/agenda/compromissos/{agenda_item_id}/concluir',
      '/credit/agenda/compromissos/{agenda_item_id}/cancelar',
      '/credit/agenda/lembretes/{lembrete_id}/reagendar',
      '/credit/agenda/lembretes/{lembrete_id}/enviar',
      '/credit/agenda/lembretes/{lembrete_id}/concluir',
      '/credit/agenda/lembretes/{lembrete_id}/cancelar',
      '/credit/carteiras/{carteira_id}/devedores/{devedor_id}/comunicacoes',
      '/credit/comunicacoes',
    ]) {
      assertText(source.loader + source.contractTest, endpoint, `endpoint oficial Agenda/Comunicacao ${endpoint}`);
    }
    assertText(source.loader + source.bffTest + source.contractTest, 'sem-idempotency:/credit/agenda', 'consulta Agenda nao inventa Idempotency-Key');
    assertText(source.loader + source.bffTest + source.contractTest, 'sem-idempotency:/credit/comunicacoes', 'consulta Comunicacao nao inventa Idempotency-Key');
    for (const required of [
      '/credit/carteiras/{carteira_id}/devedores/{devedor_id}/agenda/compromissos',
      '/credit/agenda/compromissos/{agenda_item_id}/lembretes',
      '/credit/agenda/compromissos/{agenda_item_id}/reagendar',
      '/credit/agenda/compromissos/{agenda_item_id}/concluir',
      '/credit/agenda/compromissos/{agenda_item_id}/cancelar',
      '/credit/agenda/lembretes/{lembrete_id}/reagendar',
      '/credit/agenda/lembretes/{lembrete_id}/enviar',
      '/credit/agenda/lembretes/{lembrete_id}/concluir',
      '/credit/agenda/lembretes/{lembrete_id}/cancelar',
      '/credit/carteiras/{carteira_id}/devedores/{devedor_id}/comunicacoes',
    ]) {
      assertText(source.loader + source.bffTest + source.contractTest, `Idempotency-Key:${required}`, `Idempotency-Key obrigatoria em ${required}`);
    }
    assert.doesNotMatch(source.component + source.commandDialog + source.page, /accessToken|refreshToken|Authorization|Bearer|localStorage|sessionStorage/, 'Agenda/Comunicacao nao expoe tokens no browser');
    assert.doesNotMatch(source.component + source.commandDialog + source.loader + source.policy, /\.reduce\(|parseFloat\(|parseInt\(|Math\.(?:round|floor|ceil)|Intl\.NumberFormat|toFixed\(|\+\s*(?:saldo|total|valor|pendente|declarado)|(?:saldo|total|valor|pendente|declarado)\s*\+/, 'Agenda/Comunicacao nao calcula financeiro localmente');
    assert.doesNotMatch(source.component + source.commandDialog + source.page + source.actions + source.loader, /\/app\/(?:relatorios|configuracoes|iam|automacao)\b|\/credit\/(?:relatorios|configuracoes-financeiras|automacao|notificacoes\/templates)\b/i, 'Agenda/Comunicacao nao antecipa Relatorios/Configuracoes/IAM/Automacao');
    for (const marker of ['loading', 'empty', 'denied', '404', 'Erro', 'overflow', 'Historico de comunicacao', 'Compromisso idempotente', 'Lembrete idempotente', 'Comunicacao idempotente']) {
      assertText(source.component + source.commandDialog + source.componentTest + source.e2eTest, marker, `estado Agenda/Comunicacao ${marker}`);
    }
    for (const marker of ['409', '422']) {
      assertText(source.bffTest + source.contractTest, marker, `status Agenda/Comunicacao ${marker}`);
    }
    assertText(source.component, 'Agenda ou comunicacao nao encontrada ou indisponivel.', 'UI Agenda/Comunicacao preserva 404 neutro');
    assertText(source.loader, 'Agenda ou comunicacao nao encontrada ou indisponivel.', 'BFF Agenda/Comunicacao preserva 404 neutro');
    const packageJson = JSON.parse(source.packageJson);
    assertText(packageJson.scripts?.['test:agenda'] ?? '', 'playwright.agenda.config.ts', 'script Playwright Agenda dedicado');
    assertText(packageJson.scripts?.['test:harness'] ?? '', 'npm run test:agenda', 'harness inclui Agenda/Comunicacao');
    const manifest = JSON.parse(source.manifest);
    assert.strictEqual(manifest.baselineCount, 280, 'baseline IMP-296 exato');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist IMP-296 usa paths exatos');
    assert.ok(!manifest.mutableBaselinePaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-296 nao libera backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.allowedNewPaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-296 nao cria backend/Product/Registry/OpenAPI');
    for (const [suffix, width, height] of [
      ['agenda-list-desktop', 1440, 900],
      ['agenda-list-mobile', 390, 844],
      ['agenda-command-desktop', 1440, 900],
      ['comunicacao-flow-mobile', 390, 844],
    ]) {
      const relative = `docs/audits/evidence/frontend-mvp-imp-296-${suffix}.png`;
      const bytes = fs.readFileSync(path.join(ROOT, relative));
      assert.strictEqual(bytes.readUInt32BE(16), width, `${suffix} largura`);
      assert.strictEqual(bytes.readUInt32BE(20), height, `${suffix} altura`);
      assertText(source.report, crypto.createHash('sha256').update(bytes).digest('hex'), `relatorio publica SHA ${suffix}`);
    }
    assertText(source.plan, '**Versao:** 3.1.0', 'PLAN final IMP-298');
    assertText(source.backlog, '**Versao:** 3.1.0', 'backlog final IMP-298');
    assertText(source.discovery, '3.2.0', 'Discovery final IMP-298');
    assertText(source.matrix, '**Versao:** 3.9.0', 'matriz final IMP-298');
    const imp296 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-296');
    const imp297 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-297');
    assertText(imp296?.text ?? '', '- **Status:** Concluido.', 'IMP-296 deve estar concluido');
    assertText(imp297?.text ?? '', '- **Status:** Concluido.', 'IMP-297 deve estar concluido');
  },

  formatoBrasileiro(source = readFormatoBrasileiro()) {
    // O modulo formata dinheiro para exibicao. Ele entra nesta varredura de
    // proposito: o guardrail anti-motor-paralelo veta conversao numerica nas
    // telas financeiras, e a saida correta foi respeitar a regra e ampliar a
    // cobertura, nao abrir excecao nela (PLAN-029 secao 5).
    assert.doesNotMatch(
      source.modulo,
      /Intl\.NumberFormat|toFixed\(|parseFloat\(|parseInt\(|Number\(|\.reduce\(|Math\./,
      'formatacao nao converte valor financeiro para numero',
    );
    assert.doesNotMatch(source.modulo, /new Date|Date\.now/, 'formatacao de data nao usa Date, que aplicaria fuso do navegador');
    assertText(source.modulo, 'agruparMilhares', 'formatacao agrupa milhares por manipulacao de texto');
    for (const esperado of ['R$ 10.000,00', '390.533.447-05', '17/08/2026']) {
      assertText(source.teste, esperado, `teste fixa formato ${esperado}`);
    }
    assertText(source.teste, '01/01/2026', 'teste cobre meia-noite UTC, que deslocaria o dia via Date');
  },

  bffErrorSanitization(source = readBffErrorSanitization()) {
    assertText(source.testPlan, 'node scripts/tests/test-bff-error-sanitization-scope.js', 'contrato documental aponta para scope corrente de sanitizacao BFF');
    assertText(source.report, 'Sanitizacao transversal de erros BFF', 'relatorio registra hardening transversal');
    assertText(source.report, 'IMP-297 permanece Planejado', 'relatorio nao autoriza IMP-297');

    const manifest = JSON.parse(source.manifest);
    assert.strictEqual(manifest.baselineCount, 301, 'baseline de sanitizacao BFF exato');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 12, 'allowlist mutavel de sanitizacao BFF');
    assert.strictEqual(manifest.protectedBaselineCount, 289, 'sanitizacao BFF protege 289 paths');
    assert.strictEqual(manifest.allowedNewPaths.length, 3, 'allowlist nova de sanitizacao BFF');
    assert.strictEqual(manifest.expectedFinalCount, 304, 'inventario final de sanitizacao BFF');
    assert.ok(manifest.mutableBaselinePaths.every((relative) => !relative.endsWith('/')), 'allowlist mutavel de sanitizacao usa paths exatos');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist nova de sanitizacao usa paths exatos');
    for (const forbidden of ['src/', 'migrations/', 'tests/', 'docs/product/', 'docs/governance/registry/', 'docs/governance/contracts/openapi/', 'frontend/package-lock.json']) {
      assert.ok(!manifest.mutableBaselinePaths.some((relative) => relative.startsWith(forbidden)), `sanitizacao nao libera ${forbidden}`);
      assert.ok(!manifest.allowedNewPaths.some((relative) => relative.startsWith(forbidden)), `sanitizacao nao cria ${forbidden}`);
    }

    const modules = [
      ['Devedores', source.devedoresLoader, source.devedoresTest, 'Nao foi possivel concluir a operacao de Devedores.'],
      ['Comercial', source.comercialLoader, source.comercialTest, 'Nao foi possivel concluir a operacao Comercial.'],
      ['Contratos', source.contratosLoader, source.contratosTest, 'Nao foi possivel concluir a operacao de Contratos.'],
      ['Motor', source.motorLoader, source.motorTest, 'Nao foi possivel concluir a operacao do Motor.'],
      ['Cobranca', source.cobrancaLoader, source.cobrancaTest, 'Nao foi possivel concluir a operacao de Cobranca.'],
    ];
    for (const [label, loader, testSource, safeMessage] of modules) {
      assert.doesNotMatch(loader, /mensagem:\s*errorBody\.mensagem/, `${label} nao repassa mensagem bruta do backend`);
      assertText(loader, 'const selectedCorrelation = responseCorrelation(response, fallback);', `${label} seleciona correlation uma vez`);
      assertText(loader, safeMessage, `${label} publica mensagem segura`);
      assertText(testSource, 'expect(result.problem.mensagem).not.toContain("cross-carteira");', `${label} testa nao vazamento em todos os status estruturados`);
      assert.doesNotMatch(testSource, /status === 404 \|\| status === 500/, `${label} nao limita sanitizacao a 404/500`);
    }
    assert.doesNotMatch(source.agendaLoader, /mensagem:\s*errorBody\.mensagem/, 'Agenda permanece sem mensagem bruta');

    const imp299 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-299');
    const imp300 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-300');
    assertText(imp299?.text ?? '', '- **Status:** Concluido.', 'IMP-299 deve estar concluido');
    assertText(imp300?.text ?? '', '- **Status:** Concluido.', 'IMP-300 deve estar concluido');
  },

  relatorios(source = readRelatorios()) {
    assert.match(source.loader, /^import "server-only";/, 'loader Relatorios deve ser server-only');
    assertText(source.packageJson, '"test:relatorios"', 'package expoe gate Relatorios');
    assertText(source.workflow, 'npm run test:relatorios', 'CI executa gate Relatorios');
    assertText(source.navigationPolicy, 'href: "/app/relatorios"', 'navegacao Relatorios sob shell autenticado');
    assertText(source.loader, 'context.carteira_padrao.id', 'BFF Relatorios usa somente Carteira propria');
    assert.doesNotMatch(source.loader + source.page, /searchParams\.(?:tenant_id|carteira_id)|query\.(?:tenant_id|carteira_id)|formData\.get\(["'](?:tenant_id|carteira_id)["']\)/, 'Relatorios nao aceita Tenant/Carteira do browser');
    assertText(source.policy + source.loader + source.unitTest + source.bffTest + source.navigationTest, 'relatorios.operacionais.ler', 'permissao Relatorios exata');
    assert.doesNotMatch(source.policy, /startsWith|includes\(permission\)|permission\.\*|["']relatorios\.[^"']*\*[^"']*["']/, 'RBAC Relatorios nao usa prefixo/wildcard');
    for (const endpoint of [
      '/credit/carteiras/{carteira_id}/relatorios/resumo',
      '/credit/carteiras/{carteira_id}/relatorios/vencimentos',
      '/credit/carteiras/{carteira_id}/relatorios/pagamentos',
      '/credit/carteiras/{carteira_id}/relatorios/fluxo',
    ]) {
      assertText(source.loader + source.contractTest, endpoint, `endpoint oficial Relatorios ${endpoint}`);
    }
    assertText(source.loader + source.bffTest + source.contractTest, 'sem-idempotency:/credit/carteiras/{carteira_id}/relatorios/resumo', 'resumo nao inventa Idempotency-Key');
    assertText(source.loader + source.bffTest + source.contractTest, 'sem-idempotency:/credit/carteiras/{carteira_id}/relatorios/pagamentos', 'pagamentos nao inventa Idempotency-Key');
    assert.doesNotMatch(source.loader, /Idempotency-Key/, 'loader Relatorios nao pode enviar Idempotency-Key');
    assert.doesNotMatch(source.loader + source.policy + source.component, /\.reduce\(|parseFloat\(|parseInt\(|Math\.(?:round|floor|ceil)|Intl\.NumberFormat|toFixed\(|\+\s*(?:saldo|total|valor|previsto|realizado)|(?:saldo|total|valor|previsto|realizado)\s*\+/, 'Relatorios nao calcula financeiro localmente');
    assert.doesNotMatch(source.component, /\.(?:operacoes_quitadas|parcela_ids|pagamento_ids)\.length\b/, 'Relatorios nao deriva contagens locais de arrays oficiais');
    assert.doesNotMatch(source.component + source.page + source.loader, /\/app\/(?:configuracoes|iam|automacao)\b|\/credit\/(?:configuracoes-financeiras|automacao|notificacoes\/templates)\b/i, 'Relatorios nao antecipa Configuracoes/IAM/Automacao');
    for (const marker of ['loading', 'empty', 'denied', '400', '403', '404', '500', 'overflow', 'Resumo oficial', 'Pagamentos oficiais', 'Acertos e recebimentos por dia']) {
      assertText(source.component + source.componentTest + source.e2eTest + source.loading, marker, `estado Relatorios ${marker}`);
    }
    assertText(source.component, 'Dados de relatorio nao encontrados ou indisponiveis.', 'UI Relatorios preserva 404 neutro');
    assertText(source.loader, 'Dados de relatorio nao encontrados ou indisponiveis.', 'BFF Relatorios preserva 404 neutro');
    assertText(source.loader + source.bffTest, 'Nao foi possivel concluir a consulta de Relatorios.', 'Relatorios sanitiza mensagem backend estruturada');
    assert.doesNotMatch(source.loader, /mensagem:\s*errorBody\.mensagem/, 'Relatorios nao repassa mensagem bruta backend');
    const packageJson = JSON.parse(source.packageJson);
    assertText(packageJson.scripts?.['test:relatorios'] ?? '', 'playwright.relatorios.config.ts', 'script Playwright Relatorios dedicado');
    assertText(packageJson.scripts?.['test:harness'] ?? '', 'npm run test:relatorios', 'harness inclui Relatorios');
    const manifest = JSON.parse(source.manifest);
    assert.strictEqual(manifest.baselineCount, 304, 'baseline IMP-297 exato');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 10, 'allowlist mutavel IMP-297 exata');
    assert.strictEqual(manifest.protectedBaselineCount, 294, 'IMP-297 protege 294 paths');
    assert.strictEqual(manifest.allowedNewPaths.length, 20, 'allowlist nova IMP-297 exata');
    assert.strictEqual(manifest.expectedFinalCount, 324, 'inventario final IMP-297 exato');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist IMP-297 usa paths exatos');
    assert.ok(!manifest.mutableBaselinePaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-297 nao libera backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.allowedNewPaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-297 nao cria backend/Product/Registry/OpenAPI');
    for (const [suffix, width, height] of [
      ['relatorios-list-desktop', 1440, 900],
      ['relatorios-list-mobile', 390, 844],
      ['fluxo-desktop', 1440, 900],
      ['relatorios-states-mobile', 390, 844],
    ]) {
      const relative = `docs/audits/evidence/frontend-mvp-imp-297-${suffix}.png`;
      const bytes = fs.readFileSync(path.join(ROOT, relative));
      assert.strictEqual(bytes.readUInt32BE(16), width, `${suffix} largura`);
      assert.strictEqual(bytes.readUInt32BE(20), height, `${suffix} altura`);
      assertText(source.report, crypto.createHash('sha256').update(bytes).digest('hex'), `relatorio publica SHA ${suffix}`);
    }
    assertText(source.plan, '**Versao:** 3.1.0', 'PLAN final IMP-298');
    assertText(source.backlog, '**Versao:** 3.1.0', 'backlog final IMP-298');
    assertText(source.discovery, '3.2.0', 'Discovery final IMP-298');
    assertText(source.matrix, '**Versao:** 3.9.0', 'matriz final IMP-298');
    const imp297 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-297');
    const imp298 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-298');
    const imp299 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-299');
    const imp300 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-300');
    assertText(imp297?.text ?? '', '- **Status:** Concluido.', 'IMP-297 deve estar concluido');
    assertText(imp298?.text ?? '', '- **Status:** Concluido.', 'IMP-298 deve estar concluido');
    assertText(imp299?.text ?? '', '- **Status:** Concluido.', 'IMP-299 deve estar concluido');
    assertText(imp300?.text ?? '', '- **Status:** Concluido.', 'IMP-300 deve estar concluido');
  },

  configuracoes(source = readConfiguracoes()) {
    assert.match(source.loader, /^import "server-only";/, 'loader Configuracoes Financeiras deve ser server-only');
    assertText(source.packageJson, '"test:configuracoes"', 'package expoe gate Configuracoes Financeiras');
    assertText(source.workflow, 'npm run test:configuracoes', 'CI executa gate Configuracoes Financeiras');
    assertText(source.navigationPolicy, 'href: "/app/configuracoes-financeiras"', 'navegacao Configuracoes sob shell autenticado');
    assertText(source.navigationPolicy + source.navigationTest, 'configuracoes_financeiras.configuracao.ler', 'navegacao Configuracoes exige permissao exata');
    assertText(source.loader, 'context.carteira_padrao.id', 'BFF Configuracoes usa Carteira operacional propria');
    assert.doesNotMatch(source.loader + source.page + source.actions, /searchParams\.(?:tenant_id|carteira_id)|query\.(?:tenant_id|carteira_id)|formData\.get\(["'](?:tenant_id|carteira_id)["']\)/, 'Configuracoes nao aceita Tenant/Carteira do browser');
    for (const permission of [
      'configuracoes_financeiras.configuracao.ler',
      'configuracoes_financeiras.configuracao.gerir',
      'configuracoes_financeiras.configuracao.aprovar',
      'configuracoes_financeiras.configuracao.ativar',
      'configuracoes_financeiras.modalidade.gerir',
      'configuracoes_financeiras.calendario.gerir',
      'configuracoes_financeiras.snapshot.capturar',
    ]) {
      assertText(source.policy + source.loader + source.unitTest + source.bffTest + source.navigationTest, permission, `permissao Configuracoes ${permission}`);
    }
    assert.doesNotMatch(source.policy, /startsWith|includes\(permission\)|permission\.\*|["']configuracoes_financeiras\.[^"']*\*[^"']*["']/, 'RBAC Configuracoes nao usa prefixo/wildcard');
    for (const endpoint of [
      '/credit/configuracoes-financeiras',
      '/credit/configuracoes-financeiras/vigente',
      '/credit/configuracoes-financeiras/{configuracao_id}',
      '/credit/configuracoes-financeiras/{configuracao_id}/aprovar',
      '/credit/configuracoes-financeiras/{configuracao_id}/programar',
      '/credit/configuracoes-financeiras/{configuracao_id}/ativar',
      '/credit/configuracoes-financeiras/{configuracao_id}/inativar',
      '/credit/configuracoes-financeiras/modalidades',
      '/credit/configuracoes-financeiras/calendarios',
      '/credit/configuracoes-financeiras/snapshots',
    ]) {
      assertText(source.loader + source.contractTest, endpoint, `endpoint oficial Configuracoes ${endpoint}`);
    }
    assertText(source.contractTest, '13 operacoes oficiais', 'contrato Configuracoes conta 13 operacoes');
    assertText(source.loader + source.bffTest + source.contractTest, 'Idempotency-Key:/credit/configuracoes-financeiras', 'Configuracoes envia Idempotency-Key em criacao');
    assertText(source.loader + source.bffTest + source.contractTest, 'Idempotency-Key:/credit/configuracoes-financeiras/snapshots', 'Configuracoes envia Idempotency-Key em snapshot');
    assertText(source.loader, 'Idempotency-Key', 'loader Configuracoes envia Idempotency-Key nos comandos');
    assert.doesNotMatch(source.loader + source.policy + source.component + source.actionForm, /\.reduce\(|parseFloat\(|parseInt\(|Math\.(?:round|floor|ceil)|Intl\.NumberFormat|toFixed\(|\+\s*(?:taxa|juros|valor|saldo|parcela|total)|(?:taxa|juros|valor|saldo|parcela|total)\s*\+/, 'Configuracoes nao calcula financeiro localmente');
    assert.doesNotMatch(source.component + source.actionForm + source.page + source.actions + source.loader, /\/app\/(?:iam|automacao|templates)\b|\/credit\/(?:automacao|notificacoes\/templates)\b/i, 'Configuracoes nao antecipa IAM/Automacao/Templates');
    for (const marker of ['loading', 'empty', 'denied', '400', '403', '404', '409', '422', '500', 'overflow', 'Configuracoes cadastradas', 'Configuracao vigente', 'Modalidades', 'Calendarios']) {
      assertText(source.component + source.componentTest + source.e2eTest + source.loading, marker, `estado Configuracoes ${marker}`);
    }
    assertText(source.component, 'Configuracao Financeira nao encontrada ou indisponivel.', 'UI Configuracoes preserva 404 neutro');
    assertText(source.loader, 'Configuracao Financeira nao encontrada ou indisponivel.', 'BFF Configuracoes preserva 404 neutro');
    assertText(source.loader + source.bffTest, 'Nao foi possivel concluir Configuracoes Financeiras.', 'Configuracoes sanitiza mensagem backend estruturada');
    assert.doesNotMatch(source.loader, /mensagem:\s*errorBody\.mensagem/, 'Configuracoes nao repassa mensagem bruta backend');
    const packageJson = JSON.parse(source.packageJson);
    assertText(packageJson.scripts?.['test:configuracoes'] ?? '', 'playwright.configuracoes.config.ts', 'script Playwright Configuracoes dedicado');
    assertText(packageJson.scripts?.['test:harness'] ?? '', 'npm run test:configuracoes', 'harness inclui Configuracoes');
    const manifest = JSON.parse(source.manifest);
    assert.strictEqual(manifest.baselineCount, 324, 'baseline IMP-298 exato');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 9, 'allowlist mutavel IMP-298 exata');
    assert.strictEqual(manifest.protectedBaselineCount, 315, 'IMP-298 protege 315 paths');
    assert.strictEqual(manifest.allowedNewPaths.length, 22, 'allowlist nova IMP-298 exata');
    assert.strictEqual(manifest.expectedFinalCount, 346, 'inventario final IMP-298 exato');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist IMP-298 usa paths exatos');
    assert.ok(!manifest.mutableBaselinePaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-298 nao libera backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.allowedNewPaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-298 nao cria backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.mutableBaselinePaths.includes('frontend/package-lock.json'), 'lockfile fica imutavel no IMP-298');
    for (const [suffix, width, height] of [
      ['configuracoes-desktop', 1440, 900],
      ['configuracoes-mobile', 390, 844],
      ['configuracoes-states-desktop', 1440, 900],
      ['configuracoes-states-mobile', 390, 844],
    ]) {
      const relative = `docs/audits/evidence/frontend-mvp-imp-298-${suffix}.png`;
      const bytes = fs.readFileSync(path.join(ROOT, relative));
      assert.strictEqual(bytes.readUInt32BE(16), width, `${suffix} largura`);
      assert.strictEqual(bytes.readUInt32BE(20), height, `${suffix} altura`);
      assertText(source.report, crypto.createHash('sha256').update(bytes).digest('hex'), `relatorio publica SHA ${suffix}`);
    }
    assertText(source.plan, '**Versao:** 3.1.0', 'PLAN final IMP-298');
    assertText(source.backlog, '**Versao:** 3.1.0', 'backlog final IMP-298');
    assertText(source.discovery, '3.2.0', 'Discovery final IMP-298');
    assertText(source.matrix, '**Versao:** 3.9.0', 'matriz final IMP-298');
    const imp298 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-298');
    const imp299 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-299');
    const imp300 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-300');
    assertText(imp298?.text ?? '', '- **Status:** Concluido.', 'IMP-298 deve estar concluido');
    assertText(imp299?.text ?? '', '- **Status:** Concluido.', 'IMP-299 deve estar concluido');
    assertText(imp300?.text ?? '', '- **Status:** Concluido.', 'IMP-300 deve estar concluido');
  },

  iam(source = readIam()) {
    assert.match(source.loader, /^import "server-only";/, 'loader IAM deve ser server-only');
    assertText(source.packageJson, '"test:iam"', 'package expoe gate IAM');
    assertText(source.workflow, 'npm run test:iam', 'CI executa gate IAM');
    assertText(source.navigationPolicy, 'href: "/app/iam"', 'navegacao IAM sob shell autenticado');
    for (const permission of ['perfil.ler', 'perfil.gerir']) {
      assertText(source.policy + source.loader + source.unitTest + source.bffTest + source.navigationTest, permission, `permissao IAM ${permission}`);
    }
    assert.doesNotMatch(source.policy, /startsWith|includes\(permission\)|permission\.\*|["']perfil\.[^"']*\*[^"']*["']/, 'RBAC IAM nao usa prefixo/wildcard');
    for (const endpoint of [
      '/iam/perfis',
      '/iam/perfis/{perfil_id}',
      '/iam/perfis/{perfil_id}/inativar',
      '/iam/perfis/{perfil_id}/permissoes/{codigo}',
      '/iam/permissoes',
      '/iam/usuarios/{usuario_id}/perfil',
      '/iam/usuarios/{usuario_id}/perfil/{perfil_id}',
      '/iam/usuarios/{usuario_id}/permissoes',
    ]) {
      assertText(source.loader + source.contractTest, endpoint, `endpoint oficial IAM ${endpoint}`);
    }
    assertText(source.contractTest, '11 operacoes IAM permitidas', 'contrato IAM limita 11 operacoes permitidas');
    assert.doesNotMatch(source.loader + source.page + source.actions + source.component, /\/iam\/credencial|credencial\/redefinir|GET \/iam\/usuarios["']|\/iam\/usuarios\?(?!.*permissoes)/, 'IAM nao antecipa credenciais nem lista de Usuarios');
    assertText(source.component + source.componentTest + source.e2eTest, 'ID do usuario', 'IAM explicita ID do usuario sem listagem');
    assertText(source.report + source.backlog, 'Lacuna 7', 'IAM explicita limite da Lacuna 7');
    for (const required of [
      'POST /iam/perfis',
      'PATCH /iam/perfis/{perfil_id}',
      'POST /iam/perfis/{perfil_id}/inativar',
      'PUT /iam/perfis/{perfil_id}/permissoes/{codigo}',
      'DELETE /iam/perfis/{perfil_id}/permissoes/{codigo}',
      'DELETE /iam/usuarios/{usuario_id}/perfil',
      'PUT /iam/usuarios/{usuario_id}/perfil/{perfil_id}',
    ]) {
      assertText(source.contractTest, `Idempotency-Key:${required}`, `Idempotency-Key certificada para ${required}`);
    }
    for (const forbidden of [
      'GET /iam/perfis',
      'GET /iam/perfis/{perfil_id}',
      'GET /iam/permissoes',
      'GET /iam/usuarios/{usuario_id}/permissoes',
    ]) {
      assertText(source.contractTest + source.bffTest, `sem-idempotency:${forbidden}`, `consulta IAM nao inventa Idempotency-Key para ${forbidden}`);
    }
    assert.doesNotMatch(source.component + source.actionForm + source.page, /accessToken|refreshToken|Authorization|Bearer|localStorage|sessionStorage/, 'IAM nao expoe tokens no browser');
    assert.doesNotMatch(source.component + source.actionForm + source.page + source.actions + source.loader, /\/app\/(?:automacao|templates)\b|\/credit\/(?:automacao|notificacoes\/templates)\b/i, 'IAM nao antecipa Automacao/Templates');
    for (const marker of ['loading', 'empty', 'denied', '400', '403', '404', '409', '422', '500', 'overflow', 'Catalogo de permissoes', 'Perfis', 'Permissoes efetivas']) {
      assertText(source.component + source.componentTest + source.e2eTest + source.loading, marker, `estado IAM ${marker}`);
    }
    assertText(source.component, 'Recurso de acesso nao encontrado ou indisponivel.', 'UI IAM preserva 404 neutro');
    assertText(source.loader, 'Recurso IAM nao encontrado ou indisponivel.', 'BFF IAM preserva 404 neutro');
    assert.doesNotMatch(source.loader, /mensagem:\s*errorBody\.mensagem/, 'IAM nao repassa mensagem bruta backend');
    const packageJson = JSON.parse(source.packageJson);
    assertText(packageJson.scripts?.['test:iam'] ?? '', 'playwright.iam.config.ts', 'script Playwright IAM dedicado');
    assertText(packageJson.scripts?.['test:harness'] ?? '', 'npm run test:iam', 'harness inclui IAM');
    const manifest = JSON.parse(source.manifest);
    assert.strictEqual(manifest.baselineCount, 346, 'baseline IMP-299 exato');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 9, 'allowlist mutavel IMP-299 exata');
    assert.strictEqual(manifest.protectedBaselineCount, 337, 'IMP-299 protege 337 paths');
    assert.strictEqual(manifest.allowedNewPaths.length, 22, 'allowlist nova IMP-299 exata');
    assert.strictEqual(manifest.expectedFinalCount, 368, 'inventario final IMP-299 exato');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist IMP-299 usa paths exatos');
    assert.ok(!manifest.mutableBaselinePaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-299 nao libera backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.allowedNewPaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-299 nao cria backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.mutableBaselinePaths.includes('frontend/package-lock.json'), 'lockfile fica imutavel no IMP-299');
    for (const [suffix, width, height] of [
      ['iam-desktop', 1440, 900],
      ['iam-mobile', 390, 844],
      ['iam-states-desktop', 1440, 900],
      ['iam-states-mobile', 390, 844],
    ]) {
      const relative = `docs/audits/evidence/frontend-mvp-imp-299-${suffix}.png`;
      const bytes = fs.readFileSync(path.join(ROOT, relative));
      assert.strictEqual(bytes.readUInt32BE(16), width, `${suffix} largura`);
      assert.strictEqual(bytes.readUInt32BE(20), height, `${suffix} altura`);
      assertText(source.report, crypto.createHash('sha256').update(bytes).digest('hex'), `relatorio publica SHA ${suffix}`);
    }
    assertText(source.plan, '**Versao:** 3.1.0', 'PLAN final IMP-299');
    assertText(source.backlog, '**Versao:** 3.1.0', 'backlog final IMP-299');
    assertText(source.discovery, '3.2.0', 'Discovery final IMP-299');
    assertText(source.matrix, '**Versao:** 3.9.0', 'matriz final IMP-299');
    const imp299 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-299');
    const imp300 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-300');
    assertText(imp299?.text ?? '', '- **Status:** Concluido.', 'IMP-299 deve estar concluido');
    assertText(imp300?.text ?? '', '- **Status:** Concluido.', 'IMP-300 deve estar concluido');
  },

  automacao(source = readAutomacao()) {
    assert.match(source.loader, /^import "server-only";/, 'loader Automacao deve ser server-only');
    assertText(source.packageJson, '"test:automacao"', 'package expoe gate Automacao');
    assertText(source.workflow, 'npm run test:automacao', 'CI executa gate Automacao');
    assertText(source.navigationPolicy, 'href: "/app/automacao"', 'navegacao Automacao sob shell autenticado');
    for (const permission of [
      'automacao.job.consultar',
      'automacao.job.cancelar',
      'automacao.job.retry',
      'notificacao.consultar',
      'notificacao.template.gerir',
      'notificacao.conciliar',
    ]) {
      assertText(source.policy + source.loader + source.unitTest + source.bffTest + source.navigationTest, permission, `permissao Automacao ${permission}`);
    }
    assert.doesNotMatch(source.policy, /startsWith|includes\(permission\)|permission\.\*|["'](?:automacao|notificacao)\.[^"']*\*[^"']*["']/, 'RBAC Automacao nao usa prefixo/wildcard');
    for (const endpoint of [
      '/credit/automacao/jobs',
      '/credit/automacao/jobs/{job_id}',
      '/credit/automacao/jobs/{job_id}/cancelar',
      '/credit/automacao/jobs/{job_id}/retry',
      '/credit/notificacoes',
      '/credit/notificacoes/{notification_id}',
      '/credit/notificacoes/templates',
      '/credit/notificacoes/templates/{template_id}/aprovar',
      '/credit/notificacoes/templates/{template_id}/ativar',
      '/credit/notificacoes/{notification_id}/conciliar',
    ]) {
      assertText(source.loader + source.contractTest, endpoint, `endpoint oficial Automacao ${endpoint}`);
    }
    assertText(source.contractTest, '11 operacoes Automacao', 'contrato Automacao limita 11 operacoes permitidas');
    assert.doesNotMatch(source.loader + source.page + source.actions + source.component, /\/credit\/agenda\/lembretes\/[^"'\s]+\/enviar|disparo arbitrario|provider direto/i, 'Automacao nao antecipa envio arbitrario');
    assertText(source.loader + source.bffTest + source.contractTest, 'Idempotency-Key:/credit/notificacoes/{notification_id}/conciliar', 'conciliacao usa Idempotency-Key certificada');
    for (const idem of [
      'Idempotency-Key:/credit/automacao/jobs/{job_id}/cancelar',
      'Idempotency-Key:/credit/automacao/jobs/{job_id}/retry',
      'Idempotency-Key:/credit/notificacoes/templates',
      'Idempotency-Key:/credit/notificacoes/templates/{template_id}/aprovar',
      'Idempotency-Key:/credit/notificacoes/templates/{template_id}/ativar',
    ]) assertText(source.loader + source.bffTest + source.contractTest, idem, `Automacao envia ${idem}`);
    assert.doesNotMatch(source.component + source.actionForm + source.page, /accessToken|refreshToken|Authorization|Bearer|localStorage|sessionStorage/, 'Automacao nao expoe tokens no browser');
    assert.doesNotMatch(source.loader + source.policy + source.component + source.actionForm, /\.reduce\(|parseFloat\(|parseInt\(|Math\.(?:round|floor|ceil)|Intl\.NumberFormat|toFixed\(|\b(?:juros|mora|multa|amortiza|saldo|quitacao|renegocia)\w*/i, 'Automacao nao calcula financeiro localmente');
    assert.doesNotMatch(source.component + source.actionForm + source.page + source.actions + source.loader, /\/app\/(?:auditoria|observabilidade)\b|\/credit\/(?:workers|scheduler\/claim)\b/i, 'Automacao nao antecipa IMP-301/worker');
    for (const marker of ['loading', 'empty', 'denied', '400', '403', '404', '409', '422', '500', 'overflow', 'Jobs', 'Templates', 'Notificacoes']) {
      assertText(source.component + source.componentTest + source.e2eTest + source.loading, marker, `estado Automacao ${marker}`);
    }
    assertText(source.component, 'Automacao nao encontrada ou indisponivel', 'UI Automacao preserva 404 neutro');
    assertText(source.loader, 'Recurso de Automacao nao encontrado ou indisponivel.', 'BFF Automacao preserva 404 neutro');
    assert.doesNotMatch(source.loader, /mensagem:\s*errorBody\.mensagem/, 'Automacao nao repassa mensagem bruta backend');
    const packageJson = JSON.parse(source.packageJson);
    assertText(packageJson.scripts?.['test:automacao'] ?? '', 'playwright.automacao.config.ts', 'script Playwright Automacao dedicado');
    assertText(packageJson.scripts?.['test:harness'] ?? '', 'npm run test:automacao', 'harness inclui Automacao');
    const manifest = JSON.parse(source.manifest);
    assert.strictEqual(manifest.baselineCount, 368, 'baseline IMP-300 exato');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 9, 'allowlist mutavel IMP-300 exata');
    assert.strictEqual(manifest.protectedBaselineCount, 359, 'IMP-300 protege 359 paths');
    assert.strictEqual(manifest.allowedNewPaths.length, 22, 'allowlist nova IMP-300 exata');
    assert.strictEqual(manifest.expectedFinalCount, 390, 'inventario final IMP-300 exato');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist IMP-300 usa paths exatos');
    assert.ok(!manifest.mutableBaselinePaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-300 nao libera backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.allowedNewPaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-300 nao cria backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.mutableBaselinePaths.includes('frontend/package-lock.json'), 'lockfile fica imutavel no IMP-300');
    for (const [suffix, width, height] of [
      ['automacao-desktop', 1440, 900],
      ['automacao-mobile', 390, 844],
      ['automacao-states-desktop', 1440, 900],
      ['automacao-states-mobile', 390, 844],
    ]) {
      const relative = `docs/audits/evidence/frontend-mvp-imp-300-${suffix}.png`;
      const bytes = fs.readFileSync(path.join(ROOT, relative));
      assert.strictEqual(bytes.readUInt32BE(16), width, `${suffix} largura`);
      assert.strictEqual(bytes.readUInt32BE(20), height, `${suffix} altura`);
      assertText(source.report, crypto.createHash('sha256').update(bytes).digest('hex'), `relatorio publica SHA ${suffix}`);
    }
    assertText(source.plan, '**Versao:** 3.1.0', 'PLAN final IMP-300');
    assertText(source.backlog, '**Versao:** 3.1.0', 'backlog final IMP-300');
    assertText(source.discovery, '3.2.0', 'Discovery final IMP-300');
    assertText(source.matrix, '**Versao:** 3.9.0', 'matriz final IMP-300');
    const imp300 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-300');
    const imp301 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-301');
    const imp302 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-302');
    const imp303 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-303');
    assertText(imp300?.text ?? '', '- **Status:** Concluido.', 'IMP-300 deve estar concluido');
    assertText(imp301?.text ?? '', '- **Status:** Concluido.', 'IMP-301 deve estar concluido');
    assertText(imp302?.text ?? '', '- **Status:** Concluido.', 'IMP-302 deve estar concluido');
    assertText(imp303?.text ?? '', '- **Status:** Concluido.', 'IMP-303 deve estar concluido');
  },

  jornadas(source = readJornadas()) {
    assertText(source.packageJson, '"test:jornadas"', 'package expoe gate de jornadas compostas');
    assertText(source.packageJson, 'playwright.jornadas.config.ts', 'gate de jornadas usa Playwright dedicado');
    assertText(source.workflow, 'npm run test:jornadas', 'CI executa jornadas compostas');
    assertText(source.playwrightConfig, 'jornadas-e2e/real-stack.mjs', 'Playwright usa stack real governado');
    assertText(source.realStack, 'postgres:16', 'jornadas sobem PostgreSQL real');
    assertText(source.realStack, 'uvicorn', 'jornadas sobem FastAPI real');
    assertText(source.realStack, 'npm', 'jornadas sobem Next real');
    assertText(source.realStack, 'seed_integrated.py', 'jornadas executam seed deterministico');
    assertText(source.seed, 'Base.metadata.create_all', 'seed cria schema real a partir da metadata backend');
    assertText(source.seed, 'SqlAlchemyUnitOfWork', 'seed reutiliza UoW/repositories reais');
    for (const marker of [
      'login, refresh e logout',
      'acesso negado por RBAC',
      '404 neutro cross-scope',
      'Devedor -> Proposta',
      'Proposta -> Contrato -> Emprestimo',
      'pagamento repetido com a mesma chave',
      'consulta do Motor sem calculo local',
      'cobranca -> promessa -> agenda -> comunicacao',
      'automacao operacional',
      '5xx correlacionado',
    ]) {
      assertText(source.e2eTest + source.report, marker, `jornada composta ${marker}`);
    }
    assert.doesNotMatch(source.e2eTest + source.realStack + source.seed, /page\.route\(|route\.fulfill\(|backend-fixture|mock-only/i, 'IMP-301 nao pode substituir stack real por mock Playwright');
    assert.doesNotMatch(source.e2eTest + source.realStack + source.seed, /localStorage|sessionStorage|accessToken|refreshToken|Authorization:\s*["']Bearer/i, 'jornadas nao expoem tokens ao browser/teste');
    assert.doesNotMatch(source.e2eTest, /\.reduce\(|parseFloat\(|parseInt\(|Math\.(?:round|floor|ceil)|toFixed\(|\b(?:juros|mora|multa|amortiza|saldo|quitacao|renegocia)\w*/i, 'jornadas nao calculam financeiro no teste frontend');
    const manifest = JSON.parse(source.manifest);
    assert.strictEqual(manifest.baselineCount, 390, 'baseline IMP-301 exato');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 7, 'allowlist mutavel IMP-301 exata');
    assert.strictEqual(manifest.protectedBaselineCount, 383, 'IMP-301 protege 383 paths');
    assert.strictEqual(manifest.allowedNewPaths.length, 7, 'allowlist nova IMP-301 exata');
    assert.strictEqual(manifest.expectedFinalCount, 397, 'inventario final IMP-301 exato');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist IMP-301 usa paths exatos');
    assert.ok(!manifest.mutableBaselinePaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-301 nao libera backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.allowedNewPaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-301 nao cria backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.mutableBaselinePaths.includes('frontend/package-lock.json'), 'lockfile fica imutavel no IMP-301');
    assertText(source.plan, '**Versao:** 3.1.0', 'PLAN final IMP-301');
    assertText(source.backlog, '**Versao:** 3.1.0', 'backlog final IMP-301');
    assertText(source.discovery, '3.2.0', 'Discovery final IMP-301');
    assertText(source.matrix, '**Versao:** 3.9.0', 'matriz final IMP-301');
    const imp301 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-301');
    const imp302 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-302');
    const imp303 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-303');
    assertText(imp301?.text ?? '', '- **Status:** Concluido.', 'IMP-301 deve estar concluido');
    assertText(imp302?.text ?? '', '- **Status:** Concluido.', 'IMP-302 deve estar concluido');
    assertText(imp303?.text ?? '', '- **Status:** Concluido.', 'IMP-303 deve estar concluido');
  },

  certification(source = readCertification()) {
    assertText(source.packageJson, '"test:certification"', 'package expoe gate de certificacao');
    assertText(source.packageJson, 'ui-security-boundaries.mjs', 'gate de certificacao usa script dedicado');
    assertText(source.packageJson, 'npm run test:certification', 'harness inclui certificacao');
    assertText(source.workflow, 'npm run test:certification', 'CI executa certificacao UI/seguranca');
    assertText(source.certificationScript, 'docs/audits/evidence', 'certificacao varre evidencias visuais');
    assertText(source.certificationScript, 'frontend-mvp-imp-', 'certificacao cobre PNGs dos IMPs frontend');
    assertText(source.certificationScript, 'readPngDimensions', 'certificacao valida dimensoes PNG');
    assertText(source.certificationScript, '.next/static', 'certificacao varre bundle publico');
    assertText(source.certificationScript, 'Web Interface Guidelines', 'certificacao documenta regras de interface');
    for (const pattern of ['transition: all', 'outline-none', '<div', 'onClick', 'localStorage', 'sessionStorage', 'FRONTEND_BACKEND_URL', 'Bearer']) {
      assertText(source.certificationScript, pattern, `certificacao bloqueia ${pattern}`);
    }
    assertText(source.certificationScript, 'financePattern', 'certificacao possui scanner anti-calculo financeiro');
    assertText(source.report, '50 PNGs', 'relatorio registra evidencia visual agregada');
    assertText(source.report, 'bundle publico', 'relatorio registra varredura de bundle publico');
    assertText(source.report, 'Web Interface Guidelines', 'relatorio registra guideline usada');
    assertText(source.report, 'IMP-303 permanece Planejado', 'relatorio bloqueia proximo IMP');
    const manifest = JSON.parse(source.manifest);
    assert.strictEqual(manifest.baselineCount, 397, 'baseline IMP-302 exato');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 7, 'allowlist mutavel IMP-302 exata');
    assert.strictEqual(manifest.protectedBaselineCount, 390, 'IMP-302 protege 390 paths');
    assert.strictEqual(manifest.allowedNewPaths.length, 4, 'allowlist nova IMP-302 exata');
    assert.strictEqual(manifest.expectedFinalCount, 401, 'inventario final IMP-302 exato');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist IMP-302 usa paths exatos');
    assert.ok(!manifest.mutableBaselinePaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-302 nao libera backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.allowedNewPaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-302 nao cria backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.mutableBaselinePaths.includes('frontend/package-lock.json'), 'lockfile fica imutavel no IMP-302');
    assertText(source.plan, '**Versao:** 3.1.0', 'PLAN final IMP-302');
    assertText(source.backlog, '**Versao:** 3.1.0', 'backlog final IMP-302');
    assertText(source.discovery, '3.2.0', 'Discovery final IMP-302');
    assertText(source.matrix, '**Versao:** 3.9.0', 'matriz final IMP-302');
    const imp302 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-302');
    const imp303 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-303');
    assertText(imp302?.text ?? '', '- **Status:** Concluido.', 'IMP-302 deve estar concluido');
    assertText(imp303?.text ?? '', '- **Status:** Concluido.', 'IMP-303 deve estar concluido');
  },

  finalReadiness(source = readFinalReadiness()) {
    assert.doesNotMatch(source.workflow, /node scripts\/tests\/test-imp-302-scope\.js/, 'CI nao executa scope historico IMP-302 como corrente');
    assertText(source.report, 'Frontend MVP concluido localmente', 'relatorio final declara conclusao local');
    assertText(source.report, 'IMP-274..IMP-303', 'relatorio final cobre toda a faixa do frontend');
    assertText(source.report, '172/172', 'relatorio final preserva contrato documental IMP-302');
    assertText(source.report, '50 PNGs', 'relatorio final preserva evidencia visual agregada');
    assertText(source.report, '107 operacoes, 133 schemas', 'relatorio final preserva OpenAPI');
    assertText(source.report, '8dadf18eab0dad186044d71e832f72a5850661307d196187f2d0794b9d1d9ec1', 'relatorio final preserva SHA OpenAPI');
    assertText(source.report, 'CI remota nao observada', 'relatorio final nao inventa CI remota');
    assertText(source.report, 'avisos EOL', 'relatorio final registra caveat EOL');
    const manifest = JSON.parse(source.manifest);
    assert.strictEqual(manifest.baselineCount, 401, 'baseline IMP-303 exato');
    assert.strictEqual(manifest.mutableBaselinePaths.length, 66, 'allowlist mutavel IMP-303 exata');
    assert.strictEqual(manifest.protectedBaselineCount, 335, 'IMP-303 protege 335 paths');
    assert.strictEqual(manifest.allowedNewPaths.length, 3, 'allowlist nova IMP-303 exata');
    assert.strictEqual(manifest.expectedFinalCount, 404, 'inventario final IMP-303 exato');
    assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist IMP-303 usa paths exatos');
    assert.ok(!manifest.mutableBaselinePaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-303 nao libera backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.allowedNewPaths.some((relative) => /^(src|migrations|tests|docs\/product|docs\/governance\/registry|docs\/governance\/contracts\/openapi)\//.test(relative)), 'IMP-303 nao cria backend/Product/Registry/OpenAPI');
    assert.ok(!manifest.mutableBaselinePaths.includes('frontend/package-lock.json'), 'lockfile fica imutavel no IMP-303');
    assertText(source.plan, '**Versao:** 3.1.0', 'PLAN final do Frontend MVP');
    assertText(source.backlog, '**Versao:** 3.1.0', 'backlog final do Frontend MVP');
    assertText(source.discovery, '**Vers?o:** 3.2.0', 'Discovery final do Frontend MVP');
    assertText(source.matrix, '**Versao:** 3.9.0', 'matriz final do Frontend MVP');
    assertText(source.plan, 'Frontend MVP concluido localmente', 'PLAN declara conclusao local');
    assertText(source.backlog, 'Frontend MVP concluido localmente', 'backlog declara conclusao local');
    const imp303 = impBlocks(source.backlog).find(({ id }) => id === 'IMP-303');
    assertText(imp303?.text ?? '', '- **Status:** Concluido.', 'IMP-303 deve estar concluido');
    const api = JSON.parse(source.openapi);
    const httpMethods = new Set(['get', 'post', 'put', 'patch', 'delete', 'options', 'head', 'trace']);
    const operationCount = Object.values(api.paths ?? {}).flatMap((pathItem) => Object.keys(pathItem).filter((method) => httpMethods.has(method))).length;
    const schemaCount = Object.keys(api.components?.schemas ?? {}).length;
    // 105 apos o IMP-351 remover POST /platform/tenants e POST /auth/ativar.
    // Eram 107 desde o IMP-332, que acrescentou o estorno parcial de Pagamento.
    assert.strictEqual(operationCount, 107, 'OpenAPI reflete o endpoint do IMP-362');
    assert.strictEqual(schemaCount, 135, 'OpenAPI reflete o endpoint do IMP-362');
    const openapiSha = crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT, FINAL_READINESS_FILES.openapi))).digest('hex');
    assert.strictEqual(openapiSha, '23d8d91f5f5890ef5ca010d1fc45a458458e5028042c80e7e15dbf82052af76a', 'OpenAPI corresponde ao snapshot governado vigente');
  },
};

function validateAll(source) {
  contracts.filesAndRegistry(source);
  contracts.productDecision(source);
  contracts.matrix(source);
  contracts.gaps(source);
  contracts.backlog(source);
  contracts.hardening(source);
  contracts.gates(source);
}

const cases = [];
const test = (name, fn) => cases.push({ name, fn });

test('arquivos e Registry incluem PLAN-025 e US-125/126', () => contracts.filesAndRegistry(docs));
test('decisao Product reutiliza hierarquia sem artefato artificial', () => contracts.productDecision(docs));
test('matriz soma 106 operacoes e certifica endpoints IAM', () => contracts.matrix(docs));
test('sete lacunas possuem decisao, contrato, teste, pacote e impacto', () => contracts.gaps(docs));
test('backlog contem IMP-274..IMP-303 sem dependencia futura', () => contracts.backlog(docs));
test('snapshot e relatorio comprovam o hardening', () => contracts.hardening(docs));
test('gates aparecem no PLAN/backlog e suite integra docs:test', () => contracts.gates(docs));
test('IMP-284 materializa scaffold frontend governado', () => contracts.scaffold());
test('relatorio do IMP-284 registra evidencias e mantem IMP-285 sob judge', () => contracts.scaffoldEvidence(docs));
test('IMP-285 materializa harness executavel por categoria', () => contracts.harness());
test('evidencia historica do IMP-285 preserva suas fronteiras', () => contracts.harnessEvidence(docs));
test('baseline IMP-286 encadeia a evidencia imutavel do IMP-285', () => {
  const manifest = JSON.parse(docs.foundationManifest);
  const predecessor = path.join(ROOT, manifest.predecessor.path);
  const predecessorHash = crypto.createHash('sha256').update(fs.readFileSync(predecessor)).digest('hex');
  assert.strictEqual(manifest.predecessor.sha256, predecessorHash, 'hash predecessor IMP-285');
  assert.ok(manifest.allowedNewPaths.every((relative) => !relative.endsWith('/')), 'allowlist IMP-286 deve ser exata');
});
test('IMP-286 materializa design foundation acessivel e neutra', () => contracts.foundation());
test('evidencia do IMP-286 preserva escopo e mantem IMP-287 sob judge', () => contracts.foundationEvidence(docs));
test('evidencia historica do IMP-286 permanece encadeada ao IMP-285', () => {
  const manifest = JSON.parse(docs.foundationManifest);
  const predecessor = path.join(ROOT, manifest.predecessor.path);
  const predecessorHash = crypto.createHash('sha256').update(fs.readFileSync(predecessor)).digest('hex');
  assert.strictEqual(manifest.predecessor.sha256, predecessorHash, 'hash predecessor IMP-285');
});
test('IMP-287 materializa cliente OpenAPI governado', () => contracts.openapiClient());
test('evidencia do IMP-287 preserva escopo e mantem IMP-288 sob judge', () => contracts.openapiEvidence(docs));
test('IMP-288 materializa sessao e BFF server-only governados', () => contracts.bff());
test('IMP-289 materializa shell autenticado e contexto operacional governados', () => contracts.shell());
test('IMP-290 materializa Dashboard operacional governado', () => contracts.dashboard());
test('IMP-291 materializa Devedores governados', () => contracts.devedores());
test('IMP-292 materializa Comercial governado', () => contracts.comercial());
test('IMP-293 materializa Contratos governados', () => contracts.contratos());
test('IMP-294 materializa Motor e pagamentos governados', () => contracts.motor());
test('IMP-295 materializa Cobranca governada', () => contracts.cobranca());
test('IMP-296 materializa Agenda e Comunicacao governadas', () => contracts.agendaComunicacao());
test('hardening transversal sanitiza mensagens dos BFFs herdados', () => contracts.bffErrorSanitization());
test('IMP-316 formata valores sem converter para numero', () => contracts.formatoBrasileiro());
test('IMP-297 materializa Relatorios governados', () => contracts.relatorios());
test('IMP-298 materializa Configuracoes Financeiras governadas', () => contracts.configuracoes());
test('IMP-299 materializa IAM permitido governado', () => contracts.iam());
test('IMP-300 materializa Automacao governada', () => contracts.automacao());
test('IMP-301 certifica jornadas compostas em stack real', () => contracts.jornadas());
test('IMP-302 certifica UI seguranca e fronteiras', () => contracts.certification());
test('IMP-303 recertifica e publica relatorio final do Frontend MVP', () => contracts.finalReadiness());

test('mutacao IMP-295: inventar Idempotency-Key na fila e rejeitado', () => {
  const source = readCobranca();
  const loader = source.loader.replace('sem-idempotency:/credit/cobrancas/casos', 'Idempotency-Key:/credit/cobrancas/casos');
  assert.notStrictEqual(loader, source.loader);
  assert.throws(() => contracts.cobranca({ ...source, loader }));
});

test('mutacao IMP-295: remover Idempotency-Key de promessa e rejeitado', () => {
  const source = readCobranca();
  const loader = source.loader.replace('Idempotency-Key:/credit/cobrancas/casos/{cobranca_caso_id}/promessas', 'sem-idempotency:/credit/cobrancas/casos/{cobranca_caso_id}/promessas');
  assert.notStrictEqual(loader, source.loader);
  assert.throws(() => contracts.cobranca({ ...source, loader }));
});

test('mutacao IMP-295: usar prefixo de Permissao e rejeitado', () => {
  const source = readCobranca();
  const policy = source.policy.replace('new Set(permissions).has(permission)', 'permissions.some((value) => value.startsWith(permission))');
  assert.notStrictEqual(policy, source.policy);
  assert.throws(() => contracts.cobranca({ ...source, policy }));
});

test('mutacao IMP-295: calcular saldo local e rejeitado', () => {
  const source = readCobranca();
  assert.throws(() => contracts.cobranca({ ...source, component: `${source.component}\nconst saldo = casos.reduce((total, item) => total + parseFloat(item.total_pendente), 0);` }));
});

test('mutacao IMP-295: antecipar Agenda na Cobranca e rejeitado', () => {
  const source = readCobranca();
  assert.throws(() => contracts.cobranca({ ...source, component: `${source.component}\nconst href = "/app/agenda";` }));
});

test('mutacao IMP-295: reabrir IMP-296 e rejeitado', () => {
  const source = readCobranca();
  const block = impBlocks(source.backlog).find(({ id }) => id === 'IMP-296');
  assert.ok(block);
  const backlog = source.backlog.replace(block.text, block.text.replace('- **Status:** Concluido.', '- **Status:** Planejado.'));
  assert.throws(() => contracts.cobranca({ ...source, backlog }));
});
test('gate historico do IMP-289 permanece encadeado ao baseline IMP-290', () => {
  const current = JSON.parse(read('docs/audits/evidence/frontend-mvp-imp-290-protected-baseline.json'));
  const predecessor = fs.readFileSync(path.join(ROOT, current.predecessor.path));
  const predecessorHash = crypto.createHash('sha256').update(predecessor).digest('hex');
  assert.strictEqual(current.predecessor.sha256, predecessorHash, 'baseline IMP-290 encadeia o manifesto IMP-289');
});
test('gate historico do IMP-288 permanece encadeado ao baseline IMP-289', () => {
  const current = JSON.parse(read('docs/audits/evidence/frontend-mvp-imp-289-protected-baseline.json'));
  const predecessor = fs.readFileSync(path.join(ROOT, current.predecessor.path));
  const predecessorHash = crypto.createHash('sha256').update(predecessor).digest('hex');
  assert.strictEqual(current.predecessor.sha256, predecessorHash, 'baseline IMP-289 encadeia o manifesto IMP-288');
});
test('gate historico do IMP-287 permanece encadeado ao baseline IMP-288', () => {
  const current = JSON.parse(read('docs/audits/evidence/frontend-mvp-imp-288-protected-baseline.json'));
  const predecessor = fs.readFileSync(path.join(ROOT, current.predecessor.path));
  const predecessorHash = crypto.createHash('sha256').update(predecessor).digest('hex');
  assert.strictEqual(current.predecessor.sha256, predecessorHash, 'baseline IMP-288 encadeia o manifesto IMP-287');
});
test('contrato documental completo passa', () => validateAll(docs));

test('mutacao: remover IMP-303 e rejeitado', () => {
  const start = docs.backlog.indexOf('### IMP-303 -');
  const end = docs.backlog.indexOf('\n---', start);
  const altered = { ...docs, backlog: docs.backlog.slice(0, start) + docs.backlog.slice(end) };
  assert.throws(() => contracts.backlog(altered));
});

test('mutacao: dependencia futura e rejeitada', () => {
  const altered = { ...docs, backlog: docs.backlog.replace('**Dependencias:** IMP-274.', '**Dependencias:** IMP-303.') };
  assert.throws(() => contracts.backlog(altered));
});

test('mutacao: reduzir contagem OpenAPI e rejeitado', () => {
  const altered = { ...docs, matrix: docs.matrix.replace('| 13 | `configuracoes_', '| 12 | `configuracoes_') };
  assert.throws(() => contracts.matrix(altered));
});

test('mutacao: remover decisao da lacuna 5 e rejeitado', () => {
  const altered = { ...docs, plan: docs.plan.replace('## Lacuna 5 -', '## Gap cinco -') };
  assert.throws(() => contracts.gaps(altered));
});

test('mutacao: remover suite do docs:test e rejeitado', () => {
  const packageJson = JSON.parse(docs.packageJson);
  packageJson.scripts['docs:test'] = packageJson.scripts['docs:test'].replace(' && node scripts/tests/test-plan-025-contracts.js', '');
  assert.throws(() => contracts.gates({ ...docs, packageJson: JSON.stringify(packageJson) }));
});

test('mutacao: usar 105 como estado final e rejeitado', () => {
  const altered = {
    ...docs,
    backlog: docs.backlog.replace(
      /estado final apos IMP-283, com 107\s+operacoes/,
      'estado final apos IMP-283, com 105 operacoes',
    ),
  };
  assert.notStrictEqual(altered.backlog, docs.backlog, 'mutacao precisa alterar o backlog');
  assert.throws(() => contracts.backlog(altered));
});

test('mutacao: manter endpoints IAM apenas desejados no estado final e rejeitado', () => {
  const altered = {
    ...docs,
    backlog: docs.backlog.replace(
      /estado final apos IMP-283, com 107\s+operacoes e os dois endpoints IAM certificados/,
      'estado final apos IMP-283, com 107 operacoes e os dois endpoints IAM apenas desejados',
    ),
  };
  assert.notStrictEqual(altered.backlog, docs.backlog, 'mutacao precisa alterar o backlog');
  assert.throws(() => contracts.backlog(altered));
});

test('mutacao: remover distincao explicita do baseline historico e rejeitado', () => {
  const altered = {
    ...docs,
    backlog: docs.backlog.replace(
      'fotografia historica anterior ao hardening, com 105 operacoes',
      'estado corrente, com 105 operacoes',
    ),
  };
  assert.notStrictEqual(altered.backlog, docs.backlog, 'mutacao precisa alterar o backlog');
  assert.throws(() => contracts.backlog(altered));
});

test('mutacao IMP-284: relaxar TypeScript strict e rejeitado', () => {
  const scaffold = readScaffold();
  const tsconfig = JSON.parse(scaffold.tsconfig);
  tsconfig.compilerOptions.strict = false;
  assert.throws(() => contracts.scaffold({ ...scaffold, tsconfig: JSON.stringify(tsconfig) }));
});

test('mutacao IMP-284: permitir JavaScript sem check e rejeitado', () => {
  const scaffold = readScaffold();
  const tsconfig = JSON.parse(scaffold.tsconfig);
  tsconfig.compilerOptions.allowJs = true;
  assert.throws(() => contracts.scaffold({ ...scaffold, tsconfig: JSON.stringify(tsconfig) }));
});

test('mutacao IMP-284: antecipar Client Component fora da pagina inicial e rejeitado', () => {
  const scaffold = readScaffold();
  assert.throws(() => contracts.scaffold({ ...scaffold, page: `'use client';\n${scaffold.page}` }));
});

test('mutacao IMP-284: antecipar Server Action e rejeitado', () => {
  const scaffold = readScaffold();
  assert.throws(() => contracts.scaffold({ ...scaffold, implementation: `${scaffold.implementation}\n'use server';` }));
});

test('mutacao IMP-284: usar range de versao e rejeitado', () => {
  const scaffold = readScaffold();
  const packageJson = JSON.parse(scaffold.packageJson);
  packageJson.dependencies.next = '^16.3.0';
  assert.throws(() => contracts.scaffold({ ...scaffold, packageJson: JSON.stringify(packageJson) }));
});

test('mutacao IMP-284: remover build da CI e rejeitado', () => {
  const scaffold = readScaffold();
  const workflow = scaffold.workflow.replace('run: npm run build', 'run: echo build-removido');
  assert.notStrictEqual(workflow, scaffold.workflow, 'mutacao precisa alterar o workflow');
  assert.throws(() => contracts.scaffold({ ...scaffold, workflow }));
});

test('mutacao IMP-285: remover categoria de script e rejeitado', () => {
  const harness = readHarness();
  const packageJson = JSON.parse(harness.packageJson);
  delete packageJson.scripts['test:contract'];
  assert.throws(() => contracts.harness({ ...harness, packageJson: JSON.stringify(packageJson) }));
});

test('mutacao IMP-285: permitir zero testes e rejeitado', () => {
  const harness = readHarness();
  assert.throws(() => contracts.harness({
    ...harness,
    unitConfig: harness.unitConfig.replace('passWithNoTests: false', 'passWithNoTests: true'),
  }));
});

test('mutacao IMP-285: enfraquecer MSW fail-closed e rejeitado', () => {
  const harness = readHarness();
  assert.throws(() => contracts.harness({
    ...harness,
    componentSetup: harness.componentSetup.replace('onUnhandledRequest: "error"', 'onUnhandledRequest: "warn"'),
  }));
});

test('mutacao IMP-285: reutilizar servidor Playwright e rejeitado', () => {
  const harness = readHarness();
  assert.throws(() => contracts.harness({
    ...harness,
    playwrightConfig: harness.playwrightConfig.replace('reuseExistingServer: false', 'reuseExistingServer: true'),
  }));
});

test('mutacao IMP-285: remover publicacao de artifact e rejeitado', () => {
  const harness = readHarness();
  assert.throws(() => contracts.harness({
    ...harness,
    workflow: harness.workflow.replace('actions/upload-artifact@v4', 'artifact-removido'),
  }));
});

test('mutacao IMP-286: antecipar dependencia futura e rejeitado', () => {
  const harness = readHarness();
  const packageJson = JSON.parse(harness.packageJson);
  packageJson.dependencies.zod = '4.0.0';
  assert.throws(() => contracts.harness({ ...harness, packageJson: JSON.stringify(packageJson) }));
});

test('mutacao IMP-289: reabrir o proprio IMP concluido e rejeitado', () => {
  const start = docs.backlog.indexOf('### IMP-289 -');
  const end = docs.backlog.indexOf('### IMP-290 -', start);
  const block = docs.backlog.slice(start, end).replace('**Status:** Concluido.', '**Status:** Planejado.');
  assert.notStrictEqual(block, docs.backlog.slice(start, end), 'mutacao precisa reabrir IMP-289');
  const altered = { ...docs, backlog: docs.backlog.slice(0, start) + block + docs.backlog.slice(end) };
  assert.throws(() => contracts.backlog(altered));
});

test('mutacao IMP-285: permitir backend no manifesto e rejeitado', () => {
  const manifest = JSON.parse(docs.harnessManifest);
  manifest.allowedNewPaths.push('src/');
  assert.throws(() => contracts.harnessEvidence({ ...docs, harnessManifest: JSON.stringify(manifest) }));
});

test('mutacao IMP-285: ampliar allowlist para diretorio de testes e rejeitado', () => {
  const manifest = JSON.parse(docs.harnessManifest);
  manifest.allowedNewPaths.push('frontend/tests/');
  assert.throws(() => contracts.harnessEvidence({ ...docs, harnessManifest: JSON.stringify(manifest) }));
});

test('mutacao IMP-286: remover token semantico e rejeitado', () => {
  const foundation = readFoundation();
  assert.throws(() => contracts.foundation({
    ...foundation,
    globals: foundation.globals.replaceAll('--success:', '--success-removido:'),
  }));
});

test('mutacao IMP-286: inserir cor hardcoded em componente e rejeitado', () => {
  const foundation = readFoundation();
  assert.throws(() => contracts.foundation({ ...foundation, button: `${foundation.button}\n/* #fff */` }));
});

test('mutacao IMP-286: remover foco visivel e rejeitado', () => {
  const foundation = readFoundation();
  assert.throws(() => contracts.foundation({
    ...foundation,
    globals: foundation.globals.replaceAll(':focus-visible', ':foco-removido'),
  }));
});

test('mutacao IMP-286: remover reduced motion e rejeitado', () => {
  const foundation = readFoundation();
  assert.throws(() => contracts.foundation({
    ...foundation,
    globals: foundation.globals.replace('prefers-reduced-motion', 'motion-removido'),
  }));
});

test('mutacao IMP-286: remover axe do browser e rejeitado', () => {
  const foundation = readFoundation();
  assert.throws(() => contracts.foundation({
    ...foundation,
    axeTest: foundation.axeTest.replaceAll('AxeBuilder', 'AxeRemovido'),
  }));
});

test('mutacao IMP-286: remover viewport mobile e rejeitado', () => {
  const foundation = readFoundation();
  assert.throws(() => contracts.foundation({
    ...foundation,
    e2eTest: foundation.e2eTest.replaceAll('390', '391'),
  }));
});

test('mutacao IMP-286: proliferar estado booleano no Button e rejeitado', () => {
  const foundation = readFoundation();
  assert.throws(() => contracts.foundation({
    ...foundation,
    button: `${foundation.button}\ntype ModoInvalido = { isLoading?: boolean };`,
  }));
});

test('mutacao IMP-286: remover estado explicito e rejeitado', () => {
  const foundation = readFoundation();
  assert.throws(() => contracts.foundation({
    ...foundation,
    feedback: foundation.feedback.replaceAll('PermissionDeniedState', 'EstadoRemovido'),
  }));
});

test('mutacao IMP-286: ampliar allowlist para diretorio e rejeitado', () => {
  const manifest = JSON.parse(docs.foundationManifest);
  manifest.allowedNewPaths.push('frontend/src/components/');
  assert.throws(() => contracts.foundationEvidence({ ...docs, foundationManifest: JSON.stringify(manifest) }));
});

test('mutacao IMP-286: permitir backend no manifesto e rejeitado', () => {
  const manifest = JSON.parse(docs.foundationManifest);
  manifest.allowedNewPaths.push('src/emprestimo/presentation/api/falso.py');
  assert.throws(() => contracts.foundationEvidence({ ...docs, foundationManifest: JSON.stringify(manifest) }));
});

test('mutacao IMP-286: remover captura de console error e rejeitado', () => {
  const foundation = readFoundation();
  assert.throws(() => contracts.foundation({
    ...foundation,
    e2eTest: foundation.e2eTest.replace('page.on("console"', 'page.on("console-removido"'),
  }));
});

test('mutacao IMP-286: remover captura de pageerror e rejeitado', () => {
  const foundation = readFoundation();
  assert.throws(() => contracts.foundation({
    ...foundation,
    axeTest: foundation.axeTest.replace('page.on("pageerror"', 'page.on("pageerror-removido"'),
  }));
});

test('mutacao IMP-286: fazer lint analisar artifacts gerados e rejeitado', () => {
  const scaffold = readScaffold();
  const packageJson = JSON.parse(scaffold.packageJson);
  packageJson.scripts.lint = packageJson.scripts.lint.replace(' --ignore-pattern playwright-report', '');
  assert.throws(() => contracts.scaffold({ ...scaffold, packageJson: JSON.stringify(packageJson) }));
});

test('mutacao IMP-287: remover server-only e rejeitado', () => {
  const source = readOpenapiClient();
  assert.throws(() => contracts.openapiClient({
    ...source,
    client: source.client.replace('import "server-only";', ''),
  }));
});

test('mutacao IMP-287: apagar paths gerados com any e rejeitado', () => {
  const source = readOpenapiClient();
  assert.throws(() => contracts.openapiClient({
    ...source,
    client: source.client.replace('createClient<paths>', 'createClient<any>'),
  }));
});

test('mutacao IMP-287: introduzir cast contratual e rejeitado', () => {
  const source = readOpenapiClient();
  assert.throws(() => contracts.openapiClient({
    ...source,
    client: `${source.client}\nconst contrato = {} as unknown;\n`,
  }));
});

test('mutacao IMP-287: introduzir modelo manual paralelo e rejeitado', () => {
  const source = readOpenapiClient();
  assert.throws(() => contracts.openapiClient({
    ...source,
    client: `${source.client}\ninterface AuthLoginManual { segredo: string }\n`,
  }));
});

test('mutacao IMP-287: remover drift check da CI e rejeitado', () => {
  const source = readOpenapiClient();
  assert.throws(() => contracts.openapiClient({
    ...source,
    workflow: source.workflow.replace('run: npm run api:check', 'run: echo api-check-removido'),
  }));
});

test('mutacao IMP-287: remover canonicalizacao EOL do check e rejeitado', () => {
  const source = readOpenapiClient();
  assert.throws(() => contracts.openapiClient({
    ...source,
    codegen: source.codegen.replace('canonicalizeLineEndings(actual) !== expected', 'actual !== expected'),
  }));
});

test('mutacao IMP-287: remover typecheck do contrato e rejeitado', () => {
  const source = readOpenapiClient();
  const packageJson = JSON.parse(source.packageJson);
  packageJson.scripts['test:contract'] = packageJson.scripts['test:contract'].replace(' && npm run typecheck', '');
  assert.throws(() => contracts.openapiClient({ ...source, packageJson: JSON.stringify(packageJson) }));
});

test('mutacao IMP-287: remover suporte a checkout limpo da CI e rejeitado', () => {
  const source = readOpenapiClient();
  assert.throws(() => contracts.openapiClient({
    ...source,
    scopeScript: source.scopeScript.replace('`${manifest.head}...HEAD`', '`HEAD...HEAD`'),
  }));
});

test('mutacao IMP-287: negar frontend corrente no Discovery e rejeitado', () => {
  const altered = {
    ...docs,
    discovery: `${docs.discovery}\nNão existe aplicação frontend no estado atual.\n`,
  };
  assert.throws(() => contracts.openapiEvidence(altered));
});

test('mutacao IMP-287: antecipar Authorization no cliente e rejeitado', () => {
  const source = readOpenapiClient();
  assert.throws(() => contracts.openapiClient({
    ...source,
    client: `${source.client}\nconst Authorization = "Bearer futuro";\n`,
  }));
});

test('mutacao IMP-287: adicionar dependencia futura e rejeitado', () => {
  const source = readOpenapiClient();
  const packageJson = JSON.parse(source.packageJson);
  packageJson.dependencies['@tanstack/react-query'] = '5.0.0';
  assert.throws(() => contracts.scaffold({ ...readScaffold(), packageJson: JSON.stringify(packageJson) }));
});

test('mutacao IMP-288: remover server-only e rejeitado', () => {
  const source = readBff();
  assert.throws(() => contracts.bff({ ...source, session: source.session.replace('import "server-only";', '') }));
});

test('mutacao IMP-288: trocar JWE por codificacao nao autenticada e rejeitado', () => {
  const source = readBff();
  assert.throws(() => contracts.bff({ ...source, session: source.session.replace('new EncryptJWT', 'new TextEncoder') }));
});

for (const [name, fragment] of [
  ['HttpOnly', 'httpOnly: true'],
  ['SameSite', 'sameSite: "lax"'],
  ['Secure de producao', 'secure: config.production'],
]) {
  test(`mutacao IMP-288: remover ${name} e rejeitado`, () => {
    const source = readBff();
    assert.throws(() => contracts.bff({ ...source, session: source.session.replaceAll(fragment, `/* ${name} removido */`) }));
  });
}

test('mutacao IMP-288: aceitar secret default e rejeitado', () => {
  const source = readBff();
  assert.throws(() => contracts.bff({ ...source, session: `${source.session}\nconst sessionKey = "default-secret-inseguro";\n` }));
});

test('mutacao IMP-288: introduzir segredo NEXT_PUBLIC e rejeitado', () => {
  const source = readBff();
  assert.throws(() => contracts.bff({ ...source, envExample: `${source.envExample}\nNEXT_PUBLIC_SESSION_KEY=inseguro\n` }));
});

test('mutacao IMP-288: serializar token no JSON e rejeitado', () => {
  const source = readBff();
  assert.throws(() => contracts.bff({ ...source, backend: `${source.backend}\nResponse.json({ accessToken: "vazamento" });\n` }));
});

test('mutacao IMP-288: remover Origin e rejeitado', () => {
  const source = readBff();
  assert.throws(() => contracts.bff({ ...source, session: source.session.replace('origin !== config.origin', 'false') }));
});

test('mutacao IMP-288: remover CSRF e rejeitado', () => {
  const source = readBff();
  assert.throws(() => contracts.bff({ ...source, session: source.session.replace('csrf !== CSRF_HEADER_VALUE', 'false') }));
});

test('mutacao IMP-288: habilitar refresh fora de 401 e rejeitado', () => {
  const source = readBff();
  assert.throws(() => contracts.bff({ ...source, backend: source.backend.replace('if (firstResponse.status !== 401)', 'if (firstResponse.status !== 500)') }));
});

test('mutacao IMP-288: remover clone do replay e rejeitado', () => {
  const source = readBff();
  assert.throws(() => contracts.bff({ ...source, backend: source.backend.replaceAll('original.clone()', 'original') }));
});

test('mutacao IMP-288: repetir mutacao sem Idempotency-Key e rejeitado', () => {
  const source = readBff();
  assert.throws(() => contracts.bff({ ...source, backend: source.backend.replace('IDEMPOTENCY_PATTERN.test(key)', 'true') }));
});

test('mutacao IMP-288: introduzir any e rejeitado', () => {
  const source = readBff();
  assert.throws(() => contracts.bff({ ...source, backend: `${source.backend}\nconst bypass: any = {};\n` }));
});

test('mutacao IMP-288: restaurar terceiro correlation ID em respostas 2xx e rejeitado', () => {
  const source = readBff();
  const backend = source.backend.replaceAll(
    'responseCorrelationId(result.response, requestCorrelation)',
    'correlationId(result.response.headers.get("X-Correlation-ID") ?? requestCorrelation)',
  );
  assert.notStrictEqual(backend, source.backend, 'mutacao precisa restaurar o bug de correlation');
  assert.throws(() => contracts.bff({ ...source, backend }));
});

test('mutacao IMP-288: reduzir casos de correlation do logout e rejeitado', () => {
  const source = readBff();
  const bffTest = source.bffTest.replace(
    'it.each(RESPONSE_CORRELATION_CASES)(\n    "logout 2xx',
    'it.each(RESPONSE_CORRELATION_CASES.slice(0, 2))(\n    "logout 2xx',
  );
  assert.notStrictEqual(bffTest, source.bffTest, 'mutacao precisa reduzir os casos do logout');
  assert.throws(() => contracts.bff({ ...source, bffTest }));
});

test('mutacao IMP-288: alterar semantica dos casos de correlation e rejeitado', () => {
  const source = readBff();
  const semanticMutations = [
    [
      '  { label: "invalido", backendCorrelation: "correlation invalido", expected: CORRELATION },',
      '  { label: "invalido", backendCorrelation: "corr-backend-valid-288", expected: "corr-backend-valid-288" },',
    ],
    [
      '  { label: "ausente", backendCorrelation: undefined, expected: CORRELATION },',
      '  { label: "ausente", backendCorrelation: "corr-backend-valid-288", expected: "corr-backend-valid-288" },',
    ],
  ];

  for (const [original, replacement] of semanticMutations) {
    const bffTest = source.bffTest.replace(original, replacement);
    assert.notStrictEqual(bffTest, source.bffTest, 'mutacao precisa alterar a semantica da fixture');
    assert.throws(() => contracts.bff({ ...source, bffTest }));
  }
});

test('mutacao IMP-288: introduzir calculo financeiro e rejeitado', () => {
  const source = readBff();
  assert.throws(() => contracts.bff({ ...source, backend: `${source.backend}\nconst juros = 1;\n` }));
});

test('mutacao IMP-288: remover BFF da CI e rejeitado', () => {
  const source = readBff();
  assert.throws(() => contracts.bff({ ...source, workflow: source.workflow.replace('run: npm run test:bff', 'run: echo bff-removido') }));
});

test('mutacao IMP-288: ampliar allowlist para diretorio e rejeitado', () => {
  const source = readBff();
  const manifest = JSON.parse(source.manifest);
  manifest.allowedNewPaths.push('frontend/src/lib/bff/');
  assert.throws(() => contracts.bff({ ...source, manifest: JSON.stringify(manifest) }));
});

test('mutacao IMP-288: permitir backend no manifesto e rejeitado', () => {
  const source = readBff();
  const manifest = JSON.parse(source.manifest);
  manifest.allowedNewPaths.push('src/emprestimo/falso.py');
  assert.throws(() => contracts.bff({ ...source, manifest: JSON.stringify(manifest) }));
});

test('mutacao IMP-289: aceitar Tenant arbitrario no contexto e rejeitado', () => {
  const source = readShell();
  assert.throws(() => contracts.shell({ ...source, context: `${source.context}\nconst unsafe = "?tenant_id=externo";` }));
});

test('mutacao IMP-289: aceitar identidade divergente da sessao e rejeitado', () => {
  const source = readShell();
  const context = source.context.replace(' || !contextMatchesSession(payload, session)', '');
  assert.notStrictEqual(context, source.context);
  assert.throws(() => contracts.shell({ ...source, context }));
});

test('mutacao IMP-289: encaminhar status nao certificado do contexto e rejeitado', () => {
  const source = readShell();
  const context = source.context.replace('response.status !== 401 && response.status !== 409', 'response.status !== 404');
  assert.notStrictEqual(context, source.context);
  assert.throws(() => contracts.shell({ ...source, context }));
});

test('mutacao IMP-289: usar prefixo de Permissao e rejeitado', () => {
  const source = readShell();
  const navigationPolicy = source.navigationPolicy.replace('granted.has(destination.requiredPermission)', 'destination.requiredPermission.startsWith("permission")');
  assert.notStrictEqual(navigationPolicy, source.navigationPolicy);
  assert.throws(() => contracts.shell({ ...source, navigationPolicy }));
});

test('mutacao IMP-289: antecipar Dashboard na navegacao e rejeitado', () => {
  const source = readShell();
  const navigationPolicy = source.navigationPolicy.replace('label: "Inicio",', 'label: "Inicio",\n  },\n  { grupo: "principal", href: "/dashboard", label: "Dashboard paralelo"');
  assert.notStrictEqual(navigationPolicy, source.navigationPolicy);
  assert.throws(() => contracts.shell({ ...source, navigationPolicy }));
});

test('mutacao IMP-289: expor token no Client Component e rejeitado', () => {
  const source = readShell();
  assert.throws(() => contracts.shell({ ...source, loginForm: `${source.loginForm}\nconst accessToken = "vazado";` }));
});

test('mutacao IMP-289: remover guarda de loop do recovery e rejeitado', () => {
  const source = readShell();
  const recovery = source.recovery.replaceAll('started.current', 'false');
  assert.notStrictEqual(recovery, source.recovery);
  assert.throws(() => contracts.shell({ ...source, recovery }));
});

test('mutacao IMP-289: remover marcador entre montagens do recovery e rejeitado', () => {
  const source = readShell();
  const context = source.context.replace('cookies.set(recoveryAttemptCookieName(dependencies.config), "1", {', 'void ({');
  assert.notStrictEqual(context, source.context);
  assert.throws(() => contracts.shell({ ...source, context }));
});

test('mutacao IMP-289: manter PII apos logout local em erro remoto e rejeitado', () => {
  const source = readShell();
  const logoutButton = source.logoutButton.replace(
    '// O Route Handler sempre limpa o cookie local, mesmo quando o backend\n        // remoto falha. Remova imediatamente a PII da tela em toda resposta.',
    'if (!response.ok && response.status !== 401) return;',
  );
  assert.notStrictEqual(logoutButton, source.logoutButton);
  assert.throws(() => contracts.shell({ ...source, logoutButton }));
});

test('mutacao IMP-289: remover caso 409 da suite BFF e rejeitado', () => {
  const source = readShell();
  const bffTest = source.bffTest.replace('409 de contexto incompleto', 'conflito generico');
  assert.notStrictEqual(bffTest, source.bffTest);
  assert.throws(() => contracts.shell({ ...source, bffTest }));
});

test('mutacao IMP-289: remover Playwright da CI e rejeitado', () => {
  const source = readShell();
  assert.throws(() => contracts.shell({ ...source, workflow: source.workflow.replace('run: npm run test:session', 'run: echo sessao-removida') }));
});

test('mutacao IMP-289: ampliar allowlist para diretorio e rejeitado', () => {
  const source = readShell();
  const manifest = JSON.parse(source.manifest);
  manifest.allowedNewPaths.push('frontend/src/components/shell/');
  assert.throws(() => contracts.shell({ ...source, manifest: JSON.stringify(manifest) }));
});

test('mutacao IMP-289: retirar hash de screenshot do relatorio e rejeitado', () => {
  const source = readShell();
  const bytes = fs.readFileSync(path.join(ROOT, 'docs/audits/evidence/frontend-mvp-imp-289-shell-mobile.png'));
  const hash = crypto.createHash('sha256').update(bytes).digest('hex');
  assert.throws(() => contracts.shell({ ...source, report: source.report.replace(hash, 'hash-removido') }));
});

test('mutacao IMP-289: reabrir IMP-296 e rejeitado', () => {
  const source = readShell();
  const block = impBlocks(source.backlog).find(({ id }) => id === 'IMP-296');
  assert.ok(block);
  const backlog = source.backlog.replace(block.text, block.text.replace('- **Status:** Concluido.', '- **Status:** Planejado.'));
  assert.throws(() => contracts.shell({ ...source, backlog }));
});

test('mutacao IMP-290: aceitar Carteira arbitraria na URL e rejeitado', () => {
  const source = readDashboard();
  assert.throws(() => contracts.dashboard({ ...source, page: `${source.page}\nconst unsafe = query.carteira_id;` }));
});

test('mutacao IMP-290: usar prefixo de Permissao e rejeitado', () => {
  const source = readDashboard();
  const policy = source.policy.replace('new Set(permissions).has(permission)', 'permissions.some((value) => value.startsWith(permission))');
  assert.notStrictEqual(policy, source.policy);
  assert.throws(() => contracts.dashboard({ ...source, policy }));
});

test('mutacao IMP-290: somar valores financeiros e rejeitado', () => {
  const source = readDashboard();
  assert.throws(() => contracts.dashboard({ ...source, component: `${source.component}\nconst total = itens.reduce((sum, item) => sum + parseFloat(item.valor), 0);` }));
});

test('mutacao IMP-290: ocultar erro como vazio e rejeitado', () => {
  const source = readDashboard();
  const bffTest = source.bffTest.replace('sem fabricar vazio', 'como vazio');
  assert.notStrictEqual(bffTest, source.bffTest);
  assert.throws(() => contracts.dashboard({ ...source, bffTest }));
});

test('mutacao IMP-290: remover correlation publico e rejeitado', () => {
  const source = readDashboard();
  const component = source.component.replace('Correlation ID:', 'Referencia:');
  assert.notStrictEqual(component, source.component);
  assert.throws(() => contracts.dashboard({ ...source, component }));
});

test('mutacao IMP-290: revelar body de erro backend e rejeitado', () => {
  const source = readDashboard();
  assert.throws(() => contracts.dashboard({ ...source, loader: `${source.loader}\nconst leaked = await response.json();` }));
});

test('mutacao IMP-290: aceitar qualquer 2xx e rejeitado', () => {
  const source = readDashboard();
  const loader = source.loader.replace('result.response.status !== 200', '!result.response.ok');
  assert.notStrictEqual(loader, source.loader);
  assert.throws(() => contracts.dashboard({ ...source, loader }));
});

test('mutacao IMP-290: remover campo nullable obrigatorio e rejeitado', () => {
  const source = readDashboard();
  const loader = source.loader.replace('requiredNullableDateTime(item, "atualizado_em")', 'true');
  assert.notStrictEqual(loader, source.loader);
  assert.throws(() => contracts.dashboard({ ...source, loader }));
});

test('mutacao IMP-290: normalizar date-time impossivel e rejeitado', () => {
  const source = readDashboard();
  const loader = source.loader.replaceAll('calendarPartsAreValid(year, month, day)', '!Number.isNaN(Date.parse(value))');
  assert.notStrictEqual(loader, source.loader);
  assert.throws(() => contracts.dashboard({ ...source, loader }));
});

test('mutacao IMP-290: fixar offset e ignorar IANA historica e rejeitado', () => {
  const source = readDashboard();
  const policy = source.policy.replace('timeZoneName: "longOffset"', 'timeZoneName: undefined');
  assert.notStrictEqual(policy, source.policy);
  assert.throws(() => contracts.dashboard({ ...source, policy }));
});

test('mutacao IMP-290: aceitar periodo sem validacao de calendario e rejeitado', () => {
  const source = readDashboard();
  const policy = source.policy.replace('calendarDateIsValid(raw)', 'true');
  assert.notStrictEqual(policy, source.policy);
  assert.throws(() => contracts.dashboard({ ...source, policy }));
});

test('mutacao IMP-290: usar relogio do browser e rejeitado', () => {
  const source = readDashboard();
  assert.throws(() => contracts.dashboard({ ...source, component: `"use client";\n${source.component}\nconst browserToday = new Date();` }));
});

test('mutacao IMP-290: expor token ao componente e rejeitado', () => {
  const source = readDashboard();
  assert.throws(() => contracts.dashboard({ ...source, component: `${source.component}\nconst accessToken = "vazado";` }));
});

test('mutacao IMP-290: antecipar link Devedores e rejeitado', () => {
  const source = readDashboard();
  assert.throws(() => contracts.dashboard({ ...source, component: `${source.component}\nconst href = "/devedores";` }));
});

test('mutacao IMP-290: criar comando POST e rejeitado', () => {
  const source = readDashboard();
  assert.throws(() => contracts.dashboard({ ...source, loader: `${source.loader}\nclient.POST("/credit/comando", {});` }));
});

test('mutacao IMP-290: ampliar allowlist para diretorio e rejeitado', () => {
  const source = readDashboard();
  const manifest = JSON.parse(source.manifest);
  manifest.allowedNewPaths.push('frontend/src/components/dashboard/');
  assert.throws(() => contracts.dashboard({ ...source, manifest: JSON.stringify(manifest) }));
});

test('mutacao IMP-290: liberar Product no manifesto e rejeitado', () => {
  const source = readDashboard();
  const manifest = JSON.parse(source.manifest);
  manifest.mutableBaselinePaths.push('docs/product/credit/features/FEATURE-031-consultar-relatorios-operacionais.md');
  assert.throws(() => contracts.dashboard({ ...source, manifest: JSON.stringify(manifest) }));
});

test('mutacao IMP-290: remover gate Dashboard da CI e rejeitado', () => {
  const source = readDashboard();
  assert.throws(() => contracts.dashboard({ ...source, workflow: source.workflow.replace('run: npm run test:dashboard', 'run: echo dashboard-removido') }));
});

test('mutacao IMP-290: reabrir IMP-296 e rejeitado', () => {
  const source = readDashboard();
  const block = impBlocks(source.backlog).find(({ id }) => id === 'IMP-296');
  assert.ok(block);
  const backlog = source.backlog.replace(block.text, block.text.replace('- **Status:** Concluido.', '- **Status:** Planejado.'));
  assert.throws(() => contracts.dashboard({ ...source, backlog }));
});

test('mutacao IMP-296: remover Idempotency-Key de compromisso e rejeitado', () => {
  const source = readAgendaComunicacao();
  const marker = 'Idempotency-Key:/credit/carteiras/{carteira_id}/devedores/{devedor_id}/agenda/compromissos';
  const mutated = 'sem-idempotency:/credit/carteiras/{carteira_id}/devedores/{devedor_id}/agenda/compromissos';
  assert.throws(() => contracts.agendaComunicacao({
    ...source,
    loader: source.loader.replaceAll(marker, mutated),
    bffTest: source.bffTest.replaceAll(marker, mutated),
    contractTest: source.contractTest.replaceAll(marker, mutated),
  }));
});

test('mutacao IMP-296: inventar Idempotency-Key nas consultas e rejeitado', () => {
  const source = readAgendaComunicacao();
  assert.throws(() => contracts.agendaComunicacao({
    ...source,
    loader: source.loader.replaceAll('sem-idempotency:/credit/agenda', 'Idempotency-Key:/credit/agenda'),
    bffTest: source.bffTest.replaceAll('sem-idempotency:/credit/agenda', 'Idempotency-Key:/credit/agenda'),
    contractTest: source.contractTest.replaceAll('sem-idempotency:/credit/agenda', 'Idempotency-Key:/credit/agenda'),
  }));
});

test('mutacao IMP-296: usar prefixo de Permissao e rejeitado', () => {
  const source = readAgendaComunicacao();
  const policy = source.policy.replace('new Set(permissions).has(permission)', 'permissions.some((value) => value.startsWith(permission))');
  assert.notStrictEqual(policy, source.policy);
  assert.throws(() => contracts.agendaComunicacao({ ...source, policy }));
});

test('mutacao IMP-296: calcular valor financeiro local e rejeitado', () => {
  const source = readAgendaComunicacao();
  assert.throws(() => contracts.agendaComunicacao({ ...source, component: `${source.component}\nconst saldo = itens.reduce((total, item) => total + parseFloat(item.valor), 0);` }));
});

test('mutacao IMP-296: antecipar Relatorios e rejeitado', () => {
  const source = readAgendaComunicacao();
  assert.throws(() => contracts.agendaComunicacao({ ...source, component: `${source.component}\nconst href = "/app/relatorios";` }));
});

test('mutacao IMP-296: ampliar allowlist para diretorio e rejeitado', () => {
  const source = readAgendaComunicacao();
  const manifest = JSON.parse(source.manifest);
  manifest.allowedNewPaths.push('frontend/src/components/agenda/');
  assert.throws(() => contracts.agendaComunicacao({ ...source, manifest: JSON.stringify(manifest) }));
});

test('mutacao IMP-297: reabrir IMP-299 e rejeitado', () => {
  const source = readRelatorios();
  const block = impBlocks(source.backlog).find(({ id }) => id === 'IMP-299');
  assert.ok(block);
  const backlog = source.backlog.replace(block.text, block.text.replace('- **Status:** Concluido.', '- **Status:** Planejado.'));
  assert.throws(() => contracts.relatorios({ ...source, backlog }));
});

test('mutacao IMP-297: inventar Idempotency-Key no loader e rejeitado', () => {
  const source = readRelatorios();
  assert.throws(() => contracts.relatorios({ ...source, loader: `${source.loader}\nheaders.set("Idempotency-Key", "inventada");` }));
});

test('mutacao IMP-297: derivar contagens locais dos arrays oficiais e rejeitado', () => {
  const source = readRelatorios();
  assert.throws(() => contracts.relatorios({
    ...source,
    component: `${source.component}\nconst contagensLocais = data.operacoes_quitadas.length + item.parcela_ids.length + item.pagamento_ids.length;`,
  }));
});

test('mutacao IMP-298: remover Idempotency-Key dos comandos e rejeitado', () => {
  const source = readConfiguracoes();
  assert.throws(() => contracts.configuracoes({
    ...source,
    loader: source.loader.replaceAll('Idempotency-Key', 'Idempotency-Removed'),
    bffTest: source.bffTest.replaceAll('Idempotency-Key', 'Idempotency-Removed'),
    contractTest: source.contractTest.replaceAll('Idempotency-Key', 'Idempotency-Removed'),
  }));
});

test('mutacao IMP-298: usar prefixo de Permissao e rejeitado', () => {
  const source = readConfiguracoes();
  const policy = source.policy.replace('new Set(permissions).has(permission)', 'permissions.some((value) => value.startsWith(permission))');
  assert.notStrictEqual(policy, source.policy);
  assert.throws(() => contracts.configuracoes({ ...source, policy }));
});

test('mutacao IMP-298: calcular taxa local e rejeitado', () => {
  const source = readConfiguracoes();
  assert.throws(() => contracts.configuracoes({
    ...source,
    component: `${source.component}\nconst totalCalculado = taxa + juros + valor;`,
  }));
});

test('mutacao IMP-298: aceitar Carteira arbitraria do browser e rejeitado', () => {
  const source = readConfiguracoes();
  assert.throws(() => contracts.configuracoes({
    ...source,
    actions: `${source.actions}\nconst carteira = formData.get("carteira_id");`,
  }));
});

test('mutacao IMP-298: ampliar allowlist para diretorio e rejeitado', () => {
  const source = readConfiguracoes();
  const manifest = JSON.parse(source.manifest);
  manifest.allowedNewPaths.push('frontend/src/components/configuracoes-financeiras/');
  assert.throws(() => contracts.configuracoes({ ...source, manifest: JSON.stringify(manifest) }));
});

test('mutacao IMP-298: permitir OpenAPI no manifesto e rejeitado', () => {
  const source = readConfiguracoes();
  const manifest = JSON.parse(source.manifest);
  manifest.mutableBaselinePaths.push('docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json');
  assert.throws(() => contracts.configuracoes({ ...source, manifest: JSON.stringify(manifest) }));
});

test('mutacao IMP-298: reabrir IMP-299 e rejeitado', () => {
  const source = readConfiguracoes();
  const block = impBlocks(source.backlog).find(({ id }) => id === 'IMP-299');
  assert.ok(block);
  const backlog = source.backlog.replace(block.text, block.text.replace('- **Status:** Concluido.', '- **Status:** Planejado.'));
  assert.throws(() => contracts.configuracoes({ ...source, backlog }));
});

test('mutacao sanitizacao BFF: restaurar mensagem bruta e rejeitado', () => {
  const source = readBffErrorSanitization();
  const loader = source.devedoresLoader.replace('mensagem: "Nao foi possivel concluir a operacao de Devedores."', 'mensagem: errorBody.mensagem');
  assert.throws(() => contracts.bffErrorSanitization({ ...source, devedoresLoader: loader }));
});

test('mutacao sanitizacao BFF: limitar teste a 404/500 e rejeitado', () => {
  const source = readBffErrorSanitization();
  const testSource = source.comercialTest.replace(
    'expect(result.problem.mensagem).not.toContain("cross-carteira");',
    'if (status === 404 || status === 500) expect(result.problem.mensagem).not.toContain("cross-carteira");',
  );
  assert.throws(() => contracts.bffErrorSanitization({ ...source, comercialTest: testSource }));
});

test('mutacao sanitizacao BFF: ampliar allowlist para diretorio e rejeitado', () => {
  const source = readBffErrorSanitization();
  const manifest = JSON.parse(source.manifest);
  manifest.mutableBaselinePaths.push('frontend/src/lib/bff/');
  assert.throws(() => contracts.bffErrorSanitization({ ...source, manifest: JSON.stringify(manifest) }));
});

test('mutacao sanitizacao BFF: reabrir IMP-299 e rejeitado', () => {
  const source = readBffErrorSanitization();
  const block = impBlocks(source.backlog).find(({ id }) => id === 'IMP-299');
  assert.ok(block);
  const backlog = source.backlog.replace(block.text, block.text.replace('- **Status:** Concluido.', '- **Status:** Planejado.'));
  assert.throws(() => contracts.bffErrorSanitization({ ...source, backlog }));
});

test('mutacao IMP-293: remover Idempotency-Key e rejeitado', () => {
  const source = readContratos();
  assert.throws(() => contracts.contratos({
    ...source,
    loader: source.loader.replaceAll('Idempotency-Key', 'Idempotency-Removed'),
    bffTest: source.bffTest.replaceAll('Idempotency-Key', 'Idempotency-Removed'),
    contractTest: source.contractTest.replaceAll('Idempotency-Key', 'Idempotency-Removed'),
  }));
});

test('mutacao IMP-293: antecipar Motor por emprestimos e rejeitado', () => {
  const source = readContratos();
  assert.throws(() => contracts.contratos({ ...source, loader: `${source.loader}\nclient.POST("/credit/contratos/{contrato_id}/emprestimos", {});` }));
});

test('mutacao IMP-293: usar prefixo de Permissao e rejeitado', () => {
  const source = readContratos();
  const policy = source.policy.replace('new Set(permissions).has(permission)', 'permissions.some((value) => value.startsWith(permission))');
  assert.notStrictEqual(policy, source.policy);
  assert.throws(() => contracts.contratos({ ...source, policy }));
});

test('mutacao IMP-293: ocultar 404 neutro e rejeitado', () => {
  const source = readContratos();
  const component = source.component.replace('Contrato nao encontrado ou indisponivel.', 'Detalhe do backend indisponivel.');
  assert.notStrictEqual(component, source.component);
  assert.throws(() => contracts.contratos({ ...source, component }));
});

test('mutacao IMP-293: ampliar allowlist para diretorio e rejeitado', () => {
  const source = readContratos();
  const manifest = JSON.parse(source.manifest);
  manifest.allowedNewPaths.push('frontend/src/components/contratos/');
  assert.throws(() => contracts.contratos({ ...source, manifest: JSON.stringify(manifest) }));
});

test('mutacao IMP-293: remover hash de evidencia visual e rejeitado', () => {
  const source = readContratos();
  const bytes = fs.readFileSync(path.join(ROOT, 'docs/audits/evidence/frontend-mvp-imp-293-contrato-flow-mobile.png'));
  const hash = crypto.createHash('sha256').update(bytes).digest('hex');
  assert.throws(() => contracts.contratos({ ...source, report: source.report.replace(hash, 'hash-removido') }));
});

test('mutacao IMP-293: reabrir IMP-296 e rejeitado', () => {
  const source = readContratos();
  const block = impBlocks(source.backlog).find(({ id }) => id === 'IMP-296');
  assert.ok(block);
  const backlog = source.backlog.replace(block.text, block.text.replace('- **Status:** Concluido.', '- **Status:** Planejado.'));
  assert.throws(() => contracts.contratos({ ...source, backlog }));
});

function run() {
  let failures = 0;
  console.log('test-plan-025-contracts');
  console.log('='.repeat(50));
  for (const item of cases) {
    try {
      item.fn();
      console.log(`  [PASS] ${item.name}`);
    } catch (error) {
      failures += 1;
      console.log(`  [FAIL] ${item.name}`);
      console.log(`         ${error.message}`);
    }
  }
  console.log('='.repeat(50));
  console.log(`Resumo: ${cases.length - failures}/${cases.length} teste(s) passaram.`);
  return failures;
}

if (require.main === module) process.exit(run() ? 1 : 0);

module.exports = { FILES, contracts, docs, run };
