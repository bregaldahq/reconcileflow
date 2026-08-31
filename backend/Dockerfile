FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/reconcileflow

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/src ./src
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic

RUN python -m pip install --no-cache-dir . \
    && groupadd --system reconcileflow \
    && useradd --system --gid reconcileflow --home-dir /opt/reconcileflow reconcileflow \
    && chown -R reconcileflow:reconcileflow /opt/reconcileflow

USER reconcileflow

EXPOSE 8000

CMD ["python", "-m", "reconcileflow"]
