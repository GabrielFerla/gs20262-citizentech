# Arquitetura — fase 1

```mermaid
flowchart LR
    subgraph Campo["Sensores (IoT)"]
        SIM["Simulador Python<br/>26 sensores<br/>nível · chuva · ocupação"]
        ESP["ESP32 no Wokwi<br/>HC-SR04 · potenciômetro · PIR<br/>LED de alerta local"]
    end

    subgraph Internet
        PUB[("Broker público<br/>broker.hivemq.com")]
    end

    subgraph Compose["docker compose (roda sem internet)"]
        PONTE["Ponte Wokwi<br/>HMAC · lista de sensores<br/>seq · horário · 1 msg/s"]
        MQ[("Mosquitto<br/>usuário + senha + ACL")]
        ING["Ingestor<br/>valida contrato e regras<br/>regra de alerta"]
        GER["Gerador de histórico<br/>30 dias (NDJSON)"]
        LAND[/"Data lake: landing<br/>arquivos NDJSON"/]
        LOTE["Carga em lote<br/>mesmas regras do MQTT"]
        subgraph PG["PostgreSQL"]
            B[("bronze<br/>tudo o que chegou")]
            S[("silver<br/>leituras validadas · alertas · cadastros")]
            G[("gold<br/>visões para decisão")]
        end
        EXP["Exportador<br/>usuário bi_ro (só lê gold)"]
    end

    PBI["Power BI<br/>dashboard"]
    APP["App + API<br/>(fase 3)"]
    IA["IA de previsão de nível<br/>(fase 2)"]

    SIM -- "MQTT QoS 1<br/>citizentech/v1/sim/#" --> MQ
    ESP -- "MQTT" --> PUB --> PONTE -- "citizentech/v1/wokwi/#" --> MQ
    MQ --> ING --> B
    GER --> LAND --> LOTE --> B
    B --> S --> G
    G --> EXP -- "CSV" --> PBI
    G -. "v_abrigo_status · v_estacao_atual" .-> APP
    G -. "v_ml_features" .-> IA
```

## Fluxo de uma leitura

1. O sensor publica um JSON no contrato [`leitura.v1`](../contratos/leitura.v1.schema.json) no tópico `citizentech/v1/{origem}/{sensor_id}`.
2. O Mosquitto confere usuário, senha e permissão. O simulador só publica em `sim/`; a ponte só publica em `wokwi/`.
3. O ingestor processa a leitura:
   1. Grava a mensagem bruta no **bronze**. Uma mensagem idêntica que chega de novo (reentrega do QoS 1) é barrada aqui.
   2. Valida a leitura:
      - schema e tópico;
      - sensor cadastrado e com a origem certa;
      - unidade e faixa de valor;
      - horário.
      Se falhar, a mensagem fica no bronze como `rejeitada`, com o motivo.
   3. Grava no **silver**. Uma leitura com salto de nível impossível vira `suspeita` e fica fora das visões gold.
   4. Se for nível de rio, aplica a regra de alerta: abre, escala ou fecha, com uma folga de 0,10 m para não ficar abrindo e fechando.
4. As visões **gold** respondem às perguntas de decisão:
   - Qual rio está em alerta?
   - Quais abrigos têm vaga e podem ser recomendados?
   - Como foi a série histórica?

## Duas entradas de dados, mesmas regras

| Caminho | Entrada | Uso |
|---|---|---|
| Tempo real | MQTT, uma mensagem por leitura | Situação atual, alertas, app |
| Lote | Arquivos NDJSON na zona de chegada (landing) | Série histórica, dashboard, treino da IA |

As duas entradas chamam a mesma função `processar()` ([`processamento.py`](../area2-bigdata/ingestor/ingestor/processamento.py)).
Por isso um dado nunca entra no banco por um caminho mais frouxo.

## Decisões e por quê

| Decisão | Motivo |
|---|---|
| Um contrato JSON Schema compartilhado | Simulador, ESP32, ingestor e o futuro app falam o mesmo formato. É validado em um lugar só |
| Camadas bronze/silver/gold no PostgreSQL | Guarda o dado bruto para auditoria e mantém o dado tratado separado das visões de decisão |
| Ocupação do abrigo enviada como número absoluto | Se a mesma mensagem chegar duas vezes, o resultado não muda |
| Broker público + ponte para o Wokwi | O Wokwi gratuito não alcança o computador local; a ponte filtra o que chega da internet |
| Migrações próprias (`migrar.py`) | Rodam a cada subida e são idempotentes, e param com erro se uma migração já aplicada for editada. O `initdb.d` do Postgres só roda com o banco vazio |
| Simulação acelerada com "aquecimento" | A demo mostra uma enchente em minutos, e o rio continua de onde o histórico parou |
