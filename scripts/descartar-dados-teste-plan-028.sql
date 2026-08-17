-- PLAN-028 / IMP-314 — descarte dos dados de teste gerados sob a convencao
-- antiga de juros (DR-003, Resolucao: "Os 9 emprestimos do ambiente local sao
-- dados de teste e podem ser descartados").
--
-- Preserva tenant, usuario, carteira, perfis, permissoes, configuracoes e os
-- devedores: devedor sem emprestimo e estado legitimo, e mantem o caminho
-- "escolher devedor existente" do wizard testavel.
--
-- Uso (stack local em Docker):
--   docker compose exec -T postgres psql -U emprestimo -d emprestimo \
--     -v ON_ERROR_STOP=1 -f - < scripts/descartar-dados-teste-plan-028.sql
--
-- NAO executar contra producao.

BEGIN;

TRUNCATE
    proposta_comercial,
    contrato_credito,
    emprestimo,
    parcela,
    pagamento,
    memoria_calculo
CASCADE;

SELECT 'emprestimo' AS tabela, count(*) FROM emprestimo
UNION ALL SELECT 'parcela', count(*) FROM parcela
UNION ALL SELECT 'devedor (preservado)', count(*) FROM devedor
UNION ALL SELECT 'tenant (preservado)', count(*) FROM tenant
UNION ALL SELECT 'usuario (preservado)', count(*) FROM usuario;

COMMIT;
