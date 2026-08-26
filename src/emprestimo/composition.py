"""Decisoes de montagem compartilhadas pelos dois pontos de entrada.

A API (`presentation/api/dependencies.py`) e o worker
(`worker/scheduler_worker.py`) sao composition roots independentes, e por isso
cada um pode importar Application e Infrastructure. O que **nao** podem e
manter copias da mesma decisao: foi o que aconteceu com a escolha do canal de
e-mail, duplicada nos dois arquivos com o mesmo `raise RuntimeError`.

Duas copias da mesma regra sao duas chances de divergir, e elas divergiriam na
primeira vez que so uma fosse atualizada — exatamente o que este modulo evita.
Aqui moram decisoes de fiacao que os dois pontos de entrada precisam tomar do
mesmo jeito.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from emprestimo.application.notifications import (
    CanalNaoConfiguradoNotificationChannel,
    FakeNotificationChannel,
)
from emprestimo.domain.credit.automacao_ports import NotificationChannel
from emprestimo.infrastructure.notifications import ResendNotificationChannel


def resolver_canal_email(ambiente: Mapping[str, str] | None = None) -> NotificationChannel:
    """Escolhe o canal de e-mail a partir do ambiente.

    Tres casos, e o do meio e o que exige explicacao:

    1. credenciais presentes -> `ResendNotificationChannel`, sem surpresa;
    2. producao sem credenciais -> **recusa nomeada**, nao fake. E-mail esta
       fora do escopo do MVP (`contexto-externo.md` §2.3): nao ha conta Resend
       e o canal real da operacao e o WhatsApp. Antes disto, o processo
       **recusava iniciar**, o que bloqueava o deploy inteiro por um canal que
       ninguem usa. Cair no fake seria pior do que derrubar, porque ele devolve
       `ACEITA` com comprovante sintetico e a trilha registraria como entregue
       um e-mail que nunca saiu;
    3. desenvolvimento sem credenciais -> `FakeNotificationChannel`, que e o
       proposito dele.
    """
    valores = os.environ if ambiente is None else ambiente
    api_key = valores.get("RESEND_API_KEY")
    remetente = valores.get("RESEND_FROM")
    if api_key and remetente:
        return ResendNotificationChannel(api_key=api_key, remetente=remetente)
    if valores.get("APP_ENV", "development") == "production":
        return CanalNaoConfiguradoNotificationChannel("email")
    return FakeNotificationChannel()
