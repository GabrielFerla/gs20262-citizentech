# Bases de cadastro (seeds)

| Arquivo | Origem | Conteúdo |
|---|---|---|
| `estacoes.csv` | Escrito à mão pelo grupo | Pontos de medição de nível e chuva, com as cotas de atenção, alerta e inundação |
| `bairros.csv` | Gerado do OpenStreetMap | Os 94 bairros de Porto Alegre, com zona de risco e ponto central |
| `abrigos.csv` | Gerado do OpenStreetMap | 20 escolas e ginásios reais usados como abrigos candidatos, mais 1 abrigo de demonstração e 1 de teste |
| `sensores.csv` | Gerado pelo script | Sensores de nível e chuva de cada estação e o sensor de ocupação de cada abrigo |

Para gerar de novo (precisa de internet):

```bash
python area2-bigdata/db/seeds/gerar_seeds_osm.py
```

## Simplificações (dizer no pitch e no PDF)

- **Capacidade dos abrigos é estimada.** O OpenStreetMap não informa capacidade. Usamos 150 pessoas para escola e 300 para ginásio (coluna `capacidade_estimada = true`).
- **Zona de risco é uma simplificação.** Os bairros com `zona_risco = alta` foram os atingidos pela enchente de maio de 2024. Antes de citar no pitch, confira com o mapa oficial de inundação.
- **Cotas das estações:**
  - Guaíba (Cais Mauá): alerta 2,50 m e inundação 3,00 m são referências públicas. Confira a fonte oficial antes de citar. A cota de atenção (2,00 m) foi definida pelo grupo.
  - Arroio Dilúvio e Rio Gravataí: cotas simuladas pelo grupo.
- A estação `demo-wokwi` e o abrigo `abr-demo` são fictícios. Eles recebem os dados do circuito ESP32 no Wokwi.
- A estação `tst-integracao`, o abrigo `abr-teste` e os sensores `tst-*` também são fictícios e só recebem dados dos
  testes de integração ([`test_integracao.py`](../../../area4-devops/testes/test_integracao.py)). Assim os testes não mexem
  na simulação nem no ESP32. Como as duas estações estão marcadas como demonstração (`demo = true`), ficam fora do
  treino da IA, das recomendações e das telas do app.

## Atribuição

Dados de bairros, escolas e ginásios © colaboradores do OpenStreetMap, licença ODbL — <https://www.openstreetmap.org/copyright>.
