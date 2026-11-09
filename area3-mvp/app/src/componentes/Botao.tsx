/** Botão grande e fácil de tocar (48 px ou mais), com rótulo de acessibilidade em português. */
import { Pressable, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';

import { ALVO_DE_TOQUE, cores, espaco, peso, raio, texto } from '@/tema';

import { Icone, type NomeDoIcone } from './Icones';

type Variante = 'principal' | 'secundario' | 'claro' | 'escuro';

interface Props {
  titulo: string;
  aoTocar: () => void;
  /**
   * principal: verde cheio; secundario: contorno verde sobre branco;
   * claro: branco com texto escuro (sobre a faixa de Alerta e Inundação);
   * escuro: escuro com texto branco (sobre a faixa amarela de Atenção).
   */
  variante?: Variante;
  /** 56 de altura (o padrão é 52). */
  grande?: boolean;
  /** 48 de altura e raio 14 (Trocar, Tentar de novo). */
  pequeno?: boolean;
  /** Ícone antes do texto (ex.: navegar) ou, com iconeNoFim, depois (ex.: seta). */
  icone?: NomeDoIcone;
  iconeNoFim?: boolean;
  dica?: string;
  estilo?: StyleProp<ViewStyle>;
}

const COR_DO_TEXTO: Record<Variante, string> = {
  principal: '#FFFFFF',
  secundario: cores.primaria,
  claro: cores.texto,
  escuro: '#FFFFFF',
};

export function Botao({
  titulo,
  aoTocar,
  variante = 'principal',
  grande,
  pequeno,
  icone,
  iconeNoFim,
  dica,
  estilo,
}: Props) {
  const cor = COR_DO_TEXTO[variante];
  const desenho = icone ? <Icone nome={icone} cor={cor} tamanho={pequeno ? 20 : 22} /> : null;
  return (
    <Pressable
      onPress={aoTocar}
      accessibilityRole="button"
      accessibilityLabel={titulo}
      accessibilityHint={dica}
      style={({ pressed }) => [
        estilos.base,
        grande ? estilos.grande : pequeno ? estilos.pequeno : null,
        estilos[variante],
        pressed && PRESSIONADO[variante],
        estilo,
      ]}
    >
      <View style={estilos.conteudo}>
        {iconeNoFim ? null : desenho}
        <Text
          style={[
            grande ? texto.botaoGrande : pequeno ? estilos.textoPequeno : texto.botao,
            estilos.texto,
            { color: cor },
          ]}
        >
          {titulo}
        </Text>
        {iconeNoFim ? desenho : null}
      </View>
    </Pressable>
  );
}

const PRESSIONADO = StyleSheet.create({
  // No toque, o verde escurece (sem sombra nem escala).
  principal: { backgroundColor: cores.primariaEscura },
  // Cinza-claro, não verde-claro: o texto verde mantém 4,5:1 também no toque.
  secundario: { backgroundColor: cores.neutroFundo },
  claro: { backgroundColor: cores.neutroFundo },
  escuro: { opacity: 0.85 },
});

const estilos = StyleSheet.create({
  base: {
    minHeight: 52,
    paddingHorizontal: espaco.lg,
    borderRadius: raio.botao,
    alignItems: 'center',
    justifyContent: 'center',
  },
  grande: { minHeight: 56 },
  pequeno: { minHeight: ALVO_DE_TOQUE, paddingHorizontal: 18, borderRadius: raio.controle },
  conteudo: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10 },
  principal: { backgroundColor: cores.primaria },
  secundario: { backgroundColor: cores.superficie, borderWidth: 2, borderColor: cores.primaria },
  claro: { backgroundColor: cores.superficie },
  escuro: { backgroundColor: cores.texto },
  texto: { textAlign: 'center', flexShrink: 1 },
  textoPequeno: { ...peso('700'), fontSize: 16, lineHeight: 20 },
});
