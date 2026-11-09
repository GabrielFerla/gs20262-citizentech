/**
 * Estrutura comum das telas: título, rolagem, largura de celular no navegador e o rodapé de dados
 * simulados. Nas telas fora das abas, a barra com 199 e 193 fica fixa embaixo.
 */
import type { ReactNode } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { cores, espaco, texto } from '@/tema';

import { BarraDeTelefones } from './BarraInferior';

interface Props {
  children: ReactNode;
  /** Título grande no topo da rolagem. */
  titulo?: string;
  /** Linha de apoio abaixo do título (ex.: a estação e a hora da leitura). */
  subtitulo?: string;
  /** Puxar para atualizar (no celular). */
  aoAtualizar?: () => void;
  atualizando?: boolean;
  /** Texto extra no rodapé, ex.: "atualizado às 14:02:31". */
  rodape?: string;
  /** Mostra a barra fixa com 199 e 193 (as telas das abas já têm a barra inferior). */
  telefones?: boolean;
}

export function Tela({ children, titulo, subtitulo, aoAtualizar, atualizando = false, rodape, telefones }: Props) {
  const rolagem = (
    <ScrollView
      style={estilos.rolagem}
      contentContainerStyle={estilos.conteudo}
      refreshControl={
        aoAtualizar ? (
          <RefreshControl refreshing={atualizando} onRefresh={aoAtualizar} tintColor={cores.primaria} />
        ) : undefined
      }
    >
      <View style={estilos.coluna}>
        {titulo ? <TituloDaTela titulo={titulo} subtitulo={subtitulo} /> : null}
        {children}
        <Rodape extra={rodape} />
      </View>
    </ScrollView>
  );

  if (!telefones) return rolagem;
  return (
    <View style={estilos.comBarra}>
      {rolagem}
      <BarraDeTelefones />
    </View>
  );
}

/** Título grande da tela (28/34) e a linha de apoio. Use direto quando o título depende dos dados. */
export function TituloDaTela({ titulo, subtitulo }: { titulo: string; subtitulo?: string }) {
  return (
    <View style={estilos.titulo}>
      <Text style={texto.tituloTela} accessibilityRole="header">
        {titulo}
      </Text>
      {subtitulo ? <Text style={texto.apoio}>{subtitulo}</Text> : null}
    </View>
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
  comBarra: { flex: 1, backgroundColor: cores.fundo },
  rolagem: { flex: 1, backgroundColor: cores.fundo },
  conteudo: { flexGrow: 1, alignItems: 'center' },
  // No navegador de computador, o app fica com largura de celular.
  coluna: {
    width: '100%',
    maxWidth: 560,
    paddingHorizontal: espaco.margem,
    paddingTop: espaco.sm,
    paddingBottom: espaco.xl,
    gap: espaco.entreCartoes,
  },
  titulo: { gap: 2, paddingBottom: espaco.xs },
  rodape: {
    marginTop: espaco.entreSecoes - espaco.entreCartoes,
    paddingTop: espaco.md,
    borderTopWidth: 1,
    borderTopColor: cores.borda,
    gap: 2,
  },
  rodapeTexto: { ...texto.apoio, fontSize: 13, lineHeight: 18, textAlign: 'center' },
});
