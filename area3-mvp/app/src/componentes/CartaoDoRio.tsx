/** Cartão de um rio na tela Agora: nível agora → em 6 h, situação, tendência e avisos. Abre a tela Rio. */
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { EstacaoPrevisao } from '@/api/tipos';
import { metros } from '@/logica/formato';
import { distanciaDaCota, piorDoRio, textoDaTendencia } from '@/logica/situacao';
import { cores, espaco, raio, situacoes, texto } from '@/tema';

import { SeloDaSituacao, SelosDoRio } from './Selo';

function descricaoParaLeitorDeTela(rio: EstacaoPrevisao): string {
  const agora = situacoes[rio.situacao_atual].nome;
  const depois = situacoes[rio.situacao_prevista].nome;
  return (
    `${rio.corpo_hidrico}: agora ${metros(rio.nivel_atual_m)}, ${agora}. ` +
    `Em 6 horas ${metros(rio.nivel_previsto_6h_m)}, ${depois}. ` +
    `${rio.alerta_antecipado ? 'Alerta antecipado. ' : ''}Toque para ver o gráfico.`
  );
}

export function CartaoDoRio({ rio }: { rio: EstacaoPrevisao }) {
  const router = useRouter();
  const pior = situacoes[piorDoRio(rio)];
  const seta = { subindo: '↑', estavel: '→', descendo: '↓' }[rio.tendencia];

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={descricaoParaLeitorDeTela(rio)}
      onPress={() => router.push({ pathname: '/rio/[id]', params: { id: rio.estacao_id } })}
      style={({ pressed }) => [estilos.cartao, { borderLeftColor: pior.forte }, pressed && { opacity: 0.9 }]}
    >
      <View>
        <Text style={texto.subtitulo}>{rio.corpo_hidrico}</Text>
        <Text style={texto.suave}>{rio.estacao}</Text>
      </View>

      <View style={estilos.niveis}>
        <View style={estilos.coluna}>
          <Text style={texto.suave}>Agora</Text>
          <Text style={estilos.nivel}>{metros(rio.nivel_atual_m)}</Text>
          <SeloDaSituacao situacao={rio.situacao_atual} />
        </View>
        <Text style={estilos.seta} accessibilityElementsHidden importantForAccessibility="no">
          {seta}
        </Text>
        <View style={estilos.coluna}>
          <Text style={texto.suave}>Em 6 horas</Text>
          <Text style={estilos.nivel}>{metros(rio.nivel_previsto_6h_m)}</Text>
          <SeloDaSituacao situacao={rio.situacao_prevista} />
        </View>
      </View>

      <Text style={texto.suave}>
        {textoDaTendencia(rio)[0].toUpperCase() + textoDaTendencia(rio).slice(1)} · {distanciaDaCota(rio)}
      </Text>
      <SelosDoRio rio={rio} />
      <Text style={estilos.mais}>Ver gráfico ›</Text>
    </Pressable>
  );
}

const estilos = StyleSheet.create({
  cartao: {
    backgroundColor: cores.superficie,
    borderRadius: raio.lg,
    padding: espaco.lg,
    gap: espaco.md,
    borderWidth: 1,
    borderColor: cores.borda,
    borderLeftWidth: 6,
  },
  niveis: { flexDirection: 'row', alignItems: 'center', gap: espaco.md },
  coluna: { flex: 1, gap: 4 },
  nivel: { fontSize: 26, fontWeight: '800', color: cores.texto },
  seta: { fontSize: 28, color: cores.textoSuave, fontWeight: '700' },
  mais: { fontSize: 15, fontWeight: '700', color: cores.primaria },
});
