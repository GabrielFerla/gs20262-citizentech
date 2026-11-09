# Abriga — Alerta de enchentes e "onde ficar seguro" (Porto Alegre)

Global Solution 2026/2 (desafio CitizenTech) · FIAP · Engenharia de Software (4ESOA)

Sensores de nível de rio, chuva e ocupação de abrigos alimentam um pipeline de dados em
tempo real. Com ele a Defesa Civil acompanha os rios, recebe alertas de cheia e sabe quais
abrigos ainda têm vaga. Uma IA prevê o nível dos rios para daqui a 6 horas e avisa antes de
a cheia chegar. O cidadão recebe um alerta em linguagem simples e é orientado para um abrigo
que vai ter vaga quando ele chegar e que não vai alagar.

O nome técnico continua `citizentech` (repositório, banco, tópicos MQTT e imagens Docker), igual ao nome do desafio.

> **Fases 1 a 3 (este README):** sensores → MQTT → ingestão → PostgreSQL (bronze/silver/gold) → CSVs do Power BI,
> a API de IA (previsão, "onde ficar seguro" e mensagens) e o app do cidadão, que roda no navegador em `localhost:5173`.

| Área do edital | Pasta | O que tem |
|---|---|---|
| 1. IA e automação | [`area1-ia/`](area1-ia/README.md) | Previsão do nível em 6 h (scikit-learn), recomendação de abrigo com o risco previsto, mensagens em linguagem simples, alerta antecipado automático, API FastAPI |
| 2. Big Data e visualização | [`area2-bigdata/`](area2-bigdata/README.md) | Camadas bronze/silver/gold, ingestão em tempo real e em lote, exportação, Power BI |
| 3. MVP, IoT e experiência digital | [`area3-mvp/app/`](area3-mvp/app/README.md) | App **Abriga** (React Native/Expo): 5 telas, aviso de alerta novo, "onde ficar seguro" pelo bairro ou pelo GPS (a posição fica no aparelho), Como chegar |
| 3. MVP, IoT e experiência digital | [`area3-mvp/iot/`](area3-mvp/iot/README.md) | Broker MQTT, 26 sensores simulados + 3 do ESP32 no Wokwi, ponte segura |
| 4. DevOps, segurança e qualidade | [`area4-devops/`](area4-devops/plano-de-testes.md) | Docker Compose, CI no GitHub Actions, plano de testes, práticas de segurança |
| Contrato das mensagens | [`contratos/`](contratos/leitura.v1.schema.json) | JSON Schema seguido por todos os serviços |
| Arquitetura | [`docs/arquitetura.md`](docs/arquitetura.md) | Diagrama e fluxo dos dados |

## Como rodar

**Pré-requisito:** Docker Desktop aberto (Windows, macOS ou Linux). Não precisa de Python
instalado. A internet só é necessária na primeira subida, para baixar as imagens e os pacotes,
e depois só para a ponte opcional do Wokwi.

```bash
cp .env.example .env
```

No Windows (PowerShell), use `Copy-Item .env.example .env` no lugar do comando acima.
Quem já tinha um `.env` de uma fase anterior deve copiar de novo. A fase 2 acrescentou `IA_DB_PASSWORD`, e a fase 3 acrescentou `http://localhost:8081` ao `API_CORS_ORIGENS`, que só é usado pelo app em desenvolvimento.

```bash
docker compose up -d --build --wait
```

Na primeira vez leva de 3 a 5 minutos, conforme a internet, para baixar as imagens e os pacotes, treinar o modelo e gerar o app. O Compose sobe e conecta tudo sozinho:

1. **postgres** e **mosquitto** (broker MQTT com usuário, senha e permissões por tópico);
2. **migrar**: cria as tabelas e visões e carrega os cadastros (94 bairros, 4 estações, 21 abrigos, 29 sensores);
3. **historico-gerar** e **historico-carregar**: geram e carregam 30 dias de histórico (cerca de 112 mil leituras);
4. **ingestor**: recebe as leituras do MQTT em tempo real;
5. **simulador**: publica as leituras dos sensores. Cada segundo real equivale a 10 minutos simulados, então uma enchente completa leva uns 13 minutos;
6. **api**: a IA (previsão, abrigos e mensagens). O modelo é treinado no build da imagem.
7. **app**: o app do cidadão, exportado para a web e servido por um nginx que também repassa `/api` para a API.

