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
import { ALVO_DE_TOQUE, cores, espaco, raio, texto } from '@/tema';

import { EstadoDaConsulta } from './EstadoDaConsulta';
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
        style={({ pressed }) => [estilos.campo, pressed && { opacity: 0.85 }]}
      >
        <Text style={texto.suave}>De qual bairro você sai</Text>
        <View style={estilos.linhaDoCampo}>
          <Text style={[estilos.valor, !bairroNome && { color: cores.primaria }]}>
            {bairroNome ?? 'Escolher bairro'}
          </Text>
          <Text style={estilos.trocar}>{bairroNome ? 'Trocar' : '›'}</Text>
        </View>
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
          <Pressable onPress={aoFechar} accessibilityRole="button" style={estilos.fechar}>
            <Text style={estilos.trocar}>Fechar</Text>
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
                      {item.zona_risco === 'alta' ? (
                        <Selo texto="Área de risco" fundo={cores.avisoFundo} cor={cores.aviso} />
                      ) : null}
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
    backgroundColor: cores.superficie,
    borderRadius: raio.lg,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espaco.lg,
    gap: 2,
    minHeight: ALVO_DE_TOQUE,
  },
  linhaDoCampo: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: espaco.sm },
  valor: { fontSize: 20, fontWeight: '700', color: cores.texto, flexShrink: 1 },
  trocar: { fontSize: 16, fontWeight: '700', color: cores.primaria },
  modal: { flex: 1, backgroundColor: cores.fundo, padding: espaco.lg, gap: espaco.md },
  topo: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  fechar: { minHeight: ALVO_DE_TOQUE, minWidth: ALVO_DE_TOQUE, justifyContent: 'center', alignItems: 'flex-end' },
  busca: {
    minHeight: ALVO_DE_TOQUE,
    backgroundColor: cores.superficie,
    borderRadius: raio.md,
    borderWidth: 1,
    borderColor: cores.borda,
    paddingHorizontal: espaco.md,
    fontSize: 17,
    color: cores.texto,
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
