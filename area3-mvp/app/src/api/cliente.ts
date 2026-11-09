/**
 * Cliente HTTP da API de IA: descobre o endereço, põe um tempo limite e traduz cada
 * falha numa mensagem simples para a tela.
 */
import Constants from 'expo-constants';
import { Platform } from 'react-native';

export const TEMPO_LIMITE_MS = 8000;
const PORTA_DA_API = 8000;

export type TipoErro =
  'sem_conexao' | 'servidor_indisponivel' | 'tempo_esgotado' | 'nao_encontrado' | 'invalido' | 'outro';

const MENSAGENS: Record<TipoErro, string> = {
  sem_conexao: 'Sem conexão com o Abriga. Confira a internet ou se o servidor está ligado.',
  servidor_indisponivel: 'O servidor de dados está fora do ar. Tentando de novo…',
  tempo_esgotado: 'O servidor demorou para responder. Tentando de novo…',
  nao_encontrado: 'Não encontramos o que você pediu.',
  invalido: 'O pedido não foi aceito pelo servidor.',
  outro: 'Algo deu errado. Tentando de novo…',
};

export class ErroApi extends Error {
  readonly tipo: TipoErro;
  readonly status?: number;
  /** Texto técnico da API (campo "detail"), para depuração. */
  readonly detalhe?: string;

  constructor(tipo: TipoErro, status?: number, detalhe?: string) {
    super(MENSAGENS[tipo]);
    this.name = 'ErroApi';
    this.tipo = tipo;
    this.status = status;
    this.detalhe = detalhe;
  }

  /** Vale tentar de novo? (não adianta repetir um 404 ou um 422) */
  get passageiro(): boolean {
    return this.tipo !== 'nao_encontrado' && this.tipo !== 'invalido';
  }
}

export function mensagemDoErro(erro: unknown): string {
  return erro instanceof ErroApi ? erro.message : MENSAGENS.outro;
}

export function tipoPorStatus(status: number): TipoErro {
  if (status === 404) return 'nao_encontrado';
  if (status === 422 || status === 400) return 'invalido';
  // 503: banco fora do ar (a API responde assim em qualquer rota).
  // 502 e 504: o nginx do app não alcançou a API.
  if (status === 502 || status === 503 || status === 504) return 'servidor_indisponivel';
  return 'outro';
}

/**
 * Endereço da API, nesta ordem:
 * 1. EXPO_PUBLIC_API_URL, gravado no build (no Docker vale "/api": o nginx do app repassa para a API);
 * 2. no navegador, em desenvolvimento: http://localhost:8000;
 * 3. no Expo Go: a API no mesmo computador do Metro (o IP vem do endereço do Metro).
 */
export function urlBaseDaApi(
  configurada: string | undefined = process.env.EXPO_PUBLIC_API_URL,
  plataforma: string = Platform.OS,
  enderecoDoMetro: string | null | undefined = Constants.expoConfig?.hostUri,
): string {
  if (configurada) return configurada.replace(/\/+$/, '');
  if (plataforma !== 'web' && enderecoDoMetro) {
    const host = enderecoDoMetro.split('/')[0].replace(/:\d+$/, '');
    return `http://${host}:${PORTA_DA_API}`;
  }
  return `http://localhost:${PORTA_DA_API}`;
}

async function lerDetalhe(resposta: Response): Promise<string | undefined> {
  try {
    const corpo = await resposta.json();
    return typeof corpo?.detail === 'string' ? corpo.detail : undefined;
  } catch {
    return undefined;
  }
}

/**
 * GET que devolve JSON. O sinal vem do TanStack Query (cancela quando a tela sai).
 * O tempo limite vale para o pedido inteiro, até o fim do corpo da resposta.
 */
export async function buscarJson<T>(caminho: string, sinal?: AbortSignal): Promise<T> {
  const controle = new AbortController();
  let estourou = false;
  const relogio = setTimeout(() => {
    estourou = true;
    controle.abort();
  }, TEMPO_LIMITE_MS);
  const repassarCancelamento = () => controle.abort();
  sinal?.addEventListener('abort', repassarCancelamento);

  // Falha de rede ou de leitura: a tela cancelou (repassa), estourou o tempo ou não há conexão.
  const traduzir = (erro: unknown, seNaoForTempo: ErroApi): never => {
    if (sinal?.aborted) throw erro;
    throw estourou ? new ErroApi('tempo_esgotado') : seNaoForTempo;
  };

  try {
    let resposta: Response;
    try {
      resposta = await fetch(`${urlBaseDaApi()}${caminho}`, {
        signal: controle.signal,
        headers: { Accept: 'application/json' },
      });
    } catch (erro) {
      return traduzir(erro, new ErroApi('sem_conexao'));
    }

    if (!resposta.ok) {
      throw new ErroApi(tipoPorStatus(resposta.status), resposta.status, await lerDetalhe(resposta));
    }
    try {
      return (await resposta.json()) as T;
    } catch (erro) {
      return traduzir(erro, new ErroApi('outro', resposta.status, 'resposta não é JSON'));
    }
  } finally {
    clearTimeout(relogio);
    sinal?.removeEventListener('abort', repassarCancelamento);
  }
}
