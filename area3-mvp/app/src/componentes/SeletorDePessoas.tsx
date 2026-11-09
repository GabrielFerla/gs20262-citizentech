/** Quantas pessoas vão juntas (1 a 50): o abrigo precisa ter vaga para todo o grupo. */
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { PESSOAS_MAX, PESSOAS_MIN } from '@/estado/preferencias';
import { ALVO_DE_TOQUE, cores, espaco, raio, texto } from '@/tema';

interface Props {
  pessoas: number;
  aoMudar: (pessoas: number) => void;
}

function BotaoPasso({
  rotulo,
  sinal,
  desligado,
  aoTocar,
}: {
  rotulo: string;
  sinal: string;
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
      style={({ pressed }) => [estilos.passo, desligado && estilos.desligado, pressed && { opacity: 0.8 }]}
    >
      <Text style={estilos.sinal}>{sinal}</Text>
    </Pressable>
  );
}

export function SeletorDePessoas({ pessoas, aoMudar }: Props) {
  return (
    <View style={estilos.caixa}>
      <View style={estilos.rotulo}>
        <Text style={texto.suave}>Quantas pessoas vão juntas</Text>
        <Text style={estilos.valor} accessibilityLiveRegion="polite" accessibilityLabel={`${pessoas} pessoas`}>
          {pessoas} {pessoas === 1 ? 'pessoa' : 'pessoas'}
        </Text>
      </View>
      <View style={estilos.botoes}>
        <BotaoPasso
          rotulo="Uma pessoa a menos"
          sinal="−"
          desligado={pessoas <= PESSOAS_MIN}
          aoTocar={() => aoMudar(pessoas - 1)}
        />
        <BotaoPasso
          rotulo="Uma pessoa a mais"
          sinal="+"
          desligado={pessoas >= PESSOAS_MAX}
          aoTocar={() => aoMudar(pessoas + 1)}
        />
      </View>
    </View>
  );
}

const estilos = StyleSheet.create({
  caixa: {
    backgroundColor: cores.superficie,
    borderRadius: raio.lg,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espaco.lg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: espaco.md,
  },
  rotulo: { flexShrink: 1, gap: 2 },
  valor: { fontSize: 20, fontWeight: '700', color: cores.texto },
  botoes: { flexDirection: 'row', gap: espaco.sm },
  passo: {
    width: ALVO_DE_TOQUE,
    height: ALVO_DE_TOQUE,
    borderRadius: raio.md,
    backgroundColor: cores.primaria,
    alignItems: 'center',
    justifyContent: 'center',
  },
  desligado: { backgroundColor: cores.borda },
  sinal: { color: '#FFFFFF', fontSize: 26, fontWeight: '700', lineHeight: 30 },
});
