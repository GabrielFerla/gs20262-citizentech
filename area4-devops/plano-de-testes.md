# Plano de testes — fases 1 a 3

**Objetivo:** garantir que as leituras dos sensores chegam ao banco validadas, sem duplicar,
que dados inválidos ou de origem não autorizada são barrados, e que os alertas e as vagas
dos abrigos são calculados corretamente. Na fase 2, garantir também que a IA prevê melhor
que a regra simples, que nunca recomenda um abrigo inapto e que as mensagens seguem as
regras de linguagem simples. Na fase 3, garantir que o app avisa do alerta, leva a pessoa a um abrigo
seguro sem enviar a posição dela e continua útil quando a API cai.

| Tipo | Ferramenta | Como rodar | Quantidade |
|---|---|---|---|
| Unidade | pytest | `.venv/bin/python -m pytest` | 275 testes (97 da fase 1 + 178 da IA) |
| Integração | pytest no docker compose (broker, banco, API, app e serviços reais) | `docker compose --profile ferramentas run --rm --build testes` | 23 testes |
| App (unidade e telas) | Jest + Testing Library | `cd area3-mvp/app && npm test` | 112 testes |
| Métrica da IA | relatório contra os dados do pipeline | `docker compose --profile ferramentas run --rm ia-relatorio` | sai em `relatorios/ia/`; referência em [`RELATORIO.md`](../area1-ia/relatorio/RELATORIO.md) |
| Lint e tipos | ruff (Python); ESLint e TypeScript (app) | `.venv/bin/ruff check .`; `npm run lint && npm run typecheck` | — |
| CI | GitHub Actions ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)) | automático a cada push e pull request | todos os acima, menos a métrica |

**Evidências:**
- relatórios JUnit em `relatorios/` (gerados localmente e anexados pelo CI);
- print do GitHub Actions verde;
- prints dos comandos abaixo;
- prints do app em `docs/evidencias/app-*.png`.

## Casos de teste

Execução em 09/11/2026 (macOS, Docker 29), com o app da fase 3: **unidade 275/275 ok · integração 23/23 ok · app 112/112 ok**.

