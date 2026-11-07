# Exemplos de entrada e saída do gerador de mensagens

Gerados por `python -m ia.mensagens` (rode de novo para conferir: a saída é sempre a mesma).
São os exemplos "few-shot" do [prompt de sistema](sistema.md): mostram o formato esperado para cada intenção.

## Guaíba vai passar da cota de inundação (aviso antecipado, com abrigo)

Entrada:
```json
{
  "estacao": "Guaíba - Cais Mauá",
  "corpo_hidrico": "Lago Guaíba",
  "nivel_atual_m": 2.62,
  "nivel_previsto_m": 3.08,
  "severidade_atual": 2,
  "severidade_prevista": 3,
  "cota_m": 3.0,
  "bairro": "Navegantes",
  "abrigo": {
    "nome": "Colégio Dom João Becker",
    "minutos_a_pe": 34,
    "vagas": 96
  },
  "erro_modelo_m": 0.022,
  "erro_regra_simples_m": 0.075
}
```

Saída:
```json
{
  "intencao": "saia_agora",
  "sms": "DEFESA CIVIL: Saia agora para um lugar alto. O Lago Guaiba deve alagar ruas em ate 6 h. Va para Colegio Dom Joao Becker (34 min a pe). Emergencia: 199 ou 193.",
  "push_titulo": "Saia agora: risco de alagamento",
  "push_corpo": "Saia agora para um lugar alto. O Lago Guaíba deve alagar ruas em até 6 h. Vá para Colégio Dom João Becker (34 min a pé). Emergência: 199 ou 193. Não atravesse ruas alagadas.",
  "whatsapp": "*Defesa Civil de Porto Alegre*\n\n*Saia agora para um lugar alto.*\nO Lago Guaíba deve alagar ruas no bairro Navegantes nas próximas 6 horas.\n\nVá para Colégio Dom João Becker. Fica a 34 min a pé e tem 96 vagas.\nNão atravesse ruas alagadas.\nEmergência: 199 (Defesa Civil) ou 193 (Bombeiros).",
  "defesa_civil": "[ALERTA ANTECIPADO] Guaíba - Cais Mauá: 2,62 m agora (alerta). Previsão para 6 h: 3,08 m (inundação; cota 3,00 m), variação +0,46 m. Erro médio da IA no teste: 0,022 m (regra simples: 0,075 m). Evitar abrigos em área de risco ligados a esta estação. Abrigo sugerido para Navegantes: Colégio Dom João Becker.",
  "verificacao": {
    "sms": [],
    "push_titulo": [],
    "push_corpo": [],
    "whatsapp": [],
    "defesa_civil": []
  }
}
```

## Gravataí deve entrar em alerta (aviso antecipado, sem bairro)

Entrada:
```json
{
  "estacao": "Rio Gravataí - Sarandi",
  "corpo_hidrico": "Rio Gravataí",
  "nivel_atual_m": 3.21,
  "nivel_previsto_m": 3.55,
  "severidade_atual": 1,
  "severidade_prevista": 2,
  "cota_m": 3.5,
  "bairro": null,
  "abrigo": null,
  "erro_modelo_m": null,
  "erro_regra_simples_m": null
}
```

Saída:
```json
{
  "intencao": "prepare_se",
  "sms": "DEFESA CIVIL: Prepare-se para sair de casa. O Rio Gravatai deve subir muito em ate 6 h. Procure o abrigo mais perto no app. Emergencia: 199 ou 193.",
  "push_titulo": "Prepare-se: o rio vai subir",
  "push_corpo": "Prepare-se para sair de casa. O Rio Gravataí deve subir muito em até 6 h. Procure o abrigo mais perto no app. Emergência: 199 ou 193. Separe documentos, remédios e água.",
  "whatsapp": "*Defesa Civil de Porto Alegre*\n\n*Prepare-se para sair de casa.*\nO Rio Gravataí deve subir muito nas próximas 6 horas.\n\nProcure o abrigo mais perto no app.\nSepare documentos, remédios e água.\nEmergência: 199 (Defesa Civil) ou 193 (Bombeiros).",
  "defesa_civil": "[ALERTA ANTECIPADO] Rio Gravataí - Sarandi: 3,21 m agora (atenção). Previsão para 6 h: 3,55 m (alerta; cota 3,50 m), variação +0,34 m. Evitar abrigos em área de risco ligados a esta estação.",
  "verificacao": {
    "sms": [],
    "push_titulo": [],
    "push_corpo": [],
    "whatsapp": [],
    "defesa_civil": []
  }
}
```

