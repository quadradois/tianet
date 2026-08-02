"""App FastAPI — esqueleto da camada Presentation.

Apenas o healthcheck é exposto nesta fase: os endpoints de negócio
(POST /platform/tenants, GET /platform/tenants/{id}) pertencem a IMP-017/018
e não são implementados antes da fase de API (PLAN-001-EXEC §6).
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="TiaNet — API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Healthcheck do serviço."""
    return {"status": "ok"}