**Abrir o app:** <http://localhost:5173>, de preferência em largura de celular (no Chrome: F12 e Ctrl+Shift+M).
Para ver o alerta chegar, rode `docker compose restart simulador`: a cheia começa uns 4 minutos depois.
O roteiro completo está em [`area3-mvp/app/README.md`](area3-mvp/app/README.md#roteiro-da-demonstração).

Conferir que está tudo de pé:

```bash
docker compose ps
```

Ver as leituras chegando (Ctrl+C sai):

```bash
docker compose logs -f ingestor simulador
```

Ver a situação atual dos rios e dos abrigos direto no banco:

```bash
docker compose exec postgres psql -U migrador -d citizentech -c "SELECT estacao_id, nivel_m, situacao, alerta_severidade FROM gold.v_estacao_atual;" -c "SELECT abrigo, ocupacao, vagas, status_lotacao, recomendavel, motivo_nao_recomendado FROM gold.v_abrigo_status ORDER BY abrigo_id;"
```

Abrir a API de IA no navegador (Swagger: dá para testar todas as rotas):
http://localhost:8000/docs. Exemplos de uso e o relatório de métricas estão em
[`area1-ia/README.md`](area1-ia/README.md#como-rodar-e-demonstrar).

```bash
curl -s 'localhost:8000/abrigos/recomendacao?bairro=navegantes&pessoas=4'
```

### Gerar o relatório da IA (métricas e gráficos)

```bash
docker compose --profile ferramentas run --rm ia-relatorio
```

Os arquivos saem em `relatorios/ia/` (`RELATORIO.md`, gráficos e `demo.md`), fora do git. Os números
mudam a cada subida, porque o histórico termina na hora em que o ambiente subiu. A versão de
referência, citada no PDF, fica em [`area1-ia/relatorio/`](area1-ia/relatorio/RELATORIO.md).

### Exportar os dados para o Power BI

```bash
docker compose --profile ferramentas run --rm exportar
```

Os CSVs saem em `area2-bigdata/powerbi/dados/`. O passo a passo do dashboard está em [`area2-bigdata/powerbi/README.md`](area2-bigdata/powerbi/README.md).

### Rodar os testes

Testes de integração (23 casos contra o ambiente rodando; o relatório vai para `relatorios/integracao.xml`):

```bash
docker compose --profile ferramentas run --rm --build testes
```

Lint, tipos e testes do app (103 testes; precisa do Node 22.13 ou mais novo; o relatório vai para `relatorios/app.xml`):

```bash
cd area3-mvp/app && npm ci
```

```bash
npm run lint && npm run typecheck && npm test
```

No Windows PowerShell 5, troque `&&` por `;`.

Testes de unidade e lint (precisa de Python 3.12 ou mais novo).

macOS e Linux:

```bash
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-dev.txt
```

```bash
.venv/bin/python -m ruff check . && .venv/bin/python -m pytest
```

Windows (PowerShell):

```powershell
python -m venv .venv; .venv\Scripts\python -m pip install -r requirements-dev.txt
```

```powershell
.venv\Scripts\python -m ruff check .; .venv\Scripts\python -m pytest
```

### Circuito ESP32 no Wokwi (opcional)

Veja [`area3-mvp/iot/README.md`](area3-mvp/iot/README.md#circuito-esp32-no-wokwi). Resumo: suba a ponte com o comando abaixo e rode o projeto no wokwi.com.

```bash
docker compose --profile wokwi up -d ponte-wokwi
```

### Parar e zerar

Para tudo e mantém os dados:

```bash
docker compose down
```

Para tudo e apaga o banco e o data lake (na próxima subida o histórico é gerado de novo, terminando no horário atual):

```bash
docker compose down -v
```

## Portas

As portas só aceitam conexões da própria máquina (`127.0.0.1`), porque as senhas de exemplo estão públicas no repositório.

| Serviço | Endereço | Uso |
|---|---|---|
| PostgreSQL | `localhost:55432` | Banco `citizentech`. O usuário `bi_ro` só lê a camada gold |
| Mosquitto (MQTT) | `localhost:11883` | Exige usuário e senha (veja o `.env`) |
| API de IA | `localhost:8000` | Swagger em `/docs`. Lê só a camada gold (usuário `ia_ro`) |
| App Abriga | `localhost:5173` | App do cidadão (web). O endereço `/api` repassa para a API de IA |

## Uso de IA generativa

Declaração exigida pelo edital.

| Ferramenta | Para quê |
|---|---|
| Claude (Anthropic), via Claude Code | Pesquisa de versões e limitações (Wokwi, Mosquitto 2, PostgreSQL 18), desenho da arquitetura, geração de código, testes e documentação, calibração do modelo de simulação |
| Claude (Anthropic), via Claude Code | Fase 2: desenho do treino sem vazamento e da métrica antes/depois, código da IA e da API, prompt de sistema das mensagens. Detalhes em [`area1-ia/README.md`](area1-ia/README.md#uso-de-ia-generativa-no-desenvolvimento) |
| Claude (Anthropic), via Claude Code | Fase 3: pesquisa das versões do Expo SDK 58, desenho das telas e do fluxo, código do app e dos testes, conta da distância no aparelho com teste de paridade com a IA, Dockerfile e nginx, roteiro da demo e prints. Detalhes em [`area3-mvp/app/README.md`](area3-mvp/app/README.md#uso-de-ia-generativa-no-desenvolvimento) |

A solução **não chama** nenhuma IA generativa em execução: as mensagens de alerta saem de modelos de texto que seguem um prompt documentado ([`area1-ia/prompts/`](area1-ia/prompts/sistema.md)).

O grupo revisou, executou e testou todo o código entregue e consegue explicar cada parte. Os testes de unidade e de integração e o CI são a evidência de que tudo roda.

## Integrantes e pitch

Ver [`integrantes.txt`](integrantes.txt). Link do vídeo pitch: **(preencher)**.

## Créditos de dados

Bairros, escolas e ginásios de Porto Alegre: © colaboradores do OpenStreetMap (ODbL).
As cotas e a zona de risco são simplificações; veja [`area2-bigdata/db/seeds/README.md`](area2-bigdata/db/seeds/README.md).