| ID | Requisito | Tipo | Passos | Resultado esperado | Obtido | Teste automatizado |
|---|---|---|---|---|---|---|
| CT-01 | Leitura válida chega ao banco | Integração | Publicar leitura do `wok-nivel` no MQTT | 1 linha em `silver.leitura` em até 15 s | ✅ | `test_it01_mensagem_publicada_chega_na_silver` |
| CT-02 | Não duplicar reentregas do QoS 1 | Integração | Publicar a mesma mensagem 2 vezes | 1 linha no bronze e 1 no silver | ✅ | `test_it02_mesma_mensagem_duas_vezes_vira_uma_linha` |
| CT-03 | Rejeitar dado fora do contrato | Integração | Publicar leitura com unidade `cm` | Bronze com status `rejeitada` e motivo `contrato:`; nada no silver | ✅ | `test_it03_mensagem_invalida_fica_rejeitada_no_bronze` |
| CT-04 | Sensor só aceito da sua origem | Integração | Publicar sensor do Wokwi no tópico `sim/` | Rejeitada com motivo `origem:` | ✅ | `test_it04_sensor_publicando_com_origem_errada_e_rejeitado` |
| CT-05 | Broker exige autenticação | Integração | Conectar no MQTT sem usuário | Conexão recusada | ✅ | `test_it05_conexao_anonima_e_recusada` |
| CT-06 | ACL por tópico | Integração | Usuário `simulador` publica em `wokwi/` | Mensagem descartada pelo broker; nada no banco | ✅ | `test_it06_acl_impede_simulador_de_publicar_como_wokwi` |
| CT-07 | Dashboard só lê o gold | Integração | Usuário `bi_ro` consulta `silver.leitura` | Erro de permissão; consulta ao gold funciona | ✅ | `test_it07_usuario_do_dashboard_so_le_a_camada_gold` |
| CT-08 | Ingestor não apaga dados | Integração | Usuário `ingestor_rw` executa `DELETE` | Erro de permissão | ✅ | `test_it08_ingestor_nao_consegue_apagar_dados` |
| CT-09 | Alerta abre, escala e fecha uma vez | Integração | Níveis 0,30 → 1,00 → 1,30 → 0,75 → 0,50 m (cotas 0,8/1,2/1,6) | 1 alerta, severidade 2 (alerta), pico 1,30 m, fechado | ✅ | `test_it09_alerta_abre_escala_e_fecha_uma_vez` |
| CT-10 | Vagas do abrigo | Integração | Ocupação 45 no abrigo de 50 lugares | 5 vagas, status `quase_cheio` | ✅ | `test_it10_vagas_do_abrigo_sao_calculadas` |
| CT-11 | Migrações idempotentes | Integração | Rodar as migrações de novo | Nenhuma migração reaplicada | ✅ | `test_it11_migracoes_rodam_de_novo_sem_mudar_nada` |
| CT-12 | Histórico carregado e base de treino | Integração | Consultar `bronze.carga` e `gold.v_ml_features` | Carga concluída; exemplos com o alvo de 6 h preenchido | ✅ | `test_it12_historico_foi_carregado_e_gera_base_de_treino` |
| CT-13 | Sensores publicando em tempo real | Integração | Consultar leituras MQTT do último minuto | Mais de 0 leituras | ✅ | `test_it13_simulador_esta_publicando_em_tempo_real` |
| CT-14 | Contrato aceita os exemplos válidos e recusa os inválidos | Unidade | Validar `contratos/exemplos/*` | 3 válidos ok, 7 inválidos recusados | ✅ | `test_contrato.py` |
| CT-15 | Regra de alerta com folga (histerese) | Unidade | Nível 1,95 m com alerta aberto (atenção 2,00) | Mantém aberto; só fecha abaixo de 1,90 m | ✅ | `test_alertas.py::test_folga_evita_abre_e_fecha` |
| CT-16 | Pico falso de sensor | Unidade | Leitura pula 2,5 m em 10 min | Marcada `suspeita` e não abre alerta | ✅ | `test_processamento.py::test_leitura_suspeita_nao_abre_alerta` |
| CT-17 | Simulação reproduzível | Unidade | Rodar 2 vezes com a semente 42 | Dados idênticos | ✅ | `test_modelo.py::test_mesma_semente_gera_os_mesmos_dados` |
| CT-18 | Física do rio | Unidade | Pulso de 6 h de chuva | Pico do Guaíba mais de 6 h depois da chuva; o Dilúvio responde antes | ✅ | `test_modelo.py` |
| CT-19 | Ponte rejeita mensagem forjada | Unidade | Mensagem com assinatura errada ou valor alterado | Recusada | ✅ | `test_ponte_wokwi.py` |
| CT-20 | Ponte rejeita reenvio e excesso | Unidade | Repetir `seq`; 2 mensagens em 0,5 s | Recusadas | ✅ | `test_ponte_wokwi.py` |
| CT-21 | Ponte Wokwi ponta a ponta | Manual | Publicador Python no `broker.hivemq.com` envia 1 leitura assinada e 1 forjada | Assinada no banco (estação `demo-wokwi` entra em alerta com 1,37 m); forjada recusada pela ponte | ✅ | — (log da ponte) |
| CT-22 | Projeto roda só com o README | Manual | Clone limpo + comandos do README | Todos os serviços `healthy`; dados no gold | ✅ | — |
| CT-23 | Valor gigante não derruba nada | Unidade | Leitura com valor = inteiro de 400 dígitos, no ingestor e na ponte | Rejeitada com motivo `faixa:` / "grande demais"; processo segue de pé | ✅ | `test_processamento.py::test_valor_gigante_e_rejeitado_sem_erro`, `test_ponte_wokwi.py::test_valor_gigante_e_recusado_sem_derrubar_a_ponte` |
| CT-24 | Nenhuma leitura perdida se o banco cair | Manual | Desligar o Postgres por 20 s com o simulador publicando (`docker compose stop postgres`, esperar, `start`) | Ingestor espera o banco voltar e grava tudo: 40 leituras em 39 s, maior intervalo 1,0 s | ✅ | — (log do ingestor + consulta) |
| CT-25 | Migração editada é detectada | Integração | Editar `004_gold.sql` já aplicada e rodar as migrações | Para com erro explicando que é preciso criar uma migração nova | ✅ | `test_it14_migracao_editada_depois_de_aplicada_para_com_erro` |
| CT-26 | Ponte barra reenvio logo após reiniciar | Unidade | Mensagem medida antes do início da ponte | Recusada | ✅ | `test_ponte_wokwi.py::test_mensagem_medida_antes_de_a_ponte_reiniciar_e_recusada` |
| CT-27 | Simulador não dispara rajada após pausa | Unidade | Processo parado 10 min | Retoma do horário atual, sem publicar os passos atrasados | ✅ | `test_tempo_real.py` |
| CT-28 | Banco e broker fechados para a rede | Manual | `docker compose ps` | Portas publicadas só em `127.0.0.1` | ✅ | — |

