# Área 2 — Big Data e visualização

| Critério do edital | Onde está |
|---|---|
| Estrutura dos dados (camadas, data lake) | [`db/migrations/`](db/migrations): esquemas `bronze`, `silver`, `gold`; zona de chegada no volume `datalake` |
| Ingestão e processamento | [`ingestor/`](ingestor): tempo real (MQTT) e lote (NDJSON), validação, deduplicação, qualidade |
| Dashboard (3+ indicadores com filtros) | [`powerbi/`](powerbi/README.md): CSVs prontos e montagem sugerida |
| Funções analíticas (DAX) | [`powerbi/README.md`](powerbi/README.md#medidas-dax) e janelas SQL em `gold.v_ml_features` |

## Camadas

| Camada | Tabelas e visões | Para quê |
|---|---|---|
| **landing** (arquivos) | volume Docker `datalake` (`/dados/landing/*.ndjson`) | Dado bruto da carga histórica, imutável. O banco pode ser refeito a partir daqui |
| **bronze** | `bronze.mensagem`, `bronze.carga` | Tudo o que chegou, inclusive o inválido, com status e motivo (auditoria) |
| **silver** | `silver.leitura`, `silver.alerta` e os cadastros `bairro`, `estacao`, `abrigo`, `sensor` | Dado validado e tratado; regra de alerta aplicada |
| **gold** | `dim_*`, `v_estacao_horaria`, `v_abrigo_horaria`, `v_ml_features`, `v_estacao_atual`, `v_abrigo_status`, `v_alertas`, `v_qualidade`, `v_kpis` | Visões prontas para o dashboard, o app e a IA |

## Do sensor ao dado tratado

```
sensor ──MQTT──► bronze.mensagem ──validação──► silver.leitura ──agregação──► gold.v_*
                     │                              │
                     └─ rejeitada (motivo)          └─ suspeita (salto impossível) fica fora do gold
```

**Validações** ([`validacao.py`](ingestor/ingestor/validacao.py)):
- contrato JSON Schema;
- tópico coerente com a mensagem;
- sensor cadastrado, ativo e com a origem certa;
- unidade e faixa do sensor;
- ocupação inteira;
- horário que não está no futuro.

**Deduplicação em duas barreiras:**
1. `hash` único da mensagem no bronze, contra reentrega do QoS 1.
2. Chave `(sensor, horário)` no silver.

**Qualidade:** um salto de nível maior que `salto_max_m` em 10 minutos marca a leitura como `suspeita`. Ela fica no silver e fora do gold.

## Comandos

Exportar a camada gold para CSV:

```bash
docker compose --profile ferramentas run --rm exportar
```

Ver os arquivos do data lake (copia para `datalake/` no projeto, útil para print no PDF):

```bash
docker compose cp historico-gerar:/dados/landing ./area2-bigdata/datalake/
```

Gerar um histórico novo do zero (apaga banco e data lake; o novo histórico termina no horário atual):

```bash
docker compose down -v
```

```bash
docker compose up -d --wait
```

**Mudar o banco:** nunca edite uma migração já aplicada. Crie um arquivo novo (`007_...sql`),
como foi feito em [`006_ml_features_uma_agregacao.sql`](db/migrations/006_ml_features_uma_agregacao.sql).
O `migrar` guarda o hash de cada migração e para com erro se uma delas for editada.

Consultar o banco direto (senha do usuário `migrador` no `.env`): `localhost:55432`, banco `citizentech`.
