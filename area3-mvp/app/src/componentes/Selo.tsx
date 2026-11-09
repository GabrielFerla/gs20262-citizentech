/** Selos curtos: situação do rio (cor + palavra), alerta antecipado e avisos sobre o dado. */
import { StyleSheet, Text, View } from 'react-native';

import type { EstacaoPrevisao, Situacao } from '@/api/tipos';
import { cores, espaco, raio, situacoes } from '@/tema';

interface Props {
  texto: string;
  fundo: string;
  cor: string;
  borda?: string;
}

export function Selo({ texto, fundo, cor, borda }: Props) {
  return (
    <View style={[estilos.selo, { backgroundColor: fundo, borderColor: borda ?? fundo }]}>
      <Text style={[estilos.texto, { color: cor }]}>{texto}</Text>
    </View>
  );
}

export function SeloDaSituacao({ situacao }: { situacao: Situacao }) {
  const c = situacoes[situacao];
  return <Selo texto={c.nome} fundo={c.fundo} cor={c.texto} borda={c.forte} />;
}

/** Os selos que avisam algo sobre o rio: alerta antecipado, leitura atrasada, dados incompletos. */
export function SelosDoRio({ rio }: { rio: EstacaoPrevisao }) {
  const prevista = situacoes[rio.situacao_prevista];
  return (
    <View style={estilos.linha}>
      {rio.alerta_antecipado ? (
        <Selo
          texto={`Alerta antecipado: ${prevista.nome.toLowerCase()} em até 6 h`}
          fundo={prevista.forte}
          cor={prevista.sobreForte}
        />
      ) : null}
      {rio.leitura_velha ? (
        <Selo texto="Leitura atrasada: a previsão pode não valer" fundo={cores.avisoFundo} cor={cores.aviso} />
      ) : null}
      {rio.dados_incompletos ? (
        <Selo texto="Dados incompletos: previsão igual ao nível de agora" fundo={cores.avisoFundo} cor={cores.aviso} />
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  linha: { flexDirection: 'row', flexWrap: 'wrap', gap: espaco.xs },
  selo: {
    alignSelf: 'flex-start',
    borderRadius: raio.pilula,
    borderWidth: 1,
    paddingHorizontal: espaco.sm + 2,
    paddingVertical: 3,
  },
  texto: { fontSize: 13, fontWeight: '700' },
});