## Dilúvio acima do normal (atenção)

Entrada:
```json
{
  "estacao": "Arroio Dilúvio - Av. Ipiranga",
  "corpo_hidrico": "Arroio Dilúvio",
  "nivel_atual_m": 1.92,
  "nivel_previsto_m": 1.95,
  "severidade_atual": 1,
  "severidade_prevista": 1,
  "cota_m": 1.8,
  "bairro": null,
  "abrigo": null,
  "erro_modelo_m": null,
  "erro_regra_simples_m": null
}
```

Saída:
```json
{
  "intencao": "fique_atento",
  "sms": "DEFESA CIVIL: Fique atento. O Arroio Diluvio esta acima do normal. Evite as margens e acompanhe os avisos.",
  "push_titulo": "Atenção: rio acima do normal",
  "push_corpo": "Fique atento. O Arroio Dilúvio está acima do normal. Evite as margens e acompanhe os avisos.",
  "whatsapp": "*Defesa Civil de Porto Alegre*\n\n*Fique atento.*\nO Arroio Dilúvio está acima do normal.\n\nEvite as margens e acompanhe os avisos.",
  "defesa_civil": "[ALERTA EM CURSO] Arroio Dilúvio - Av. Ipiranga: 1,92 m agora (atenção). Previsão para 6 h: 1,95 m (atenção; cota 1,80 m), variação +0,03 m.",
  "verificacao": {
    "sms": [],
    "push_titulo": [],
    "push_corpo": [],
    "whatsapp": [],
    "defesa_civil": []
  }
}
```

## Guaíba baixando depois da cheia

Entrada:
```json
{
  "estacao": "Guaíba - Cais Mauá",
  "corpo_hidrico": "Lago Guaíba",
  "nivel_atual_m": 3.05,
  "nivel_previsto_m": 2.88,
  "severidade_atual": 3,
  "severidade_prevista": 2,
  "cota_m": 3.0,
  "bairro": "Centro Histórico",
  "abrigo": null,
  "erro_modelo_m": null,
  "erro_regra_simples_m": null
}
```

Saída:
```json
{
  "intencao": "nao_volte",
  "sms": "DEFESA CIVIL: Nao volte para casa ainda. O Lago Guaiba comecou a baixar, mas as ruas ainda sao perigosas. Emergencia: 199 ou 193.",
  "push_titulo": "Rio baixando: ainda não volte",
  "push_corpo": "Não volte para casa ainda. O Lago Guaíba começou a baixar, mas as ruas ainda são perigosas. Emergência: 199 ou 193. Espere a Defesa Civil liberar a volta.",
  "whatsapp": "*Defesa Civil de Porto Alegre*\n\n*Não volte para casa ainda.*\nO Lago Guaíba começou a baixar, mas as ruas no bairro Centro Histórico ainda são perigosas.\n\nEspere a Defesa Civil liberar a volta.\nEmergência: 199 (Defesa Civil) ou 193 (Bombeiros).",
  "defesa_civil": "[RIO BAIXANDO] Guaíba - Cais Mauá: 3,05 m agora (inundação). Previsão para 6 h: 2,88 m (alerta; cota 3,00 m), variação −0,17 m.",
  "verificacao": {
    "sms": [],
    "push_titulo": [],
    "push_corpo": [],
    "whatsapp": [],
    "defesa_civil": []
  }
}
```

