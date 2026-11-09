/** Escolha entre duas opções ("Meu bairro" | "Minha localização"), com alvo de toque grande. */
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ALVO_DE_TOQUE, cores, espaco, raio } from '@/tema';

interface Opcao<T extends string> {
  valor: T;
  rotulo: string;
}

interface Props<T extends string> {
  opcoes: Opcao<T>[];
  valor: T;
  aoMudar: (valor: T) => void;
  rotulo: string;
}

export function Alternador<T extends string>({ opcoes, valor, aoMudar, rotulo }: Props<T>) {
  return (
    <View style={estilos.caixa} accessibilityRole="radiogroup" accessibilityLabel={rotulo}>
      {opcoes.map((o) => {
        const ativa = o.valor === valor;
        return (
          <Pressable
            key={o.valor}
            onPress={() => aoMudar(o.valor)}
            accessibilityRole="radio"
            accessibilityLabel={o.rotulo}
            aria-checked={ativa}
            aria-selected={ativa}
            style={[estilos.opcao, ativa && estilos.ativa]}
          >
            <Text style={[estilos.texto, ativa && estilos.textoAtivo]}>{o.rotulo}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const estilos = StyleSheet.create({
  caixa: {
    flexDirection: 'row',
    backgroundColor: cores.superficie,
    borderRadius: raio.lg,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: 4,
    gap: 4,
  },
  opcao: {
    flex: 1,
    minHeight: ALVO_DE_TOQUE,
    borderRadius: raio.md,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: espaco.sm,
  },
  ativa: { backgroundColor: cores.primaria },
  texto: { fontSize: 16, fontWeight: '700', color: cores.primaria, textAlign: 'center' },
  textoAtivo: { color: '#FFFFFF' },
});
