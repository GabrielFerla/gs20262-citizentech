/** Rio: nível agora e em 6 h, gráfico com as cotas e como a previsão é feita. */
import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { usePrevisaoDoRio } from '@/api/consultas';
import { Botao } from '@/componentes/Botao';
import { ColunaDoNivel, SetaDaTendencia } from '@/componentes/CartaoDoRio';
import { AvisoDeErro, EstadoDaConsulta } from '@/componentes/EstadoDaConsulta';
import { GraficoDoRio } from '@/componentes/GraficoDoRio';
import { Icone, type NomeDoIcone } from '@/componentes/Icones';
import { SelosDoRio } from '@/componentes/Selo';
import { Tela, TituloDaTela } from '@/componentes/Tela';
import { useLeiturasDoRio } from '@/estado/historico';
import { horaCurta, metros } from '@/logica/formato';
import { distanciaDaCota, explicacaoDoModelo, pedeParaSair, piorDoRio, textoDaTendencia } from '@/logica/situacao';
import { cartao, espaco, peso, situacoes, texto } from '@/tema';

const ICONE_DA_COTA: Record<'atencao' | 'alerta' | 'inundacao', NomeDoIcone> = {
  atencao: 'circuloExclamacao',
  alerta: 'trianguloExclamacao',
  inundacao: 'ondas',
};

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
      telefones
    >
      <Stack.Screen options={{ title: consulta.data?.corpo_hidrico ?? 'Rio' }} />
      <EstadoDaConsulta consulta={consulta} carregando="Lendo o rio…">
        {(rio) =>
          rio === null ? (
            <AvisoDeErro mensagem="Não encontramos este rio." />
          ) : (
            <>
              <TituloDaTela
                titulo={rio.corpo_hidrico}
                subtitulo={`${rio.estacao}${rio.medido_em_utc ? ` · leitura das ${horaCurta(new Date(rio.medido_em_utc))}` : ''}`}
              />

              <View style={estilos.cartao}>
                <View style={estilos.niveis}>
                  <ColunaDoNivel rotulo="Agora" valor={rio.nivel_atual_m} situacao={rio.situacao_atual} />
                  <SetaDaTendencia tendencia={rio.tendencia} />
                  <ColunaDoNivel rotulo="Em 6 horas" valor={rio.nivel_previsto_6h_m} situacao={rio.situacao_prevista} />
                </View>
                <Text style={estilos.destaque}>
                  O rio está {textoDaTendencia(rio)}. {distanciaDaCota(rio)}.
                </Text>
                <SelosDoRio rio={rio} />
              </View>

              <GraficoDoRio rio={rio} leituras={leituras} />

              <View style={estilos.cartao}>
                <Text style={texto.tituloCartao} accessibilityRole="header">
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
                    <Icone nome={ICONE_DA_COTA[s]} cor={situacoes[s].texto} tamanho={22} />
                    <Text style={[texto.corpoCartao, estilos.textoDaCota]}>
                      <Text style={peso('700')}>{situacoes[s].nome}</Text> a partir de {metros(cota)}: {acao}
                    </Text>
                  </View>
                ))}
              </View>

              <View style={estilos.cartao}>
                <Text style={texto.tituloCartao} accessibilityRole="header">
                  Como a previsão é feita
                </Text>
                <Text style={estilos.explicacao}>{explicacaoDoModelo(rio)}</Text>
              </View>

              {pedeParaSair(piorDoRio(rio)) ? (
                <Botao
                  titulo="Onde ficar seguro"
                  grande
                  icone="setaDireita"
                  iconeNoFim
                  aoTocar={() => router.navigate('/abrigos')}
                />
              ) : null}
            </>
          )
        }
      </EstadoDaConsulta>
    </Tela>
  );
}

const estilos = StyleSheet.create({
  cartao: { ...cartao, gap: espaco.md },
  niveis: { flexDirection: 'row', alignItems: 'flex-start', gap: 6 },
  destaque: { ...texto.corpoCartao, ...peso('600') },
  cota: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  textoDaCota: { flex: 1 },
  explicacao: { ...texto.corpoCartao, lineHeight: 24 },
});
