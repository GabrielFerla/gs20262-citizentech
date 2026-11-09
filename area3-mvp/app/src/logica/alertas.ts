/**
 * Quando avisar: o vigia da API abre o alerta antecipado sozinho (quando a PREVISÃO cruza uma cota)
 * e o escala. O app avisa uma vez por alerta novo ou escalado, com o texto de push da API.
 */
import { SITUACOES, type AlertaDoVigia, type RespostaAlertas } from '@/api/tipos';

import { mensagensDoRio, nomeDaSituacao, pedeParaSair } from './situacao';

/** Muda quando o alerta abre (aberto_em) ou escala (severidade). */
export function chaveDoAlerta(alerta: AlertaDoVigia): string {
  return `${alerta.estacao_id}:${alerta.severidade}:${alerta.aberto_em}`;
}

export interface Aviso {
  chave: string;
  estacaoId: string;
  severidade: number;
  /** Nome do rio ("Lago Guaíba"). */
  rio: string;
  titulo: string;
  corpo: string;
  /** Para onde o toque no aviso leva. */
  rota: '/abrigos' | '/';
  /** Os outros rios que abriram ou escalaram na mesma leitura ("Também: Rio Gravataí (atenção)."). */
  tambem?: string;
}

/**
 * Guarda os alertas já vistos (só na memória). Na primeira leitura, o que já estava aberto
 * conta como visto: aparece na tela Agora, sem notificação.
 */
export class DetectorDeAlertas {
  private vistos = new Set<string>();
  private primeiraLeitura = true;

  /** Devolve os alertas novos desta leitura, do mais grave para o menos grave. */
  novos(abertos: AlertaDoVigia[]): AlertaDoVigia[] {
    const novos = abertos.filter((a) => !this.vistos.has(chaveDoAlerta(a)));
    novos.forEach((a) => this.vistos.add(chaveDoAlerta(a)));
    if (this.primeiraLeitura) {
      this.primeiraLeitura = false;
      return [];
    }
    return novos.sort((a, b) => b.severidade - a.severidade);
  }
}

/** O aviso de um alerta novo, com o texto de push da API (linguagem simples). */
export function avisoDoAlerta(alerta: AlertaDoVigia, resposta: RespostaAlertas): Aviso {
  const mensagens = mensagensDoRio(resposta, alerta.estacao_id);
  const situacao = SITUACOES[Math.min(Math.max(alerta.severidade, 0), 3)];
  const rio = resposta.rios_fora_do_normal.find((r) => r.previsao.estacao_id === alerta.estacao_id)?.previsao;
  return {
    chave: chaveDoAlerta(alerta),
    estacaoId: alerta.estacao_id,
    severidade: alerta.severidade,
    rio: rio?.corpo_hidrico ?? 'um rio',
    titulo: mensagens?.push_titulo ?? `Alerta: ${rio?.corpo_hidrico ?? 'um rio'} deve subir`,
    corpo: mensagens?.push_corpo ?? 'Abra o Abriga para ver a situação dos rios e onde ficar seguro.',
    rota: pedeParaSair(situacao) ? '/abrigos' : '/',
  };
}

/**
 * A faixa cobre o topo da tela. Quem já está em "Onde ficar seguro" ou no detalhe de um abrigo não precisa
 * dela para um aviso que leva para lá: a lista na tela já é a atual. (A notificação do sistema continua.)
 */
export function mostraFaixa(aviso: Aviso, rotaAtual: string): boolean {
  const jaProcuraAbrigo = rotaAtual === '/abrigos' || rotaAtual.startsWith('/abrigo/');
  return !(aviso.rota === '/abrigos' && jaProcuraAbrigo);
}

/**
 * Vários alertas podem abrir ou escalar na mesma leitura (na cheia simulada, o Guaíba e o Gravataí juntos).
 * Cada um ganha a sua notificação do sistema; a faixa mostra o mais grave (o primeiro) e cita os outros.
 */
export function faixaDosAvisos(avisos: Aviso[]): Aviso {
  const [principal, ...outros] = avisos;
  if (outros.length === 0) return principal;
  const lista = outros.map((o) => `${o.rio} (${nomeDaSituacao(o.severidade)})`).join(', ');
  return { ...principal, tambem: `Também: ${lista}.` };
}
