/** Rio: nível agora e em 6 h, gráfico com as cotas e como a previsão é feita. */
import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { usePrevisaoDoRio } from '@/api/consultas';
import { Botao } from '@/componentes/Botao';
import { AvisoDeErro, EstadoDaConsulta } from '@/componentes/EstadoDaConsulta';
import { GraficoDoRio } from '@/componentes/GraficoDoRio';
import { SeloDaSituacao, SelosDoRio } from '@/componentes/Selo';
import { Tela } from '@/componentes/Tela';
import { useLeiturasDoRio } from '@/estado/historico';
import { horaCurta, metros } from '@/logica/formato';
import { distanciaDaCota, explicacaoDoModelo, pedeParaSair, piorDoRio, textoDaTendencia } from '@/logica/situacao';
import { cores, espaco, raio, situacoes, texto } from '@/tema';

function Numero({ rotulo, valor, situacao }: { rotulo: string; valor: number; situacao: keyof typeof situacoes }) {
  return (
    <View style={estilos.numero}>
      <Text style={texto.suave}>{rotulo}</Text>
      <Text style={texto.numeroGrande}>{metros(valor)}</Text>
      <SeloDaSituacao situacao={situacao} />
    </View>
  );
}

export default function DetalheDoRio() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const consulta = usePrevisaoDoRio(id);
  const leituras = useLeiturasDoRio(id);

  return (
    <Tela
      aoAtualizar={() => consulta.refetch()}
      atualizando={consulta.isRefetching}
      rodape={consulta.dataUpdatedAt ? `atualizado às ${horaCurta(new Date(consulta.dataUpdatedAt))}` : undefined}
    >
      <Stack.Screen options={{ title: consulta.data?.corpo_hidrico ?? 'Rio' }} />
      <EstadoDaConsulta consulta={consulta} carregando="Lendo o rio…">
        {(rio) =>
          rio === null ? (
            <AvisoDeErro mensagem="Não encontramos este rio." />
          ) : (
            <>
              <View>
                <Text style={texto.titulo}>{rio.corpo_hidrico}</Text>
                <Text style={texto.suave}>
                  {rio.estacao}
                  {rio.medido_em_utc ? ` · leitura das ${horaCurta(new Date(rio.medido_em_utc))}` : ''}
                </Text>
              </View>
              <SelosDoRio rio={rio} />

              <View style={estilos.numeros}>
                <Numero rotulo="Agora" valor={rio.nivel_atual_m} situacao={rio.situacao_atual} />
                <Numero rotulo="Em 6 horas" valor={rio.nivel_previsto_6h_m} situacao={rio.situacao_prevista} />
              </View>
              <Text style={texto.corpo}>
                O rio está {textoDaTendencia(rio)}. {distanciaDaCota(rio)}.
              </Text>

              <GraficoDoRio rio={rio} leituras={leituras} />

              <View style={estilos.cartao}>
                <Text style={texto.subtitulo} accessibilityRole="header">
                  Cotas deste rio
                </Text>
                {(
                  [
                    ['atencao', rio.cotas.atencao_m, 'fique atento'],
                    ['alerta', rio.cotas.alerta_m, 'prepare-se para sair'],
                    ['inundacao', rio.cotas.inundacao_m, 'ruas alagando: saia'],
                  ] as const
                ).map(([s, cota, acao]) => (
                  <View key={s} style={estilos.cota}>
                    <View style={[estilos.bolinha, { backgroundColor: situacoes[s].forte }]} />
                    <Text style={texto.corpo}>
                      <Text style={{ fontWeight: '700' }}>{situacoes[s].nome}</Text> a partir de {metros(cota)}: {acao}
                    </Text>
                  </View>
                ))}
              </View>

              <View style={estilos.cartao}>
                <Text style={texto.subtitulo} accessibilityRole="header">
                  Como a previsão é feita
                </Text>
                <Text style={texto.corpo}>{explicacaoDoModelo(rio)}</Text>
              </View>

              {pedeParaSair(piorDoRio(rio)) ? (
                <Botao titulo="Onde ficar seguro" grande aoTocar={() => router.navigate('/abrigos')} />
              ) : null}
            </>
          )
        }
      </EstadoDaConsulta>
    </Tela>
  );
}

const estilos = StyleSheet.create({
  numeros: { flexDirection: 'row', gap: espaco.md },
  numero: {
    flex: 1,
    gap: 4,
    backgroundColor: cores.superficie,
    borderRadius: raio.lg,
    padding: espaco.lg,
    borderWidth: 1,
    borderColor: cores.borda,
  },
  cartao: {
    backgroundColor: cores.superficie,
    borderRadius: raio.lg,
    padding: espaco.lg,
    gap: espaco.sm,
    borderWidth: 1,
    borderColor: cores.borda,
  },
  cota: { flexDirection: 'row', alignItems: 'center', gap: espaco.sm },
  bolinha: { width: 14, height: 14, borderRadius: 7 },
});
