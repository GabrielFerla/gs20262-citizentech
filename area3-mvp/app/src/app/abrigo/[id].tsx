/**
 * Detalhe do abrigo, com dados ao vivo (GET /abrigos): vagas agora e na chegada, quanto falta para
 * lotar, risco da região e "Como chegar", que abre o mapa só com o destino.
 */
import { Stack, useIsFocused, useLocalSearchParams } from 'expo-router';
import { Linking, StyleSheet, Text, View } from 'react-native';

import { useAbrigos, usePrevisao } from '@/api/consultas';
import type { AbrigoAvaliado, EstacaoPrevisao } from '@/api/tipos';
import { Botao } from '@/componentes/Botao';
import { AvisoDeErro, EstadoDaConsulta } from '@/componentes/EstadoDaConsulta';
import { Tela } from '@/componentes/Tela';
import { usePosicao } from '@/estado/posicao';
import { usePreferencias } from '@/estado/preferencias';
import { horaCurta, km, minutosAPeTexto } from '@/logica/formato';
import { distanciaKm, lotaAntesDeChegar, minutosAPe, vagasNaChegada } from '@/logica/geo';
import { urlComoChegar } from '@/logica/rota';
import { capitalizar } from '@/logica/texto';
import { cores, espaco, raio, situacoes, texto } from '@/tema';

type Parametros = { id: string; minutos?: string; km?: string; origem?: 'bairro' | 'localizacao' };

function numeroOuNulo(valor: string | undefined): number | null {
  const n = valor === undefined ? NaN : Number(valor);
  return Number.isFinite(n) && n >= 0 ? n : null;
}

function Linha({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <View style={estilos.linha}>
      <Text style={texto.suave}>{rotulo}</Text>
      <Text style={[texto.corpo, estilos.valor]}>{valor}</Text>
    </View>
  );
}

function BarraDeOcupacao({ abrigo }: { abrigo: AbrigoAvaliado }) {
  const fracao = abrigo.capacidade > 0 ? Math.min(abrigo.ocupacao / abrigo.capacidade, 1) : 1;
  const cor =
    fracao >= 0.9 ? situacoes.inundacao.forte : fracao >= 0.7 ? situacoes.alerta.forte : situacoes.normal.forte;
  return (
    <View
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel={`Ocupação: ${abrigo.ocupacao} de ${abrigo.capacidade} lugares`}
      style={estilos.barra}
    >
      <View style={[estilos.barraCheia, { width: `${Math.round(fracao * 100)}%`, backgroundColor: cor }]} />
    </View>
  );
}

interface PropsDetalhe {
  abrigo: AbrigoAvaliado;
  pessoas: number;
  minutos: number | null;
  distancia: number | null;
  origem: Parametros['origem'];
  rios: EstacaoPrevisao[] | undefined;
  /** Veio do modo localização, mas a posição já não está na memória (a página foi recarregada). */
  semPosicao: boolean;
}

