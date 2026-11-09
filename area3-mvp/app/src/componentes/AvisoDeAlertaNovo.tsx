/**
 * Faixa que desce no topo do app quando o vigia abre (ou escala) um alerta com o app aberto.
 * Vale no celular e no navegador; a notificação do sistema, quando permitida, vem junto.
 * Cartão escuro e flutuante; a gravidade vem no selo da situação (cor, palavra e ícone).
 */
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { SITUACOES } from '@/api/tipos';
import type { Aviso } from '@/logica/alertas';
import { ALVO_DE_TOQUE, cores, espaco, peso, raio, sombra, texto } from '@/tema';

import { Botao } from './Botao';
import { Icone } from './Icones';
import { SeloDaSituacao } from './Selo';

interface Props {
  aviso: Aviso;
  aoAbrir: () => void;
  aoFechar: () => void;
}

export function AvisoDeAlertaNovo({ aviso, aoAbrir, aoFechar }: Props) {
  const { top } = useSafeAreaInsets();
  const situacao = SITUACOES[Math.min(Math.max(aviso.severidade, 1), 3)];

  return (
    <View
      style={[estilos.faixa, { top: top + espaco.sm }]}
      accessibilityRole="alert"
      accessibilityLiveRegion="assertive"
      testID="aviso-de-alerta-novo"
    >
      <View style={estilos.cabeca}>
        <Text style={estilos.rotulo}>Alerta novo · Abriga</Text>
        <Pressable
          onPress={aoFechar}
          accessibilityRole="button"
          accessibilityLabel="Fechar o aviso"
          style={({ pressed }) => [estilos.fechar, pressed && { backgroundColor: '#FFFFFF26' }]}
        >
          <Icone nome="fechar" cor="#FFFFFF" tamanho={22} />
        </Pressable>
      </View>
      <View style={estilos.corpo}>
        <View style={estilos.situacao}>
          <SeloDaSituacao situacao={situacao} tamanho="p" />
          <Text style={estilos.rio}>{aviso.rio}</Text>
        </View>
        <Text style={estilos.titulo}>{aviso.titulo}</Text>
        <Text style={estilos.texto}>{aviso.corpo}</Text>
        {aviso.tambem ? <Text style={estilos.tambem}>{aviso.tambem}</Text> : null}
        <Botao
          titulo={aviso.rota === '/abrigos' ? 'Onde ficar seguro' : 'Ver os rios'}
          variante="claro"
          icone="setaDireita"
          iconeNoFim
          aoTocar={aoAbrir}
          estilo={estilos.botao}
        />
      </View>
    </View>
  );
}

const estilos = StyleSheet.create({
  faixa: {
    position: 'absolute',
    left: espaco.md,
    right: espaco.md,
    zIndex: 1000,
    alignSelf: 'center',
    maxWidth: 560,
    borderRadius: raio.cartao,
    backgroundColor: cores.texto,
    paddingTop: 6,
    paddingRight: 6,
    paddingBottom: espaco.lg,
    paddingLeft: espaco.lg,
    gap: espaco.sm,
    ...sombra.flutuante,
  },
  cabeca: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: espaco.sm },
  rotulo: { ...texto.rotulo, letterSpacing: 1.3, color: cores.primariaSobreEscuro, flexShrink: 1 },
  fechar: {
    width: ALVO_DE_TOQUE,
    height: ALVO_DE_TOQUE,
    borderRadius: raio.controle,
    alignItems: 'center',
    justifyContent: 'center',
  },
  corpo: { gap: espaco.sm, paddingRight: 10 },
  situacao: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: espaco.sm },
  rio: { ...peso('600'), fontSize: 15, lineHeight: 20, color: cores.textoSobreEscuro },
  titulo: { ...peso('700'), fontSize: 21, lineHeight: 27, color: '#FFFFFF' },
  texto: { ...texto.corpoCartao, color: cores.textoSobreEscuro },
  tambem: { ...peso('700'), fontSize: 15, lineHeight: 20, color: '#FFFFFF' },
  botao: { marginTop: 6 },
});
