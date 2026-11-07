# Imagem da IA: treina o modelo no build e serve a API (FastAPI).
# Contexto de build: raiz do repositório (precisa do simulador e dos cadastros para gerar o treino).
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SEEDS_DIR=/app/seeds \
    MODELO_DIR=/app/modelo \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app
COPY area1-ia/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY area2-bigdata/db/seeds/*.csv seeds/
COPY area3-mvp/iot/simuladores/simuladores/ simuladores/
COPY area1-ia/ia/ ia/

# Treino determinístico (24 meses simulados, sementes fixas), sem banco: o modelo nasce na imagem.
RUN python -m ia.treino --saida /app/modelo

# Não roda como root (segurança).
RUN useradd --uid 10001 --no-create-home app
USER app

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/saude', timeout=4).status == 200 else 1)"

# Sem log de acesso: o healthcheck a cada 10 s esconderia as linhas do vigia no "docker compose logs".
CMD ["python", "-m", "uvicorn", "ia.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
