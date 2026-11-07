# Imagem do ingestor (consumidor MQTT, carga em lote, migrações e exportação).
# Contexto de build: raiz do repositório (precisa de contratos/ e db/).
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CONTRATOS_DIR=/app/contratos \
    MIGRACOES_DIR=/app/db/migrations \
    SEEDS_DIR=/app/db/seeds

WORKDIR /app
COPY area2-bigdata/ingestor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY contratos/ contratos/
COPY area2-bigdata/db/migrations/ db/migrations/
COPY area2-bigdata/db/seeds/*.csv db/seeds/
COPY area2-bigdata/ingestor/ingestor/ ingestor/

# Não roda como root (segurança).
RUN useradd --uid 10001 --no-create-home app
USER app

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import os,sys,time; sys.exit(0 if time.time()-os.path.getmtime('/tmp/ingestor-vivo')<30 else 1)"

CMD ["python", "-m", "ingestor.consumidor"]
