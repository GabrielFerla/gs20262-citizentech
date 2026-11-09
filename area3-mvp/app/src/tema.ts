/**
 * Identidade do Abriga: serviço cidadão, sem imitar marca nem órgão público.
 * Verde da marca, texto escuro e fundo claro. Todo texto passa no WCAG AA (4,5:1 ou mais);
 * ícones, bordas de controle e formas têm no mínimo 3:1.
 * A situação do rio vem sempre com cor, palavra e ícone, nunca só a cor.
 */
import { Platform, type TextStyle, type ViewStyle } from 'react-native';

import type { Situacao } from './api/tipos';

export const cores = {
  /** Botão primário, links e rótulos verdes. Branco sobre ela: 5,25:1. */
  primaria: '#1F7A5C',
  /** Botão pressionado; texto sobre primariaClara. */
  primariaEscura: '#145A43',
  /** Aba ativa, selo Recomendado, botões − e +. */
  primariaClara: '#E0F0EC',
  fundo: '#F5F8FA',
  superficie: '#FFFFFF',
  texto: '#14212B',
  /** Horários, estação, legendas, abas inativas. */
  textoSuave: '#4A5966',
  /** Divisórias e contorno dos cartões (decorativa: os cartões também têm sombra). */
  borda: '#DCE3E9',
  erro: '#B73823',
  erroFundo: '#FDECE9',
  /** Leitura atrasada, dados incompletos, sem servidor. */
  aviso: '#865400',
  avisoFundo: '#FFF3D6',
  /** Destaque de risco: só em ícones e formas, nunca em texto pequeno (3,95:1). */
  risco: '#E04E39',
  /** Selo Dados simulados, botões 199 e 193, trilho do alternador. */
  neutroFundo: '#EBF0F4',
  /** Rótulo verde sobre fundo escuro (Alerta novo). */
  primariaSobreEscuro: '#7DD3AE',
  /** Texto de apoio sobre fundo escuro. */
  textoSobreEscuro: '#C5D0D9',
  /** Trilho da chave desligada e contornos de controle (3,54:1). */
  bordaControle: '#7B8A97',
  /** Borda das caixas de aviso (sobre avisoFundo). */
  bordaAviso: '#F1D89B',
} as const;

interface CoresDaSituacao {
  /** Palavra mostrada na tela. */
  nome: string;
  /** Cor forte: faixa e selo cheios (Atenção, Alerta, Inundação) e ícones. */
  forte: string;
  /** Texto e ícone sobre a cor forte. */
  sobreForte: string;
  /** Fundo claro: faixa e selo do Normal, faixas do gráfico. */
  fundo: string;
  /** Texto e ícone sobre o fundo claro. */
  texto: string;
  /** Borda da faixa de situação. */
  bordaDaFaixa: string;
  /**
   * Normal nunca aparece em cor cheia (para não parecer botão nem a marca): usa fundo + texto.
   * As outras três usam a cor forte cheia com sobreForte.
   */
  cheia: boolean;
}

export const situacoes: Record<Situacao, CoresDaSituacao> = {
  normal: {
    nome: 'Normal',
    forte: '#4E9C3E',
    sobreForte: '#14212B',
    fundo: '#ECF7E5',
    texto: '#2B6421',
    bordaDaFaixa: '#CFE8C1',
    cheia: false,
  },
  atencao: {
    nome: 'Atenção',
    forte: '#F2B705',
    sobreForte: '#14212B',
    fundo: '#FFF5D2',
    texto: '#7A5700',
    bordaDaFaixa: '#F2B705',
    cheia: true,
  },
  alerta: {
    nome: 'Alerta',
    forte: '#C2410C',
    sobreForte: '#FFFFFF',
    fundo: '#FFEDE3',
    texto: '#9A3412',
    bordaDaFaixa: '#C2410C',
    cheia: true,
  },
  inundacao: {
    nome: 'Inundação',
    forte: '#B42318',
    sobreForte: '#FFFFFF',
    fundo: '#FEEBEA',
    texto: '#951F15',
    bordaDaFaixa: '#B42318',
    cheia: true,
  },
};

/** Espaços: 4, 8, 12, 16, 20, 24, 28. */
export const espaco = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 28,
  /** Margem lateral das telas. */
  margem: 16,
  /** Padding do cartão. */
  cartao: 16,
  /** Padding da faixa de situação. */
  faixa: 20,
  entreCartoes: 12,
  entreSecoes: 28,
} as const;

export const raio = {
  sm: 8,
  md: 12,
  lg: 16,
  pilula: 999,
  /** Selos, aba ativa, botões − e +. */
  selo: 999,
  /** Segmento do alternador, botão Trocar, botões pequenos (12 a 14). */
  controle: 14,
  /** Botões principais e trilho do alternador. */
  botao: 16,
  /** Cartões do rio e do abrigo. */
  cartao: 20,
  /** Faixa de situação. */
  faixa: 24,
} as const;

