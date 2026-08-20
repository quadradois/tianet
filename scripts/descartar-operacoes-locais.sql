-- Descarta as operacoes de credito do ambiente LOCAL.
--
-- Preserva tenant, usuario, carteira, perfis, permissoes, configuracoes e os
-- devedores: devedor sem emprestimo e estado legitimo, e mantem o caminho
-- "escolher devedor existente" do wizard testavel.
--
-- Usado em cada mudanca de regra financeira que invalida o que ja foi gravado:
--   PLAN-028 (DR-003) — base de normalizacao dos juros;
--   PLAN-030 (DR-004) — juros sobre saldo devedor e fim do plano de parcelas.
--
-- Parcelas ficam gravadas no banco e nao se recalculam sozinhas: um emprestimo
-- criado sob a regra antiga continua exibindo os valores antigos para sempre.
-- Por isso o descarte, e nao um recalculo.
--
-- Uso (stack local em Docker, a partir da raiz do repositorio):
--   docker compose exec -T postgres psql -U emprestimo -d emprestimo \
--     -v ON_ERROR_STOP=1 -f - < scripts/descartar-operacoes-locais.sql
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
UNION ALL SELECT 'carteira (preservada)', count(*) FROM carteira
UNION ALL SELECT 'usuario (preservado)', count(*) FROM usuario;

COMMIT;
