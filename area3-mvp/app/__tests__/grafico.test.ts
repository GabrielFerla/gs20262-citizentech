import { faixaDoGrafico, marcasDoEixo, paraY, posicoesX } from '@/logica/grafico';

const COTAS_GUAIBA = { atencao_m: 2, alerta_m: 2.5, inundacao_m: 3 };

describe('gráfico do rio', () => {
  it('a faixa do eixo inclui as leituras, a previsão e as três cotas', () => {
    const faixa = faixaDoGrafico([2.1, 2.3, 3.4], COTAS_GUAIBA);
    expect(faixa.min).toBeLessThanOrEqual(2);
    expect(faixa.max).toBeGreaterThanOrEqual(3.4);
    // arredondada de 0,5 em 0,5 m
    expect(faixa.min % 0.5).toBe(0);
    expect(faixa.max % 0.5).toBe(0);
  });

  it('com o rio baixo, as cotas continuam aparecendo (o eixo sobe até a inundação)', () => {
    const faixa = faixaDoGrafico([0.4], { atencao_m: 1.8, alerta_m: 2.5, inundacao_m: 3.2 });
    expect(faixa).toEqual({ min: 0, max: 3.5 });
  });

  it('nunca vai abaixo de zero', () => {
    expect(faixaDoGrafico([0.05], COTAS_GUAIBA).min).toBe(0);
  });

  it('ignora valores inválidos', () => {
    expect(faixaDoGrafico([NaN, 2.2], COTAS_GUAIBA)).toEqual(faixaDoGrafico([2.2], COTAS_GUAIBA));
  });

  it('converte metros em pixels: mais alto = mais perto do topo, sem sair da área', () => {
    const faixa = { min: 1, max: 3 };
    expect(paraY(3, faixa, 10, 200)).toBe(10);
    expect(paraY(1, faixa, 10, 200)).toBe(210);
    expect(paraY(2, faixa, 10, 200)).toBe(110);
    expect(paraY(9, faixa, 10, 200)).toBe(10); // fora da faixa: preso na borda
  });

  it('marca o eixo de 0,5 em 0,5 m, ou de 1 em 1 m quando a faixa é grande', () => {
    expect(marcasDoEixo({ min: 1.5, max: 3.5 })).toEqual([1.5, 2, 2.5, 3, 3.5]);
    expect(marcasDoEixo({ min: 0, max: 6 })).toEqual([0, 1, 2, 3, 4, 5, 6]);
  });

  it('espalha as leituras pela parte da esquerda; uma leitura só fica na ponta dessa parte', () => {
    expect(posicoesX(3, 40, 100)).toEqual([40, 90, 140]);
    expect(posicoesX(1, 40, 100)).toEqual([140]);
    expect(posicoesX(0, 40, 100)).toEqual([]);
  });
});
