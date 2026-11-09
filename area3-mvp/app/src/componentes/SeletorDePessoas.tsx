/** Quantas pessoas vão juntas (1 a 50): o abrigo precisa ter vaga para todo o grupo. */
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { PESSOAS_MAX, PESSOAS_MIN } from '@/estado/preferencias';
import { ALVO_DE_TOQUE, cores, espaco, peso, raio, tabular } from '@/tema';

import { Icone } from './Icones';

interface Props {
  pessoas: number;
  aoMudar: (pessoas: number) => void;
}

function BotaoPasso({
  rotulo,
  icone,
  desligado,
  aoTocar,
}: {
  rotulo: string;
  icone: 'menos' | 'mais';
  desligado: boolean;
  aoTocar: () => void;
}) {
  return (
    <Pressable
      onPress={aoTocar}
      disabled={desligado}
      accessibilityRole="button"
      accessibilityLabel={rotulo}
      aria-disabled={desligado}
      style={({ pressed }) => [
        estilos.passo,
        desligado && estilos.desligado,
        pressed && !desligado && { backgroundColor: cores.primaria },
      ]}
    >
      {({ pressed }) => (
        <Icone
          nome={icone}
          cor={desligado ? cores.bordaControle : pressed ? '#FFFFFF' : cores.primariaEscura}
          tamanho={22}
        />
      )}
    </Pressable>
  );
}

export function SeletorDePessoas({ pessoas, aoMudar }: Props) {
  return (
    <View style={estilos.caixa}>
      <View style={estilos.rotulo}>
        <Icone nome="pessoas" cor={cores.primaria} tamanho={22} />
        <Text style={estilos.rotuloTexto}>Quantas pessoas vão juntas</Text>
      </View>
      <View style={estilos.controle}>
        <BotaoPasso
          rotulo="Uma pessoa a menos"
          icone="menos"
          desligado={pessoas <= PESSOAS_MIN}
          aoTocar={() => aoMudar(pessoas - 1)}
        />
        <Text style={estilos.valor} accessibilityLiveRegion="polite" accessibilityLabel={`${pessoas} pessoas`}>
          {pessoas} {pessoas === 1 ? 'pessoa' : 'pessoas'}
        </Text>
        <BotaoPasso
          rotulo="Uma pessoa a mais"
          icone="mais"
          desligado={pessoas >= PESSOAS_MAX}
          aoTocar={() => aoMudar(pessoas + 1)}
        />
      </View>
    </View>
  );
}

const estilos = StyleSheet.create({
  caixa: { gap: espaco.sm },
  rotulo: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  rotuloTexto: { ...peso('600'), fontSize: 17, lineHeight: 22, color: cores.texto, flexShrink: 1 },
  controle: { flexDirection: 'row', alignItems: 'center', gap: espaco.xs },
  valor: {
    ...peso('700'),
    ...tabular,
    flex: 1,
    fontSize: 18,
    lineHeight: 24,
    color: cores.texto,
    textAlign: 'center',
  },
  passo: {
    width: ALVO_DE_TOQUE,
    height: ALVO_DE_TOQUE,
    borderRadius: raio.selo,
    backgroundColor: cores.primariaClara,
    alignItems: 'center',
    justifyContent: 'center',
  },
  desligado: { backgroundColor: cores.neutroFundo },
});
