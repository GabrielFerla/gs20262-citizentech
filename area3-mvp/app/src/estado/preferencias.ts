/**
 * Preferências da pessoa, guardadas só neste aparelho (AsyncStorage; no navegador, localStorage).
 * O bairro e o tamanho do grupo vão para a API só como parâmetro da consulta; nada mais sai daqui.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useSyncExternalStore } from 'react';

export interface Preferencias {
  bairroId: string | null;
  bairroNome: string | null;
  /** Tamanho do grupo (1 a 50, o limite da API). */
  pessoas: number;
  /** Avisar quando o vigia abrir ou escalar um alerta. */
  avisos: boolean;
}

export const CHAVE = 'abriga:preferencias:v1';
export const PESSOAS_MIN = 1;
export const PESSOAS_MAX = 50;
export const PADRAO: Preferencias = { bairroId: null, bairroNome: null, pessoas: 1, avisos: true };

interface Estado {
  carregado: boolean;
  valores: Preferencias;
}

let estado: Estado = { carregado: false, valores: PADRAO };
const ouvintes = new Set<() => void>();
let carregando: Promise<void> | null = null;

function mudar(novo: Estado) {
  estado = novo;
  ouvintes.forEach((avisar) => avisar());
}

export function limitarPessoas(n: number): number {
  if (!Number.isFinite(n)) return PADRAO.pessoas;
  return Math.min(PESSOAS_MAX, Math.max(PESSOAS_MIN, Math.round(n)));
}

/** Aceita só o que tem o formato certo: um valor estragado no armazenamento não derruba o app. */
function validar(bruto: unknown): Preferencias {
  const p = (bruto && typeof bruto === 'object' ? bruto : {}) as Record<string, unknown>;
  const texto = (v: unknown) => (typeof v === 'string' && v.length > 0 && v.length <= 80 ? v : null);
  const bairroId = texto(p.bairroId);
  return {
    bairroId,
    bairroNome: bairroId ? texto(p.bairroNome) : null,
    pessoas: typeof p.pessoas === 'number' ? limitarPessoas(p.pessoas) : PADRAO.pessoas,
    avisos: typeof p.avisos === 'boolean' ? p.avisos : PADRAO.avisos,
  };
}

export function carregarPreferencias(): Promise<void> {
  carregando ??= AsyncStorage.getItem(CHAVE)
    .then((salvo) => mudar({ carregado: true, valores: salvo ? validar(JSON.parse(salvo)) : PADRAO }))
    .catch(() => mudar({ carregado: true, valores: PADRAO }));
  return carregando;
}

export async function salvarPreferencias(mudancas: Partial<Preferencias>): Promise<void> {
  const valores = validar({ ...estado.valores, ...mudancas });
  mudar({ carregado: true, valores });
  try {
    await AsyncStorage.setItem(CHAVE, JSON.stringify(valores));
  } catch {
    // Sem armazenamento (aba anônima, por exemplo): vale só enquanto o app estiver aberto.
  }
}

/** Só para os testes. */
export function reiniciarPreferencias(): void {
  carregando = null;
  mudar({ carregado: false, valores: PADRAO });
}

function assinar(avisar: () => void) {
  ouvintes.add(avisar);
  void carregarPreferencias();
  return () => ouvintes.delete(avisar);
}

export function usePreferencias(): Estado & { salvar: typeof salvarPreferencias } {
  const atual = useSyncExternalStore(
    assinar,
    () => estado,
    () => estado,
  );
  return { ...atual, salvar: salvarPreferencias };
}
