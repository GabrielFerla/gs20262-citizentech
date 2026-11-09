/**
 * Tipos das respostas da API de IA (area1-ia/ia/api.py).
 * Espelham os modelos Pydantic: se a API mudar um campo, mude aqui também.
 * Os testes usam respostas reais da API, guardadas em __fixtures__/.
 */

export const SITUACOES = ['normal', 'atencao', 'alerta', 'inundacao'] as const;
export type Situacao = (typeof SITUACOES)[number];

export type Tendencia = 'subindo' | 'estavel' | 'descendo';

export interface Cotas {
  atencao_m: number;
  alerta_m: number;
  inundacao_m: number;
}

export interface EstacaoPrevisao {
  estacao_id: string;
  estacao: string;
  corpo_hidrico: string;
  medido_em_utc: string | null;
  /** Última leitura com mais de 30 min: previsão pouco confiável. */
  leitura_velha: boolean;
  /** Faltou leitura para alguma entrada do modelo: a previsão repete o nível de agora. */
  dados_incompletos: boolean;
  nivel_atual_m: number;
  nivel_previsto_6h_m: number;
  persistencia_6h_m: number;
  variacao_prevista_m: number;
  tendencia: Tendencia;
  situacao_atual: Situacao;
  situacao_prevista: Situacao;
  /** A previsão está pior que a situação de agora. */
  alerta_antecipado: boolean;
  cotas: Cotas;
  /** random_forest | regressao_linear | regra_simples */
  modelo: string;
  entrada: Record<string, number>;
}

export interface AbrigoAvaliado {
  abrigo_id: string;
  abrigo: string;
  lat: number;
  lon: number;
  capacidade: number;
  ocupacao: number;
  vagas: number;
  /** Só na recomendação por bairro (a API sabe a distância). */
  vagas_previstas_na_chegada: number | null;
  chegando_por_hora: number;
  /** Em quantos minutos deixa de ter vaga para o grupo (nulo = não está enchendo). */
  minutos_ate_lotar: number | null;
  em_area_de_risco: boolean;
  estacao_proxima_id: string;
  situacao_atual_regiao: Situacao;
  situacao_prevista_regiao: Situacao;
  /** Em GET /abrigos: apto AGORA; o app ainda confere se lota antes de a pessoa chegar. */
  apto: boolean;
  /** Por que não é recomendado (linguagem simples). */
  motivo: string | null;
  distancia_km: number | null;
  minutos_a_pe: number | null;
}

export interface Mensagens {
  intencao: string;
  sms: string | null;
  push_titulo: string | null;
  push_corpo: string | null;
  whatsapp: string | null;
  defesa_civil: string;
  verificacao: Record<string, string[]>;
}

export interface Recomendacao {
  bairro_id: string;
  bairro: string;
  origem: string;
  pessoas: number;
  estacao_da_regiao: EstacaoPrevisao | null;
  recomendados: AbrigoAvaliado[];
  /** Abrigos mais perto que o 1º recomendado, com o motivo. */
  evitados: AbrigoAvaliado[];
  mensagens: Mensagens | null;
}

export interface Bairro {
  bairro_id: string;
  bairro: string;
  zona_risco: string;
}

/** Alerta aberto pelo vigia (a automação que olha a previsão). */
export interface AlertaDoVigia {
  estacao_id: string;
  /** 1 atenção, 2 alerta, 3 inundação */
  severidade: number;
  aberto_em: string;
  atualizado_em: string;
  nivel_previsto_m: number;
  pico_previsto_m: number;
  antecipado: boolean;
  mensagem_sms: string | null;
}

export interface EventoDoVigia {
  quando: string;
  estacao_id: string;
  acao: 'abrir' | 'escalar' | 'fechar' | 'sem_dados';
  severidade: number;
  nivel_atual_m: number | null;
  nivel_previsto_m: number;
}

export interface RespostaAlertas {
  vigia: {
    ultima_rodada_utc: string | null;
    ultimo_erro: string | null;
    abertos: AlertaDoVigia[];
    eventos: EventoDoVigia[];
  };
  rios_fora_do_normal: { previsao: EstacaoPrevisao; mensagens: Mensagens }[];
}

export interface Saude {
  status: string;
  banco: boolean;
  modelo: { estacoes: string[]; horizonte_h: number };
  vigia: { ultima_rodada_utc: string | null; ultimo_erro: string | null };
}
