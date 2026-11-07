# Dashboard Power BI

O Power BI Desktop só roda no Windows. Quem montar o dashboard não precisa rodar o projeto:
a pasta [`amostra/`](amostra) tem os CSVs prontos (30 dias, semente 42).
Para dados novos, rode `docker compose --profile ferramentas run --rm exportar`. Os arquivos saem em `dados/`.

## 1. Importar os CSVs

Os arquivos usam **vírgula como separador e ponto como decimal**. Um Power BI em português
lê "2.87" como 287. Para evitar isso:

1. **Obter dados → Pasta** e escolha `amostra/` (ou `dados/`). Depois **Combinar e transformar** um a um, ou importe cada CSV separado.
2. No Power Query, selecione a consulta e vá em **Página Inicial → Usar primeira linha como cabeçalho**.
3. Em cada coluna numérica ou de data, clique com o botão direito: **Alterar tipo → Usando localidade… → Inglês (Estados Unidos)**.
   Use **Decimal** para `*_m`, `*_mm` e `pct_*`, e **Data/Hora** para `hora_local` e `*_local`.

Use sempre as colunas **`*_local`** (horário de Brasília) nos eixos de tempo.

## 2. Relacionamentos (modelo estrela)

| De (1) | Para (*) | Coluna |
|---|---|---|
| `dim_bairro` | `dim_estacao` | `bairro_id` |
| `dim_bairro` | `dim_abrigo` | `bairro_id` |
| `dim_estacao` | `v_estacao_horaria` | `estacao_id` |
| `dim_estacao` | `v_alertas` | `estacao_id` |
| `dim_abrigo` | `v_abrigo_horaria` | `abrigo_id` |
| `dim_abrigo` | `v_abrigo_status` | `abrigo_id` |

Não ligue o `bairro_id` das tabelas de fatos (`v_estacao_horaria`, `v_abrigo_horaria`)
direto ao `dim_bairro`. Isso cria dois caminhos de filtro e o Power BI reclama.

## 3. Indicadores sugeridos (o edital pede 3 ou mais, com filtros)

| # | Indicador | Visual | Decisão que ele apoia |
|---|---|---|---|
| 1 | **Nível do rio contra as cotas** ao longo do tempo | Linha: `hora_local` × `nivel_max_m`, com linhas constantes nas cotas de atenção, alerta e inundação | Quando emitir alerta e evacuar cada região |
| 2 | **Ocupação e vagas dos abrigos** | Barras por abrigo (`pct_lotacao_max`) e mapa com `lat`/`lon` de `dim_abrigo` | Para onde encaminhar as pessoas; quando abrir abrigos novos |
| 3 | **Chuva acumulada × nível** | Gráfico combinado: colunas de `chuva_mm` e linha de `nivel_medio_m` | Mostra o atraso entre a chuva e a cheia (base para a IA de previsão) |
| 4 | **Alertas** por estação e severidade, com duração | Tabela e cartões | Quantas horas cada região passou em risco |
| 5 | **Qualidade dos dados** | Rosca: `v_qualidade` por `status` e `motivo` | Confiança nos sensores |

**Filtros (segmentações):** estação, bairro, período (`hora_local`), tipo de abrigo, abrigo em área de risco (`em_area_de_risco`) e severidade do alerta.

## Medidas DAX

Crie uma tabela de medidas e cole uma por vez:

```DAX
Nível Máx (m) = MAX ( v_estacao_horaria[nivel_max_m] )

Chuva Total (mm) = SUM ( v_estacao_horaria[chuva_mm] )

Horas em Alerta =
CALCULATE (
    COUNTROWS ( v_estacao_horaria ),
    v_estacao_horaria[situacao] IN { "alerta", "inundacao" }
)

% Tempo em Alerta = DIVIDE ( [Horas em Alerta], COUNTROWS ( v_estacao_horaria ) )

Folga até a Cota de Inundação (m) =
MAX ( dim_estacao[cota_inundacao_m] ) - [Nível Máx (m)]

Lotação Máx (%) = MAX ( v_abrigo_horaria[pct_lotacao_max] )

Pessoas Abrigadas (pico) =
MAXX (
    VALUES ( v_abrigo_horaria[hora_local] ),
    CALCULATE ( SUM ( v_abrigo_horaria[ocupacao_max] ) )
)

Vagas Recomendáveis Agora =
CALCULATE ( SUM ( v_abrigo_status[vagas] ), v_abrigo_status[recomendavel] = "true" )

Qtde Alertas = COUNTROWS ( v_alertas )

Duração Média do Alerta (h) = AVERAGE ( v_alertas[duracao_h] )

Taxa de Rejeição (%) =
DIVIDE (
    CALCULATE ( SUM ( v_qualidade[mensagens] ), v_qualidade[status] = "rejeitada" ),
    SUM ( v_qualidade[mensagens] )
)
```

Se o Power Query tiver convertido `recomendavel` para verdadeiro/falso, troque `"true"` por `TRUE()`.

Evidências para o PDF: prints do dashboard com os filtros aplicados e da tela de medidas.
