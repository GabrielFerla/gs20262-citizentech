/**
 * Identidade do Abriga: serviço cidadão, sem imitar marca nem órgão público.
 * Cores com contraste alto; a situação do rio sempre vem com a palavra, nunca só a cor.
 */
import type { Situacao } from './api/tipos';

export const cores = {
  primaria: '#0B5D73',
  primariaEscura: '#073F4F',
  primariaClara: '#E1F0F4',
  fundo: '#F4F7F9',
  superficie: '#FFFFFF',
  texto: '#14212B',
  textoSuave: '#4A5A66',
  borda: '#D5DEE5',
  erro: '#B42318',
  erroFundo: '#FDE3E1',
  aviso: '#8A6100',
  avisoFundo: '#FFF4CC',
} as const;

interface CoresDaSituacao {
  /** Palavra mostrada na tela. */
  nome: string;
  /** Cor forte (faixa do topo, bolinha). */
  forte: string;
  /** Texto sobre a cor forte. */
  sobreForte: string;
  /** Fundo claro (cartões e selos). */
  fundo: string;
  /** Texto sobre o fundo claro. */
  texto: string;
}

export const situacoes: Record<Situacao, CoresDaSituacao> = {
  normal: { nome: 'Normal', forte: '#1F7A45', sobreForte: '#FFFFFF', fundo: '#E3F4EA', texto: '#14532D' },
  atencao: { nome: 'Atenção', forte: '#F2B705', sobreForte: '#2E2300', fundo: '#FFF4CC', texto: '#6B4B00' },
  alerta: { nome: 'Alerta', forte: '#C2410C', sobreForte: '#FFFFFF', fundo: '#FFE8D6', texto: '#7C2D12' },
  inundacao: { nome: 'Inundação', forte: '#B42318', sobreForte: '#FFFFFF', fundo: '#FDE3E1', texto: '#7A1A12' },
};

export const espaco = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;
export const raio = { sm: 8, md: 12, lg: 16, pilula: 999 } as const;

/** Toque confortável (WCAG / Material): pelo menos 48 px. */
export const ALVO_DE_TOQUE = 48;

export const texto = {
  titulo: { fontSize: 24, fontWeight: '700' as const, color: cores.texto },
  subtitulo: { fontSize: 18, fontWeight: '700' as const, color: cores.texto },
  corpo: { fontSize: 16, color: cores.texto, lineHeight: 22 },
  suave: { fontSize: 14, color: cores.textoSuave, lineHeight: 20 },
  numeroGrande: { fontSize: 32, fontWeight: '800' as const, color: cores.texto },
};
