# Área 3 — IoT (sensores e broker)

| Componente | Pasta | O que faz |
|---|---|---|
| Broker MQTT | [`mosquitto/`](mosquitto) | Mosquitto 2 com usuário e senha, ACL por tópico e limite de 4 KB por mensagem |
| Sensores simulados | [`simuladores/`](simuladores) | 3 estações (nível + chuva) e 20 abrigos (ocupação). São 26 sensores, em tempo real e histórico |
| Circuito físico simulado | [`esp32_wokwi/`](esp32_wokwi) | ESP32 com ultrassônico (nível), potenciômetro (chuva), PIR + botão (ocupação) e LED de alerta |
| Ponte segura | [`simuladores/simuladores/ponte_wokwi.py`](simuladores/simuladores/ponte_wokwi.py) | Traz as leituras do broker público para o local |

## Contrato MQTT

- **Tópico:** `citizentech/v1/{origem}/{sensor_id}`, com origem `sim` (simulador) ou `wokwi` (ESP32 via ponte).
- **Mensagem:** veja [`contratos/leitura.v1.schema.json`](../../contratos/leitura.v1.schema.json) e os [exemplos](../../contratos/exemplos).

```json
{"v":1,"sensor_id":"gua-cais-nivel","valor":2.87,"unidade":"m","medido_em":"2026-11-07T15:00:00Z","seq":812}
```

| Tipo | Unidade | Significado |
|---|---|---|
| `nivel_rio` | m | Nível do rio |
| `chuva` | mm | Chuva nos últimos 10 minutos |
| `ocupacao_abrigo` | pessoas | Pessoas no abrigo agora. É número absoluto, então chegar duas vezes não muda nada |

## Simulador

A física fica em [`modelo.py`](simuladores/simuladores/modelo.py) e é determinística: a mesma semente gera os mesmos dados.
- **Chuva:** cadeia de Markov, com cenários `normal`, `chuva_forte` e `enchente`.
- **Rio:** dois reservatórios em série. O nível sobe com **atraso** depois da chuva: rápido no Arroio Dilúvio, lento no Guaíba.
- **Abrigos:** as pessoas chegam rápido quando o rio passa da cota de alerta e saem devagar. Um abrigo em área de risco é evacuado se o rio inundar.
- **Defeitos reais de sensor:** 0,5% das leituras não chegam, 0,1% têm pico absurdo e 0,1% chegam corrompidas.

| Modo | Comando (já roda no `docker compose up`) | Saída |
|---|---|---|
| Histórico | `python -m simuladores.historico --dias 30` | Arquivo NDJSON na zona de chegada do data lake |
| Tempo real | `python -m simuladores.tempo_real --cenario ciclo --velocidade 600` | MQTT. Cada segundo real = 10 minutos simulados; ciclo de enchente em cerca de 13 minutos |

## Circuito ESP32 no Wokwi

1. Em <https://wokwi.com>, crie um projeto **ESP32** e substitua `sketch.ino` e `diagram.json` pelos desta pasta.
2. Em **Library Manager**, adicione **PubSubClient** (é o que está em `libraries.txt`).
3. No projeto, suba a ponte, que fica ouvindo o broker público:

   ```bash
   docker compose --profile wokwi up -d ponte-wokwi
   ```

4. Rode a simulação no Wokwi. Para interagir:
   - clique no HC-SR04 e mude a distância (menos distância = rio mais alto; o LED acende a partir de 1,20 m);
   - gire o potenciômetro para simular chuva;
   - acione o PIR para contar entradas no abrigo e aperte o botão azul para contar saídas.
5. Acompanhe a ponte:

   ```bash
   docker compose logs -f ponte-wokwi
   ```

   Os dados aparecem na estação `demo-wokwi` e no abrigo `abr-demo`:

   ```bash
   docker compose exec postgres psql -U migrador -d citizentech -c "SELECT * FROM gold.v_estacao_atual WHERE estacao_id='demo-wokwi';"
   ```

**Por que uma ponte?** No plano gratuito, o Wokwi só acessa a internet; ele não alcança o computador local.
O ESP32 publica em `broker.hivemq.com`, num prefixo próprio do grupo (`WOKWI_PREFIXO` no `.env`).

A ponte só repassa uma mensagem se ela passar por todas estas checagens:
- assinatura HMAC-SHA256 correta (`WOKWI_CHAVE`);
- sensor na lista permitida;
- `seq` crescente (impede reenvio);
- horário a no máximo 2 minutos do relógio da ponte;
- no máximo 1 mensagem por segundo por sensor.

Os sensores do Wokwi pertencem a uma estação de demonstração: nada que venha da internet dispara alerta de um rio real.

> A chave no sketch é de **demonstração**, porque o projeto no Wokwi fica público. Para uso real, gere outra chave e troque no `.env` e no sketch.

> **Validado:** a ponte foi testada de ponta a ponta pelo broker público, com um publicador Python fazendo o papel do ESP32. A mensagem assinada chegou ao banco e a forjada foi recusada.
> **Ainda não validado:** o `sketch.ino` e o `diagram.json` não foram rodados no Wokwi. Confira na primeira execução e anote ajustes aqui.
