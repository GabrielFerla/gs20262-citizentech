/**
 * Gráfico do rio (SVG): faixas das cotas, a linha das leituras recebidas desde que o app abriu
 * e o ponto tracejado da previsão para daqui a 6 h, na ponta direita.
 * Só Rect, Line, Polyline, Circle e Text, sem gradiente; cada cota tem cor, palavra e ícone.
 */
import { useState } from 'react';
import { StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';
import Svg, { Circle, Line, Polyline, Rect, Text as TextoSvg } from 'react-native-svg';

import type { EstacaoPrevisao, Situacao } from '@/api/tipos';
import type { Leitura } from '@/estado/historico';
import { metros } from '@/logica/formato';
import { faixaDoGrafico, marcasDoEixo, paraY, posicoesX } from '@/logica/grafico';
import { cartao, cores, espaco, familias, peso, situacoes } from '@/tema';

import { DECORATIVO, FormasDoIcone, type NomeDoIcone } from './Icones';

const ALTURA = 224;
// À esquerda, as marcas do eixo; os rótulos das cotas ficam dentro das faixas, à esquerda.
const MARGEM = { esquerda: 36, direita: 12, topo: 12, base: 28 };
/** As leituras ocupam 78% da largura; a previsão fica sozinha na ponta. */
const PARTE_DAS_LEITURAS = 0.78;

const ICONE_DA_COTA: Record<Exclude<Situacao, 'normal'>, NomeDoIcone> = {
  atencao: 'circuloExclamacao',
  alerta: 'trianguloExclamacao',
  inundacao: 'ondas',
};

interface Props {
  rio: EstacaoPrevisao;
  leituras: readonly Leitura[];
}

export function GraficoDoRio({ rio, leituras }: Props) {
  const [largura, setLargura] = useState(0);
  const aoMedir = (e: LayoutChangeEvent) => setLargura(Math.round(e.nativeEvent.layout.width));

  // A leitura de agora entra sempre (mesmo antes de o histórico registrar).
  const niveis = leituras.map((l) => l.nivel);
  if (leituras.at(-1)?.medidoEm !== rio.medido_em_utc || niveis.length === 0) niveis.push(rio.nivel_atual_m);

  const { cotas } = rio;
  const faixa = faixaDoGrafico([...niveis, rio.nivel_previsto_6h_m], cotas);
  const alturaUtil = ALTURA - MARGEM.topo - MARGEM.base;
  const larguraUtil = Math.max(largura - MARGEM.esquerda - MARGEM.direita, 10);
  const y = (v: number) => paraY(v, faixa, MARGEM.topo, alturaUtil);
  const xs = posicoesX(niveis.length, MARGEM.esquerda, larguraUtil * PARTE_DAS_LEITURAS);
  const xAgora = xs.at(-1) ?? MARGEM.esquerda;
  const xPrevisao = MARGEM.esquerda + larguraUtil;
  const yAgora = y(rio.nivel_atual_m);
  const yPrevisao = y(rio.nivel_previsto_6h_m);
  const yBase = ALTURA - MARGEM.base;

  // Faixas coloridas só acima da cota de atenção (o Normal fica em branco).
  const faixas: [Exclude<Situacao, 'normal'>, number, number][] = [
    ['atencao', cotas.atencao_m, cotas.alerta_m],
    ['alerta', cotas.alerta_m, cotas.inundacao_m],
    ['inundacao', cotas.inundacao_m, faixa.max],
  ];

  const descricao =
    `Gráfico do ${rio.corpo_hidrico}. Nível agora ${metros(rio.nivel_atual_m)}, ` +
    `previsto para daqui a 6 horas ${metros(rio.nivel_previsto_6h_m)}. ` +
    `Cotas: atenção ${metros(cotas.atencao_m)}, alerta ${metros(cotas.alerta_m)}, inundação ${metros(cotas.inundacao_m)}.`;

  return (
    <View style={estilos.cartao}>
      <View
        onLayout={aoMedir}
        accessible
        accessibilityRole="image"
        accessibilityLabel={descricao}
        testID="grafico-do-rio"
      >
        {largura > 0 ? (
          <Svg width={largura} height={ALTURA}>
            {faixas.map(([s, de, ate]) =>
              ate > de ? (
                <Rect
                  key={s}
                  x={MARGEM.esquerda}
                  y={y(ate)}
                  width={largura - MARGEM.esquerda}
                  height={y(de) - y(ate)}
                  fill={situacoes[s].fundo}
                />
              ) : null,
            )}

            <Line x1={MARGEM.esquerda} x2={largura} y1={yBase} y2={yBase} stroke={cores.borda} strokeWidth={1} />
            {marcasDoEixo(faixa).map((m) => (
              <TextoSvg
                key={m}
                fontFamily={familias['500']}
                x={MARGEM.esquerda - 6}
                y={y(m) + 4}
                fontSize={12}
                fill={cores.textoSuave}
                textAnchor="end"
              >
                {m.toFixed(1).replace('.', ',')}
              </TextoSvg>
            ))}

            {faixas.map(([s, cota]) => (
              <Line
                key={`linha-${s}`}
                x1={MARGEM.esquerda}
                x2={largura}
                y1={y(cota)}
                y2={y(cota)}
                stroke={situacoes[s].texto}
                strokeWidth={1.5}
              />
            ))}

            {/* "Agora" divide as leituras (à esquerda) da previsão (à direita). */}
            <Line x1={xAgora} x2={xAgora} y1={MARGEM.topo} y2={yBase} stroke={cores.textoSuave} strokeWidth={1.5} />

            {niveis.length > 1 ? (
              <Polyline
                points={niveis.map((n, i) => `${xs[i]},${y(n)}`).join(' ')}
                fill="none"
                stroke={cores.texto}
                strokeWidth={2.5}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            ) : null}
            {/* Previsão: tracejado do nível de agora até o previsto para daqui a 6 h. */}
            <Line
              x1={xAgora}
              y1={yAgora}
              x2={xPrevisao}
              y2={yPrevisao}
              stroke={cores.texto}
              strokeWidth={2.5}
              strokeDasharray="7 5"
            />

            {/* Rótulo de cada cota: ícone e palavra, com um contorno da cor da faixa para ler sobre a linha. */}
            {faixas.map(([s, cota]) => {
              const base = y(cota) - 6;
              const rotulo = `${situacoes[s].nome} ${cota.toFixed(2).replace('.', ',')}`;
              const xTexto = MARGEM.esquerda + 26;
              return [
                <FormasDoIcone
                  key={`icone-${s}`}
                  nome={ICONE_DA_COTA[s]}
                  cor={cores.texto}
                  x={MARGEM.esquerda + 6}
                  y={base - 12}
                  tamanho={15}
                />,
                <TextoSvg
                  key={`contorno-${s}`}
                  fontFamily={familias['700']}
                  x={xTexto}
                  y={base}
                  fontSize={13}
                  fill={situacoes[s].fundo}
                  stroke={situacoes[s].fundo}
                  strokeWidth={4}
                  strokeLinejoin="round"
                >
                  {rotulo}
                </TextoSvg>,
                <TextoSvg
                  key={`rotulo-${s}`}
                  fontFamily={familias['700']}
                  x={xTexto}
                  y={base}
                  fontSize={13}
                  fill={cores.texto}
                >
                  {rotulo}
                </TextoSvg>,
              ];
            })}

            <Circle cx={xAgora} cy={yAgora} r={5.5} fill={cores.texto} stroke={cores.superficie} strokeWidth={2} />
            <Circle
              cx={xPrevisao}
              cy={yPrevisao}
              r={5}
              fill={cores.superficie}
              stroke={cores.texto}
              strokeWidth={2.5}
            />

            <TextoSvg
              fontFamily={familias['800']}
              x={xAgora}
              y={ALTURA - 8}
              fontSize={13}
              fill={cores.texto}
              textAnchor="middle"
            >
              agora
            </TextoSvg>
            <TextoSvg
              fontFamily={familias['500']}
              x={largura - 2}
              y={ALTURA - 8}
              fontSize={13}
              fill={cores.textoSuave}
              textAnchor="end"
            >
              em 6 h
            </TextoSvg>
          </Svg>
        ) : (
          <View style={{ height: ALTURA }} />
        )}
      </View>

      <View style={estilos.legenda}>
        <View style={estilos.itemDaLegenda}>
          <Amostra />
          <Text style={estilos.textoDaLegenda}>Leituras desde que você abriu o app</Text>
        </View>
        <View style={estilos.itemDaLegenda}>
          <Amostra tracejada />
          <Text style={estilos.textoDaLegenda}>Previsão da IA para daqui a 6 horas</Text>
        </View>
      </View>
    </View>
  );
}

function Amostra({ tracejada }: { tracejada?: boolean }) {
  return (
    <Svg width={28} height={10} {...DECORATIVO}>
      <Line
        x1={tracejada ? 0 : 1.5}
        x2={tracejada ? 28 : 26.5}
        y1={5}
        y2={5}
        stroke={cores.texto}
        strokeWidth={2.5}
        strokeLinecap={tracejada ? 'butt' : 'round'}
        strokeDasharray={tracejada ? '7 5' : undefined}
      />
    </Svg>
  );
}

const estilos = StyleSheet.create({
  cartao: { ...cartao, gap: espaco.md },
  legenda: { gap: espaco.sm },
  itemDaLegenda: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  textoDaLegenda: { ...peso('500'), fontSize: 15, lineHeight: 20, color: cores.texto, flexShrink: 1 },
});
