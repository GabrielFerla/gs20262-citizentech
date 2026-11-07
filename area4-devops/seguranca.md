# Segurança — práticas aplicadas

O edital pede pelo menos 2 práticas. A fase 1 aplica 10, e cada uma tem teste ou evidência.

| # | Prática | Onde | Evidência |
|---|---|---|---|
| 1 | **Autenticação no broker MQTT**: `allow_anonymous false`; uma senha por serviço, gerada a partir do `.env` | [`mosquitto.conf`](../area3-mvp/iot/mosquitto/mosquitto.conf), [`entrypoint.sh`](../area3-mvp/iot/mosquitto/entrypoint.sh) | CT-05 |
| 2 | **Autorização por tópico (ACL)**: o simulador só publica em `sim/`, a ponte só em `wokwi/`, o ingestor só lê | [`acl`](../area3-mvp/iot/mosquitto/acl) | CT-06 |
| 3 | **Validação de entrada**: JSON Schema, sensor cadastrado e com a origem certa, unidade, faixa (inclusive números gigantes), horário e tamanho máximo (4 KB). Tudo que é rejeitado fica auditado no bronze | [`validacao.py`](../area2-bigdata/ingestor/ingestor/validacao.py), [`processamento.py`](../area2-bigdata/ingestor/ingestor/processamento.py) | CT-03, CT-04, CT-23, `gold.v_qualidade` |
| 4 | **Menor privilégio no banco**: `ingestor_rw` não apaga nem altera estrutura; `bi_ro` só lê o gold | [`005_permissoes.sql`](../area2-bigdata/db/migrations/005_permissoes.sql) | CT-07, CT-08 |
| 5 | **Segredos fora do código**: senhas só no `.env`, que fica fora do git (`.gitignore`); o `.env.example` traz só valores de desenvolvimento | [`.env.example`](../.env.example) | revisão do repositório |
| 6 | **Integridade dos dados vindos da internet**: assinatura HMAC-SHA256, lista de sensores, `seq` crescente contra reenvio (inclusive logo após a ponte reiniciar), janela de 2 min e limite de 1 msg/s | [`ponte_wokwi.py`](../area3-mvp/iot/simuladores/simuladores/ponte_wokwi.py) | CT-19, CT-20, CT-21, CT-26 |
| 7 | **Contenção**: o que vem da internet só alimenta a estação `demo-wokwi`; uma mensagem falsa nunca dispara alerta de rio real | cadastros em [`seeds/`](../area2-bigdata/db/seeds) | CT-04 |
| 8 | **Containers sem root**: as imagens do ingestor e do simulador rodam como usuário `app` (uid 10001) | Dockerfiles | `docker compose exec ingestor id` |
| 9 | **Rede fechada**: banco e broker só aceitam conexões da própria máquina (`127.0.0.1`), porque as senhas de exemplo estão no repositório público | [`docker-compose.yml`](../docker-compose.yml) | CT-28 |
| 10 | **Resiliência a entrada maliciosa**: nenhuma mensagem derruba o ingestor ou a ponte (erros inesperados são registrados e o processamento segue), e uma leitura só é confirmada ao broker depois de gravada | [`consumidor.py`](../area2-bigdata/ingestor/ingestor/consumidor.py), [`ponte_wokwi.py`](../area3-mvp/iot/simuladores/simuladores/ponte_wokwi.py) | CT-23, CT-24 |

## Proteção de dados (LGPD)

A fase 1 não coleta dado pessoal: as leituras são de rios e contagens anônimas de pessoas
nos abrigos. Para o app (fase 3), a decisão é que **a localização do cidadão fique só no
celular**: o app baixa a lista de abrigos e calcula a distância localmente, sem enviar a
posição ao servidor.

## Limitações conhecidas (sinceridade no pitch)

- A chave HMAC do Wokwi é de demonstração: o projeto no Wokwi é público, então ela fica visível.
- O MQTT local não usa TLS. Num ambiente real, o broker teria TLS (porta 8883) e certificados.
- As senhas do `.env.example` são de desenvolvimento; num ambiente real ficariam num cofre de segredos.
