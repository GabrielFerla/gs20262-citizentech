# Imagem dos sensores simulados (tempo real via MQTT e geração do histórico).
# Contexto de build: raiz do repositório (precisa dos cadastros em area2-bigdata/db/seeds).
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SEEDS_DIR=/app/seeds

WORKDIR /app
COPY area3-mvp/iot/simuladores/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY area2-bigdata/db/seeds/*.csv seeds/
COPY area3-mvp/iot/simuladores/simuladores/ simuladores/

# /dados/landing já nasce do usuário app: o volume do data lake herda esse dono.
RUN useradd --uid 10001 --no-create-home app \
    && mkdir -p /dados/landing && chown app /dados/landing
USER app

HEALTHCHECK --interval=10s --timeout=3s --start-period=60s --retries=3 \
  CMD python -c "import os,sys,time; sys.exit(0 if time.time()-os.path.getmtime('/tmp/simulador-vivo')<30 else 1)"

CMD ["python", "-m", "simuladores.tempo_real"]
