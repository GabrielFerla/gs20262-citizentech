/**
 * Onde ficar seguro: os 3 abrigos aptos mais perto (vaga quando a pessoa chegar e fora de área
 * que deve alagar) e os mais perto que foram evitados, com o motivo. Dois jeitos:
 * - Meu bairro: a API recomenda a partir do centro do bairro (GET /abrigos/recomendacao);
 * - Minha localização: a API avalia todos os abrigos (GET /abrigos) e o APARELHO calcula a distância,
 *   descarta os que lotam antes de a pessoa chegar e ordena. A posição não sai do celular (LGPD).
 */
import { useIsFocused } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { useAbrigos, useRecomendacao } from '@/api/consultas';
import type { AbrigoAvaliado, Recomendacao } from '@/api/tipos';
import { Alternador } from '@/componentes/Alternador';
import { Botao } from '@/componentes/Botao';
import { CartaoDoAbrigo } from '@/componentes/CartaoDoAbrigo';
import { EstadoDaConsulta } from '@/componentes/EstadoDaConsulta';
import { SeletorDeBairro } from '@/componentes/SeletorDeBairro';
import { SeletorDePessoas } from '@/componentes/SeletorDePessoas';
import { Tela } from '@/componentes/Tela';
import { localizar, mensagemDaFalha, usePosicao } from '@/estado/posicao';
import { usePreferencias } from '@/estado/preferencias';
import { abrigosPerto, type Posicao } from '@/logica/geo';
import { cores, espaco, raio, situacoes, texto } from '@/tema';

type Modo = 'bairro' | 'localizacao';

interface ItemDaLista {
  abrigo: AbrigoAvaliado;
  vagasNaChegada: number | null;
  motivo: string | null;
}

/** Recomendados e evitados: a mesma apresentação nos dois modos. */
function ListaDeAbrigos({
  recomendados,
  evitados,
  pessoas,
  origem,
  nota,
}: {
  recomendados: ItemDaLista[];
  evitados: ItemDaLista[];
  pessoas: number;
  origem: Modo;
  nota: string;
}) {
  return (
    <>
      <Text style={texto.subtitulo} accessibilityRole="header">
        Vá para um destes
      </Text>
      {recomendados.length > 0 ? (
        recomendados.map((r, i) => (
          <CartaoDoAbrigo
            key={r.abrigo.abrigo_id}
            abrigo={r.abrigo}
            ordem={i + 1}
            vagasNaChegada={r.vagasNaChegada}
            origem={origem}
          />
        ))
      ) : (
        <View style={estilos.semAbrigo} accessibilityRole="alert">
          <Text style={[texto.subtitulo, { color: cores.erro }]}>Nenhum abrigo seguro com vaga agora</Text>
          <Text style={texto.corpo}>
            Não há abrigo com vaga para {pessoas} {pessoas === 1 ? 'pessoa' : 'pessoas'} fora de área de risco. Procure
            um lugar alto e ligue 199 (Defesa Civil) ou 193 (Bombeiros).
          </Text>
        </View>
      )}

      {evitados.length > 0 ? (
        <>
          <Text style={[texto.subtitulo, estilos.secao]} accessibilityRole="header">
            Evitamos estes, mais perto de você
          </Text>
          <Text style={texto.suave}>Ficam mais perto, mas não são seguros agora:</Text>
          {evitados.map((r) => (
            <CartaoDoAbrigo key={r.abrigo.abrigo_id} abrigo={r.abrigo} motivo={r.motivo} origem={origem} />
          ))}
        </>
      ) : null}

      <Text style={[texto.suave, estilos.nota]}>{nota}</Text>
    </>
  );
}

function RioDaRegiao({ r }: { r: Recomendacao }) {
  const rio = r.estacao_da_regiao;
  if (!rio) return null;
  const agora = situacoes[rio.situacao_atual];
  const depois = situacoes[rio.situacao_prevista];
  return (
    <Text style={texto.suave}>
      Rio da região de {r.bairro}: {rio.corpo_hidrico}, agora em {agora.nome.toLowerCase()}, em 6 h em{' '}
      {depois.nome.toLowerCase()}.
    </Text>
  );
}

function PorBairro({ ativa }: { ativa: boolean }) {
  const { carregado, valores, salvar } = usePreferencias();
  const recomendacao = useRecomendacao(valores.bairroId, valores.pessoas, ativa);

  return (
    <>
      <SeletorDeBairro
        bairroNome={valores.bairroNome}
        aoEscolher={(b) => salvar({ bairroId: b.bairro_id, bairroNome: b.bairro })}
      />
      <SeletorDePessoas pessoas={valores.pessoas} aoMudar={(pessoas) => salvar({ pessoas })} />
      {carregado && !valores.bairroId ? (
        <Text style={[texto.corpo, estilos.dica]}>Escolha o bairro para ver os abrigos seguros mais perto.</Text>
      ) : null}
      {valores.bairroId ? (
        <EstadoDaConsulta consulta={recomendacao} carregando="Procurando abrigos seguros…">
          {(r) => (
            <>
              <RioDaRegiao r={r} />
              <ListaDeAbrigos
                recomendados={r.recomendados.map((a) => ({
                  abrigo: a,
                  vagasNaChegada: a.vagas_previstas_na_chegada,
                  motivo: null,
                }))}
                evitados={r.evitados.map((a) => ({ abrigo: a, vagasNaChegada: null, motivo: a.motivo }))}
                pessoas={r.pessoas}
                origem="bairro"
                nota="O tempo a pé é estimado a partir do centro do bairro (linha reta × 1,3, a 4 km/h). Sua localização exata não é usada."
              />
            </>
          )}
        </EstadoDaConsulta>
      ) : null}
    </>
  );
}

