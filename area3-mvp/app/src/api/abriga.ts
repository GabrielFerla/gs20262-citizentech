/**
 * Rotas da API usadas pelo app. Repare que nenhuma recebe latitude ou longitude:
 * a posição da pessoa nunca sai do aparelho (LGPD). O mais perto que vai é o bairro.
 */
import { buscarJson } from './cliente';
import type { AbrigoAvaliado, Bairro, EstacaoPrevisao, Recomendacao, RespostaAlertas, Saude } from './tipos';

const q = encodeURIComponent;

export const api = {
  saude: (sinal?: AbortSignal) => buscarJson<Saude>('/saude', sinal),

  previsao: (sinal?: AbortSignal) => buscarJson<EstacaoPrevisao[]>('/previsao', sinal),

  alertas: (bairroId: string | null, sinal?: AbortSignal) =>
    buscarJson<RespostaAlertas>(bairroId ? `/alertas?bairro=${q(bairroId)}` : '/alertas', sinal),

  bairros: (sinal?: AbortSignal) => buscarJson<Bairro[]>('/bairros', sinal),

  /** Todos os abrigos avaliados agora; o app termina a conta no aparelho (modo localização). */
  abrigos: (pessoas: number, sinal?: AbortSignal) => buscarJson<AbrigoAvaliado[]>(`/abrigos?pessoas=${pessoas}`, sinal),

  /** Os 3 aptos mais perto do centro do bairro, e por que os mais próximos foram evitados. */
  recomendacao: (bairroId: string, pessoas: number, sinal?: AbortSignal) =>
    buscarJson<Recomendacao>(`/abrigos/recomendacao?bairro=${q(bairroId)}&pessoas=${pessoas}`, sinal),
};
