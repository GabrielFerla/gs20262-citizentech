/**
 * Campo "De qual bairro você sai": abre uma lista dos 94 bairros (GET /bairros) com busca sem acento.
 * O bairro escolhido fica guardado só neste aparelho.
 */
import { useState } from 'react';
import { FlatList, Modal, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useBairros } from '@/api/consultas';
import type { Bairro } from '@/api/tipos';
import { filtrarBairros } from '@/logica/texto';
import { ALVO_DE_TOQUE, cores, espaco, peso, raio, texto } from '@/tema';

import { EstadoDaConsulta } from './EstadoDaConsulta';
import { Icone } from './Icones';
import { Selo } from './Selo';

interface Props {
  bairroNome: string | null;
  aoEscolher: (bairro: Bairro) => void;
}

export function SeletorDeBairro({ bairroNome, aoEscolher }: Props) {
  const [aberto, setAberto] = useState(false);

  return (
    <>
      <Pressable
        onPress={() => setAberto(true)}
        accessibilityRole="button"
        accessibilityLabel={bairroNome ? `Bairro: ${bairroNome}. Toque para trocar` : 'Escolher bairro'}
        style={estilos.campo}
      >
        {({ pressed }) => (
          <>
            <Icone nome="alfinete" cor={cores.primaria} tamanho={22} />
            <View style={estilos.textos}>
              <Text style={estilos.rotulo}>De qual bairro você sai</Text>
              <Text style={[estilos.valor, !bairroNome && { color: cores.primaria }]}>
                {bairroNome ?? 'Escolher bairro'}
              </Text>
            </View>
            {/* "Trocar" tem cara de botão, mas o toque vale para a linha inteira. */}
            {bairroNome ? (
              <View style={[estilos.trocar, pressed && { backgroundColor: cores.neutroFundo }]}>
                <Text style={estilos.trocarTexto}>Trocar</Text>
              </View>
            ) : (
              <Icone nome="chevronDireita" cor={cores.primaria} tamanho={24} />
            )}
          </>
        )}
      </Pressable>
      {aberto ? (
        <ListaDeBairros
          aoFechar={() => setAberto(false)}
          aoEscolher={(b) => {
            aoEscolher(b);
            setAberto(false);
          }}
        />
      ) : null}
    </>
  );
}

function ListaDeBairros({ aoFechar, aoEscolher }: { aoFechar: () => void; aoEscolher: (b: Bairro) => void }) {
  const bairros = useBairros();
  const [busca, setBusca] = useState('');

  return (
    <Modal visible animationType="slide" onRequestClose={aoFechar}>
      <SafeAreaView style={estilos.modal}>
        <View style={estilos.topo}>
          <Text style={texto.titulo} accessibilityRole="header">
            Escolha seu bairro
          </Text>
          <Pressable
            onPress={aoFechar}
            accessibilityRole="button"
            style={({ pressed }) => [estilos.fechar, pressed && { backgroundColor: cores.neutroFundo }]}
          >
            <Text style={estilos.trocarTexto}>Fechar</Text>
          </Pressable>
        </View>
        <TextInput
          value={busca}
          onChangeText={setBusca}
          placeholder="Buscar bairro (ex.: Navegantes)"
          placeholderTextColor={cores.textoSuave}
          accessibilityLabel="Buscar bairro"
          autoCorrect={false}
          autoFocus
          style={estilos.busca}
        />
        <View style={estilos.lista}>
          <EstadoDaConsulta consulta={bairros} carregando="Carregando os bairros…">
            {(todos) => {
              const filtrados = filtrarBairros(todos, busca);
              return (
                <FlatList
                  data={filtrados}
                  keyExtractor={(b) => b.bairro_id}
                  keyboardShouldPersistTaps="handled"
                  ListEmptyComponent={<Text style={texto.corpo}>Nenhum bairro com “{busca}”.</Text>}
                  renderItem={({ item }) => (
                    <Pressable
                      onPress={() => aoEscolher(item)}
                      accessibilityRole="button"
                      accessibilityLabel={`${item.bairro}${item.zona_risco === 'alta' ? ', área de risco de cheia' : ''}`}
                      style={({ pressed }) => [estilos.item, pressed && { backgroundColor: cores.primariaClara }]}
                    >
                      <Text style={texto.corpo}>{item.bairro}</Text>
                      {item.zona_risco === 'alta' ? <Selo tipo="risco" tamanho="p" texto="Área de risco" /> : null}
                    </Pressable>
                  )}
                />
              );
            }}
          </EstadoDaConsulta>
        </View>
      </SafeAreaView>
    </Modal>
  );
}

const estilos = StyleSheet.create({
  campo: {
    minHeight: ALVO_DE_TOQUE,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  textos: { flex: 1, minWidth: 0 },
  rotulo: { ...peso('600'), fontSize: 14, lineHeight: 18, color: cores.textoSuave },
  valor: { ...texto.tituloCartao, flexShrink: 1 },
  trocar: {
    minHeight: ALVO_DE_TOQUE,
    paddingHorizontal: 18,
    justifyContent: 'center',
    borderRadius: raio.controle,
    borderWidth: 2,
    borderColor: cores.primaria,
    backgroundColor: cores.superficie,
  },
  trocarTexto: { ...peso('700'), fontSize: 16, lineHeight: 20, color: cores.primaria },
  modal: { flex: 1, backgroundColor: cores.fundo, padding: espaco.margem, gap: espaco.md },
  topo: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  fechar: {
    minHeight: ALVO_DE_TOQUE,
    minWidth: ALVO_DE_TOQUE,
    paddingHorizontal: espaco.md,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: raio.controle,
  },
  busca: {
    ...texto.corpo,
    minHeight: ALVO_DE_TOQUE,
    backgroundColor: cores.superficie,
    borderRadius: raio.controle,
    borderWidth: 1,
    borderColor: cores.bordaControle,
    paddingHorizontal: espaco.md,
  },
  lista: { flex: 1 },
  item: {
    minHeight: ALVO_DE_TOQUE + 4,
    paddingHorizontal: espaco.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottomWidth: 1,
    borderBottomColor: cores.borda,
    gap: espaco.sm,
  },
});
