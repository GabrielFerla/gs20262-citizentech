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

/**
 * round() do Python: só o ",5" EXATO vai para o par; o resto, para o mais perto. (x − piso é exato em
 * ponto flutuante, então a comparação com 0,5 não precisa de tolerância; com tolerância, 13,4999999999
 * viraria 14 aqui e 13 no Python.)
 */
export function arredondarComoPython(x: number): number {
  const piso = Math.floor(x);
  const resto = x - piso;
  if (resto === 0.5) return piso % 2 === 0 ? piso : piso + 1;
  return resto < 0.5 ? piso : piso + 1;
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

export interface Posicao {
  lat: number;
  lon: number;
}

/** Centro de Porto Alegre (Paço Municipal) e o raio em que o modo localização faz sentido. */
export const CENTRO_POA: Posicao = { lat: -30.0277, lon: -51.2287 };
export const RAIO_POA_KM = 30;

export function distanciaDoCentroKm(posicao: Posicao): number {
  return distanciaKm(posicao.lat, posicao.lon, CENTRO_POA.lat, CENTRO_POA.lon);
}

/** Fora de Porto Alegre, os abrigos ficariam a horas de caminhada: o app usa o bairro. */
export function dentroDePortoAlegre(posicao: Posicao): boolean {
  return distanciaDoCentroKm(posicao) <= RAIO_POA_KM;
}

/**
 * Motivos de abrigo fora de uso (os mesmos de area1-ia/ia/servicos.py). Como em recomendar(),
 * esses abrigos nem entram na conta: não são "evitados", simplesmente não existem para a pessoa.
 */
export const MOTIVOS_INDISPONIVEL = ['abrigo inativo', 'abrigo de demonstração', 'sem leitura recente de ocupação'];

/** Abrigo com a conta feita no aparelho. */
export interface AbrigoPerto extends AbrigoAvaliado {
  distancia_km: number;
  minutos_a_pe: number;
  /** Vagas quando a pessoa chegar (conta do aparelho). */
  vagas_na_chegada: number;
  /** Apto agora (API) E não lota antes de a pessoa chegar (aparelho). */
  seguro: boolean;
  /** Por que não é seguro (o da API ou "deve lotar antes de você chegar"). */
  motivo_final: string | null;
}

export interface Resultado {
  recomendados: AbrigoPerto[];
  /** Os não seguros que ficam mais perto que o 1º recomendado. */
  evitados: AbrigoPerto[];
}

/**
 * "Abrigos perto de mim", no aparelho, com a mesma regra de recomendar() (area1-ia/ia/abrigos.py):
 * descarta os indisponíveis, calcula a caminhada, descarta quem lota antes de a pessoa chegar,
 * ordena pela distância e devolve os 3 primeiros seguros e os não seguros mais perto que eles.
 * A posição entra aqui e não sai daqui: nada disso vai para a API.
 */
export function abrigosPerto(abrigos: AbrigoAvaliado[], posicao: Posicao, limite = 3): Resultado {
  const avaliados: AbrigoPerto[] = abrigos
    .filter((a) => !(a.motivo && MOTIVOS_INDISPONIVEL.includes(a.motivo)))
    .map((a) => {
      const distancia = distanciaKm(posicao.lat, posicao.lon, a.lat, a.lon);
      const minutos = minutosAPe(distancia);
      const lota = lotaAntesDeChegar(a, minutos);
      return {
        ...a,
        distancia_km: Math.round(distancia * 100) / 100,
        minutos_a_pe: minutos,
        vagas_na_chegada: vagasNaChegada(a, minutos),
        seguro: a.apto && !lota,
        motivo_final: a.motivo ?? (lota ? 'deve lotar antes de você chegar' : null),
      };
    })
    .sort((a, b) => a.distancia_km - b.distancia_km || (a.abrigo_id < b.abrigo_id ? -1 : 1));

  const recomendados = avaliados.filter((a) => a.seguro).slice(0, limite);
  const limiteDeDistancia = recomendados[0]?.distancia_km ?? Infinity;
  const evitados = avaliados.filter((a) => !a.seguro && a.distancia_km < limiteDeDistancia);
  return { recomendados, evitados };
}
