# App do cidadão (área 3): o Expo gera os arquivos do navegador e o nginx os serve.
# Contexto de build: a própria pasta do app (area3-mvp/app).

# 1) Build: instala só as dependências de produção e exporta a versão web (pasta dist/).
FROM node:22.23.2-bookworm-slim AS build
WORKDIR /app
ENV CI=1 \
    EXPO_NO_TELEMETRY=1
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund
COPY . .
# A API fica no mesmo endereço do app: o nginx repassa /api para o serviço "api" do Compose.
ARG EXPO_PUBLIC_API_URL=/api
ENV EXPO_PUBLIC_API_URL=$EXPO_PUBLIC_API_URL
RUN npx expo export -p web

# 2) Servidor: nginx sem root (usuário nginx, porta 8080).
FROM nginxinc/nginx-unprivileged:1.30-alpine
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/seguranca.conf /etc/nginx/snippets/seguranca.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
