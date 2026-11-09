/**
 * Um abrigo na lista "Onde ficar seguro": recomendado (com a ordem) ou evitado (com o motivo).
 * Toque abre o detalhe, levando os minutos a pé calculados (a API ou o aparelho já sabem a distância).
 */
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { AbrigoAvaliado } from '@/api/tipos';
import { km, minutosAPeTexto } from '@/logica/formato';
import { capitalizar } from '@/logica/texto';
import { cores, espaco, raio, situacoes, texto } from '@/tema';

interface Props {
  abrigo: AbrigoAvaliado;
  /** 1, 2, 3 para os recomendados; ausente para os evitados. */
  ordem?: number;
  /** Por que foi evitado (o motivo da API ou o calculado no aparelho). */
  motivo?: string | null;
  /** Vagas na chegada (da API no modo bairro, do aparelho no modo localização). */
  vagasNaChegada?: number | null;
  origem: 'bairro' | 'localizacao';
}

export function CartaoDoAbrigo({ abrigo, ordem, motivo, vagasNaChegada, origem }: Props) {
  const router = useRouter();
  const evitado = ordem === undefined;
  const minutos = abrigo.minutos_a_pe;
  const distancia = abrigo.distancia_km;

  const caminho = [minutos !== null ? minutosAPeTexto(minutos) : null, distancia !== null ? km(distancia) : null]
    .filter(Boolean)
    .join(' · ');
  const vagas =
    vagasNaChegada !== undefined && vagasNaChegada !== null
      ? `${abrigo.vagas} vagas agora · ${vagasNaChegada} quando você chegar`
      : `${abrigo.vagas} vagas agora`;

  const abrir = () =>
    router.push({
      pathname: '/abrigo/[id]',
      params: {
        id: abrigo.abrigo_id,
        ...(minutos !== null ? { minutos: String(minutos) } : {}),
        ...(distancia !== null ? { km: String(distancia) } : {}),
        origem,
      },
    });

  return (
    <Pressable
      onPress={abrir}
      accessibilityRole="button"
      accessibilityLabel={
        evitado
          ? `Evitado: ${abrigo.abrigo}, ${caminho}. Motivo: ${motivo ?? ''}. Toque para ver detalhes.`
          : `${ordem}º recomendado: ${abrigo.abrigo}, ${caminho}, ${vagas}. Toque para ver detalhes e como chegar.`
      }
      style={({ pressed }) => [
        estilos.cartao,
        { borderLeftColor: evitado ? situacoes.alerta.forte : situacoes.normal.forte },
        pressed && { opacity: 0.9 },
      ]}
    >
      <View style={estilos.cabeca}>
        {ordem !== undefined ? (
          <View style={estilos.ordem}>
            <Text style={estilos.ordemTexto}>{ordem}</Text>
          </View>
        ) : null}
        <Text style={[texto.subtitulo, estilos.nome]}>{abrigo.abrigo}</Text>
      </View>
      {caminho ? <Text style={texto.corpo}>{caminho}</Text> : null}
      {evitado ? (
        <Text style={[texto.corpo, { color: situacoes.alerta.texto, fontWeight: '700' }]}>
          {capitalizar(motivo ?? 'não recomendado agora')}
        </Text>
      ) : (
        <Text style={texto.suave}>{vagas}</Text>
      )}
    </Pressable>
  );
}

const estilos = StyleSheet.create({
  cartao: {
    backgroundColor: cores.superficie,
    borderRadius: raio.lg,
    padding: espaco.lg,
    gap: espaco.xs,
    borderWidth: 1,
    borderColor: cores.borda,
    borderLeftWidth: 6,
  },
  cabeca: { flexDirection: 'row', alignItems: 'center', gap: espaco.sm },
  nome: { flexShrink: 1 },
  ordem: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: situacoes.normal.forte,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ordemTexto: { color: '#FFFFFF', fontWeight: '800', fontSize: 16 },
});
