# Fonte do PDF de entregáveis

O [`entregaveis.html`](entregaveis.html) gera o [`Abriga-Entregaveis.pdf`](../Abriga-Entregaveis.pdf),
o PDF com a solução, a arquitetura e as evidências de cada área que o edital pede.

## Antes de gerar

- **Integrantes e link do pitch:** troque os textos em amarelo da capa do `entregaveis.html`.
  Use os mesmos dados do [`integrantes.txt`](../../../integrantes.txt).
- **Prints do Power BI:** salve em `docs/evidencias/` com estes nomes. Eles entram sozinhos no PDF;
  enquanto não existirem, o PDF mostra um quadro amarelo no lugar.
  - `powerbi-1.png`: rios e alertas, com os filtros;
  - `powerbi-2.png`: ocupação e vagas dos abrigos;
  - `powerbi-3.png`: tela das medidas DAX.

## Gerar o PDF

O diagrama da arquitetura é desenhado na hora (Mermaid), então precisa de internet.

**Em qualquer sistema (Chrome):** abra o `entregaveis.html` no Chrome e espere o diagrama aparecer
na seção 4. Depois vá em **Imprimir → Salvar como PDF**. Em **Mais definições**, desligue
**Cabeçalhos e rodapés** e ligue **Gráficos de plano de fundo**. Salve como `docs/pdf/Abriga-Entregaveis.pdf`.

**No macOS, pelo terminal** (na raiz do repositório):

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --no-pdf-header-footer --virtual-time-budget=15000 --print-to-pdf=docs/pdf/Abriga-Entregaveis.pdf docs/pdf/fonte/entregaveis.html
```
