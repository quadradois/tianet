FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml alembic.ini ./
COPY src ./src
COPY migrations ./migrations

RUN pip install --no-cache-dir .

# Artefatos de deploy viajam na imagem para que o gate da VPS possa provar que
# a topologia e ele mesmo correspondem à tag publicada. Não são executados
# daqui: servem só de referência para conferência de digest.
COPY docker-compose.prod.yml scripts/deploy-gate.sh ./deploy/

# Nao rodar como root: o container so precisa ler /app e falar com o Postgres.
RUN groupadd --gid 10003 agentipc \
    && useradd --create-home --uid 10001 app \
    && usermod --append --groups agentipc app
USER app

EXPOSE 8000

CMD ["uvicorn", "emprestimo.presentation.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