### Fase 2 — IA e automação (área 1)

| ID | Requisito | Tipo | Passos | Resultado esperado | Obtido | Teste automatizado |
|---|---|---|---|---|---|---|
| CT-29 | API da IA no ar | Integração | `GET /saude` | 200, banco acessível, modelo dos 3 rios carregado | ✅ | `test_it15_api_da_ia_esta_saudavel` |
| CT-30 | Previsão de 6 h dos rios | Integração | `GET /previsao` | 3 estações reais, nível previsto entre 0 e 15 m, persistência = nível atual, features de entrada | ✅ | `test_it16_previsao_de_6h_para_os_tres_rios` |
| CT-31 | Recomendação só traz abrigo apto | Integração | `GET /abrigos/recomendacao?bairro=navegantes&pessoas=4` | Recomendados com vaga agora e na chegada, fora de área de risco com alerta (atual ou previsto), ordenados por distância; evitados com motivo; bairro inexistente → 404 | ✅ | `test_it17_recomendacao_so_traz_abrigos_aptos_e_explica_os_evitados` |
| CT-32 | Treino e uso calculam as features igual | Integração | Calcular as features em Python a partir de `silver.leitura` e comparar com `gold.v_ml_features` | Mesmas horas e mesmos valores (diferença < 1e-9) | ✅ (2.163 linhas, 0 diferenças) | `test_it18_features_do_python_iguais_as_da_visao_sql` |
| CT-33 | Usuário da IA só lê o gold | Integração | `ia_ro` consulta `gold.v_ml_features_atual` e `silver.leitura` | Gold funciona (3 linhas); silver dá erro de permissão | ✅ | `test_it19_usuario_da_ia_so_le_a_camada_gold` |
| CT-34 | Mensagem em linguagem simples | Integração + unidade | `POST /mensagens/gerar`; todas as combinações de situação × abrigo × bairro | SMS ≤ 160 sem acento e com 199; verificação sem problemas em todos os canais | ✅ | `test_it20_...`, `test_mensagens_alerta.py` |
| CT-35 | IA melhor que a regra simples | Manual (relatório) | `docker compose --profile ferramentas run --rm ia-relatorio` | Erro menor que a persistência no Guaíba e no Gravataí, alerta antes da cota | ✅ Guaíba −71% (alerta 4–5 h antes), Gravataí −61% (6 h antes); Dilúvio fica com a regra simples | `relatorio/RELATORIO.md` |
| CT-36 | Treino reproduzível e sem vazamento | Unidade | Treinar 2 vezes; semente 42 no treino | Mesmas previsões; semente do pipeline recusada; validação por semente (GroupKFold) | ✅ | `test_treino.py` |
| CT-37 | Abrigo seguro: antes × depois | Unidade + manual (relatório) | Cenários com abrigo que vai lotar e que vai alagar; 200 pessoas × horas de crise do histórico | Só a IA evita os dois; no histórico, falha cai de 15,9% (mais próximo) para 0,1% (regra da fase 1: 0,5%) | ✅ | `test_cenarios_abrigos.py`, `RELATORIO.md` |
| CT-38 | Vigia usa a regra de alerta da fase 1 | Unidade | 2.000 níveis aleatórios na regra do vigia e na `proximo_alerta` da fase 1 | Mesmas ações e severidades; abre, escala, mantém e fecha pela previsão | ✅ | `test_vigia.py` |
| CT-39 | Alerta antecipado automático | Manual | `docker compose logs -f api` durante a cheia simulada; comparar com o horário em que o nível passou da cota em `silver.leitura` | `[vigia] ... ANTECIPADO` antes de o rio passar da cota | ✅ Guaíba: atenção 45 s antes (≈ 7,5 h simuladas, conta como 6 h, o horizonte), alerta 30 s antes (≈ 5 h); Gravataí: atenção 26 s antes (≈ 4,3 h) | — (log da API) |
| CT-40 | API valida a entrada | Unidade | Estação ou bairro inexistente, `pessoas=0`, severidade 5 | 404 ou 422 com mensagem clara | ✅ | `test_api.py` |
| CT-41 | Privacidade: localização não vai ao servidor | Unidade | `GET /abrigos` sem posição; recomendação pelo bairro | Lista sem distância, com `minutos_ate_lotar` para o app decidir no celular; recomendação usa o centro do bairro | ✅ | `test_api.py` |
| CT-42 | Banco fora do ar | Unidade | Banco recusa a conexão; banco cai no meio da consulta | 503 com mensagem clara em qualquer rota (não 500) | ✅ | `test_api.py::test_banco_*` |
| CT-43 | Dado velho e abrigo inativo | Unidade | Previsão com leitura velha; abrigo inativo; estação sem leitura com alerta aberto | Previsão velha não decide abrigo; inativo é recusado; vigia encerra o alerta (`sem_dados`) | ✅ | `test_api.py`, `test_vigia.py` |
| CT-44 | Antecedência honesta | Unidade | Previsão avisando 30 h antes da cheia | Conta no máximo o horizonte (6 h) | ✅ | `test_avaliacao.py` |
| CT-45 | Relatório com histórico curto | Unidade | Gerar o relatório sem histórico | Gera `RELATORIO.md` e `demo.md` explicando a falta de dados, sem erro | ✅ | `test_relatorio.py` |
| CT-50 | Previsão com feature faltando | Unidade | Variação da última hora ausente (menos de 2 h de leituras) | Previsão repete o nível de agora (regra simples), marcada `dados_incompletos`; não decide abrigo nem alerta antecipado | ✅ | `test_api.py::test_feature_faltando_repete_o_nivel_e_nao_decide_nada` |
| CT-51 | Conexões reaproveitadas | Unidade | Pegar e devolver conexões; banco reinicia; conexão cai; excesso de conexões | Reaproveita a conexão viva, descarta a que caiu, guarda no máximo 5; banco fora do ar continua dando 503 na hora | ✅ | `test_api.py::test_conexoes_sao_reaproveitadas_e_descartadas_quando_caem` |
| CT-52 | Features ao vivo iguais às do treino | Unidade + Integração | Mesmas leituras pela regra do treino (hora cheia) e pela regra ao vivo; depois, Python × visão `gold.v_ml_features_atual` num retrato do banco | Valores iguais nos dois casos | ✅ | `test_features.py::test_features_ao_vivo_*`, `test_it21_features_ao_vivo_do_python_iguais_as_da_visao_sql` |
| CT-53 | Abrigo desativado no cadastro | Integração | Desativar um abrigo em `silver.abrigo` e chamar `GET /abrigos` | `apto` falso e motivo "abrigo inativo" (lido de `gold.dim_abrigo`, migração 009) | ✅ | `test_it22_abrigo_desativado_nao_e_recomendado_pela_ia` |

