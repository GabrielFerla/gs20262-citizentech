/**
 * Contas do gráfico do rio (tela Rio): faixa do eixo, posição dos pontos e marcas.
 * Funções puras, testadas em __tests__/grafico.test.ts.
 */
import type { Cotas } from '@/api/tipos';

export interface Faixa {
  min: number;
  max: number;
}

const FOLGA_M = 0.3;
const PASSO_M = 0.5;

/**
 * Faixa do eixo vertical: inclui todas as leituras, a previsão e as três cotas (as faixas de
 * cor sempre aparecem), com uma folga, arredondada de 0,5 em 0,5 m e nunca abaixo de 0.
 */
export function faixaDoGrafico(valores: number[], cotas: Cotas): Faixa {
  const todos = [...valores.filter(Number.isFinite), cotas.atencao_m, cotas.inundacao_m];
  const menor = Math.min(...todos) - FOLGA_M;
  const maior = Math.max(...todos) + FOLGA_M;
  return {
    min: Math.max(0, Math.floor(menor / PASSO_M) * PASSO_M),
    max: Math.ceil(maior / PASSO_M) * PASSO_M,
  };
}

/** Converte metros em pixels (o 0 do SVG fica em cima). */
export function paraY(valor: number, faixa: Faixa, topo: number, altura: number): number {
  const fracao = (valor - faixa.min) / (faixa.max - faixa.min || 1);
  return topo + altura * (1 - Math.min(Math.max(fracao, 0), 1));
}

/** Marcas do eixo vertical, de 0,5 em 0,5 m (ou de 1 em 1 m quando a faixa é grande). */
export function marcasDoEixo(faixa: Faixa): number[] {
  const passo = faixa.max - faixa.min > 4 ? 1 : PASSO_M;
  const marcas: number[] = [];
  for (let v = Math.ceil(faixa.min / passo) * passo; v <= faixa.max + 1e-9; v += passo) {
    marcas.push(Math.round(v * 100) / 100);
  }
  return marcas;
}

/**
 * Posição horizontal das leituras: ocupam a parte da esquerda, igualmente espaçadas;
 * a previsão de 6 h fica sozinha na ponta direita.
 */
export function posicoesX(quantidade: number, esquerda: number, larguraDasLeituras: number): number[] {
  if (quantidade <= 0) return [];
  if (quantidade === 1) return [esquerda + larguraDasLeituras];
  const passo = larguraDasLeituras / (quantidade - 1);
  return Array.from({ length: quantidade }, (_, i) => esquerda + i * passo);
}