/** Toque confortável (WCAG / Material): pelo menos 48 px. */
export const ALVO_DE_TOQUE = 48;

/**
 * Inter, um arquivo por peso (carregados em src/app/_layout.tsx).
 * Com fonte própria, o peso vem do nome da família: os estilos não usam fontWeight
 * (no navegador, fontWeight sobre uma família de um peso só engrossa a letra de novo).
 */
export const familias = {
  '400': 'Inter_400Regular',
  '500': 'Inter_500Medium',
  '600': 'Inter_600SemiBold',
  '700': 'Inter_700Bold',
  '800': 'Inter_800ExtraBold',
} as const;

export type Peso = keyof typeof familias;

/** A família da Inter no peso pedido (no lugar de fontWeight). */
export function peso(p: Peso): TextStyle {
  return { fontFamily: familias[p] };
}

/** Números com algarismos de largura igual (não "pulam" quando mudam). */
export const tabular: TextStyle = { fontVariant: ['tabular-nums'] };

function estilo(p: Peso, fontSize: number, lineHeight: number, extra?: TextStyle): TextStyle {
  return { fontFamily: familias[p], fontSize, lineHeight, color: cores.texto, ...extra };
}

const tituloTela = estilo('700', 28, 34, { letterSpacing: -0.28 });
const tituloCartao = estilo('700', 18, 24);
const numero = estilo('700', 30, 34, { letterSpacing: -0.3, ...tabular });
const corpo = estilo('400', 17, 24);
const apoio = estilo('500', 15, 20, { color: cores.textoSuave });

export const texto = {
  /** Título das telas (28/34). */
  titulo: tituloTela,
  /** Nome do abrigo e títulos de cartão (18/24). */
  subtitulo: tituloCartao,
  /** Texto corrido (17/24). */
  corpo,
  /** Horário, estação e legendas (15/20, textoSuave). */
  suave: apoio,
  /** Nível do rio (30/34, tabular). */
  numeroGrande: numero,

  tituloTela,
  /** Ação na faixa de situação (26/32). */
  tituloFaixa: estilo('700', 26, 32, { letterSpacing: -0.26 }),
  /** Seções e nome do rio (20/26). */
  tituloSecao: estilo('700', 20, 26),
  tituloCartao,
  numero,
  /** Vagas (26/30, tabular). */
  numeroMedio: estilo('700', 26, 30, tabular),
  /** Texto dentro de cartões (16/22; peso de 400 a 600). */
  corpoCartao: estilo('400', 16, 22),
  /** Rótulo dos botões (17/22). */
  botao: estilo('700', 17, 22),
  /** Rótulo do botão de 56 (18/22). */
  botaoGrande: estilo('700', 18, 22),
  apoio,
  /** Selo médio (15/20). */
  selo: estilo('700', 15, 20),
  /** Selo pequeno (13/16). */
  seloPequeno: estilo('700', 13, 16),
  /** Rótulo em maiúsculas, verde (13/16). */
  rotulo: estilo('800', 13, 16, { letterSpacing: 1, textTransform: 'uppercase', color: cores.primaria }),
  /** Barra inferior (13/16; ativa em 700). */
  aba: estilo('600', 13, 16),
  abaAtiva: estilo('700', 13, 16),
};

/** Sombra na cor do texto. No navegador vira boxShadow (o react-native-web não usa mais shadow*). */
function criarSombra(opacidade: number, desfoque: number, y: number, elevacao: number): ViewStyle {
  return (
    Platform.select<ViewStyle>({
      web: { boxShadow: `0px ${y}px ${desfoque}px rgba(20, 33, 43, ${opacidade})` },
      default: {
        shadowColor: cores.texto,
        shadowOpacity: opacidade,
        shadowRadius: desfoque,
        shadowOffset: { width: 0, height: y },
        elevation: elevacao,
      },
    }) ?? {}
  );
}

export const sombra = {
  /** Cartões sobre o fundo. */
  cartao: criarSombra(0.08, 12, 4, 2),
  /** Faixa Alerta novo. */
  flutuante: criarSombra(0.18, 24, 8, 8),
  /** Barra inferior (com borda de 1 no topo). */
  barra: criarSombra(0.06, 12, -2, 8),
} as const;

/** Cartão: superfície branca, borda de 1 px, raio 20, padding 16 e sombra. */
export const cartao: ViewStyle = {
  backgroundColor: cores.superficie,
  borderRadius: raio.cartao,
  borderWidth: 1,
  borderColor: cores.borda,
  padding: espaco.cartao,
  ...sombra.cartao,
};