### Circuito ESP32 no Wokwi (área 3)

Execução manual em 07/11/2026 no [Wokwi](https://wokwi.com), com a ponte local ligada (`docker compose --profile wokwi up -d ponte-wokwi`). Print: [`docs/evidencias/wokwi-simulacao.jpg`](../docs/evidencias/wokwi-simulacao.jpg).

| ID | Requisito | Tipo | Passos | Resultado esperado | Obtido | Teste automatizado |
|---|---|---|---|---|---|---|
| CT-46 | ESP32 publica e a ponte repassa | Manual | Rodar `sketch.ino` + `diagram.json` no Wokwi por alguns minutos | Leituras de `wok-nivel`, `wok-chuva` e `wok-ocup` aceitas no bronze e gravadas no silver | ✅ 150 aceitas, 0 rejeitadas | — (a ponte tem testes em `test_ponte_wokwi.py`) |
| CT-47 | Alerta local e no pipeline | Manual | Distância do HC-SR04: 300 → 270 → 220 → 360 cm | LED acende a partir de 1,20 m; alerta da `demo-wokwi` abre, escala para inundação e fecha quando o nível cai | ✅ 0,97 → 1,28 → 1,78 → 0,37 m; alerta aberto e fechado | — |
| CT-48 | Chuva pelo potenciômetro | Manual | Girar o potenciômetro | Valor em mm aparece em `wok-chuva` | ✅ 7,63 mm | — |
| CT-49 | Contagem de pessoas no abrigo | Manual | 2 entradas no PIR e 1 toque rápido no botão de saída | `abr-demo` com 1 pessoa em `gold.v_abrigo_status` | ✅ depois da correção (antes, o toque rápido se perdia) | — |

### Fase 3 — App do cidadão (área 3)

Execução em 09/11/2026 com o simulador (`docker compose restart simulador`), o app aberto no Chrome em 390 × 844 e o bairro Navegantes. Prints em [`docs/evidencias/`](../docs/evidencias).

| ID | Requisito | Tipo | Passos | Resultado esperado | Obtido | Teste automatizado |
|---|---|---|---|---|---|---|
| CT-54 | App sobe no Compose e fala com a API pelo proxy | Integração | `docker compose up -d --build --wait`; pedir `/`, `/abrigo/abr-10`, `/api/saude` e `/api/abrigos/recomendacao` no app | HTML do Abriga (`lang="pt-BR"`); rota do app cai no index; API responde pelo proxy com `no-store`; cabeçalhos CSP, `nosniff`, `no-referrer` e `frame-ancestors 'none'` | ✅ | `test_it23_app_web_no_ar_e_api_pelo_proxy` |
| CT-55 | Distância e tempo a pé iguais aos da IA | Unidade | Rodar `recomendar()` do Python em 3 pontos (Navegantes 4 pessoas, Centro Histórico 1, Cristal 6) e 2 abrigos de teste; comparar com o cálculo do app | Mesmos recomendados, evitados, minutos a pé, vagas na chegada e motivos | ✅ | `paridade-geo.test.ts` |
| CT-56 | Abrigo que lota antes de a pessoa chegar sai da lista | Unidade | Abrigo apto com `minutos_ate_lotar` menor que o tempo a pé | Vai para os evitados com "deve lotar antes de você chegar"; `minutos_ate_lotar` nulo não lota | ✅ | `logica-abrigos.test.ts`, `telas-abrigos.test.tsx` |
| CT-57 | Posição não sai do aparelho | Unidade + manual | Modo "Minha localização": registrar todas as URLs pedidas; abrir o detalhe; tocar em "Como chegar" | Só `GET /abrigos?pessoas=`; nenhuma URL nem rota da tela com latitude ou longitude; mapa só com o destino | ✅ Ao vivo, com o GPS simulado, o app pediu só `/api/abrigos?pessoas=1` | `telas-abrigos.test.tsx`, `telas-localizacao-ajustes.test.tsx`, `cliente.test.ts` |
| CT-58 | Sem permissão, GPS falhando ou fora de Porto Alegre → usa o bairro | Unidade | Permissão negada; erro do GPS; posição a mais de 30 km do centro; detalhe do abrigo aberto depois de recarregar (sem a posição) | Mensagem simples e volta para "Meu bairro", sem travar; sem a posição, o detalhe não promete vaga em abrigo que está enchendo | ✅ | `telas-localizacao-ajustes.test.tsx` |
| CT-59 | API ou banco fora do ar → aviso amigável, sem tela branca | Unidade + manual | 503, 502, sem rede e tempo esgotado; `docker compose stop api` com o app aberto, depois `start` | Mensagem simples; últimos dados com a hora; "Tentar de novo" quando não há dado; o app volta sozinho | ✅ | `cliente.test.ts`, `EstadoDaConsulta.test.tsx`, `telas-agora-rio.test.tsx`; print `app-erro.png` |
| CT-60 | Leitura atrasada e dados incompletos sinalizados | Unidade | Previsão com `leitura_velha` e `dados_incompletos` | Selos "Leitura atrasada" e "Dados incompletos" no cartão do rio | ✅ | `telas-agora-rio.test.tsx` |
| CT-61 | Alerta novo avisa uma vez só | Unidade | Mesmo alerta em várias leituras; escalar; fechar e abrir de novo; dois alertas na mesma leitura; alerta já aberto ao abrir o app; avisos desligados; pessoa já na tela de abrigos; toque na notificação | 1 aviso por alerta; escalar avisa de novo; dois juntos: duas notificações e a faixa do mais grave cita o outro rio; o que já estava aberto e os avisos desligados não avisam; na tela de abrigos, só a notificação; o toque leva à tela e fecha a faixa | ✅ | `alertas.test.ts`, `aviso-de-alerta.test.tsx` |
| CT-62 | Alerta antecipado aparece no app antes da cota | Manual | `docker compose restart simulador` com o app aberto; comparar com o nível do Guaíba em `/previsao` | Selo "Alerta antecipado" e aviso antes de o rio passar da cota | ✅ Atenção 50 s antes (≈ 8 h simuladas), alerta 31 s antes (≈ 5 h) | — (prints `app-aviso.png`, `app-agora.png`) |
| CT-63 | Fluxo completo: rio sobe → aviso → abrigo → Como chegar | Manual + unidade | Com a faixa de alerta na tela, tocar em "Onde ficar seguro", no 1º recomendado e em "Como chegar" | Recomendados do bairro salvo, detalhe do abrigo e mapa a pé só com o destino | ✅ | `aviso-de-alerta.test.tsx`, `telas-abrigos.test.tsx`; prints `app-aviso.png`, `app-abrigos.png`, `app-abrigo.png` |
| CT-64 | Funciona em largura de celular | Manual | Abrir as 5 telas em 390 × 844 | Nada cortado e sem rolagem lateral; botões com 48 px ou mais de altura | ✅ | — (prints `app-*.png`) |
| CT-65 | Lint, tipos e testes do app no CI | CI | Push na `main` | Job `app` verde, com o relatório `relatorio-app` | ✅ | job `app` em [`ci.yml`](../.github/workflows/ci.yml) |
| CT-66 | Identidade própria, sem se passar por órgão oficial | Unidade | Textos da faixa e do aviso de alerta; rodapé e Ajustes | Nunca "DEFESA CIVIL" como remetente; "Dados simulados" e os telefones 199 e 193 sempre visíveis | ✅ | `situacao.test.ts`, `telas-agora-rio.test.tsx`, `telas-localizacao-ajustes.test.tsx` |

## Como gerar as evidências para o PDF

Rodar os testes de integração e guardar o relatório em `relatorios/integracao.xml`:

```bash
docker compose --profile ferramentas run --rm --build testes
```

Rodar os testes de unidade e guardar o relatório em `relatorios/unitarios.xml`:

```bash
.venv/bin/python -m pytest --junitxml=relatorios/unitarios.xml
```

Rodar o lint, os tipos e os testes do app e guardar o relatório em `relatorios/app.xml`:

```bash
cd area3-mvp/app && npm run lint && npm run typecheck && npm run test:ci
```

Para o PDF: print do terminal com os testes passando, print da aba **Actions** do GitHub com o pipeline verde, o print do circuito rodando no Wokwi (`docs/evidencias/wokwi-simulacao.jpg`) e os prints do app (`docs/evidencias/app-*.png`).
