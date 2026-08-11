"""Contratos de logs estruturados e mascaramento (IMP-194)."""

from __future__ import annotations

from emprestimo.presentation.api.observability import mask_sensitive, resolve_correlation_id


def test_mask_sensitive_oculta_campos_tecnicos_e_pessoais() -> None:
    masked = mask_sensitive(
        {
            "Authorization": "Bearer segredo",
            "database_url": "postgresql://user:pass@host/db",
            "perfil": {"senha": "abc", "nome": "Maria"},
            "documento": "12345678900",
            "items": [{"token_ativacao": "token"}],
        }
    )

    assert masked == {
        "Authorization": "***",
        "database_url": "***",
        "perfil": {"senha": "***", "nome": "Maria"},
        "documento": "***",
        "items": [{"token_ativacao": "***"}],
    }


def test_resolve_correlation_id_aceita_valido_e_regenera_invalido() -> None:
    assert resolve_correlation_id("trace-abc_123") == "trace-abc_123"
    generated = resolve_correlation_id("valor com espaco")

    assert generated != "valor com espaco"
    assert len(generated) == 36
