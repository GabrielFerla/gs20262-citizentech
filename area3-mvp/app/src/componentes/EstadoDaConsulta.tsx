/**
 * Mostra uma consulta à API em qualquer estado, sem tela em branco:
 * - carregando pela primeira vez;
 * - erro sem nenhum dado ainda (com "Tentar de novo");
 * - erro depois de já ter dado: continua mostrando o último dado bom, com um aviso.
 */
import type { UseQueryResult } from '@tanstack/react-query';
import { type ReactNode, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { mensagemDoErro } from '@/api/cliente';
import { horaCurta } from '@/logica/formato';
import { cartao, cores, espaco, peso, raio, texto } from '@/tema';

import { Botao } from './Botao';
import { Icone } from './Icones';

interface Props<T> {
  consulta: UseQueryResult<T>;
  children: (dados: T) => ReactNode;
  carregando?: string;
  /** Enquanto carrega, mostra o contorno da faixa e de um cartão (tela Agora). */
  esqueleto?: boolean;
}

export function EstadoDaConsulta<T>({ consulta, children, carregando = 'Carregando…', esqueleto }: Props<T>) {
  const { data, error, failureReason, isRefetchError } = consulta;

  // Sem nenhum dado, cada atualização automática volta a consulta para "carregando" e apaga o erro
  // (é assim no TanStack Query). Para o aviso não piscar, guardamos a última falha vista.
  // (Ajuste de estado durante a renderização: padrão recomendado pelo React para lembrar o valor anterior.)
  const falhaAgora = error ?? failureReason;
  const [ultimaFalha, setUltimaFalha] = useState<unknown>(null);
  if (falhaAgora && falhaAgora !== ultimaFalha) setUltimaFalha(falhaAgora);
  const jaFalhou = consulta.errorUpdateCount > 0 || consulta.failureCount > 0;

  if (data === undefined) {
    if (!jaFalhou) {
      return (
        <>
          <View style={estilos.carregando} accessibilityRole="progressbar" accessibilityLabel={carregando}>
            <ActivityIndicator color={cores.primaria} size="small" />
            <Text style={estilos.carregandoTexto}>{carregando}</Text>
          </View>
          {esqueleto ? <Esqueleto /> : null}
        </>
      );
    }
    return <AvisoDeErro mensagem={mensagemDoErro(falhaAgora ?? ultimaFalha)} aoTentar={() => consulta.refetch()} />;
  }

  return (
    <>
      {isRefetchError || (error && !consulta.isFetching) ? (
        <AvisoDadoAntigo mensagem={mensagemDoErro(error)} desde={consulta.dataUpdatedAt} />
      ) : null}
      {children(data)}
    </>
  );
}

/** Contorno da faixa de situação e de um cartão de rio, enquanto os dados não chegam. */
function Esqueleto() {
  return (
    <View accessibilityElementsHidden importantForAccessibility="no-hide-descendants" style={estilos.esqueleto}>
      <View style={estilos.faixaVazia}>
        <View style={estilos.linhaDaFaixa}>
          <View style={[estilos.barraEscura, { width: 110, height: 22, borderRadius: raio.selo }]} />
          <View style={[estilos.barraEscura, { width: 84, height: 22, borderRadius: raio.selo }]} />
        </View>
        <View style={[estilos.barraEscura, { width: '86%', height: 26 }]} />
        <View style={[estilos.barraEscura, { width: '58%', height: 26 }]} />
        <View style={[estilos.barraEscura, { width: '100%', height: 16 }]} />
        <View style={[estilos.barraEscura, { width: '82%', height: 16 }]} />
        <View style={[estilos.barraEscura, estilos.botaoVazio]} />
      </View>
      <View style={estilos.titulosVazios}>
        <View style={[estilos.barraClara, { width: 230, height: 22 }]} />
        <View style={[estilos.barraClara, { width: 140, height: 16 }]} />
      </View>
      <View style={[cartao, estilos.cartaoVazio]}>
        <View style={[estilos.barraClara, { width: 130, height: 22 }]} />
        <View style={[estilos.barraClara, { width: 210, height: 16 }]} />
        <View style={[estilos.barraClara, { width: 96, height: 32 }]} />
        <View style={[estilos.barraClara, { width: '100%', height: 16 }]} />
        <View style={[estilos.barraClara, { width: '64%', height: 16 }]} />
      </View>
    </View>
  );
}

export function AvisoDeErro({ mensagem, aoTentar }: { mensagem: string; aoTentar?: () => void }) {
  return (
    <View style={[estilos.caixa, estilos.erro]} accessibilityRole="alert">
      <Text style={[texto.tituloCartao, { color: cores.erro }]}>Não deu para carregar</Text>
      <Text style={texto.corpoCartao}>{mensagem}</Text>
      {aoTentar ? (
        <Botao
          titulo="Tentar de novo"
          variante="secundario"
          pequeno
          icone="atualizar"
          aoTocar={aoTentar}
          estilo={estilos.tentar}
        />
      ) : null}
    </View>
  );
}

export function AvisoDadoAntigo({ mensagem, desde }: { mensagem: string; desde: number }) {
  return (
    <View style={[estilos.caixa, estilos.aviso]} accessibilityRole="alert">
      <View style={estilos.linhaDoAviso}>
        <Icone nome="semConexao" cor={cores.aviso} tamanho={24} />
        <Text style={estilos.avisoTitulo}>{mensagem}</Text>
      </View>
      {desde > 0 ? (
        <Text style={texto.corpoCartao}>Mostrando os últimos dados recebidos, das {horaCurta(new Date(desde))}.</Text>
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  carregando: { flexDirection: 'row', alignItems: 'center', gap: 10, minHeight: 24 },
  carregandoTexto: { ...texto.corpoCartao, ...peso('500'), color: cores.textoSuave },
  esqueleto: { gap: espaco.entreCartoes },
  faixaVazia: {
    height: 300,
    gap: 14,
    padding: espaco.faixa,
    borderRadius: raio.faixa,
    backgroundColor: cores.neutroFundo,
  },
  linhaDaFaixa: { flexDirection: 'row', justifyContent: 'space-between' },
  barraEscura: { backgroundColor: cores.borda, borderRadius: raio.sm },
  botaoVazio: { marginTop: 'auto', height: 54, borderRadius: raio.botao },
  titulosVazios: { gap: espaco.sm, marginTop: espaco.entreSecoes - espaco.entreCartoes },
  barraClara: { backgroundColor: cores.neutroFundo, borderRadius: raio.sm },
  cartaoVazio: { gap: espaco.md },
  caixa: { borderRadius: raio.botao, padding: 14, gap: 10, borderWidth: 1 },
  erro: { backgroundColor: cores.erroFundo, borderColor: cores.erroFundo },
  aviso: { backgroundColor: cores.avisoFundo, borderColor: cores.bordaAviso },
  linhaDoAviso: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  avisoTitulo: { ...peso('700'), fontSize: 17, lineHeight: 22, color: cores.texto, flex: 1 },
  tentar: { alignSelf: 'flex-start' },
});