function Detalhe({ abrigo, pessoas, minutos, distancia, origem, rios, semPosicao }: PropsDetalhe) {
  const lotaAntes = minutos !== null && lotaAntesDeChegar(abrigo, minutos);
  // Sem saber de onde a pessoa sai, não dá para garantir a vaga num abrigo que está enchendo.
  const incerto = minutos === null && abrigo.apto && abrigo.minutos_ate_lotar !== null;
  const seguro = abrigo.apto && !lotaAntes && !incerto;
  const motivo = abrigo.motivo ?? (lotaAntes ? 'deve lotar antes de você chegar' : null);
  const chegada = minutos !== null ? vagasNaChegada(abrigo, minutos) : null;
  const rio = rios?.find((r) => r.estacao_id === abrigo.estacao_proxima_id);
  const grupo = `${pessoas} ${pessoas === 1 ? 'pessoa' : 'pessoas'}`;

  return (
    <>
      <Text style={texto.titulo}>{abrigo.abrigo}</Text>

      {incerto ? (
        <View style={[estilos.situacao, estilos.incerto]} accessibilityRole="alert">
          <Text style={[texto.subtitulo, { color: situacoes.atencao.texto }]}>Tem vaga agora, mas está enchendo</Text>
          <Text style={texto.corpo}>
            Para {grupo}, lota em cerca de {abrigo.minutos_ate_lotar} min. Sem saber de onde você sai, não dá para
            garantir a vaga quando você chegar.
          </Text>
          {semPosicao ? (
            <Text style={texto.suave}>
              Sua localização fica só na memória e foi apagada quando o app recarregou. Volte para Onde ficar seguro e
              toque em Minha localização para refazer a conta.
            </Text>
          ) : null}
        </View>
      ) : (
        <View
          style={[estilos.situacao, seguro ? estilos.seguro : estilos.inseguro]}
          accessibilityRole={seguro ? 'summary' : 'alert'}
        >
          <Text style={[texto.subtitulo, { color: seguro ? situacoes.normal.texto : situacoes.inundacao.texto }]}>
            {seguro ? `Recomendado para ${grupo}` : 'Não recomendado agora'}
          </Text>
          <Text style={texto.corpo}>
            {seguro
              ? 'Deve ter vaga quando você chegar e não fica em área que deve alagar nas próximas 6 horas.'
              : capitalizar(motivo ?? 'não é seguro agora') + '.'}
          </Text>
        </View>
      )}

      <Botao
        titulo={seguro || incerto ? 'Como chegar' : 'Como chegar mesmo assim'}
        variante={seguro ? 'principal' : 'secundario'}
        grande={seguro}
        dica="Abre o mapa com o caminho a pé até o abrigo"
        aoTocar={() => void Linking.openURL(urlComoChegar(abrigo.lat, abrigo.lon))}
      />

      <View style={estilos.cartao}>
        <Text style={texto.subtitulo} accessibilityRole="header">
          Vagas
        </Text>
        <BarraDeOcupacao abrigo={abrigo} />
        <Linha
          rotulo="Agora"
          valor={`${abrigo.vagas} vagas (${abrigo.ocupacao} de ${abrigo.capacidade} lugares ocupados)`}
        />
        {chegada !== null ? <Linha rotulo="Quando você chegar" valor={`${chegada} vagas`} /> : null}
        <Linha
          rotulo="Chegando"
          valor={
            abrigo.chegando_por_hora > 0
              ? `${abrigo.chegando_por_hora.toLocaleString('pt-BR')} pessoas por hora`
              : 'ninguém chegou na última hora'
          }
        />
        <Linha
          rotulo={`Vai lotar para ${grupo}`}
          valor={
            abrigo.minutos_ate_lotar === null ? 'não está enchendo' : `em cerca de ${abrigo.minutos_ate_lotar} min`
          }
        />
      </View>

      <View style={estilos.cartao}>
        <Text style={texto.subtitulo} accessibilityRole="header">
          Caminho e risco
        </Text>
        {minutos !== null ? (
          <Linha
            rotulo={origem === 'localizacao' ? 'A pé, de onde você está' : 'A pé, do centro do bairro'}
            valor={`${minutosAPeTexto(minutos)}${distancia !== null ? ` (${km(distancia)} em linha reta)` : ''}`}
          />
        ) : null}
        <Linha rotulo="Fica em área de risco de cheia" valor={abrigo.em_area_de_risco ? 'sim' : 'não'} />
        <Linha
          rotulo={`Rio da região${rio ? ` (${rio.corpo_hidrico})` : ''}`}
          valor={`agora ${situacoes[abrigo.situacao_atual_regiao].nome.toLowerCase()}, em 6 h ${situacoes[
            abrigo.situacao_prevista_regiao
          ].nome.toLowerCase()}`}
        />
      </View>

      <Text style={texto.suave}>
        &quot;Como chegar&quot; abre o mapa só com o endereço do abrigo. O Abriga não envia a sua localização a ninguém.
      </Text>
    </>
  );
}

export default function DetalheDoAbrigo() {
  const params = useLocalSearchParams<Parametros>();
  const ativa = useIsFocused();
  const { valores } = usePreferencias();
  const posicao = usePosicao();
  const abrigos = useAbrigos(valores.pessoas, ativa);
  const previsao = usePrevisao();

  return (
    <Tela
      aoAtualizar={() => abrigos.refetch()}
      atualizando={abrigos.isRefetching}
      rodape={abrigos.dataUpdatedAt ? `atualizado às ${horaCurta(new Date(abrigos.dataUpdatedAt))}` : undefined}
    >
      <Stack.Screen options={{ title: 'Abrigo' }} />
      <EstadoDaConsulta consulta={abrigos} carregando="Lendo as vagas…">
        {(lista) => {
          const abrigo = lista.find((a) => a.abrigo_id === params.id);
          if (!abrigo) return <AvisoDeErro mensagem="Não encontramos este abrigo." />;
          // Pela localização, a distância é refeita aqui, com a posição que está só na memória.
          const daPosicao =
            params.origem === 'localizacao' && posicao
              ? distanciaKm(posicao.lat, posicao.lon, abrigo.lat, abrigo.lon)
              : null;
          return (
            <Detalhe
              abrigo={abrigo}
              pessoas={valores.pessoas}
              minutos={daPosicao !== null ? minutosAPe(daPosicao) : numeroOuNulo(params.minutos)}
              distancia={daPosicao !== null ? Math.round(daPosicao * 100) / 100 : numeroOuNulo(params.km)}
              origem={params.origem}
              rios={previsao.data}
              semPosicao={params.origem === 'localizacao' && !posicao}
            />
          );
        }}
      </EstadoDaConsulta>
    </Tela>
  );
}

const estilos = StyleSheet.create({
  situacao: { borderRadius: raio.lg, padding: espaco.lg, gap: espaco.xs, borderWidth: 1 },
  seguro: { backgroundColor: situacoes.normal.fundo, borderColor: situacoes.normal.forte },
  inseguro: { backgroundColor: situacoes.inundacao.fundo, borderColor: situacoes.inundacao.forte },
  incerto: { backgroundColor: situacoes.atencao.fundo, borderColor: situacoes.atencao.forte },
  cartao: {
    backgroundColor: cores.superficie,
    borderRadius: raio.lg,
    padding: espaco.lg,
    gap: espaco.md,
    borderWidth: 1,
    borderColor: cores.borda,
  },
  linha: { gap: 2 },
  valor: { fontWeight: '600' },
  barra: {
    height: 14,
    borderRadius: 7,
    backgroundColor: cores.fundo,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: cores.borda,
  },
  barraCheia: { height: '100%' },
});