function PorLocalizacao({
  ativa,
  posicao,
  aoAtualizar,
}: {
  ativa: boolean;
  posicao: Posicao;
  aoAtualizar: () => void;
}) {
  const { valores, salvar } = usePreferencias();
  // A API recebe só o número de pessoas; a distância e a ordem são calculadas aqui.
  const abrigos = useAbrigos(valores.pessoas, ativa);

  return (
    <>
      <View style={estilos.privacidade}>
        <Text style={[texto.corpo, { fontWeight: '700' }]}>Sua localização fica só neste aparelho.</Text>
        <Text style={texto.suave}>
          O servidor manda a situação de todos os abrigos, e a conta da distância é feita aqui no celular.
        </Text>
        <Botao titulo="Atualizar minha localização" variante="secundario" aoTocar={aoAtualizar} />
      </View>
      <SeletorDePessoas pessoas={valores.pessoas} aoMudar={(pessoas) => salvar({ pessoas })} />
      <EstadoDaConsulta consulta={abrigos} carregando="Procurando abrigos seguros…">
        {(lista) => {
          const { recomendados, evitados } = abrigosPerto(lista, posicao);
          return (
            <ListaDeAbrigos
              recomendados={recomendados.map((a) => ({ abrigo: a, vagasNaChegada: a.vagas_na_chegada, motivo: null }))}
              evitados={evitados.map((a) => ({ abrigo: a, vagasNaChegada: null, motivo: a.motivo_final }))}
              pessoas={valores.pessoas}
              origem="localizacao"
              nota="O tempo a pé é estimado a partir de onde você está (linha reta × 1,3, a 4 km/h)."
            />
          );
        }}
      </EstadoDaConsulta>
    </>
  );
}

export default function OndeFicarSeguro() {
  const ativa = useIsFocused();
  const posicao = usePosicao();
  const [modo, setModo] = useState<Modo>('bairro');
  const [procurando, setProcurando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  async function usarLocalizacao() {
    setModo('localizacao');
    setAviso(null);
    setProcurando(true);
    const resultado = await localizar();
    setProcurando(false);
    if (!resultado.ok) {
      setAviso(mensagemDaFalha(resultado));
      setModo('bairro');
    }
  }

  return (
    <Tela>
      <Text style={texto.corpo}>
        Abrigos que devem ter vaga quando você chegar e que ficam fora de área que deve alagar nas próximas 6 horas.
      </Text>
      <Alternador
        rotulo="De onde calcular a distância"
        opcoes={[
          { valor: 'bairro', rotulo: 'Meu bairro' },
          { valor: 'localizacao', rotulo: 'Minha localização' },
        ]}
        valor={modo}
        aoMudar={(novo) => {
          if (novo === 'localizacao') void usarLocalizacao();
          else {
            setModo('bairro');
            setAviso(null);
          }
        }}
      />
      {aviso ? (
        <View style={estilos.aviso} accessibilityRole="alert">
          <Text style={[texto.corpo, { color: cores.aviso }]}>{aviso}</Text>
        </View>
      ) : null}

      {modo === 'bairro' ? <PorBairro ativa={ativa} /> : null}
      {modo === 'localizacao' && procurando ? (
        <Text style={[texto.corpo, estilos.dica]}>Procurando sua localização…</Text>
      ) : null}
      {modo === 'localizacao' && !procurando && posicao ? (
        <PorLocalizacao ativa={ativa} posicao={posicao} aoAtualizar={() => void usarLocalizacao()} />
      ) : null}
    </Tela>
  );
}

const estilos = StyleSheet.create({
  secao: { marginTop: espaco.md },
  nota: { marginTop: espaco.sm },
  dica: { color: cores.textoSuave, textAlign: 'center', paddingVertical: espaco.lg },
  semAbrigo: {
    backgroundColor: cores.erroFundo,
    borderRadius: raio.lg,
    padding: espaco.lg,
    gap: espaco.sm,
    borderWidth: 1,
    borderColor: '#F4B4AE',
  },
  aviso: {
    backgroundColor: cores.avisoFundo,
    borderRadius: raio.md,
    padding: espaco.md,
    borderWidth: 1,
    borderColor: '#F1D27A',
  },
  privacidade: {
    backgroundColor: cores.primariaClara,
    borderRadius: raio.lg,
    padding: espaco.lg,
    gap: espaco.sm,
    borderWidth: 1,
    borderColor: '#B9DCE6',
  },
});
