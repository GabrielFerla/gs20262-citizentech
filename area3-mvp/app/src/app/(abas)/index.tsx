/**
 * Agora: a situação da cidade numa faixa (com a mensagem em linguagem simples e o botão
 * "Onde ficar seguro") e um cartão por rio, com o nível agora e o previsto para daqui a 6 h.
 */
import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { useAlertas, usePrevisao } from '@/api/consultas';
import { Botao } from '@/componentes/Botao';
import { CartaoDoRio } from '@/componentes/CartaoDoRio';
import { EstadoDaConsulta } from '@/componentes/EstadoDaConsulta';
import { FaixaDeSituacao } from '@/componentes/FaixaDeSituacao';
import { Icone } from '@/componentes/Icones';
import { Tela } from '@/componentes/Tela';
import { usePreferencias } from '@/estado/preferencias';
import { horaCurta } from '@/logica/formato';
import { ordenarPorGravidade, resumoDosRios } from '@/logica/situacao';
import { cores, espaco, raio, texto } from '@/tema';

function CartaoEscolherBairro() {
  const router = useRouter();
  return (
    <View style={estilos.convite}>
      <View style={estilos.conviteTitulo}>
        <Icone nome="alfinete" cor={cores.primariaEscura} tamanho={22} />
        <Text style={[texto.tituloCartao, estilos.textoDoConvite]}>Qual é o seu bairro?</Text>
      </View>
      <Text style={texto.corpoCartao}>
        Com o bairro, o alerta já diz qual abrigo seguro fica mais perto de você. Ele fica guardado só neste aparelho.
      </Text>
      <Botao titulo="Escolher meu bairro" variante="secundario" aoTocar={() => router.navigate('/abrigos')} />
    </View>
  );
}

export default function Agora() {
  const { carregado, valores } = usePreferencias();
  const previsao = usePrevisao();
  // Mensagens em linguagem simples (com o abrigo do bairro, se a pessoa escolheu um).
  const alertas = useAlertas(valores.bairroId);

  const atualizadoEm = previsao.dataUpdatedAt
    ? `atualizado às ${horaCurta(new Date(previsao.dataUpdatedAt))}`
    : undefined;

  return (
    <Tela
      aoAtualizar={() => {
        void previsao.refetch();
        void alertas.refetch();
      }}
      atualizando={previsao.isRefetching}
      rodape={atualizadoEm}
    >
      <EstadoDaConsulta consulta={previsao} carregando="Lendo os rios…" esqueleto>
        {(rios) => (
          <>
            <FaixaDeSituacao resumo={resumoDosRios(rios, alertas.data)} />
            {carregado && !valores.bairroId ? <CartaoEscolherBairro /> : null}
            <Text style={[texto.tituloSecao, estilos.secao]} accessibilityRole="header">
              Os rios agora e em 6 horas
            </Text>
            {ordenarPorGravidade(rios).map((rio) => (
              <CartaoDoRio key={rio.estacao_id} rio={rio} />
            ))}
          </>
        )}
      </EstadoDaConsulta>
    </Tela>
  );
}

const estilos = StyleSheet.create({
  // Entre seções, 28 (os 12 entre cartões + 16).
  secao: { marginTop: espaco.entreSecoes - espaco.entreCartoes },
  convite: {
    backgroundColor: cores.primariaClara,
    borderRadius: raio.cartao,
    padding: espaco.cartao,
    gap: espaco.md,
  },
  conviteTitulo: { flexDirection: 'row', alignItems: 'center', gap: espaco.sm },
  textoDoConvite: { color: cores.primariaEscura, flexShrink: 1 },
});
