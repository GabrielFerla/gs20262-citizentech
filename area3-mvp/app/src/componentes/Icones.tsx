/**
 * Logotipo e ícones próprios do Abriga, desenhados em SVG (sem fonte de ícones nem marca de terceiros).
 * Ícones de traço numa grade de 24, traço de 2,2 a 2,4 e pontas arredondadas. São decorativos:
 * o texto ao lado (ou o rótulo de acessibilidade do botão) diz o que eles querem dizer.
 */
import { Platform, type ColorValue } from 'react-native';
import Svg, { Circle, G, Path, Rect } from 'react-native-svg';

import { cores } from '@/tema';

/** Esconde o desenho do leitor de tela (no navegador, o <svg> só entende aria-hidden). */
export const DECORATIVO =
  Platform.OS === 'web'
    ? ({ 'aria-hidden': true } as const)
    : ({ accessibilityElementsHidden: true, importantForAccessibility: 'no-hide-descendants' } as const);

interface PropsIcone {
  cor?: ColorValue;
  tamanho?: number;
}

type Forma = { d: string } | { cx: number; cy: number; r: number; tracejado?: string };

interface Desenho {
  traco: number;
  formas: Forma[];
}

const CIRCULO: Forma = { cx: 12, cy: 12, r: 9 };
const SETA_DIREITA = ['M5 12h14', 'M13 6l6 6-6 6'];

function linhas(traco: number, ...formas: (string | Forma)[]): Desenho {
  return { traco, formas: formas.map((f) => (typeof f === 'string' ? { d: f } : f)) };
}

const DESENHOS = {
  // Situações (sempre com a palavra ao lado).
  check: linhas(2.4, CIRCULO, 'M8 12.4l2.7 2.7 5.5-5.5'),
  circuloExclamacao: linhas(2.4, CIRCULO, 'M12 7.6v5.2', 'M12 16.4v.1'),
  trianguloExclamacao: linhas(
    2.4,
    'M10.3 4.2L2.6 17.5a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0z',
    'M12 9.5v4',
    'M12 16.9v.1',
  ),
  ondas: linhas(
    2.4,
    'M3 7.5q2.25-2.5 4.5 0t4.5 0 4.5 0 4.5 0',
    'M3 12.5q2.25-2.5 4.5 0t4.5 0 4.5 0 4.5 0',
    'M3 17.5q2.25-2.5 4.5 0t4.5 0 4.5 0 4.5 0',
  ),
  // Selos sobre o dado e o abrigo.
  tendencia: linhas(2.4, 'M3 17l6-6 4 4 8-8', 'M15 7h6v6'),
  relogio: linhas(2.4, CIRCULO, 'M12 7.5V12l3 2'),
  tracejado: linhas(2.4, { cx: 12, cy: 12, r: 9, tracejado: '3.2 2.8' }, 'M12 8v4.6', 'M12 16v.1'),
  frasco: linhas(
    2.2,
    'M9 3h6',
    'M10 3v6.2l-5.1 8.9a1.9 1.9 0 0 0 1.6 2.9h11a1.9 1.9 0 0 0 1.6-2.9L14 9.2V3',
    'M7.4 15h9.2',
  ),
  pessoas: linhas(
    2.2,
    { cx: 9, cy: 8, r: 3.5 },
    'M2.5 20a6.5 6.5 0 0 1 13 0',
    'M16 4.7a3.5 3.5 0 0 1 0 6.6',
    'M18.5 14.4a6.5 6.5 0 0 1 3 5.6',
  ),
  proibido: linhas(2.4, CIRCULO, 'M5.7 5.7l12.6 12.6'),
  // Tendência do rio.
  sobe: linhas(2.4, 'M7 17L17 7', 'M9 7h8v8'),
  estavel: linhas(2.4, ...SETA_DIREITA),
  desce: linhas(2.4, 'M7 7l10 10', 'M17 9v8H9'),
  // Navegação e ações.
  setaDireita: linhas(2.4, ...SETA_DIREITA),
  chevronDireita: linhas(2.4, 'M9 5l7 7-7 7'),
  chevronEsquerda: linhas(2.4, 'M15 5l-7 7 7 7'),
  fechar: linhas(2.4, 'M6 6l12 12', 'M18 6L6 18'),
  navegar: linhas(2.4, 'M3 11l18-8-8 18-2-8z'),
  atualizar: linhas(2.4, 'M20 11a8 8 0 1 0-2.3 5.7', 'M20 4.5V11h-6.5'),
  menos: linhas(2.6, 'M5 12h14'),
  mais: linhas(2.6, 'M12 5v14', 'M5 12h14'),
  confirmar: linhas(2.6, 'M5 12.5l4.5 4.5L19 7.5'),
  // Lugar, caminho e privacidade.
  alfinete: linhas(2.2, 'M12 21s-6.5-5.8-6.5-11a6.5 6.5 0 0 1 13 0c0 5.2-6.5 11-6.5 11z', { cx: 12, cy: 10, r: 2.4 }),
  mira: linhas(2.4, { cx: 12, cy: 12, r: 7 }, { cx: 12, cy: 12, r: 2.5 }, 'M12 2v3', 'M12 19v3', 'M2 12h3', 'M19 12h3'),
  caminho: linhas(
    2.2,
    { cx: 6, cy: 19, r: 2.5 },
    { cx: 18, cy: 5, r: 2.5 },
    'M8.5 19H15a3.5 3.5 0 0 0 0-7H9a3.5 3.5 0 0 1 0-7h6.5',
  ),
  cadeado: linhas(
    2.2,
    'M7.5 11h9a2.5 2.5 0 0 1 2.5 2.5v5a2.5 2.5 0 0 1-2.5 2.5h-9a2.5 2.5 0 0 1-2.5-2.5v-5a2.5 2.5 0 0 1 2.5-2.5z',
    'M8 11V8a4 4 0 0 1 8 0v3',
  ),
  sino: linhas(2.2, 'M6 16v-5a6 6 0 0 1 12 0v5l1.5 2h-15z', 'M10 20.5a2 2 0 0 0 4 0'),
  telefone: linhas(
    2.2,
    'M6.6 3.5h2.6c.4 0 .8.3.9.7l.9 3.4c.1.4 0 .8-.3 1.1L9 10.3a12.5 12.5 0 0 0 4.7 4.7l1.6-1.7c.3-.3.7-.4 1.1-.3l3.4.9c.4.1.7.5.7.9v2.6c0 1.2-1 2.1-2.2 2A16.3 16.3 0 0 1 4.6 5.7c-.1-1.2.8-2.2 2-2.2z',
  ),
  semConexao: linhas(2.2, 'M7 18.5a4.5 4.5 0 0 1-.9-8.9 6 6 0 0 1 11.5-1.4A4.5 4.5 0 0 1 17.5 18.5z', 'M3.5 3.5l17 17'),
  // Abas.
  abaAgora: linhas(2.2, 'M3 12h3.6l2.6-6.5 4.6 13 2.6-6.5H21'),
  abaAbrigos: linhas(2.2, 'M3.5 10.6L12 3.6l8.5 7', 'M5.6 9.2V20h12.8V9.2', 'M10 20v-5.2h4V20'),
  abaAjustes: linhas(2.2, 'M4 7h9', 'M17.5 7H20', { cx: 15.2, cy: 7, r: 2.2 }, 'M4 17h2.5', 'M11 17h9', {
    cx: 8.8,
    cy: 17,
    r: 2.2,
  }),
} satisfies Record<string, Desenho>;

