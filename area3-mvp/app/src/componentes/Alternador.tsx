/** Escolha entre duas opções ("Meu bairro" | "Minha localização"), com alvo de toque grande. */
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ALVO_DE_TOQUE, cores, espaco, peso, raio } from '@/tema';

import { Icone, type NomeDoIcone } from './Icones';

interface Opcao<T extends string> {
  valor: T;
  rotulo: string;
  icone?: NomeDoIcone;
}

interface Props<T extends string> {
  opcoes: Opcao<T>[];
  valor: T;
  aoMudar: (valor: T) => void;
  rotulo: string;
}

export function Alternador<T extends string>({ opcoes, valor, aoMudar, rotulo }: Props<T>) {
  return (
    <View style={estilos.trilho} accessibilityRole="radiogroup" accessibilityLabel={rotulo}>
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
            style={({ pressed }) => [
              estilos.opcao,
              ativa ? estilos.ativa : pressed && { backgroundColor: cores.borda },
            ]}
          >
            {o.icone ? <Icone nome={o.icone} cor={ativa ? '#FFFFFF' : cores.textoSuave} tamanho={18} /> : null}
            <Text style={[estilos.texto, ativa && estilos.textoAtivo]}>{o.rotulo}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const estilos = StyleSheet.create({
  trilho: {
    flexDirection: 'row',
    backgroundColor: cores.neutroFundo,
    borderRadius: raio.botao,
    padding: espaco.xs,
    gap: espaco.xs,
  },
  opcao: {
    flex: 1,
    minWidth: 0,
    minHeight: ALVO_DE_TOQUE,
    flexDirection: 'row',
    borderRadius: raio.md,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 5,
    paddingHorizontal: 2,
  },
  ativa: { backgroundColor: cores.primaria },
  // 15 px: "Minha localização" com o ícone cabe numa linha em 390 de largura (em tela menor, quebra).
  texto: { ...peso('700'), fontSize: 15, lineHeight: 20, color: cores.texto, flexShrink: 1, textAlign: 'center' },
  textoAtivo: { color: '#FFFFFF' },
});
