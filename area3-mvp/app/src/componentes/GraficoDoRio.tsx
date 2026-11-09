/**
 * Gráfico do rio (SVG): faixas das cotas, a linha das leituras recebidas desde que o app abriu
 * e o ponto tracejado da previsão para daqui a 6 h, na ponta direita.
 */
import { useState } from 'react';
import { Platform, StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';
import Svg, { Circle, Line, Polyline, Rect, Text as TextoSvg } from 'react-native-svg';

import type { EstacaoPrevisao, Situacao } from '@/api/tipos';
import type { Leitura } from '@/estado/historico';
import { metros } from '@/logica/formato';
import { faixaDoGrafico, marcasDoEixo, paraY, posicoesX } from '@/logica/grafico';
import { cores, espaco, situacoes, texto } from '@/tema';

const ALTURA = 240;
const MARGEM = { esquerda: 40, direita: 84, topo: 12, base: 26 };
/** No navegador, o texto do SVG usaria fonte serifada; usamos a mesma fonte do resto do app. */
const FONTE = Platform.select({ web: 'system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif' });
/** As leituras ocupam 78% da largura; a previsão fica sozinha na ponta. */
const PARTE_DAS_LEITURAS = 0.78;

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
  const corPrevista = situacoes[rio.situacao_prevista].forte;

  const faixas: [Situacao, number, number][] = [
    ['normal', faixa.min, cotas.atencao_m],
    ['atencao', cotas.atencao_m, cotas.alerta_m],
    ['alerta', cotas.alerta_m, cotas.inundacao_m],
    ['inundacao', cotas.inundacao_m, faixa.max],
  ];
  const linhasDeCota: [Situacao, number][] = [
    ['atencao', cotas.atencao_m],
    ['alerta', cotas.alerta_m],
    ['inundacao', cotas.inundacao_m],
  ];

  const descricao =
    `Gráfico do ${rio.corpo_hidrico}. Nível agora ${metros(rio.nivel_atual_m)}, ` +
    `previsto para daqui a 6 horas ${metros(rio.nivel_previsto_6h_m)}. ` +
    `Cotas: atenção ${metros(cotas.atencao_m)}, alerta ${metros(cotas.alerta_m)}, inundação ${metros(cotas.inundacao_m)}.`;

  return (
    <View style={estilos.caixa}>
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
                  width={larguraUtil}
                  height={y(de) - y(ate)}
                  fill={situacoes[s].fundo}
                />
              ) : null,
            )}

            {marcasDoEixo(faixa).map((m) => (
              <TextoSvg
                fontFamily={FONTE}
                key={m}
                x={MARGEM.esquerda - 6}
                y={y(m) + 4}
                fontSize={11}
                fill={cores.textoSuave}
                textAnchor="end"
              >
                {m.toFixed(1).replace('.', ',')}
              </TextoSvg>
            ))}

            {linhasDeCota.map(([s, cota]) => (
              <Line
                key={s}
                x1={MARGEM.esquerda}
                x2={MARGEM.esquerda + larguraUtil}
                y1={y(cota)}
                y2={y(cota)}
                stroke={situacoes[s].forte}
                strokeWidth={1.5}
                strokeDasharray="6 4"
              />
            ))}
            {linhasDeCota.map(([s, cota]) => (
              <TextoSvg
                fontFamily={FONTE}
                key={`rotulo-${s}`}
                x={MARGEM.esquerda + larguraUtil + 6}
                y={y(cota) + 4}
                fontSize={11}
                fontWeight="700"
                fill={situacoes[s].texto}
              >
                {`${situacoes[s].nome} ${cota.toFixed(2).replace('.', ',')}`}
              </TextoSvg>
            ))}

            {/* Previsão: tracejado do nível de agora até o previsto para daqui a 6 h. */}
            <Line
              x1={xAgora}
              y1={yAgora}
              x2={xPrevisao}
              y2={yPrevisao}
              stroke={corPrevista}
              strokeWidth={3}
              strokeDasharray="7 5"
            />

            {niveis.length > 1 ? (
              <Polyline
                points={niveis.map((n, i) => `${xs[i]},${y(n)}`).join(' ')}
                fill="none"
                stroke={cores.primariaEscura}
                strokeWidth={3}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            ) : null}

            <Circle cx={xAgora} cy={yAgora} r={6} fill={cores.primariaEscura} />
            <Circle cx={xPrevisao} cy={yPrevisao} r={7} fill={cores.superficie} stroke={corPrevista} strokeWidth={3} />

            <TextoSvg
              fontFamily={FONTE}
              x={xAgora}
              y={ALTURA - 8}
              fontSize={12}
              fontWeight="700"
              fill={cores.texto}
              textAnchor="middle"
            >
              agora
            </TextoSvg>
            <TextoSvg
              fontFamily={FONTE}
              x={xPrevisao}
              y={ALTURA - 8}
              fontSize={12}
              fontWeight="700"
              fill={cores.texto}
              textAnchor="middle"
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
          <View style={[estilos.amostra, { backgroundColor: cores.primariaEscura }]} />
          <Text style={texto.suave}>Leituras desde que você abriu o app</Text>
        </View>
        <View style={estilos.itemDaLegenda}>
          <View style={[estilos.amostra, estilos.amostraTracejada, { borderColor: corPrevista }]} />
          <Text style={texto.suave}>Previsão da IA para daqui a 6 horas</Text>
        </View>
      </View>
    </View>
  );
}

const estilos = StyleSheet.create({
  caixa: {
    backgroundColor: cores.superficie,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: cores.borda,
    paddingVertical: espaco.md,
    paddingHorizontal: espaco.sm,
    gap: espaco.sm,
  },
  legenda: { gap: 4, paddingHorizontal: espaco.sm },
  itemDaLegenda: { flexDirection: 'row', alignItems: 'center', gap: espaco.sm },
  amostra: { width: 24, height: 3, borderRadius: 2 },
  amostraTracejada: { height: 0, borderTopWidth: 3, borderStyle: 'dashed', backgroundColor: 'transparent' },
});
