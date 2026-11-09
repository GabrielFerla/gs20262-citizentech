/**
 * Onde ficar seguro: os 3 abrigos aptos mais perto (vaga quando a pessoa chegar e fora de área
 * que deve alagar) e os mais perto que foram evitados, com o motivo. Dois jeitos:
 * - Meu bairro: a API recomenda a partir do centro do bairro (GET /abrigos/recomendacao);
 * - Minha localização: a API avalia todos os abrigos (GET /abrigos) e o APARELHO calcula a distância,
 *   descarta os que lotam antes de a pessoa chegar e ordena. A posição não sai do celular (LGPD).
 */
import { useIsFocused } from 'expo-router';
import { type ReactNode, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { useAbrigos, useRecomendacao } from '@/api/consultas';
import type { AbrigoAvaliado, Recomendacao } from '@/api/tipos';
import { Alternador } from '@/componentes/Alternador';
import { Botao } from '@/componentes/Botao';
import { CartaoDoAbrigo } from '@/componentes/CartaoDoAbrigo';
import { EstadoDaConsulta } from '@/componentes/EstadoDaConsulta';
import { Icone } from '@/componentes/Icones';
import { SeletorDeBairro } from '@/componentes/SeletorDeBairro';
import { SeletorDePessoas } from '@/componentes/SeletorDePessoas';
import { Tela } from '@/componentes/Tela';
import { localizar, mensagemDaFalha, usePosicao } from '@/estado/posicao';
import { usePreferencias } from '@/estado/preferencias';
import { abrigosPerto, type Posicao } from '@/logica/geo';
import { cartao, cores, espaco, peso, raio, situacoes, texto } from '@/tema';

type Modo = 'bairro' | 'localizacao';

/** Cartão "Ponto de partida": o alternador, de onde sair e quantas pessoas vão. */
function PontoDePartida({ children }: { children: ReactNode }) {
  return <View style={estilos.partida}>{children}</View>;
}

function Divisoria() {
  return <View style={estilos.divisoria} />;
}

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
      <Text style={[texto.tituloSecao, estilos.secao]} accessibilityRole="header">
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
          <View style={estilos.semAbrigoTitulo}>
            <Icone nome="proibido" cor={cores.risco} tamanho={22} />
            <Text style={[texto.tituloCartao, estilos.textoDeRisco]}>Nenhum abrigo seguro com vaga agora</Text>
          </View>
          <Text style={texto.corpoCartao}>
            Não há abrigo com vaga para {pessoas} {pessoas === 1 ? 'pessoa' : 'pessoas'} fora de área de risco. Procure
            um lugar alto e ligue 199 (Defesa Civil) ou 193 (Bombeiros).
          </Text>
        </View>
      )}

      {evitados.length > 0 ? (
        <>
          <Text style={[texto.tituloSecao, estilos.secao]} accessibilityRole="header">
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

function PorBairro({ ativa, topo }: { ativa: boolean; topo: ReactNode }) {
  const { carregado, valores, salvar } = usePreferencias();
  const recomendacao = useRecomendacao(valores.bairroId, valores.pessoas, ativa);

  return (
    <>
      <PontoDePartida>
        {topo}
        <View style={estilos.dentro}>
          <SeletorDeBairro
            bairroNome={valores.bairroNome}
            aoEscolher={(b) => salvar({ bairroId: b.bairro_id, bairroNome: b.bairro })}
          />
        </View>
        <Divisoria />
        <View style={estilos.dentro}>
          <SeletorDePessoas pessoas={valores.pessoas} aoMudar={(pessoas) => salvar({ pessoas })} />
        </View>
      </PontoDePartida>
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
  topo,
}: {
  ativa: boolean;
  posicao: Posicao;
  aoAtualizar: () => void;
  topo: ReactNode;
}) {
  const { valores, salvar } = usePreferencias();
  // A API recebe só o número de pessoas; a distância e a ordem são calculadas aqui.
  const abrigos = useAbrigos(valores.pessoas, ativa);

  return (
    <>
      <PontoDePartida>
        {topo}
        <View style={[estilos.dentro, estilos.privacidade]}>
          <View style={estilos.linhaComIcone}>
            <Icone nome="cadeado" cor={cores.primaria} tamanho={20} />
            <Text style={estilos.privacidadeTitulo}>Sua localização fica só neste aparelho.</Text>
          </View>
          <Text style={texto.apoio}>
            O servidor manda a situação de todos os abrigos, e a conta da distância é feita aqui no celular.
          </Text>
          <Botao
            titulo="Atualizar minha localização"
            variante="secundario"
            pequeno
            icone="mira"
            aoTocar={aoAtualizar}
            estilo={estilos.atualizar}
          />
        </View>
        <Divisoria />
        <View style={estilos.dentro}>
          <SeletorDePessoas pessoas={valores.pessoas} aoMudar={(pessoas) => salvar({ pessoas })} />
        </View>
      </PontoDePartida>
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

  // O alternador (e o aviso de quando a localização falha) abrem o cartão "Ponto de partida".
  const topo = (
    <>
      <Alternador
        rotulo="De onde calcular a distância"
        opcoes={[
          { valor: 'bairro', rotulo: 'Meu bairro', icone: 'alfinete' },
          { valor: 'localizacao', rotulo: 'Minha localização', icone: 'mira' },
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
          <Text style={[texto.corpoCartao, { color: cores.aviso }]}>{aviso}</Text>
        </View>
      ) : null}
    </>
  );

  return (
    <Tela titulo="Onde ficar seguro">
      <Text style={texto.corpo}>
        Abrigos que devem ter vaga quando você chegar e que ficam fora de área que deve alagar nas próximas 6 horas.
      </Text>

      {modo === 'bairro' ? <PorBairro ativa={ativa} topo={topo} /> : null}
      {modo === 'localizacao' && procurando ? (
        <>
          <PontoDePartida>{topo}</PontoDePartida>
          <Text style={[texto.corpo, estilos.dica]}>Procurando sua localização…</Text>
        </>
      ) : null}
      {modo === 'localizacao' && !procurando && posicao ? (
        <PorLocalizacao ativa={ativa} posicao={posicao} aoAtualizar={() => void usarLocalizacao()} topo={topo} />
      ) : null}
    </Tela>
  );
}

const estilos = StyleSheet.create({
  // Entre seções, 28 (os 12 entre cartões + 16).
  secao: { marginTop: espaco.entreSecoes - espaco.entreCartoes },
  nota: { marginTop: espaco.sm },
  dica: { color: cores.textoSuave, textAlign: 'center', paddingVertical: espaco.lg },
  partida: { ...cartao, padding: espaco.md, gap: espaco.md },
  dentro: { paddingHorizontal: espaco.xs },
  divisoria: { height: 1, marginHorizontal: espaco.xs, backgroundColor: cores.borda },
  semAbrigo: {
    backgroundColor: cores.erroFundo,
    borderRadius: raio.botao,
    padding: 14,
    gap: 10,
  },
  semAbrigoTitulo: { flexDirection: 'row', alignItems: 'center', gap: espaco.sm },
  textoDeRisco: { color: cores.erro, flexShrink: 1 },
  aviso: {
    backgroundColor: cores.avisoFundo,
    borderRadius: raio.controle,
    padding: espaco.md,
    borderWidth: 1,
    borderColor: cores.bordaAviso,
  },
  privacidade: { gap: espaco.sm },
  linhaComIcone: { flexDirection: 'row', alignItems: 'center', gap: espaco.sm },
  privacidadeTitulo: { ...texto.corpoCartao, ...peso('700'), flexShrink: 1 },
  atualizar: { alignSelf: 'flex-start' },
});
