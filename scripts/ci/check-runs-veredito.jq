# Veredito dos check runs de um commit, para o gate `precondicoes` do deploy.
#
# Entrada:  resposta de GET /repos/{repo}/commits/{sha}/check-runs
# Argumento: --arg esperados "<nomes de check run, um por linha>"
# Saída:    {ausentes, pendentes, reprovados}
#
# A allowlist é NOMINAL de propósito. A versão anterior usava um regex
# ancorado (`^(...|Frontend foundation)$`) que não casava os nomes gerados
# pela matriz de `quality.yml` — "Frontend foundation (ubuntu-latest)" — e
# por isso aprovava o deploy com as duas suites de frontend vermelhas.
# Com lista nominal, um job renomeado cai em `ausentes` e reprova o gate,
# em vez de desaparecer silenciosamente da verificação.
#
# Só `success` aprova: skipped, neutral, cancelled e stale entram em
# `reprovados`. `conclusion` é null enquanto o run não termina, mas esse
# caso já foi capturado por `pendentes`.

($esperados | split("\n") | map(select(length > 0))) as $req
| [.check_runs[] | select(.app.slug == "github-actions" and (.name | IN($req[])))] as $runs
| {
    ausentes: ($req - ($runs | map(.name))),
    pendentes: [$runs[] | select(.status != "completed") | .name],
    reprovados: [
      $runs[]
      | select(.status == "completed" and .conclusion != "success")
      | "\(.name)=\(.conclusion // "null")"
    ]
  }
