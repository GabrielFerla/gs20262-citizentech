/**
 * API de mentira para os testes: responde com as respostas reais guardadas em __fixtures__/
 * (capturadas da API em 08/11/2026, durante uma cheia simulada) e registra cada URL pedida.
 */
import abrigos4 from '../__fixtures__/abrigos-4.json';
import alertasNavegantes from '../__fixtures__/alertas-navegantes.json';
import bairros from '../__fixtures__/bairros.json';
import previsao from '../__fixtures__/previsao.json';
import recomendacaoNavegantes4 from '../__fixtures__/recomendacao-navegantes-4.json';
import saude from '../__fixtures__/saude.json';
import type { AbrigoAvaliado, EstacaoPrevisao, Recomendacao, RespostaAlertas } from '../src/api/tipos';

export const fixtures = {
  saude,
  previsao: previsao as EstacaoPrevisao[],
  alertasNavegantes: alertasNavegantes as unknown as RespostaAlertas,
  bairros,
  abrigos4: abrigos4 as AbrigoAvaliado[],
  recomendacaoNavegantes4: recomendacaoNavegantes4 as Recomendacao,
};

/** Cópia profunda, para o teste mudar um campo sem estragar a fixture dos outros testes. */
export function copia<T>(valor: T): T {
  return JSON.parse(JSON.stringify(valor));
}

type Resposta = unknown | { status: number; corpo?: unknown };

function eStatus(r: Resposta): r is { status: number; corpo?: unknown } {
  return typeof r === 'object' && r !== null && 'status' in r && typeof (r as { status: unknown }).status === 'number';
}

/**
 * Troca o fetch global. As chaves são caminhos ("/previsao") ou caminho com consulta
 * ("/alertas?bairro=navegantes"); a com consulta tem prioridade. O valor pode ser uma
 * função (para mudar a resposta no meio do teste). Rota desconhecida → 404.
 */
export function simularApi(rotas: Record<string, Resposta | (() => Resposta)>) {
  const urls: string[] = [];
  const fetchFalso = jest.fn(async (url: string) => {
    urls.push(url);
    const caminhoComConsulta = url.replace(/^https?:\/\/[^/]+/, '');
    const caminho = caminhoComConsulta.split('?')[0];
    const chave = caminhoComConsulta in rotas ? caminhoComConsulta : caminho in rotas ? caminho : null;
    let r: Resposta = chave === null ? { status: 404, corpo: { detail: 'não existe' } } : rotas[chave];
    if (typeof r === 'function') r = (r as () => Resposta)();
    const { status, corpo } = eStatus(r) ? { status: r.status, corpo: r.corpo } : { status: 200, corpo: r };
    return { ok: status >= 200 && status < 300, status, json: async () => copia(corpo) } as Response;
  });
  globalThis.fetch = fetchFalso as unknown as typeof fetch;
  return { fetchFalso, urls };
}

/** As rotas "normais" da API, como estavam na cheia simulada. */
export function rotasPadrao(): Record<string, Resposta> {
  return {
    '/saude': fixtures.saude,
    '/previsao': fixtures.previsao,
    '/alertas': fixtures.alertasNavegantes,
    '/bairros': fixtures.bairros,
    '/abrigos': fixtures.abrigos4,
    '/abrigos/recomendacao': fixtures.recomendacaoNavegantes4,
    ...Object.fromEntries(fixtures.previsao.map((rio) => [`/previsao/${rio.estacao_id}`, rio])),
  };
}
