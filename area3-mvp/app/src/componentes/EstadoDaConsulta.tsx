/**
 * Mostra uma consulta à API em qualquer estado, sem tela em branco:
 * - carregando pela primeira vez;
 * - erro sem nenhum dado ainda (com "Tentar de novo");
 * - erro depois de já ter dado: continua mostrando o último dado bom, com um aviso.
 */
import type { UseQueryResult } from '@tanstack/react-query';
import { type ReactNode, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { mensagemDoErro } from '@/api/cliente';
import { horaCurta } from '@/logica/formato';
import { ALVO_DE_TOQUE, cores, espaco, raio, texto } from '@/tema';

interface Props<T> {
  consulta: UseQueryResult<T>;
  children: (dados: T) => ReactNode;
  carregando?: string;
}

export function EstadoDaConsulta<T>({ consulta, children, carregando = 'Carregando…' }: Props<T>) {
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
        <View style={estilos.centro} accessibilityRole="progressbar" accessibilityLabel={carregando}>
          <ActivityIndicator color={cores.primaria} size="large" />
          <Text style={texto.suave}>{carregando}</Text>
        </View>
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

export function AvisoDeErro({ mensagem, aoTentar }: { mensagem: string; aoTentar?: () => void }) {
  return (
    <View style={[estilos.caixa, estilos.erro]} accessibilityRole="alert">
      <Text style={[texto.subtitulo, { color: cores.erro }]}>Não deu para carregar</Text>
      <Text style={texto.corpo}>{mensagem}</Text>
      {aoTentar ? (
        <Pressable
          onPress={aoTentar}
          accessibilityRole="button"
          style={({ pressed }) => [estilos.botao, pressed && { opacity: 0.8 }]}
        >
          <Text style={estilos.botaoTexto}>Tentar de novo</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

export function AvisoDadoAntigo({ mensagem, desde }: { mensagem: string; desde: number }) {
  return (
    <View style={[estilos.caixa, estilos.aviso]} accessibilityRole="alert">
      <Text style={[texto.corpo, { color: cores.aviso, fontWeight: '700' }]}>{mensagem}</Text>
      {desde > 0 ? (
        <Text style={texto.suave}>Mostrando os últimos dados recebidos, das {horaCurta(new Date(desde))}.</Text>
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  centro: { alignItems: 'center', gap: espaco.sm, paddingVertical: espaco.xxl },
  caixa: { borderRadius: raio.md, padding: espaco.lg, gap: espaco.sm, borderWidth: 1 },
  erro: { backgroundColor: cores.erroFundo, borderColor: '#F4B4AE' },
  aviso: { backgroundColor: cores.avisoFundo, borderColor: '#F1D27A' },
  botao: {
    alignSelf: 'flex-start',
    minHeight: ALVO_DE_TOQUE,
    justifyContent: 'center',
    paddingHorizontal: espaco.lg,
    borderRadius: raio.md,
    backgroundColor: cores.primaria,
  },
  botaoTexto: { color: '#FFFFFF', fontSize: 16, fontWeight: '700' },
});
