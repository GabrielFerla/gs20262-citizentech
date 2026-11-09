import { km, minutosAPeTexto } from '@/logica/formato';
import { lotaAntesDeChegar, vagasNaChegada } from '@/logica/geo';
import { urlComoChegar } from '@/logica/rota';
import { capitalizar, filtrarBairros, semAcento } from '@/logica/texto';

import { fixtures } from '../test-utils/apiFalsa';

describe('busca de bairro', () => {
  it('ignora acento e maiúscula', () => {
    expect(semAcento('  São JOÃO ')).toBe('sao joao');
  });

  it('acha o bairro digitando sem acento, em ordem alfabética', () => {
    const nomes = filtrarBairros(fixtures.bairros, 'sao').map((b) => b.bairro);
    expect(nomes).toContain('São João');
    expect(nomes).toEqual([...nomes].sort((a, b) => a.localeCompare(b, 'pt-BR')));
    expect(filtrarBairros(fixtures.bairros, 'naveg').map((b) => b.bairro_id)).toEqual(['navegantes']);
  });

  it('busca vazia mostra os 94 bairros', () => {
    expect(filtrarBairros(fixtures.bairros, '')).toHaveLength(94);
  });
});

describe('vagas e lotação', () => {
  const abrigo = { capacidade: 150, ocupacao: 6, chegando_por_hora: 12, minutos_ate_lotar: 690 };

  it('desconta quem está chegando durante a caminhada (como a IA)', () => {
    expect(vagasNaChegada(abrigo, 0)).toBe(144);
    expect(vagasNaChegada(abrigo, 30)).toBe(138); // 144 − 12 × 0,5
    expect(vagasNaChegada({ ...abrigo, chegando_por_hora: -3 }, 60)).toBe(144); // saindo gente não abre vaga
    expect(vagasNaChegada({ ...abrigo, chegando_por_hora: 500 }, 60)).toBe(0); // nunca negativo
  });

  it('lota antes de chegar quando a caminhada é maior que o tempo até lotar', () => {
    expect(lotaAntesDeChegar(abrigo, 690)).toBe(false);
    expect(lotaAntesDeChegar(abrigo, 691)).toBe(true);
    expect(lotaAntesDeChegar({ minutos_ate_lotar: null }, 9999)).toBe(false); // não está enchendo
  });
});

describe('"Como chegar" (LGPD)', () => {
  it('manda só o destino ao mapa, a pé, nunca a posição da pessoa', () => {
    const url = urlComoChegar(-30.02832, -51.18409);
    expect(url).toBe('https://www.google.com/maps/dir/?api=1&destination=-30.02832%2C-51.18409&travelmode=walking');
    expect(url).not.toMatch(/origin|saddr/);
  });
});

describe('formatos', () => {
  it('tempo a pé e distância em português', () => {
    expect(minutosAPeTexto(45)).toBe('45 min a pé');
    expect(minutosAPeTexto(81)).toBe('1 h 21 min a pé');
    expect(minutosAPeTexto(120)).toBe('2 h a pé');
    expect(km(4.18)).toBe('4,2 km');
    expect(km(0.85)).toBe('850 m');
  });

  it('motivo da API com a primeira letra maiúscula', () => {
    expect(capitalizar('lotado')).toBe('Lotado');
    expect(capitalizar('')).toBe('');
  });
});
