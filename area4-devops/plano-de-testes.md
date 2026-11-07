# Plano de testes — fase 1

**Objetivo:** garantir que as leituras dos sensores chegam ao banco validadas, sem duplicar,
que dados inválidos ou de origem não autorizada são barrados, e que os alertas e as vagas
dos abrigos são calculados corretamente.

| Tipo | Ferramenta | Como rodar | Quantidade |
|---|---|---|---|
| Unidade | pytest | `.venv/bin/python -m pytest` | 90 testes |
| Integração | pytest no docker compose (broker, banco e serviços reais) | `docker compose --profile ferramentas run --rm --build testes` | 13 testes |
| Lint | ruff | `.venv/bin/ruff check .` | — |
| CI | GitHub Actions ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)) | automático a cada push e pull request | os três acima |

**Evidências:**
- relatórios JUnit em `relatorios/` (gerados localmente e anexados pelo CI);
- print do GitHub Actions verde;
- prints dos comandos abaixo.

## Casos de teste

Execução em 07/11/2026 (macOS, Docker 29): **unidade 90/90 ok · integração 13/13 ok**.

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

## Como gerar as evidências para o PDF

Rodar os testes de integração e guardar o relatório em `relatorios/integracao.xml`:

```bash
docker compose --profile ferramentas run --rm --build testes
```

Rodar os testes de unidade e guardar o relatório em `relatorios/unitarios.xml`:

```bash
.venv/bin/python -m pytest --junitxml=relatorios/unitarios.xml
```

Para o PDF: print do terminal com os testes passando e print da aba **Actions** do GitHub com o pipeline verde.
