/** Logotipo e ícones próprios do Abriga, desenhados em SVG (sem fonte de ícones nem marca de terceiros). */
import type { ColorValue } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';

import { cores } from '@/tema';

interface PropsIcone {
  cor?: ColorValue;
  tamanho?: number;
}

/** Telhado com uma gota: "um teto seguro na cheia". */
export function Logo({ cor = cores.primaria, tamanho = 32 }: PropsIcone) {
  return (
    <Svg
      width={tamanho}
      height={tamanho}
      viewBox="0 0 48 48"
      accessibilityElementsHidden
      importantForAccessibility="no"
    >
      <Path
        d="M5 23 L24 7 L43 23"
        stroke={cor}
        strokeWidth={4.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <Path d="M11 21 V41 H37 V21" stroke={cor} strokeWidth={4} strokeLinejoin="round" fill="none" />
      <Path d="M24 19 C24 19 17 27.5 17 31.5 A7 7 0 0 0 31 31.5 C31 27.5 24 19 24 19 Z" fill={cor} />
    </Svg>
  );
}

/** Aba "Agora": ondas do rio. */
export function IconeRio({ cor = cores.texto, tamanho = 24 }: PropsIcone) {
  return (
    <Svg width={tamanho} height={tamanho} viewBox="0 0 24 24">
      {[7, 12, 17].map((y) => (
        <Path
          key={y}
          d={`M3 ${y} C5 ${y - 2.2} 7 ${y - 2.2} 9 ${y} S13 ${y + 2.2} 15 ${y} S19 ${y - 2.2} 21 ${y}`}
          stroke={cor}
          strokeWidth={2}
          strokeLinecap="round"
          fill="none"
        />
      ))}
    </Svg>
  );
}

/** Aba "Abrigos": casa. */
export function IconeAbrigo({ cor = cores.texto, tamanho = 24 }: PropsIcone) {
  return (
    <Svg width={tamanho} height={tamanho} viewBox="0 0 24 24">
      <Path
        d="M3 11 L12 3.5 L21 11"
        stroke={cor}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <Path d="M5.5 9.5 V20 H18.5 V9.5" stroke={cor} strokeWidth={2} strokeLinejoin="round" fill="none" />
      <Path d="M10 20 V14.5 H14 V20" stroke={cor} strokeWidth={2} strokeLinejoin="round" fill="none" />
    </Svg>
  );
}

/** Aba "Ajustes": controles deslizantes. */
export function IconeAjustes({ cor = cores.texto, tamanho = 24 }: PropsIcone) {
  return (
    <Svg width={tamanho} height={tamanho} viewBox="0 0 24 24">
      <Path d="M4 7 H20 M4 17 H20" stroke={cor} strokeWidth={2} strokeLinecap="round" />
      <Circle cx={9} cy={7} r={2.6} fill={cores.superficie} stroke={cor} strokeWidth={2} />
      <Circle cx={15} cy={17} r={2.6} fill={cores.superficie} stroke={cor} strokeWidth={2} />
    </Svg>
  );
}