export type NomeDoIcone = keyof typeof DESENHOS;

/** Um ícone de traço. Decorativo: fica escondido do leitor de tela. */
export function Icone({ nome, cor = cores.texto, tamanho = 24 }: PropsIcone & { nome: NomeDoIcone }) {
  return (
    <Svg width={tamanho} height={tamanho} viewBox="0 0 24 24" fill="none" {...DECORATIVO}>
      <FormasDoIcone nome={nome} cor={cor} x={0} y={0} tamanho={24} />
    </Svg>
  );
}

/** O mesmo desenho, para usar dentro de outro SVG (ex.: no gráfico), no ponto (x, y). */
export function FormasDoIcone({
  nome,
  cor,
  x,
  y,
  tamanho,
}: {
  nome: NomeDoIcone;
  cor: ColorValue;
  x: number;
  y: number;
  tamanho: number;
}) {
  const { traco, formas } = DESENHOS[nome];
  // Na grade de 24, sem transformação: o ícone sozinho fica mais simples para o SVG desenhar.
  const transform = tamanho === 24 && x === 0 && y === 0 ? undefined : `translate(${x} ${y}) scale(${tamanho / 24})`;
  return (
    <G transform={transform}>
      {formas.map((f, i) =>
        'd' in f ? (
          <Path
            key={i}
            d={f.d}
            stroke={cor}
            strokeWidth={traco}
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />
        ) : (
          <Circle
            key={i}
            cx={f.cx}
            cy={f.cy}
            r={f.r}
            stroke={cor}
            strokeWidth={traco}
            strokeDasharray={f.tracejado}
            fill="none"
          />
        ),
      )}
    </G>
  );
}

/**
 * Logotipo: "um telhado acima da água". Telhado branco sobre uma onda verde-clara, em fundo verde
 * (o mesmo desenho do ícone do app, gerado por scripts/gerar_icones.py).
 */
export function Logo({ tamanho = 32 }: { tamanho?: number }) {
  return (
    <Svg width={tamanho} height={tamanho} viewBox="0 0 64 64" {...DECORATIVO}>
      <Rect width={64} height={64} rx={16} fill={cores.primaria} />
      <Path
        d="M14 34L32 17l18 17"
        stroke="#FFFFFF"
        strokeWidth={6}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <Path
        d="M12 46q5-5 10 0t10 0 10 0 10 0"
        stroke={cores.primariaSobreEscuro}
        strokeWidth={5}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </Svg>
  );
}
