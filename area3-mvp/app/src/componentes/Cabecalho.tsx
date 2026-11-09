/**
 * Cabeçalho claro de todas as telas: a marca (ou "Voltar", nas telas de detalhe) e o selo
 * "Dados simulados", sempre à vista. Os títulos ficam no topo da rolagem (veja Tela).
 */
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ALVO_DE_TOQUE, cores, espaco, peso, raio, texto } from '@/tema';

import { Icone, Logo } from './Icones';
import { Selo } from './Selo';

export function Cabecalho({ aoVoltar }: { aoVoltar?: () => void }) {
  const { top } = useSafeAreaInsets();
  return (
    <View style={[estilos.cabecalho, { paddingTop: top }]}>
      <View style={estilos.linha}>
        {aoVoltar ? (
          <Pressable
            onPress={aoVoltar}
            accessibilityRole="button"
            accessibilityLabel="Voltar"
            style={({ pressed }) => [estilos.voltar, pressed && { backgroundColor: cores.primariaClara }]}
          >
            <Icone nome="chevronEsquerda" cor={cores.primaria} tamanho={26} />
            <Text style={[texto.botao, { color: cores.primaria }]}>Voltar</Text>
          </Pressable>
        ) : (
          <View style={estilos.marca} accessibilityRole="header" accessibilityLabel="Abriga">
            <Logo tamanho={32} />
            <Text style={estilos.marcaTexto}>Abriga</Text>
          </View>
        )}
        <Selo tipo="simulado" />
      </View>
    </View>
  );
}

const estilos = StyleSheet.create({
  cabecalho: { backgroundColor: cores.fundo },
  linha: {
    height: 56,
    width: '100%',
    maxWidth: 560,
    alignSelf: 'center',
    paddingHorizontal: espaco.margem,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: espaco.md,
  },
  marca: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  marcaTexto: { ...peso('800'), fontSize: 21, lineHeight: 26, letterSpacing: -0.42, color: cores.texto },
  voltar: {
    minHeight: ALVO_DE_TOQUE,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    paddingLeft: espaco.xs,
    paddingRight: 14,
    marginLeft: -espaco.sm,
    borderRadius: raio.controle,
  },
});
