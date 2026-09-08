# Verificação — IMP-370 aviso de queda do WhatsApp

**Data:** 2026-09-08
**Escopo:** `PLANO-IMP-370-AVISO-QUEDA.md`, Slices 1–4
**Parecer:** `APPROVED`

| Requisito | Evidência esperada | Check | Resultado observado | Status |
|---|---|---|---|---|
| Queda única | A borda pareada → não pareada cria um alerta | Testes de domínio, consulta e varredura | A transição grava `queda_detectada_em` antes do commit e retorna uma queda | VERIFICADO |
| Permanência desconectada | O primeiro instante é preservado sem duplicação | Testes de consulta, varredura e entidade | Ciclos seguintes não salvam nem reemitem a queda | VERIFICADO |
| Recuperação | Pareamento confirmado limpa o alerta | Testes de entidade, consulta e varredura | `parear()` limpa o timestamp e a sincronização persiste a recuperação | VERIFICADO |
| Consulta detecta primeiro | A leitura da tela pode registrar antes do worker | Testes de consulta e ordem transacional | O mesmo `_sincronizar()` roda sob lock no caminho de consulta | VERIFICADO |
| Desconexão manual | A ação da operadora não cria falso alerta | Testes de desconexão e entidade | O caso de uso usa `desparear()` e não `registrar_queda()` | VERIFICADO |
| Falha do provedor | Indisponibilidade não inventa nem limpa queda | Testes de consulta, varredura e worker | A exceção ocorre antes de `save`; o estado anterior é preservado | VERIFICADO |
| Isolamento de tenant | Uma queda não afeta outro tenant | Testes de varredura, autorização e API | Lock, repositório e contexto permanecem delimitados por tenant | VERIFICADO |
| Migration | Coluna nullable com timezone aplica e reverte | Ciclo Alembic em PostgreSQL descartável | `upgrade head → downgrade base → upgrade head` concluído; head único `c1d2e3f4a5b6` | VERIFICADO |
| UI exibe | Banner global acessível aparece com alerta ativo | BFF, componente, contrato, Playwright e axe | Banner com texto, `<time>`, `role="alert"`, link e sem dispensa passou em desktop e mobile | VERIFICADO |
| UI remove | Contexto recuperado remove o banner | Componente e jornada de sessão | Estado inativo não renderiza o banner; rerender após recuperação o remove | VERIFICADO |

## Checks executados

- Backend: 868 testes unitários e 39 integrações focais aprovados; Ruff, Black e mypy aprovados.
- Migration: ciclo destrutivo completo em PostgreSQL sintético e descartável aprovado; container removido após o teste.
- Frontend: `api:check`, typecheck, lint e build de produção aprovados; 137 testes BFF, 82 de componentes e 42 de contrato aprovados.
- Navegador: 22 testes de sessão e 4 testes dedicados de acessibilidade aprovados em Chromium desktop e mobile.
- Governança: `docs:validate` com 384 verificações OK, 36 avisos preexistentes e 0 erros; Harness com 144 checks estruturais e 43 testes de coordenação/validação aprovados.
- Revisão: `git diff --check` aprovado; auditoria OpenCode somente leitura `df28a52f-b84e-4aa8-bcf4-012c3fb9fd19` não alterou arquivos e não encontrou blocker.

## Checks não executados

Nenhum check obrigatório do plano ficou pendente.

## Riscos residuais

- A detecção periódica pode levar até cerca de 300 segundos, conforme o intervalo atual do worker.
- O alerta aparece quando a operadora está no TiaNet ou volta a ele; esta entrega não avisa com o navegador e o sistema fechados.
- O estado de queda ainda precisa passar pelo processo normal de commit, release e implantação antes de existir na VPS.

## Conclusão

O IMP-370 está `VERIFICADO` no working tree. G10 e G11 estão fechados pelas evidências e pelo handoff atualizado. O GATE-E do produto permanece aberto e nenhuma publicação foi realizada.
