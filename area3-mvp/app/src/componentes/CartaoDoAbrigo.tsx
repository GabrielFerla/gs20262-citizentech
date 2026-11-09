/**
 * Um abrigo na lista "Onde ficar seguro": recomendado (com a ordem) ou evitado (com o motivo).
 * Toque abre o detalhe, levando os minutos a pé calculados (a API ou o aparelho já sabem a distância).
 */
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { AbrigoAvaliado } from '@/api/tipos';
import { km, minutosAPeTexto } from '@/logica/formato';
import { capitalizar } from '@/logica/texto';
import { cartao, cores, espaco, peso, raio, tabular, texto } from '@/tema';

import { Icone } from './Icones';

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

/** Uma caixinha de número: "Vagas agora 62". A de destaque fica em verde-claro. */
function Numero({ rotulo, valor, destaque }: { rotulo: string; valor: number; destaque?: boolean }) {
  return (
    <View style={[estilos.numero, destaque && estilos.numeroDestaque]}>
      <Text style={[estilos.numeroRotulo, destaque && { color: cores.primariaEscura }]}>{rotulo}</Text>
      <Text style={[texto.numeroMedio, destaque && { color: cores.primariaEscura }]}>{valor}</Text>
    </View>
  );
}

export function CartaoDoAbrigo({ abrigo, ordem, motivo, vagasNaChegada, origem }: Props) {
  const router = useRouter();
  const evitado = ordem === undefined;
  const minutos = abrigo.minutos_a_pe;
  const distancia = abrigo.distancia_km;

  const caminho = [minutos !== null ? minutosAPeTexto(minutos) : null, distancia !== null ? km(distancia) : null]
    .filter(Boolean)
    .join(' · ');
  const temChegada = vagasNaChegada !== undefined && vagasNaChegada !== null;
  const vagas = temChegada
    ? `${abrigo.vagas} vagas agora · ${vagasNaChegada} quando você chegar`
    : `${abrigo.vagas} vagas agora`;

  // Pelo bairro, a distância vai no endereço da tela (é a do centro do bairro, não da pessoa).
  // Pela localização, nada derivado da posição entra no endereço: o detalhe refaz a conta na memória.
  const abrir = () =>
    router.push({
      pathname: '/abrigo/[id]',
      params:
        origem === 'bairro'
          ? {
              id: abrigo.abrigo_id,
              ...(minutos !== null ? { minutos: String(minutos) } : {}),
              ...(distancia !== null ? { km: String(distancia) } : {}),
              origem,
            }
          : { id: abrigo.abrigo_id, origem },
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
      style={({ pressed }) => [estilos.cartao, evitado && estilos.evitado, pressed && { backgroundColor: cores.fundo }]}
    >
      {evitado ? (
        <>
          <View style={estilos.nomeECaminho}>
            <Text style={texto.tituloCartao}>{abrigo.abrigo}</Text>
            {caminho ? <Text style={texto.apoio}>{caminho}</Text> : null}
          </View>
          <View style={estilos.motivo}>
            <Icone nome="proibido" cor={cores.risco} tamanho={20} />
            <Text style={estilos.motivoTexto}>{capitalizar(motivo ?? 'não recomendado agora')}</Text>
          </View>
        </>
      ) : (
        <>
          <View style={estilos.cabeca}>
            <View style={estilos.ordem}>
              <Text style={estilos.ordemTexto}>{ordem}</Text>
            </View>
            <View style={estilos.nomeECaminho}>
              <Text style={texto.tituloCartao}>{abrigo.abrigo}</Text>
              {caminho ? (
                <View style={estilos.caminho}>
                  <Icone nome="relogio" cor={cores.textoSuave} tamanho={18} />
                  <Text style={estilos.caminhoTexto}>{caminho}</Text>
                </View>
              ) : null}
            </View>
            <View style={estilos.chevron}>
              <Icone nome="chevronDireita" cor={cores.primaria} tamanho={24} />
            </View>
          </View>
          <View style={estilos.numeros}>
            <Numero rotulo="Vagas agora" valor={abrigo.vagas} />
            {temChegada ? <Numero rotulo="Quando você chegar" valor={vagasNaChegada} destaque /> : null}
          </View>
        </>
      )}
    </Pressable>
  );
}

const estilos = StyleSheet.create({
  cartao: { ...cartao, gap: espaco.md },
  evitado: { gap: 10 },
  cabeca: { flexDirection: 'row', alignItems: 'flex-start', gap: espaco.md },
  ordem: {
    width: 36,
    height: 36,
    borderRadius: raio.selo,
    backgroundColor: cores.primaria,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ordemTexto: { ...peso('800'), fontSize: 17, lineHeight: 22, color: '#FFFFFF', ...tabular },
  nomeECaminho: { flex: 1, minWidth: 0, gap: espaco.xs },
  caminho: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  caminhoTexto: { ...texto.corpoCartao, ...peso('500'), color: cores.textoSuave, flexShrink: 1 },
  chevron: { marginTop: 6 },
  numeros: { flexDirection: 'row', gap: espaco.sm },
  // Rótulo em cima e número embaixo: se um rótulo quebra a linha, os números continuam alinhados.
  numero: {
    flex: 1,
    minWidth: 0,
    gap: 2,
    justifyContent: 'space-between',
    paddingVertical: 10,
    paddingHorizontal: espaco.md,
    borderRadius: raio.controle,
    backgroundColor: cores.fundo,
  },
  numeroDestaque: { backgroundColor: cores.primariaClara },
  numeroRotulo: { ...peso('600'), fontSize: 14, lineHeight: 18, color: cores.textoSuave },
  motivo: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: espaco.sm,
    paddingVertical: 9,
    paddingHorizontal: espaco.md,
    borderRadius: raio.md,
    backgroundColor: cores.erroFundo,
  },
  motivoTexto: { ...texto.corpoCartao, ...peso('700'), color: cores.erro, flex: 1 },
});
