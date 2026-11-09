/**
 * Selos curtos, sempre com cor, palavra e ícone: situação do rio, alerta antecipado, avisos sobre
 * o dado, "Dados simulados", "Recomendado" e risco.
 * Situação: Normal em tom claro com check; Atenção, Alerta e Inundação na cor forte cheia.
 */
import { StyleSheet, Text, View } from 'react-native';

import type { EstacaoPrevisao, Situacao } from '@/api/tipos';
import { cores, espaco, raio, situacoes, texto } from '@/tema';

import { Icone, type NomeDoIcone } from './Icones';

export type TipoDeSelo = Situacao | 'antecipado' | 'atrasada' | 'incompletos' | 'simulado' | 'recomendado' | 'risco';

interface Variante {
  fundo: string;
  cor: string;
  corDoIcone: string;
  icone: NomeDoIcone;
  /** Texto quando o selo não recebe um. */
  palavra: string;
}

const ICONE_DA_SITUACAO: Record<Situacao, NomeDoIcone> = {
  normal: 'check',
  atencao: 'circuloExclamacao',
  alerta: 'trianguloExclamacao',
  inundacao: 'ondas',
};

function daSituacao(s: Situacao): Variante {
  const c = situacoes[s];
  const cor = c.cheia ? c.sobreForte : c.texto;
  return { fundo: c.cheia ? c.forte : c.fundo, cor, corDoIcone: cor, icone: ICONE_DA_SITUACAO[s], palavra: c.nome };
}

const VARIANTES: Record<TipoDeSelo, Variante> = {
  normal: daSituacao('normal'),
  atencao: daSituacao('atencao'),
  alerta: daSituacao('alerta'),
  inundacao: daSituacao('inundacao'),
  antecipado: {
    fundo: situacoes.alerta.fundo,
    cor: situacoes.alerta.texto,
    corDoIcone: situacoes.alerta.texto,
    icone: 'tendencia',
    palavra: 'Alerta antecipado',
  },
  atrasada: {
    fundo: cores.avisoFundo,
    cor: cores.aviso,
    corDoIcone: cores.aviso,
    icone: 'relogio',
    palavra: 'Leitura atrasada',
  },
  incompletos: {
    fundo: cores.avisoFundo,
    cor: cores.aviso,
    corDoIcone: cores.aviso,
    icone: 'tracejado',
    palavra: 'Dados incompletos',
  },
  simulado: {
    fundo: cores.neutroFundo,
    cor: cores.texto,
    corDoIcone: cores.textoSuave,
    icone: 'frasco',
    palavra: 'Dados simulados',
  },
  recomendado: {
    fundo: cores.primariaClara,
    cor: cores.primariaEscura,
    corDoIcone: cores.primariaEscura,
    icone: 'pessoas',
    palavra: 'Recomendado',
  },
  risco: { fundo: cores.erroFundo, cor: cores.erro, corDoIcone: cores.risco, icone: 'proibido', palavra: 'Evitar' },
};

interface Props {
  tipo: TipoDeSelo;
  /** Texto do selo (sem ele, a palavra do tipo: "Alerta", "Dados simulados"…). */
  texto?: string;
  /** m: 32 de altura; p: 26. */
  tamanho?: 'm' | 'p';
}

export function Selo({ tipo, texto: rotulo, tamanho = 'm' }: Props) {
  const v = VARIANTES[tipo];
  const pequeno = tamanho === 'p';
  return (
    <View style={[estilos.selo, pequeno ? estilos.pequeno : estilos.medio, { backgroundColor: v.fundo }]}>
      <Icone nome={v.icone} cor={v.corDoIcone} tamanho={pequeno ? 15 : 18} />
      <Text style={[pequeno ? texto.seloPequeno : texto.selo, estilos.texto, { color: v.cor }]}>
        {rotulo ?? v.palavra}
      </Text>
    </View>
  );
}

export function SeloDaSituacao({ situacao, tamanho }: { situacao: Situacao; tamanho?: 'm' | 'p' }) {
  return <Selo tipo={situacao} tamanho={tamanho} />;
}

/** Os selos que avisam algo sobre o rio: alerta antecipado, leitura atrasada, dados incompletos. */
export function SelosDoRio({ rio, tamanho = 'p' }: { rio: EstacaoPrevisao; tamanho?: 'm' | 'p' }) {
  const prevista = situacoes[rio.situacao_prevista];
  if (!rio.alerta_antecipado && !rio.leitura_velha && !rio.dados_incompletos) return null;
  return (
    <View style={estilos.linha}>
      {rio.alerta_antecipado ? (
        <Selo
          tipo="antecipado"
          tamanho={tamanho}
          texto={`Alerta antecipado: ${prevista.nome.toLowerCase()} em até 6 h`}
        />
      ) : null}
      {rio.leitura_velha ? (
        <Selo tipo="atrasada" tamanho={tamanho} texto="Leitura atrasada: a previsão pode não valer" />
      ) : null}
      {rio.dados_incompletos ? (
        <Selo tipo="incompletos" tamanho={tamanho} texto="Dados incompletos: previsão igual ao nível de agora" />
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  // Os selos quebram a linha dentro da largura disponível (nunca saem do cartão).
  linha: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, maxWidth: '100%' },
  selo: {
    alignSelf: 'flex-start',
    maxWidth: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: raio.selo,
  },
  medio: { minHeight: 32, paddingHorizontal: espaco.md, paddingVertical: 6, gap: 6 },
  pequeno: { minHeight: 26, paddingHorizontal: 10, paddingVertical: 5, gap: 5 },
  // Texto longo quebra a linha dentro do selo, sem sair dele.
  texto: { flexShrink: 1 },
});
