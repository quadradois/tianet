# Princípios de engenharia do TiaNet

## P1 — Compreender antes de mudar

Inspecione instruções, estado, decisões, documentação, código e testes relacionados antes de propor alteração.

## P2 — Desenhar antes de implementar

Mudanças relevantes precisam de desenho explícito. Mudanças arquiteturais exigem alternativas e trade-offs.

## P3 — Planejar antes de implementar

Um desenho aprovado deve virar plano executável antes de alterar código de produção.

## P4 — Trabalhar em slices pequenos

Cada slice deve entregar um comportamento revisável, testável, verificável e, quando viável, reversível.

## P5 — Preferir evidência a afirmações

Conclusões devem apontar para teste, comando, inspeção, comparação, CI ou outra observação reproduzível.

## P6 — Não redesenhar silenciosamente

Ao descobrir conflito com arquitetura aprovada: pare, explique, apresente opções, registre a decisão, atualize design e plano e somente então prossiga.

## P7 — Tornar incerteza explícita

Classifique informações materiais como `FATO`, `HIPÓTESE`, `DESCONHECIDO`, `DECISÃO`, `RISCO` ou `ADIADO`.

## P8 — Proteger arquitetura mecanicamente

Quando uma invariável importante puder ser validada com alto valor e baixo custo, combine documentação com teste estrutural, lint ou CI.
