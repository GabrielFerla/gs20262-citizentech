/**
 * Paridade com a IA: "abrigos perto de mim" calculado no aparelho (src/logica/geo.ts) tem de dar
 * o mesmo que recomendar() de area1-ia/ia/abrigos.py. O resultado do Python fica em
 * __fixtures__/paridade-geo.json (gerado por scripts/paridade_geo.py).
 */
import type { AbrigoAvaliado } from '@/api/tipos';
import {
  abrigosPerto,
  arredondarComoPython,
  dentroDePortoAlegre,
  distanciaKm,
  MOTIVOS_INDISPONIVEL,
  minutosAPe,
} from '@/logica/geo';

import paridade from '../__fixtures__/paridade-geo.json';
import { fixtures } from '../test-utils/apiFalsa';

describe('paridade com area1-ia/ia/abrigos.py', () => {
  it.each(paridade.casos.map((c) => [c.nome, c] as const))('%s: mesmos recomendados e evitados', (_nome, caso) => {
    const r = abrigosPerto(caso.abrigos as AbrigoAvaliado[], caso.posicao);

    expect(
      r.recomendados.map((a) => ({
        abrigo_id: a.abrigo_id,
        distancia_km: a.distancia_km,
        minutos_a_pe: a.minutos_a_pe,
        vagas_na_chegada: a.vagas_na_chegada,
      })),
    ).toEqual(caso.recomendados);

    expect(
      r.evitados.map((a) => ({
        abrigo_id: a.abrigo_id,
        distancia_km: a.distancia_km,
        minutos_a_pe: a.minutos_a_pe,
        motivo: a.motivo_final,
      })),
    ).toEqual(caso.evitados);
  });

  it('o caso de Navegantes exercita todos os motivos: área de risco, lotado e lota antes de chegar', () => {
    const navegantes = paridade.casos[0];
    expect(navegantes.evitados.map((e) => e.motivo)).toEqual(
      expect.arrayContaining(['deve lotar antes de você chegar', 'lotado', expect.stringMatching(/área de risco/)]),
    );
  });

  it('a mesma lista de motivos de abrigo fora de uso que a IA (ia/servicos.py)', () => {
    expect(MOTIVOS_INDISPONIVEL).toEqual([
      'abrigo inativo',
      'abrigo de demonstração',
      'sem leitura recente de ocupação',
    ]);
  });
});

describe('contas do aparelho', () => {
  it('haversine: Paço Municipal → Arena do Grêmio (≈ 6,8 km em linha reta, igual ao Python)', () => {
    expect(distanciaKm(-30.0277, -51.2287, -29.9739, -51.1949)).toBeCloseTo(6.81, 1);
  });

  it('caminhada: linha reta × 1,3 a 4 km/h, no mínimo 1 min', () => {
    expect(minutosAPe(1)).toBe(20); // 1 × 1,3 / 4 × 60 = 19,5 → 20 (arredonda para o par, como o Python)
    expect(minutosAPe(0)).toBe(1);
    expect(arredondarComoPython(19.5)).toBe(20);
    expect(arredondarComoPython(18.5)).toBe(18);
    expect(arredondarComoPython(18.6)).toBe(19);
    // Só o ",5" exato vai para o par (como no Python): quase ",5" arredonda normalmente.
    expect(arredondarComoPython(13.4999999999)).toBe(13);
    expect(arredondarComoPython(12.5000000001)).toBe(13);
    expect(arredondarComoPython(13.5)).toBe(14);
  });

  it('o abrigo de demonstração (Wokwi) nem entra na conta', () => {
    const r = abrigosPerto(fixtures.abrigos4, { lat: -30.0346, lon: -51.2177 }); // em cima do abr-demo
    const ids = [...r.recomendados, ...r.evitados].map((a) => a.abrigo_id);
    expect(ids).not.toContain('abr-demo');
  });

  it('sem nenhum abrigo seguro, não há "evitados mais perto que o 1º": mostra todos os não seguros', () => {
    const inseguros = fixtures.abrigos4.map((a) => ({ ...a, apto: false, motivo: a.motivo ?? 'lotado' }));
    const r = abrigosPerto(inseguros, { lat: -29.99363, lon: -51.20077 });
    expect(r.recomendados).toHaveLength(0);
    expect(r.evitados.length).toBeGreaterThan(0);
  });

  it('dentro e fora de Porto Alegre', () => {
    expect(dentroDePortoAlegre({ lat: -29.99363, lon: -51.20077 })).toBe(true); // Navegantes
    expect(dentroDePortoAlegre({ lat: -30.2394, lon: -51.0974 })).toBe(true); // Lami, no extremo sul
    expect(dentroDePortoAlegre({ lat: -23.5505, lon: -46.6333 })).toBe(false); // São Paulo
    expect(dentroDePortoAlegre({ lat: -29.6842, lon: -51.1328 })).toBe(false); // Novo Hamburgo
  });
});
