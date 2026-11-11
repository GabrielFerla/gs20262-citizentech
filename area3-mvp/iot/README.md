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
| Tempo real | `python -m simuladores.tempo_real --cenario ciclo --velocidade 600` | MQTT. Cada segundo real = 10 minutos simulados; ciclo de enchente em cerca de 13 minutos, que recomeça do rio normal a cada volta |

## Circuito ESP32 no Wokwi

1. Em <https://wokwi.com>, crie um projeto **ESP32** e substitua `sketch.ino` e `diagram.json` pelos desta pasta.
2. Em **Library Manager**, adicione **PubSubClient** (é o que está em `libraries.txt`).
3. No projeto, suba a ponte, que fica ouvindo o broker público:

   ```bash
   docker compose --profile wokwi up -d ponte-wokwi
   ```

4. Rode a simulação no Wokwi (a primeira compilação leva cerca de 20 s). Para interagir:
   - clique no HC-SR04 e mude a distância no controle deslizante (menos distância = rio mais alto). O sensor fica a 4 m do fundo: 270 cm dá 1,30 m e acende o LED (cota de alerta 1,20 m); 220 cm dá 1,80 m (inundação);
   - clique no potenciômetro e use as setas do teclado, ou arraste o botão, para simular chuva;
   - clique no PIR e em **Simulate motion** para contar uma entrada no abrigo; clique no botão azul para contar uma saída.

   **Deixe a aba do Wokwi visível.** Em segundo plano o navegador reduz a simulação a cerca de 3% da velocidade
   (o canto da simulação mostra a porcentagem). O relógio do ESP32 é o tempo simulado, então ele atrasa, e com
   mais de 2 minutos de atraso a ponte recusa as leituras ("horário fora da janela de 2 minutos"). O ESP32
   ressincroniza o relógio a cada minuto simulado: depois de uma pausa curta ele volta sozinho; se ficou muito
   tempo em segundo plano, clique em reiniciar a simulação.
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

**Validado no Wokwi em 07/11/2026** (casos CT-46 a CT-49 do [plano de testes](../../area4-devops/plano-de-testes.md), print em [`docs/evidencias/wokwi-simulacao.jpg`](../../docs/evidencias/wokwi-simulacao.jpg)):
- o sketch compila com o `diagram.json` e a biblioteca PubSubClient;
- 150 leituras assinadas passaram pela ponte e entraram no banco, sem nenhuma rejeitada;
- o nível subiu de 0,97 m para 1,28 m (LED aceso) e 1,78 m: o pipeline abriu o alerta da estação `demo-wokwi`, escalou para inundação e fechou quando o nível caiu para 0,37 m;
- a chuva do potenciômetro chegou como `wok-chuva` (7,63 mm);
- duas entradas no PIR e um toque no botão deixaram o abrigo `abr-demo` com 1 pessoa.

O teste achou um defeito, já corrigido: um toque rápido no botão de saída se perdia, porque o loop só olhava o pino a cada 80 ms ou mais e fica parado enquanto reconecta ao broker. Agora o PIR e o botão são lidos por interrupção, com 200 ms de debounce no botão.

A ponte também foi testada antes com um publicador Python no papel do ESP32: a mensagem assinada chegou ao banco e a forjada foi recusada.
