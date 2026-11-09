/**
 * Faixa do topo da tela Agora: a pior situação da cidade (cor, palavra e ícone), a mensagem em
 * linguagem simples e o botão. Normal fica em tom claro com check; as outras usam a cor forte cheia.
 */
import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import type { Situacao } from '@/api/tipos';
import { pedeParaSair, type Resumo } from '@/logica/situacao';
import { espaco, peso, raio, situacoes, texto } from '@/tema';

import { Botao } from './Botao';
import { Icone, type NomeDoIcone } from './Icones';

const ICONE: Record<Situacao, NomeDoIcone> = {
  normal: 'check',
  atencao: 'circuloExclamacao',
  alerta: 'trianguloExclamacao',
  inundacao: 'ondas',
};

export function FaixaDeSituacao({ resumo }: { resumo: Resumo }) {
  const router = useRouter();
  const c = situacoes[resumo.situacao];
  const urgente = pedeParaSair(resumo.situacao);
  // Sobre a cor cheia, tudo em sobreForte. No Normal (tom claro), o texto fica escuro (o sobreForte
  // do Normal) e só a palavra e o ícone ficam em verde.
  const corDoTexto = c.sobreForte;
  const corDaPalavra = c.cheia ? c.sobreForte : c.texto;

  return (
    <View
      style={[estilos.faixa, { backgroundColor: c.cheia ? c.forte : c.fundo, borderColor: c.bordaDaFaixa }]}
      accessibilityRole={resumo.situacao === 'normal' ? 'summary' : 'alert'}
    >
      <View style={estilos.topo}>
        <Icone nome={ICONE[resumo.situacao]} cor={corDaPalavra} tamanho={26} />
        <Text style={[estilos.rotulo, { color: corDaPalavra }]}>
          {resumo.rio?.alerta_antecipado ? 'Aviso antecipado pela previsão' : `Situação: ${c.nome}`}
        </Text>
      </View>
      <View style={estilos.mensagem}>
        <Text style={[texto.tituloFaixa, { color: corDoTexto }]}>{resumo.titulo}</Text>
        <Text style={[texto.corpo, { color: corDoTexto }]}>{resumo.texto}</Text>
      </View>
      {resumo.situacao !== 'normal' ? (
        <Botao
          titulo="Onde ficar seguro"
          // Sobre o amarelo, botão escuro (branco some); sobre laranja e vermelho, botão branco.
          variante={resumo.situacao === 'atencao' ? 'escuro' : 'claro'}
          grande={urgente}
          icone="setaDireita"
          iconeNoFim
          dica="Mostra os abrigos com vaga que não devem alagar"
          aoTocar={() => router.navigate('/abrigos')}
        />
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  faixa: { borderRadius: raio.faixa, borderWidth: 1, padding: espaco.faixa, gap: 14 },
  topo: { flexDirection: 'row', alignItems: 'center', gap: espaco.sm },
  rotulo: {
    ...peso('800'),
    flexShrink: 1,
    fontSize: 16,
    lineHeight: 20,
    letterSpacing: 1.28,
    textTransform: 'uppercase',
  },
  mensagem: { gap: espaco.sm },
});
