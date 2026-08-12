import pytest
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from emprestimo.presentation.api.automacao_routes import router as automacao_router
from emprestimo.presentation.api.dependencies import get_notification_channel
from emprestimo.presentation.api.main import create_app


def test_openapi_expoe_apenas_operacoes_administrativas_de_automacao() -> None:
    schema = create_app().openapi()
    paths = schema["paths"]
    esperadas = {
        "/credit/automacao/jobs",
        "/credit/automacao/jobs/{job_id}",
        "/credit/automacao/jobs/{job_id}/cancelar",
        "/credit/automacao/jobs/{job_id}/retry",
        "/credit/notificacoes",
        "/credit/notificacoes/{notification_id}",
        "/credit/notificacoes/{notification_id}/conciliar",
        "/credit/notificacoes/templates",
        "/credit/notificacoes/templates/{template_id}/aprovar",
        "/credit/notificacoes/templates/{template_id}/ativar",
    }
    assert esperadas <= set(paths)
    assert not any("enviar" in path for path in paths if path.startswith("/credit/notificacoes"))
    assert paths["/credit/agenda/lembretes/{lembrete_id}/enviar"]["post"]["deprecated"]
    assert paths["/credit/automacao/jobs/{job_id}/cancelar"]["post"]["responses"]["202"]
    assert paths["/credit/automacao/jobs/{job_id}/retry"]["post"]["responses"]["202"]
    assert paths["/credit/notificacoes/templates"]["post"]["responses"]["409"]


def test_rota_estatica_de_templates_precede_identificador_dinamico() -> None:
    rotas = [route.path for route in automacao_router.routes if isinstance(route, APIRoute)]
    assert rotas.index("/credit/notificacoes/templates") < rotas.index(
        "/credit/notificacoes/{notification_id}"
    )


def test_rotas_administrativas_exigem_autenticacao(
    monkeypatch: pytest.MonkeyPatch,
    session: Session,
) -> None:
    del session
    monkeypatch.setenv("JWT_SECRET_KEY", "automacao-test-secret-with-32-bytes")
    client = TestClient(create_app())
    response = client.get("/credit/automacao/jobs")
    assert response.status_code == 401
    assert response.headers["X-Correlation-ID"]


def test_notification_channel_falha_fechado_em_producao_sem_credenciais(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("RESEND_FROM", raising=False)

    with pytest.raises(RuntimeError, match="obrigatorios em producao"):
        get_notification_channel()
