/**
 * A posição da pessoa (modo "Minha localização"). Fica SÓ na memória deste aparelho, enquanto
 * o app está aberto: não é gravada, não entra em URL nenhuma e não é enviada à API (LGPD).
 */
import * as Location from 'expo-location';
import { useSyncExternalStore } from 'react';

import { dentroDePortoAlegre, distanciaDoCentroKm, type Posicao } from '@/logica/geo';

let posicao: Posicao | null = null;
const ouvintes = new Set<() => void>();

function mudar(nova: Posicao | null) {
  posicao = nova;
  ouvintes.forEach((avisar) => avisar());
}

export function posicaoAtual(): Posicao | null {
  return posicao;
}

export function esquecerPosicao(): void {
  mudar(null);
}

export function usePosicao(): Posicao | null {
  return useSyncExternalStore(
    (avisar) => {
      ouvintes.add(avisar);
      return () => ouvintes.delete(avisar);
    },
    () => posicao,
    () => posicao,
  );
}

export const TEMPO_LIMITE_GPS_MS = 15_000;

export type ResultadoDaLocalizacao =
  | { ok: true; posicao: Posicao }
  | { ok: false; motivo: 'sem_permissao' | 'indisponivel' }
  | { ok: false; motivo: 'fora_de_poa'; distanciaKm: number };

function comTempoLimite<T>(promessa: Promise<T>, ms: number): Promise<T> {
  return new Promise((resolver, rejeitar) => {
    const relogio = setTimeout(() => rejeitar(new Error('tempo esgotado')), ms);
    promessa.then(
      (valor) => {
        clearTimeout(relogio);
        resolver(valor);
      },
      (erro) => {
        clearTimeout(relogio);
        rejeitar(erro);
      },
    );
  });
}

/** Pede a permissão, lê o GPS uma vez e guarda a posição na memória (se for em Porto Alegre). */
export async function localizar(): Promise<ResultadoDaLocalizacao> {
  try {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') return { ok: false, motivo: 'sem_permissao' };
    const leitura = await comTempoLimite(
      Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced }),
      TEMPO_LIMITE_GPS_MS,
    );
    const nova = { lat: leitura.coords.latitude, lon: leitura.coords.longitude };
    if (!dentroDePortoAlegre(nova)) {
      return { ok: false, motivo: 'fora_de_poa', distanciaKm: Math.round(distanciaDoCentroKm(nova)) };
    }
    mudar(nova);
    return { ok: true, posicao: nova };
  } catch {
    return { ok: false, motivo: 'indisponivel' };
  }
}

export function mensagemDaFalha(resultado: Exclude<ResultadoDaLocalizacao, { ok: true }>): string {
  switch (resultado.motivo) {
    case 'sem_permissao':
      return 'Sem permissão para usar a localização. Mostrando os abrigos pelo bairro.';
    case 'fora_de_poa':
      return `Você está a ${resultado.distanciaKm} km do centro de Porto Alegre, longe dos abrigos. Mostrando pelo bairro.`;
    default:
      return 'Não deu para pegar a sua localização agora. Mostrando os abrigos pelo bairro.';
  }
}
