/**
 * Consultas com atualização automática (TanStack Query).
 *
 * A simulação anda 10 minutos por segundo real, então os rios e os alertas são lidos
 * a cada 3 s. Se uma leitura falhar, a tela continua com o último dado bom e mostra o aviso.
 */
import { QueryClient, useQuery } from '@tanstack/react-query';

import { registrarLeituras } from '@/estado/historico';

import { api } from './abriga';
import { ErroApi } from './cliente';
import type { EstacaoPrevisao } from './tipos';

export const INTERVALO_MS = {
  rios: 3_000,
  abrigos: 5_000,
  saude: 10_000,
} as const;

export const chaves = {
  saude: ['saude'] as const,
  previsao: ['previsao'] as const,
  alertas: (bairroId: string | null) => ['alertas', bairroId] as const,
  bairros: ['bairros'] as const,
  abrigos: (pessoas: number) => ['abrigos', pessoas] as const,
  recomendacao: (bairroId: string, pessoas: number) => ['recomendacao', bairroId, pessoas] as const,
};

export function criarClienteDeConsultas(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Repete só o que pode passar sozinho (servidor fora do ar, rede); 404 e 422, não.
        retry: (tentativas, erro) => tentativas < 2 && !(erro instanceof ErroApi && !erro.passageiro),
        retryDelay: (tentativa) => Math.min(1_000 * 2 ** tentativa, 5_000),
        staleTime: 0,
      },
    },
  });
}

export function useSaude() {
  return useQuery({
    queryKey: chaves.saude,
    queryFn: ({ signal }) => api.saude(signal),
    refetchInterval: INTERVALO_MS.saude,
  });
}

async function buscarPrevisao({ signal }: { signal: AbortSignal }): Promise<EstacaoPrevisao[]> {
  const rios = await api.previsao(signal);
  registrarLeituras(rios); // linha do gráfico na tela Rio
  return rios;
}

export function usePrevisao() {
  return useQuery({
    queryKey: chaves.previsao,
    queryFn: buscarPrevisao,
    refetchInterval: INTERVALO_MS.rios,
  });
}

/**
 * Um rio só, tirado da MESMA consulta de /previsao (que a tela Agora já mantém): nenhum pedido a mais
 * e uma fonte só para o histórico do gráfico. `null` quando o rio não existe.
 */
export function usePrevisaoDoRio(estacaoId: string) {
  return useQuery({
    queryKey: chaves.previsao,
    queryFn: buscarPrevisao,
    refetchInterval: INTERVALO_MS.rios,
    select: (rios: EstacaoPrevisao[]) => rios.find((r) => r.estacao_id === estacaoId) ?? null,
  });
}

export function useAlertas(bairroId: string | null) {
  return useQuery({
    queryKey: chaves.alertas(bairroId),
    queryFn: ({ signal }) => api.alertas(bairroId, signal),
    refetchInterval: INTERVALO_MS.rios,
  });
}

export function useBairros() {
  return useQuery({
    queryKey: chaves.bairros,
    queryFn: ({ signal }) => api.bairros(signal),
    staleTime: Infinity,
  });
}

/** `ativa`: só atualiza com a tela aberta. */
export function useAbrigos(pessoas: number, ativa = true) {
  return useQuery({
    queryKey: chaves.abrigos(pessoas),
    queryFn: ({ signal }) => api.abrigos(pessoas, signal),
    refetchInterval: INTERVALO_MS.abrigos,
    subscribed: ativa,
  });
}

export function useRecomendacao(bairroId: string | null, pessoas: number, ativa = true) {
  return useQuery({
    queryKey: chaves.recomendacao(bairroId ?? '', pessoas),
    queryFn: ({ signal }) => api.recomendacao(bairroId as string, pessoas, signal),
    enabled: bairroId !== null,
    refetchInterval: INTERVALO_MS.abrigos,
    subscribed: ativa,
  });
}
