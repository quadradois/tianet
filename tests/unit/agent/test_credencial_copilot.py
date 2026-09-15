"""Credencial do copiloto (IMP-356-F slice 2) — sem rede, sem banco.

Relógio, auth e store são fakes injetados: renovação proativa, 401
único sem loop, queda para senha com refresh obsoleto e ausência de
segredo em `repr`. Nada aqui encosta em JWT real.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from emprestimo.agent.api_client import ApiAutorizacaoError
from emprestimo.agent.credencial import (
    ArmazenRefresh,
    CredenciaisLogin,
    ProvedorTokenCopilot,
    RenovacaoEsgotadaError,
)

T0 = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
TENANT = uuid.uuid4()
INSTANCIA = "tianet_teste"
LOGIN = CredenciaisLogin(
    identificador_institucional="IDENT-1",
    email="copilot@exemplo.com",
    segredo="senha-forte",
)


class AuthFalsa:
    def __init__(self, agora: list[datetime]) -> None:
        self.agora = agora
        self.logins = 0
        self.refreshes = 0
        self.refresh_recusado = False

    def login(self, **kwargs: Any) -> SimpleNamespace:
        self.logins += 1
        return SimpleNamespace(
            access_token=f"access-{self.logins}",
            access_token_expira_em=self.agora[0] + timedelta(minutes=15),
            refresh_token=f"refresh-{self.logins}",
        )

    def refresh(self, *, refresh_token: str) -> SimpleNamespace:
        self.refreshes += 1
        if self.refresh_recusado:
            raise RuntimeError("revogado")
        return SimpleNamespace(
            access_token=f"renew-{self.refreshes}",
            access_token_expira_em=self.agora[0] + timedelta(minutes=15),
        )


class StoreFalso(ArmazenRefresh):
    def __init__(self) -> None:
        self.dados: dict[str, tuple[bytes, str]] = {}

    def guardar(
        self, tenant_id: object, instancia_ref: str, refresh_cifrado: bytes, chave_id: str
    ) -> None:
        self.dados[str(instancia_ref)] = (refresh_cifrado, chave_id)

    def carregar(self, tenant_id: object, instancia_ref: str) -> tuple[bytes, str] | None:
        return self.dados.get(str(instancia_ref))


def _provedor(auth: AuthFalsa, store: StoreFalso, agora: list[datetime]) -> ProvedorTokenCopilot:
    return ProvedorTokenCopilot(
        auth,
        store,
        cifrar=lambda s: b"X" + s.encode(),
        decifrar=lambda b: b[1:].decode(),
        tenant_id=TENANT,
        instancia_ref=INSTANCIA,
        agora=lambda: agora[0],
    )


def test_entrar_guarda_refresh_cifrado_e_usa_access() -> None:
    agora = [T0]
    auth, store = AuthFalsa(agora), StoreFalso()
    provedor = _provedor(auth, store, agora)
    provedor.entrar(LOGIN)
    assert auth.logins == 1
    cifrado, chave_id = store.dados[INSTANCIA]
    assert cifrado == b"Xrefresh-1" and chave_id == "v1"
    assert provedor.token() == "access-1"
    assert auth.refreshes == 0


def test_entrar_prefere_refresh_guardado_a_senha() -> None:
    agora = [T0]
    auth, store = AuthFalsa(agora), StoreFalso()
    store.dados[INSTANCIA] = (b"Xrefresh-antigo", "v1")
    provedor = _provedor(auth, store, agora)
    provedor.entrar(LOGIN)
    assert auth.logins == 0 and provedor.token() == "renew-1"


def test_entrar_cai_para_senha_com_refresh_obsoleto() -> None:
    agora = [T0]
    auth, store = AuthFalsa(agora), StoreFalso()
    auth.refresh_recusado = True
    store.dados[INSTANCIA] = (b"Xrefresh-velho", "v1")
    provedor = _provedor(auth, store, agora)
    provedor.entrar(LOGIN)
    assert auth.logins == 1 and provedor.token() == "access-1"


def test_token_renova_proativamente_antes_de_expirar() -> None:
    agora = [T0]
    auth, store = AuthFalsa(agora), StoreFalso()
    provedor = _provedor(auth, store, agora)
    provedor.entrar(LOGIN)
    agora[0] = T0 + timedelta(minutes=14)
    assert provedor.token() == "renew-1"
    assert auth.refreshes == 1


def test_executar_faz_um_refresh_e_uma_repeticao() -> None:
    agora = [T0]
    auth, store = AuthFalsa(agora), StoreFalso()
    provedor = _provedor(auth, store, agora)
    provedor.entrar(LOGIN)
    chamadas = {"n": 0}

    def _op(token: str) -> str:
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise ApiAutorizacaoError("expirado")
        return f"ok-{token}"

    assert provedor.executar(_op) == "ok-renew-1"
    assert auth.refreshes == 1 and chamadas["n"] == 2


def test_executar_encerra_no_segundo_401_sem_loop() -> None:
    agora = [T0]
    auth, store = AuthFalsa(agora), StoreFalso()
    provedor = _provedor(auth, store, agora)
    provedor.entrar(LOGIN)

    def _sempre_401(token: str) -> str:
        raise ApiAutorizacaoError("negado")

    with pytest.raises(RenovacaoEsgotadaError):
        provedor.executar(_sempre_401)
    assert auth.refreshes == 1


def test_refresh_revogado_encerra_sem_loop() -> None:
    agora = [T0]
    auth, store = AuthFalsa(agora), StoreFalso()
    auth.refresh_recusado = True
    provedor = _provedor(auth, store, agora)
    provedor.entrar(LOGIN)
    agora[0] = T0 + timedelta(minutes=14)
    with pytest.raises(RenovacaoEsgotadaError):
        provedor.token()
    assert auth.refreshes == 1


def test_segredo_nunca_em_repr() -> None:
    assert "senha-forte" not in repr(LOGIN)
    agora = [T0]
    provedor = _provedor(AuthFalsa(agora), StoreFalso(), agora)
    provedor.entrar(LOGIN)
    texto = repr(provedor)
    assert "access-1" not in texto and "refresh-1" not in texto
