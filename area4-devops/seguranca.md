# Segurança — práticas aplicadas

O edital pede pelo menos 2 práticas. O projeto aplica 12, e cada uma tem teste ou evidência.

| # | Prática | Onde | Evidência |
|---|---|---|---|
| 1 | **Autenticação no broker MQTT**: `allow_anonymous false`; uma senha por serviço, gerada a partir do `.env` | [`mosquitto.conf`](../area3-mvp/iot/mosquitto/mosquitto.conf), [`entrypoint.sh`](../area3-mvp/iot/mosquitto/entrypoint.sh) | CT-05 |
| 2 | **Autorização por tópico (ACL)**: o simulador só publica em `sim/`, a ponte só em `wokwi/`, o ingestor só lê | [`acl`](../area3-mvp/iot/mosquitto/acl) | CT-06 |
| 3 | **Validação de entrada**: JSON Schema, sensor cadastrado e com a origem certa, unidade, faixa (inclusive números gigantes), horário e tamanho máximo (4 KB). Tudo que é rejeitado fica auditado no bronze | [`validacao.py`](../area2-bigdata/ingestor/ingestor/validacao.py), [`processamento.py`](../area2-bigdata/ingestor/ingestor/processamento.py) | CT-03, CT-04, CT-23, `gold.v_qualidade` |
| 4 | **Menor privilégio no banco**: `ingestor_rw` não apaga nem altera estrutura; `bi_ro` (dashboard) e `ia_ro` (API de IA) só leem o gold | [`005_permissoes.sql`](../area2-bigdata/db/migrations/005_permissoes.sql), [`007_ia.sql`](../area2-bigdata/db/migrations/007_ia.sql) | CT-07, CT-08, CT-33 |
| 5 | **Segredos fora do código**: senhas só no `.env`, que fica fora do git (`.gitignore`); o `.env.example` traz só valores de desenvolvimento | [`.env.example`](../.env.example) | revisão do repositório |
| 6 | **Integridade dos dados vindos da internet**: assinatura HMAC-SHA256, lista de sensores, `seq` crescente contra reenvio (inclusive logo após a ponte reiniciar), janela de 2 min e limite de 1 msg/s | [`ponte_wokwi.py`](../area3-mvp/iot/simuladores/simuladores/ponte_wokwi.py) | CT-19, CT-20, CT-21, CT-26 |
| 7 | **Contenção**: o que vem da internet só alimenta a estação `demo-wokwi`; uma mensagem falsa nunca dispara alerta de rio real | cadastros em [`seeds/`](../area2-bigdata/db/seeds) | CT-04 |
| 8 | **Containers sem root**: as imagens do ingestor, do simulador e da IA rodam como usuário `app` (uid 10001); o app web roda no nginx sem root (usuário `nginx`, porta 8080) | Dockerfiles | `docker compose exec api id`, `docker compose exec app id` |
| 9 | **Rede fechada**: banco, broker, API e app só aceitam conexões da própria máquina (`127.0.0.1`), porque as senhas de exemplo estão no repositório público | [`docker-compose.yml`](../docker-compose.yml) | CT-28 |
| 10 | **Resiliência a entrada maliciosa**: nenhuma mensagem derruba o ingestor ou a ponte (erros inesperados são registrados e o processamento segue), e uma leitura só é confirmada ao broker depois de gravada | [`consumidor.py`](../area2-bigdata/ingestor/ingestor/consumidor.py), [`ponte_wokwi.py`](../area3-mvp/iot/simuladores/simuladores/ponte_wokwi.py) | CT-23, CT-24 |
| 11 | **API com entrada validada e CORS restrito**: parâmetros e corpo validados por tipo e faixa (pydantic), respostas 404/422 claras e 503 quando o banco cai (sem vazar detalhes internos); o navegador só chama a API a partir das origens do `API_CORS_ORIGENS` (só o app em desenvolvimento; o app do Compose usa o proxy, sem CORS) | [`api.py`](../area1-ia/ia/api.py) | CT-40, CT-42, `test_api.py::test_cors_libera_o_app_da_fase_3` |
| 12 | **App web com cabeçalhos de segurança e a API no mesmo endereço**: o nginx repassa `/api` para a API, então não há CORS aberto. A CSP só aceita arquivos e chamadas do próprio endereço, sem script inline. O nginx também manda `nosniff`, `X-Frame-Options: DENY` e `frame-ancestors 'none'` (contra clickjacking), `Referrer-Policy: no-referrer` e `Permissions-Policy`, que libera a localização só para o próprio app. As respostas da API passam com `no-store` | [`nginx/`](../area3-mvp/app/nginx) | CT-54 (`test_it23_app_web_no_ar_e_api_pelo_proxy`) |

## Proteção de dados (LGPD)

O sistema não coleta dado pessoal: as leituras são de rios e contagens anônimas de pessoas
nos abrigos, e o app não tem login nem cadastro. A decisão é que **a localização do cidadão
fique só no celular**:
- `GET /abrigos` devolve a avaliação de todos os abrigos (apto, vagas na chegada, risco
  previsto), e o app calcula a distância no aparelho, sem enviar a posição (CT-41, CT-57);
- `GET /abrigos/recomendacao` recebe só o **bairro** (posição aproximada, um entre 94) e
  usa o centro dele (CT-41);
- no app, a posição fica só na memória e some quando o app fecha. Ela nunca entra numa URL,
  nem na rota da tela do abrigo, e nunca é gravada (CT-57);
- **Como chegar** abre o mapa só com o destino, e o mapa usa a localização do próprio
  aparelho. Com o `no-referrer`, o mapa também não fica sabendo de qual tela a pessoa veio;
- o bairro, o tamanho do grupo e a escolha dos avisos ficam só no aparelho (AsyncStorage;
  no navegador, `localStorage`), e a pessoa pode trocar ou desligar em Ajustes.

## Limitações conhecidas (sinceridade no pitch)

- A chave HMAC do Wokwi é de demonstração: o projeto no Wokwi é público, então ela fica visível.
- O MQTT local não usa TLS. Num ambiente real, o broker teria TLS (porta 8883) e certificados.
- As senhas do `.env.example` são de desenvolvimento; num ambiente real ficariam num cofre de segredos.
- O app web roda em HTTP no `localhost`. Num ambiente real, ele ficaria atrás de HTTPS, que o GPS do navegador também exige fora do `localhost`.
- A CSP libera `style-src 'unsafe-inline'`, porque o react-native-web gera os estilos na hora. Os scripts inline continuam proibidos.
