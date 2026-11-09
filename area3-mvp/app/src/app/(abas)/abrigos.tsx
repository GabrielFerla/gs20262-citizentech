/**
 * Onde ficar seguro: a partir do bairro e do tamanho do grupo, os 3 abrigos aptos mais perto
 * (vaga quando a pessoa chegar e fora de área que deve alagar) e os mais perto que foram evitados.
 */
import { useIsFocused } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { useRecomendacao } from '@/api/consultas';
import type { Recomendacao } from '@/api/tipos';
import { CartaoDoAbrigo } from '@/componentes/CartaoDoAbrigo';
import { EstadoDaConsulta } from '@/componentes/EstadoDaConsulta';
import { SeletorDeBairro } from '@/componentes/SeletorDeBairro';
import { SeletorDePessoas } from '@/componentes/SeletorDePessoas';
import { Tela } from '@/componentes/Tela';
import { usePreferencias } from '@/estado/preferencias';
import { horaCurta } from '@/logica/formato';
import { cores, espaco, raio, situacoes, texto } from '@/tema';

function RioDaRegiao({ r }: { r: Recomendacao }) {
  const rio = r.estacao_da_regiao;
  if (!rio) return null;
  const agora = situacoes[rio.situacao_atual];
  const depois = situacoes[rio.situacao_prevista];
  return (
    <Text style={texto.suave}>
      Rio da região de {r.bairro}: {rio.corpo_hidrico}, agora em {agora.nome.toLowerCase()}, em 6 h em{' '}
      {depois.nome.toLowerCase()}.
    </Text>
  );
}

function ResultadoPorBairro({ r }: { r: Recomendacao }) {
  return (
    <>
      <RioDaRegiao r={r} />
      <Text style={texto.subtitulo} accessibilityRole="header">
        Vá para um destes
      </Text>
      {r.recomendados.length > 0 ? (
        r.recomendados.map((a, i) => (
          <CartaoDoAbrigo
            key={a.abrigo_id}
            abrigo={a}
            ordem={i + 1}
            vagasNaChegada={a.vagas_previstas_na_chegada}
            origem="bairro"
          />
        ))
      ) : (
        <View style={estilos.semAbrigo} accessibilityRole="alert">
          <Text style={[texto.subtitulo, { color: cores.erro }]}>Nenhum abrigo seguro com vaga agora</Text>
          <Text style={texto.corpo}>
            Não há abrigo com vaga para {r.pessoas} {r.pessoas === 1 ? 'pessoa' : 'pessoas'} fora de área de risco.
            Procure um lugar alto e ligue 199 (Defesa Civil) ou 193 (Bombeiros).
          </Text>
        </View>
      )}

      {r.evitados.length > 0 ? (
        <>
          <Text style={[texto.subtitulo, estilos.secao]} accessibilityRole="header">
            Evitamos estes, mais perto de você
          </Text>
          <Text style={texto.suave}>Ficam mais perto, mas não são seguros agora:</Text>
          {r.evitados.map((a) => (
            <CartaoDoAbrigo key={a.abrigo_id} abrigo={a} motivo={a.motivo} origem="bairro" />
          ))}
        </>
      ) : null}

      <Text style={[texto.suave, estilos.nota]}>
        O tempo a pé é estimado a partir do centro do bairro (linha reta × 1,3, a 4 km/h). Sua localização exata não é
        usada.
      </Text>
    </>
  );
}

export default function OndeFicarSeguro() {
  const ativa = useIsFocused();
  const { carregado, valores, salvar } = usePreferencias();
  const recomendacao = useRecomendacao(valores.bairroId, valores.pessoas, ativa);

  return (
    <Tela
      aoAtualizar={valores.bairroId ? () => recomendacao.refetch() : undefined}
      atualizando={recomendacao.isRefetching}
      rodape={
        recomendacao.dataUpdatedAt ? `atualizado às ${horaCurta(new Date(recomendacao.dataUpdatedAt))}` : undefined
      }
    >
      <Text style={texto.corpo}>
        Abrigos que devem ter vaga quando você chegar e que ficam fora de área que deve alagar nas próximas 6 horas.
      </Text>
      <SeletorDeBairro
        bairroNome={valores.bairroNome}
        aoEscolher={(b) => salvar({ bairroId: b.bairro_id, bairroNome: b.bairro })}
      />
      <SeletorDePessoas pessoas={valores.pessoas} aoMudar={(pessoas) => salvar({ pessoas })} />

      {carregado && !valores.bairroId ? (
        <Text style={[texto.corpo, estilos.dica]}>Escolha o bairro para ver os abrigos seguros mais perto.</Text>
      ) : null}
      {valores.bairroId ? (
        <EstadoDaConsulta consulta={recomendacao} carregando="Procurando abrigos seguros…">
          {(r) => <ResultadoPorBairro r={r} />}
        </EstadoDaConsulta>
      ) : null}
    </Tela>
  );
}

const estilos = StyleSheet.create({
  secao: { marginTop: espaco.md },
  nota: { marginTop: espaco.sm },
  dica: { color: cores.textoSuave, textAlign: 'center', paddingVertical: espaco.lg },
  semAbrigo: {
    backgroundColor: cores.erroFundo,
    borderRadius: raio.lg,
    padding: espaco.lg,
    gap: espaco.sm,
    borderWidth: 1,
    borderColor: '#F4B4AE',
  },
});
