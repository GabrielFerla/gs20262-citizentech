# Imagem dos testes de integração (rodam dentro da rede do docker compose).
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CONTRATOS_DIR=/app/contratos \
    MIGRACOES_DIR=/app/db/migrations \
    SEEDS_DIR=/app/db/seeds

WORKDIR /app
COPY area2-bigdata/ingestor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pytest==9.2.0

COPY contratos/ contratos/
COPY area2-bigdata/db/migrations/ db/migrations/
COPY area2-bigdata/db/seeds/*.csv db/seeds/
COPY area2-bigdata/ingestor/ingestor/ ingestor/
# Só o features.py (Python puro) é usado: paridade das features da IA com a visão SQL.
COPY area1-ia/ia/__init__.py area1-ia/ia/features.py ia/
COPY area4-devops/testes/ testes/

# Roda como root (docker-compose) para gravar em relatorios/ e, no fim, devolve o relatório ao dono da pasta:
# no Linux, sem isso, o arquivo ficaria com dono root.
CMD ["sh", "-c", "python -m pytest -m integration -v -p no:cacheprovider --junitxml=/relatorios/integracao.xml /app/testes; s=$?; chown \"$(stat -c %u:%g /relatorios)\" /relatorios/integracao.xml 2>/dev/null; exit $s"]
