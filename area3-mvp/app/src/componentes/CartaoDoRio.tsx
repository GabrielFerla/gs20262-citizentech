/** Cartão de um rio na tela Agora: nível agora → em 6 h, situação, tendência e avisos. Abre a tela Rio. */
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { EstacaoPrevisao, Situacao } from '@/api/tipos';
import { metros } from '@/logica/formato';
import { distanciaDaCota, textoDaTendencia } from '@/logica/situacao';
import { cartao, cores, espaco, peso, raio, situacoes, texto } from '@/tema';

import { Icone } from './Icones';
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

/** "3,68 m" com o "m" menor e mais claro (o texto lido continua "3,68 m"). */
export function Nivel({ valor }: { valor: number }) {
  const [numero, unidade] = metros(valor).split(' ');
  return (
    <Text style={texto.numero}>
      {numero}
      <Text style={estilos.unidade}> {unidade}</Text>
    </Text>
  );
}

/** Uma coluna "Agora" ou "Em 6 horas": rótulo verde, nível e selo da situação. */
export function ColunaDoNivel({ rotulo, valor, situacao }: { rotulo: string; valor: number; situacao: Situacao }) {
  return (
    <View style={estilos.coluna}>
      <Text style={texto.rotulo}>{rotulo}</Text>
      <Nivel valor={valor} />
      <SeloDaSituacao situacao={situacao} />
    </View>
  );
}

/** A seta da tendência num círculo, entre as duas colunas. */
export function SetaDaTendencia({ tendencia }: { tendencia: EstacaoPrevisao['tendencia'] }) {
  const nome = ({ subindo: 'sobe', estavel: 'estavel', descendo: 'desce' } as const)[tendencia];
  return (
    <View style={estilos.meio}>
      <View style={estilos.seta}>
        <Icone nome={nome} cor={cores.texto} tamanho={22} />
      </View>
    </View>
  );
}

export function CartaoDoRio({ rio }: { rio: EstacaoPrevisao }) {
  const router = useRouter();
  const tendencia = textoDaTendencia(rio);

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={descricaoParaLeitorDeTela(rio)}
      onPress={() => router.push({ pathname: '/rio/[id]', params: { id: rio.estacao_id } })}
      style={({ pressed }) => [estilos.cartao, pressed && { backgroundColor: cores.fundo }]}
    >
      <View style={estilos.corpo}>
        <View style={estilos.cabeca}>
          <View style={estilos.nomeESelos}>
            <Text style={[texto.tituloSecao, estilos.nome]}>{rio.corpo_hidrico}</Text>
            <SelosDoRio rio={rio} />
          </View>
          <Text style={texto.apoio}>{rio.estacao}</Text>
        </View>

        <View style={estilos.niveis}>
          <ColunaDoNivel rotulo="Agora" valor={rio.nivel_atual_m} situacao={rio.situacao_atual} />
          <SetaDaTendencia tendencia={rio.tendencia} />
          <ColunaDoNivel rotulo="Em 6 horas" valor={rio.nivel_previsto_6h_m} situacao={rio.situacao_prevista} />
        </View>

        <Text style={estilos.falta}>
          {tendencia[0].toUpperCase() + tendencia.slice(1)} · {distanciaDaCota(rio)}
        </Text>
      </View>
      <View style={estilos.rodape}>
        <Text style={[texto.botao, { color: cores.primaria }]}>Ver gráfico</Text>
        <Icone nome="chevronDireita" cor={cores.primaria} tamanho={22} />
      </View>
    </Pressable>
  );
}

const estilos = StyleSheet.create({
  cartao: { ...cartao, padding: 0, overflow: 'hidden' },
  corpo: { gap: espaco.lg, paddingHorizontal: espaco.cartao, paddingTop: espaco.cartao, paddingBottom: 14 },
  cabeca: { gap: 2 },
  nomeESelos: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: espaco.sm,
  },
  nome: { flexShrink: 1 },
  niveis: { flexDirection: 'row', alignItems: 'flex-start', gap: 6 },
  coluna: { flex: 1, minWidth: 0, alignItems: 'flex-start', gap: 6 },
  unidade: { ...peso('600'), fontSize: 18, lineHeight: 22, letterSpacing: 0, color: cores.textoSuave },
  meio: { width: 52, alignItems: 'center', paddingTop: 20 },
  seta: {
    width: 40,
    height: 40,
    borderRadius: raio.selo,
    backgroundColor: cores.neutroFundo,
    alignItems: 'center',
    justifyContent: 'center',
  },
  falta: { ...texto.corpoCartao, ...peso('600') },
  rodape: {
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: espaco.cartao,
    borderTopWidth: 1,
    borderTopColor: cores.borda,
  },
});
