/**
 * Faixa que desce no topo do app quando o vigia abre (ou escala) um alerta com o app aberto.
 * Vale no celular e no navegador; a notificação do sistema, quando permitida, vem junto.
 */
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { SITUACOES } from '@/api/tipos';
import type { Aviso } from '@/logica/alertas';
import { ALVO_DE_TOQUE, espaco, raio, situacoes } from '@/tema';

import { Botao } from './Botao';

interface Props {
  aviso: Aviso;
  aoAbrir: () => void;
  aoFechar: () => void;
}

export function AvisoDeAlertaNovo({ aviso, aoAbrir, aoFechar }: Props) {
  const { top } = useSafeAreaInsets();
  const c = situacoes[SITUACOES[Math.min(Math.max(aviso.severidade, 1), 3)]];
  const amarelo = aviso.severidade === 1;

  return (
    <View
      style={[estilos.faixa, { top: top + espaco.sm, backgroundColor: c.forte }]}
      accessibilityRole="alert"
      accessibilityLiveRegion="assertive"
      testID="aviso-de-alerta-novo"
    >
      <View style={estilos.cabeca}>
        <Text style={[estilos.rotulo, { color: c.sobreForte }]}>Alerta novo · Abriga</Text>
        <Pressable
          onPress={aoFechar}
          accessibilityRole="button"
          accessibilityLabel="Fechar o aviso"
          hitSlop={8}
          style={estilos.fechar}
        >
          <Text style={[estilos.x, { color: c.sobreForte }]}>×</Text>
        </Pressable>
      </View>
      <Text style={[estilos.titulo, { color: c.sobreForte }]}>{aviso.titulo}</Text>
      <Text style={[estilos.corpo, { color: c.sobreForte }]}>{aviso.corpo}</Text>
      <Botao
        titulo={aviso.rota === '/abrigos' ? 'Onde ficar seguro' : 'Ver os rios'}
        variante="claro"
        corDoTexto={amarelo ? c.sobreForte : c.forte}
        aoTocar={aoAbrir}
      />
    </View>
  );
}

const estilos = StyleSheet.create({
  faixa: {
    position: 'absolute',
    left: espaco.md,
    right: espaco.md,
    zIndex: 1000,
    elevation: 12,
    alignSelf: 'center',
    maxWidth: 560,
    borderRadius: raio.lg,
    padding: espaco.lg,
    gap: espaco.sm,
    shadowColor: '#000',
    shadowOpacity: 0.25,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
  },
  cabeca: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  rotulo: { fontSize: 13, fontWeight: '800', textTransform: 'uppercase', letterSpacing: 0.5 },
  fechar: {
    minWidth: ALVO_DE_TOQUE / 1.5,
    minHeight: ALVO_DE_TOQUE / 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  x: { fontSize: 28, fontWeight: '700', lineHeight: 30 },
  titulo: { fontSize: 20, fontWeight: '800' },
  corpo: { fontSize: 16, lineHeight: 22 },
});
