/** Estrutura comum das telas: rolagem, largura de celular no navegador e o rodapé de dados simulados. */
import type { ReactNode } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { cores, espaco, texto } from '@/tema';

interface Props {
  children: ReactNode;
  /** Puxar para atualizar (no celular). */
  aoAtualizar?: () => void;
  atualizando?: boolean;
  /** Texto extra no rodapé, ex.: "atualizado às 14:02:31". */
  rodape?: string;
}

export function Tela({ children, aoAtualizar, atualizando = false, rodape }: Props) {
  return (
    <ScrollView
      style={estilos.rolagem}
      contentContainerStyle={estilos.conteudo}
      refreshControl={aoAtualizar ? <RefreshControl refreshing={atualizando} onRefresh={aoAtualizar} /> : undefined}
    >
      <View style={estilos.coluna}>
        {children}
        <Rodape extra={rodape} />
      </View>
    </ScrollView>
  );
}

export function Rodape({ extra }: { extra?: string }) {
  return (
    <View style={estilos.rodape} accessibilityRole="text">
      <Text style={estilos.rodapeTexto}>Dados simulados para demonstração{extra ? ` · ${extra}` : ''}</Text>
      <Text style={estilos.rodapeTexto}>Em emergência real, ligue 199 (Defesa Civil) ou 193 (Bombeiros).</Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  rolagem: { flex: 1, backgroundColor: cores.fundo },
  conteudo: { flexGrow: 1, alignItems: 'center' },
  // No navegador de computador, o app fica com largura de celular.
  coluna: { width: '100%', maxWidth: 560, padding: espaco.lg, gap: espaco.md },
  rodape: { marginTop: espaco.lg, paddingTop: espaco.md, borderTopWidth: 1, borderTopColor: cores.borda, gap: 2 },
  rodapeTexto: { ...texto.suave, fontSize: 13, textAlign: 'center' },
});
