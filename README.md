# CitizenTech — Alerta de enchentes e "onde ficar seguro" (Porto Alegre)

Global Solution 2026/2 · FIAP · Engenharia de Software (4ESOA)

Sensores de nível de rio, chuva e ocupação de abrigos alimentam um pipeline de dados em
tempo real. Com ele a Defesa Civil acompanha os rios, recebe alertas de cheia e sabe quais
abrigos ainda têm vaga. O cidadão é orientado para um abrigo seguro, e um abrigo em área
de risco é evitado quando o rio da região está em alerta.

> **Fase 1 (este README):** sensores → MQTT → ingestão → PostgreSQL (bronze/silver/gold) → CSVs do Power BI.
> App, API e IA entram nas próximas fases.

| Área do edital | Pasta | O que tem |
|---|---|---|
| 1. IA e automação | *(fase 2)* | A base de treino já sai pronta em `gold.v_ml_features` |
| 2. Big Data e visualização | [`area2-bigdata/`](area2-bigdata/README.md) | Camadas bronze/silver/gold, ingestão em tempo real e em lote, exportação, Power BI |
| 3. MVP, IoT e experiência digital | [`area3-mvp/iot/`](area3-mvp/iot/README.md) | Broker MQTT, 29 sensores simulados, circuito ESP32 no Wokwi, ponte segura |
| 4. DevOps, segurança e qualidade | [`area4-devops/`](area4-devops/plano-de-testes.md) | Docker Compose, CI no GitHub Actions, plano de testes, práticas de segurança |
| Contrato das mensagens | [`contratos/`](contratos/leitura.v1.schema.json) | JSON Schema seguido por todos os serviços |
| Arquitetura | [`docs/arquitetura.md`](docs/arquitetura.md) | Diagrama e fluxo dos dados |

## Como rodar

**Pré-requisito:** Docker Desktop aberto (Windows, macOS ou Linux). Não precisa de Python
instalado nem de internet. A internet só é usada pela ponte opcional do Wokwi.

```bash
cp .env.example .env
```

No Windows (PowerShell), use `Copy-Item .env.example .env` no lugar do comando acima.

```bash
docker compose up -d --build --wait
```

Na primeira vez leva cerca de 1 minuto. O Compose sobe e conecta tudo sozinho:

1. **postgres** e **mosquitto** (broker MQTT com usuário, senha e permissões por tópico);
2. **migrar**: cria as tabelas e visões e carrega os cadastros (94 bairros, 4 estações, 21 abrigos, 29 sensores);
3. **historico-gerar** e **historico-carregar**: geram e carregam 30 dias de histórico (cerca de 112 mil leituras);
4. **ingestor**: recebe as leituras do MQTT em tempo real;
5. **simulador**: publica as leituras dos sensores. Cada segundo real equivale a 10 minutos simulados, então uma enchente completa leva uns 13 minutos.

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

### Exportar os dados para o Power BI

```bash
docker compose --profile ferramentas run --rm exportar
```

Os CSVs saem em `area2-bigdata/powerbi/dados/`. O passo a passo do dashboard está em [`area2-bigdata/powerbi/README.md`](area2-bigdata/powerbi/README.md).

### Rodar os testes

Testes de integração (13 casos contra o ambiente rodando; o relatório vai para `relatorios/integracao.xml`):

```bash
docker compose --profile ferramentas run --rm --build testes
```

Testes de unidade e lint (precisa de Python 3.12 ou mais novo):

```bash
python -m venv .venv
```

```bash
.venv/bin/pip install -r requirements-dev.txt
```

```bash
.venv/bin/ruff check . && .venv/bin/python -m pytest
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

Para tudo e apaga o banco (o histórico é recarregado do data lake na próxima subida):

```bash
docker compose down -v
```

## Portas

| Serviço | Porta no seu computador | Uso |
|---|---|---|
| PostgreSQL | 55432 | Banco `citizentech`. O usuário `bi_ro` só lê a camada gold |
| Mosquitto (MQTT) | 11883 | Exige usuário e senha (veja o `.env`) |

## Uso de IA generativa

Declaração exigida pelo edital.

| Ferramenta | Para quê |
|---|---|
| Claude (Anthropic), via Claude Code | Pesquisa de versões e limitações (Wokwi, Mosquitto 2, PostgreSQL 18), desenho da arquitetura da fase 1, geração de código, testes e documentação, calibração do modelo de simulação |

O grupo revisou, executou e testou todo o código entregue e consegue explicar cada parte. Os testes de unidade e de integração e o CI são a evidência de que tudo roda.

## Integrantes e pitch

Ver [`integrantes.txt`](integrantes.txt). Link do vídeo pitch: **(preencher)**.

## Créditos de dados

Bairros, escolas e ginásios de Porto Alegre: © colaboradores do OpenStreetMap (ODbL).
As cotas e a zona de risco são simplificações; veja [`area2-bigdata/db/seeds/README.md`](area2-bigdata/db/seeds/README.md).
