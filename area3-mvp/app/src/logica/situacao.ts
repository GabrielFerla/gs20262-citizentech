/**
 * Como o app resume a situação dos rios em linguagem simples.
 * Não decide nada novo: a situação, a previsão e as mensagens vêm da API.
 */
import { SITUACOES, type EstacaoPrevisao, type Mensagens, type RespostaAlertas, type Situacao } from '@/api/tipos';
import { metros } from './formato';

const NOMES: Record<Situacao, string> = {
  normal: 'normal',
  atencao: 'atenção',
  alerta: 'alerta',
  inundacao: 'inundação',
};

/** 0 normal, 1 atenção, 2 alerta, 3 inundação (a mesma escala da API). */
export function severidade(situacao: Situacao): number {
  return SITUACOES.indexOf(situacao);
}

/** A pior situação do rio entre agora e daqui a 6 h. */
export function piorDoRio(rio: EstacaoPrevisao): Situacao {
  return SITUACOES[Math.max(severidade(rio.situacao_atual), severidade(rio.situacao_prevista))];
}

/** Rios do mais grave para o menos grave; no empate, o alerta antecipado vem antes. */
export function ordenarPorGravidade(rios: EstacaoPrevisao[]): EstacaoPrevisao[] {
  return [...rios].sort(
    (a, b) =>
      severidade(piorDoRio(b)) - severidade(piorDoRio(a)) ||
      Number(b.alerta_antecipado) - Number(a.alerta_antecipado) ||
      a.corpo_hidrico.localeCompare(b.corpo_hidrico),
  );
}

export interface Resumo {
  situacao: Situacao;
  titulo: string;
  texto: string;
  /** Rio que puxou o resumo (o mais grave), quando há algum fora do normal. */
  rio: EstacaoPrevisao | null;
}

const TITULOS: Record<Situacao, string> = {
  normal: 'Rios normais',
  atencao: 'Atenção nos rios',
  alerta: 'Alerta de cheia',
  inundacao: 'Risco de inundação',
};

/**
 * A faixa do topo da tela Agora. Quando a API mandou a mensagem do rio mais grave, ela vem
 * pronta (título e texto de push, em linguagem simples e já verificados pela IA).
 */
export function resumoDosRios(rios: EstacaoPrevisao[], alertas?: RespostaAlertas): Resumo {
  // GET /previsao e GET /alertas chegam em momentos diferentes. Com a resposta de /alertas, o rio, o
  // título e o texto vêm da MESMA leitura; assim a faixa não pisca entre a mensagem e um texto genérico.
  const daMesmaLeitura = alertas?.rios_fora_do_normal.map((r) => r.previsao) ?? [];
  const [maisGrave] = ordenarPorGravidade(daMesmaLeitura.length > 0 ? daMesmaLeitura : rios);
  if (!maisGrave || piorDoRio(maisGrave) === 'normal') {
    return {
      situacao: 'normal',
      titulo: TITULOS.normal,
      texto: 'Nenhum rio está fora do normal agora nem deve ficar nas próximas 6 horas.',
      rio: null,
    };
  }
  const situacao = piorDoRio(maisGrave);
  const mensagens = mensagensDoRio(alertas, maisGrave.estacao_id);
  if (mensagens?.push_titulo && mensagens.push_corpo) {
    return { situacao, titulo: mensagens.push_titulo, texto: mensagens.push_corpo, rio: maisGrave };
  }
  const texto = maisGrave.alerta_antecipado
    ? `O ${maisGrave.corpo_hidrico} deve chegar a ${NOMES[maisGrave.situacao_prevista]} nas próximas 6 horas.`
    : `O ${maisGrave.corpo_hidrico} está em ${NOMES[maisGrave.situacao_atual]}.`;
  return { situacao, titulo: TITULOS[situacao], texto, rio: maisGrave };
}

export function mensagensDoRio(alertas: RespostaAlertas | undefined, estacaoId: string): Mensagens | null {
  return alertas?.rios_fora_do_normal.find((r) => r.previsao.estacao_id === estacaoId)?.mensagens ?? null;
}

/** Mandar a pessoa procurar abrigo? Só a partir do alerta (a "atenção" pede só para ficar atento). */
export function pedeParaSair(situacao: Situacao): boolean {
  return severidade(situacao) >= severidade('alerta');
}

export function textoDaTendencia(rio: EstacaoPrevisao): string {
  return { subindo: 'subindo', estavel: 'estável', descendo: 'baixando' }[rio.tendencia];
}

/** "Faltam 0,23 m para a cota de alerta" ou "0,67 m acima da cota de inundação". */
export function distanciaDaCota(rio: EstacaoPrevisao): string {
  const { atencao_m, alerta_m, inundacao_m } = rio.cotas;
  const nivel = rio.nivel_atual_m;
  const cotas: [string, number][] = [
    ['atenção', atencao_m],
    ['alerta', alerta_m],
    ['inundação', inundacao_m],
  ];
  const proxima = cotas.find(([, cota]) => nivel < cota);
  if (proxima) {
    return `Faltam ${metros(proxima[1] - nivel)} para a cota de ${proxima[0]}`;
  }
  return `${metros(nivel - inundacao_m)} acima da cota de inundação`;
}

/** Explicação curta do modelo usado no rio (sem jargão na frase principal). */
export function explicacaoDoModelo(rio: EstacaoPrevisao): string {
  if (rio.modelo === 'regra_simples') {
    return (
      'Para este rio, a previsão repete o nível de agora. Ele sobe e desce em 1 a 2 horas, e nos testes ' +
      'a IA não acertou mais que essa regra simples. Aqui, o aviso útil é o da própria chuva.'
    );
  }
  const nome = rio.modelo === 'random_forest' ? 'random forest' : rio.modelo.replace(/_/g, ' ');
  return (
    `A previsão para daqui a 6 horas é da IA (${nome}), treinada com 24 meses de cheias simuladas. ` +
    'Ela usa o nível de agora, quanto o rio subiu na última hora e a chuva de 1, 6 e 24 horas.'
  );
}
