/**
 * Contas de distância e de vaga feitas NO APARELHO, com as mesmas regras da IA
 * (area1-ia/ia/abrigos.py). Assim a posição exata da pessoa nunca precisa ir ao servidor (LGPD).
 */
import type { AbrigoAvaliado } from '@/api/tipos';

export const RAIO_TERRA_KM = 6371.0088;
/** As ruas não são linha reta: a distância em linha reta vezes 1,3. */
export const FATOR_ROTA = 1.3;
export const VELOCIDADE_KMH = 4.0;

const radianos = (graus: number) => (graus * Math.PI) / 180;

/** Distância em linha reta (fórmula de haversine), em km. */
export function distanciaKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const p1 = radianos(lat1);
  const p2 = radianos(lat2);
  const dp = p2 - p1;
  const dl = radianos(lon2 - lon1);
  const a = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return 2 * RAIO_TERRA_KM * Math.asin(Math.sqrt(a));
}

/**
 * Minutos a pé: max(1, round(d × 1,3 / 4 × 60)).
 * O round do Python arredonda o ",5" para o par (banker's rounding); fazemos igual.
 */
export function minutosAPe(distanciaRetaKm: number): number {
  return Math.max(1, arredondarComoPython((distanciaRetaKm * FATOR_ROTA * 60) / VELOCIDADE_KMH));
}

export function arredondarComoPython(x: number): number {
  const piso = Math.floor(x);
  const resto = x - piso;
  if (Math.abs(resto - 0.5) < 1e-9) return piso % 2 === 0 ? piso : piso + 1;
  return Math.round(x);
}

/** Vagas quando a pessoa chegar: capacidade − ocupação − (chegando por hora × horas de caminhada). */
export function vagasNaChegada(
  abrigo: Pick<AbrigoAvaliado, 'capacidade' | 'ocupacao' | 'chegando_por_hora'>,
  minutos: number,
): number {
  const entrando = Math.max(abrigo.chegando_por_hora, 0) * (minutos / 60);
  return Math.max(Math.floor(abrigo.capacidade - abrigo.ocupacao - entrando), 0);
}

/** O abrigo deixa de ter vaga para o grupo antes de a pessoa chegar? (nulo = não está enchendo) */
export function lotaAntesDeChegar(abrigo: Pick<AbrigoAvaliado, 'minutos_ate_lotar'>, minutos: number): boolean {
  return abrigo.minutos_ate_lotar !== null && minutos > abrigo.minutos_ate_lotar;
}
