/** Botão grande e fácil de tocar (48 px ou mais), com rótulo de acessibilidade em português. */
import { Pressable, StyleSheet, Text, type StyleProp, type ViewStyle } from 'react-native';

import { ALVO_DE_TOQUE, cores, espaco, raio } from '@/tema';

interface Props {
  titulo: string;
  aoTocar: () => void;
  /** principal: fundo cheio; secundario: contorno; claro: para usar sobre fundo colorido. */
  variante?: 'principal' | 'secundario' | 'claro';
  /** Cor do texto no botão claro (a cor da faixa em que ele está). */
  corDoTexto?: string;
  grande?: boolean;
  dica?: string;
  estilo?: StyleProp<ViewStyle>;
}

export function Botao({ titulo, aoTocar, variante = 'principal', corDoTexto, grande, dica, estilo }: Props) {
  return (
    <Pressable
      onPress={aoTocar}
      accessibilityRole="button"
      accessibilityLabel={titulo}
      accessibilityHint={dica}
      style={({ pressed }) => [
        estilos.base,
        grande && estilos.grande,
        estilos[variante],
        pressed && estilos.pressionado,
        estilo,
      ]}
    >
      <Text
        style={[
          estilos.texto,
          grande && estilos.textoGrande,
          variante === 'principal' ? { color: '#FFFFFF' } : { color: corDoTexto ?? cores.primaria },
        ]}
      >
        {titulo}
      </Text>
    </Pressable>
  );
}

const estilos = StyleSheet.create({
  base: {
    minHeight: ALVO_DE_TOQUE,
    paddingHorizontal: espaco.lg,
    borderRadius: raio.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  grande: { minHeight: 56, borderRadius: raio.lg },
  principal: { backgroundColor: cores.primaria },
  secundario: { backgroundColor: cores.superficie, borderWidth: 2, borderColor: cores.primaria },
  claro: { backgroundColor: '#FFFFFF' },
  pressionado: { opacity: 0.85 },
  texto: { fontSize: 16, fontWeight: '700', textAlign: 'center' },
  textoGrande: { fontSize: 18, fontWeight: '800' },
});
