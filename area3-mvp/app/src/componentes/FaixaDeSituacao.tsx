/** Faixa do topo da tela Agora: a pior situação da cidade, a mensagem em linguagem simples e o botão. */
import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { pedeParaSair, type Resumo } from '@/logica/situacao';
import { espaco, raio, situacoes } from '@/tema';

import { Botao } from './Botao';

export function FaixaDeSituacao({ resumo }: { resumo: Resumo }) {
  const router = useRouter();
  const c = situacoes[resumo.situacao];
  const urgente = pedeParaSair(resumo.situacao);

  return (
    <View
      style={[estilos.faixa, { backgroundColor: c.forte }]}
      accessibilityRole={resumo.situacao === 'normal' ? 'summary' : 'alert'}
    >
      <Text style={[estilos.rotulo, { color: c.sobreForte }]}>
        {resumo.rio?.alerta_antecipado ? 'Aviso antecipado pela previsão' : `Situação: ${c.nome}`}
      </Text>
      <Text style={[estilos.titulo, { color: c.sobreForte }]}>{resumo.titulo}</Text>
      <Text style={[estilos.texto, { color: c.sobreForte }]}>{resumo.texto}</Text>
      {resumo.situacao !== 'normal' ? (
        <Botao
          titulo="Onde ficar seguro"
          variante="claro"
          corDoTexto={resumo.situacao === 'atencao' ? c.sobreForte : c.forte}
          grande={urgente}
          dica="Mostra os abrigos com vaga que não devem alagar"
          aoTocar={() => router.navigate('/abrigos')}
          estilo={estilos.botao}
        />
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  faixa: { borderRadius: raio.lg, padding: espaco.lg, gap: espaco.sm },
  rotulo: { fontSize: 13, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },
  titulo: { fontSize: 24, fontWeight: '800', lineHeight: 30 },
  texto: { fontSize: 17, lineHeight: 24 },
  botao: { marginTop: espaco.xs },
});
