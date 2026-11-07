# Demonstração com entrada e saída

Momento real do histórico do pipeline: **28/10 03h** (horário de Brasília), estação **Guaíba - Cais Mauá**. Gerado por `python -m ia.relatorio`.

## 1. Previsão do nível em 6 h

Entrada (features da hora, iguais às de `gold.v_ml_features`):

```json
{
  "nivel_atual_m": 2.47,
  "variacao_1h_m": 0.11,
  "chuva_1h_mm": 13.0,
  "chuva_6h_mm": 84.3,
  "chuva_24h_mm": 152.2
}
```

Saída:

| | Nível em 6 h | Situação prevista |
|---|---|---|
| IA (random forest) | 3,09 m | inundação |
| Regra simples | 2,47 m | atenção |
| **O que aconteceu** | **3,12 m** | **inundação** |

## 2. Onde ficar seguro (família de 4 no bairro Navegantes)

Entrada: `GET /abrigos/recomendacao?bairro=navegantes&pessoas=4` naquele momento.

| Estratégia | Abrigo escolhido | Distância | O que aconteceu |
|---|---|---|---|
| Mais próximo | Colégio Cândido José de Godoi | 1,0 km | alagou nas 6 h seguintes |
| IA | Colégio Dom João Becker | 3,1 km (61 min a pé) | seguro, com vaga |

Abrigos mais perto que a IA evitou, e por quê:

- Colégio Cândido José de Godoi (1,0 km): fica em área de risco e o rio da região está em alerta
- Escola Municipal de Educação Infantil Humaitá (2,1 km): fica em área de risco e o rio da região deve entrar em alerta nas próximas 6 horas

## 3. Mensagem de alerta em linguagem simples

Entrada (fatos montados a partir da previsão e do abrigo recomendado):

```json
{
  "estacao": "Guaíba - Cais Mauá",
  "corpo_hidrico": "Lago Guaíba",
  "nivel_atual_m": 2.47,
  "nivel_previsto_m": 3.09,
  "severidade_atual": 1,
  "severidade_prevista": 3,
  "cota_m": 3.0,
  "bairro": "Navegantes",
  "abrigo": {
    "nome": "Colégio Dom João Becker",
    "minutos_a_pe": 61,
    "vagas": 47
  },
  "erro_modelo_m": 0.022,
  "erro_regra_simples_m": 0.075
}
```

Saída:

```json
{
  "intencao": "saia_agora",
  "sms": "DEFESA CIVIL: Saia agora para um lugar alto. O Lago Guaiba deve alagar ruas em ate 6 h. Va para Colegio Dom Joao Becker (61 min a pe). Emergencia: 199 ou 193.",
  "push_titulo": "Saia agora: risco de alagamento",
  "push_corpo": "Saia agora para um lugar alto. O Lago Guaíba deve alagar ruas em até 6 h. Vá para Colégio Dom João Becker (61 min a pé). Emergência: 199 ou 193. Não atravesse ruas alagadas.",
  "whatsapp": "*Defesa Civil de Porto Alegre*\n\n*Saia agora para um lugar alto.*\nO Lago Guaíba deve alagar ruas no bairro Navegantes nas próximas 6 horas.\n\nVá para Colégio Dom João Becker. Fica a 61 min a pé e tem 47 vagas.\nNão atravesse ruas alagadas.\nEmergência: 199 (Defesa Civil) ou 193 (Bombeiros).",
  "defesa_civil": "[ALERTA ANTECIPADO] Guaíba - Cais Mauá: 2,47 m agora (atenção). Previsão para 6 h: 3,09 m (inundação; cota 3,00 m), variação +0,62 m. Erro médio da IA no teste: 0,022 m (regra simples: 0,075 m). Evitar abrigos em área de risco ligados a esta estação. Abrigo sugerido para Navegantes: Colégio Dom João Becker.",
  "verificacao": {
    "sms": [],
    "push_titulo": [],
    "push_corpo": [],
    "whatsapp": [],
    "defesa_civil": []
  }
}
```

## 4. A mesma coisa ao vivo, na API

Com o ambiente no ar (`docker compose up -d --build --wait`), abra http://localhost:8000/docs ou rode:

```bash
curl -s localhost:8000/previsao
curl -s 'localhost:8000/abrigos/recomendacao?bairro=navegantes&pessoas=4'
curl -s 'localhost:8000/alertas?bairro=navegantes'
curl -s -X POST localhost:8000/mensagens/gerar -H 'Content-Type: application/json' -d @area1-ia/prompts/exemplo_entrada.json
```
