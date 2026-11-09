/**
 * Leituras dos rios recebidas desde que o app abriu, para a linha do gráfico.
 * Ficam só na memória do aparelho (somem ao fechar o app) e não são enviadas a ninguém.
 */
import { useSyncExternalStore } from 'react';

import type { EstacaoPrevisao } from '@/api/tipos';

export interface Leitura {
  medidoEm: string;
  nivel: number;
}

/** 120 leituras ≈ 6 min de app aberto (≈ 60 h simuladas na demonstração). */
export const MAXIMO_DE_LEITURAS = 120;

const VAZIO: readonly Leitura[] = Object.freeze([]);
let leituras = new Map<string, readonly Leitura[]>();
const ouvintes = new Set<() => void>();

/**
 * Guarda as leituras novas. Só entra a leitura MAIS NOVA que a última guardada: a mesma leitura repetida
 * nas consultas entra uma vez só, e uma resposta atrasada (mais velha) não faz a linha voltar no tempo.
 */
export function registrarLeituras(rios: EstacaoPrevisao[]): void {
  let mudou = false;
  const proximo = new Map(leituras);
  for (const rio of rios) {
    const medidoEm = rio.medido_em_utc ? Date.parse(rio.medido_em_utc) : NaN;
    if (!Number.isFinite(medidoEm)) continue;
    const anteriores = proximo.get(rio.estacao_id) ?? VAZIO;
    const ultima = anteriores.at(-1);
    if (ultima && medidoEm <= Date.parse(ultima.medidoEm)) continue;
    proximo.set(
      rio.estacao_id,
      [...anteriores, { medidoEm: rio.medido_em_utc as string, nivel: rio.nivel_atual_m }].slice(-MAXIMO_DE_LEITURAS),
    );
    mudou = true;
  }
  if (mudou) {
    leituras = proximo;
    ouvintes.forEach((avisar) => avisar());
  }
}

export function leiturasDe(estacaoId: string): readonly Leitura[] {
  return leituras.get(estacaoId) ?? VAZIO;
}

/** Só para os testes. */
export function limparHistorico(): void {
  leituras = new Map();
  ouvintes.forEach((avisar) => avisar());
}

function assinar(avisar: () => void) {
  ouvintes.add(avisar);
  return () => ouvintes.delete(avisar);
}

export function useLeiturasDoRio(estacaoId: string): readonly Leitura[] {
  return useSyncExternalStore(
    assinar,
    () => leiturasDe(estacaoId),
    () => leiturasDe(estacaoId),
  );
}
