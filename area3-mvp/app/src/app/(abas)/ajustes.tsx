/**
 * Ajustes: bairro e tamanho do grupo (guardados só no aparelho), avisos de alerta,
 * situação do sistema (GET /saude) e "Sobre": dados simulados, privacidade e créditos.
 */
import Constants from 'expo-constants';
import { useEffect, useState } from 'react';
import { Platform, Pressable, StyleSheet, Text, View } from 'react-native';

import { urlBaseDaApi } from '@/api/cliente';
import { useSaude } from '@/api/consultas';
import { Botao } from '@/componentes/Botao';
import { EstadoDaConsulta } from '@/componentes/EstadoDaConsulta';
import { Icone } from '@/componentes/Icones';
import { SeletorDeBairro } from '@/componentes/SeletorDeBairro';
import { SeletorDePessoas } from '@/componentes/SeletorDePessoas';
import { Tela } from '@/componentes/Tela';
import { estadoDaPermissao, pedirPermissao, type EstadoDaPermissao } from '@/estado/notificacoes';
import { usePreferencias } from '@/estado/preferencias';
import { horaCurta } from '@/logica/formato';
import { cartao, cores, espaco, peso, raio, texto } from '@/tema';

/** Cada seção é um cartão com o título em rótulo verde. */
function Secao({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <View style={estilos.secao}>
      <Text style={texto.rotulo} accessibilityRole="header">
        {titulo}
      </Text>
      {children}
    </View>
  );
}

function Divisoria() {
  return <View style={estilos.divisoria} />;
}

function Item({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <View style={estilos.item}>
      <Text style={texto.apoio}>{rotulo}</Text>
      <Text style={estilos.valor}>{valor}</Text>
    </View>
  );
}

function SituacaoDoSistema() {
  const saude = useSaude();
  return (
    <EstadoDaConsulta consulta={saude} carregando="Consultando o servidor…">
      {(s) => (
        <View style={estilos.itens}>
          <Item rotulo="Servidor" valor={s.status === 'ok' ? 'No ar' : s.status} />
          <Item rotulo="Banco de dados" valor={s.banco ? 'Acessível' : 'Fora do ar'} />
          <Item rotulo="Previsão" valor={`${s.modelo.estacoes.length} rios, ${s.modelo.horizonte_h} h à frente`} />
          <Item
            rotulo="Vigia de alertas (última rodada)"
            valor={s.vigia.ultima_rodada_utc ? horaCurta(new Date(s.vigia.ultima_rodada_utc)) : 'ainda não rodou'}
          />
          {s.vigia.ultimo_erro ? <Item rotulo="Último erro do vigia" valor={s.vigia.ultimo_erro} /> : null}
          <Item rotulo="Endereço da API" valor={urlBaseDaApi()} />
        </View>
      )}
    </EstadoDaConsulta>
  );
}

const ONDE = Platform.OS === 'web' ? 'do navegador' : 'do aparelho';

function TextoDaPermissao({ permissao, aoPedir }: { permissao: EstadoDaPermissao | null; aoPedir: () => void }) {
  if (permissao === 'permitida') return <Text style={texto.suave}>Notificações {ONDE}: permitidas.</Text>;
  if (permissao === 'nao_perguntada') {
    return <Botao titulo="Permitir notificações" icone="sino" aoTocar={aoPedir} />;
  }
  if (permissao === 'negada') {
    return (
      <Text style={texto.suave}>
        Notificações bloqueadas nas configurações {ONDE}. O aviso aparece só dentro do app.
      </Text>
    );
  }
  if (permissao === 'indisponivel') {
    return <Text style={texto.suave}>Aqui não há notificação do sistema. O aviso aparece dentro do app.</Text>;
  }
  return null;
}

export default function Ajustes() {
  const { valores, salvar } = usePreferencias();
  const [permissao, setPermissao] = useState<EstadoDaPermissao | null>(null);

  useEffect(() => {
    let ativo = true;
    void estadoDaPermissao().then((estado) => ativo && setPermissao(estado));
    return () => {
      ativo = false;
    };
  }, []);

  // No navegador, a permissão só pode ser pedida a partir de um toque (este botão ou a chave).
  const pedir = () => void pedirPermissao().then(setPermissao);

  return (
    <Tela titulo="Ajustes">
      <Secao titulo="Você">
        <SeletorDeBairro
          bairroNome={valores.bairroNome}
          aoEscolher={(b) => salvar({ bairroId: b.bairro_id, bairroNome: b.bairro })}
        />
        <Divisoria />
        <SeletorDePessoas pessoas={valores.pessoas} aoMudar={(pessoas) => salvar({ pessoas })} />
        <Text style={texto.suave}>
          O bairro e o tamanho do grupo ficam guardados só neste aparelho. Eles servem para escolher o abrigo e a
          mensagem do alerta.
        </Text>
      </Secao>

      <Secao titulo="Avisos">
        {/* A linha inteira é o interruptor: alvo de toque grande (o Switch nativo no navegador tem 40 × 20 px). */}
        <Pressable
          onPress={() => {
            const avisos = !valores.avisos;
            void salvar({ avisos });
            if (avisos && permissao === 'nao_perguntada') pedir();
          }}
          accessibilityRole="switch"
          aria-checked={valores.avisos}
          accessibilityLabel="Avisar quando abrir um alerta"
          style={({ pressed }) => [estilos.linhaDoAviso, pressed && { opacity: 0.85 }]}
        >
          <Icone nome="sino" cor={cores.primaria} tamanho={22} />
          <View style={estilos.textoDoAviso}>
            <Text style={estilos.tituloDoAviso}>Avisar quando abrir um alerta</Text>
            <Text style={texto.apoio}>
              Com o app aberto, o Abriga avisa quando a previsão indicar que um rio vai entrar em alerta.
            </Text>
          </View>
          <View style={[estilos.trilho, valores.avisos ? estilos.trilhoLigado : estilos.trilhoDesligado]}>
            <View style={estilos.bolinha} />
          </View>
        </Pressable>
        {valores.avisos ? <TextoDaPermissao permissao={permissao} aoPedir={pedir} /> : null}
      </Secao>

      <Secao titulo="Situação do sistema">
        <SituacaoDoSistema />
      </Secao>

      <Secao titulo="Sobre o Abriga">
        <View style={estilos.sobre}>
          <Text style={texto.corpoCartao}>
            <Text style={estilos.destaque}>Dados simulados. </Text>
            Os níveis dos rios, a chuva e a ocupação dos abrigos vêm de sensores simulados e de um ESP32 no Wokwi. A
            previsão é de uma IA treinada com cheias simuladas. Não use o app numa emergência real.
          </Text>
          <Text style={texto.corpoCartao}>
            <Text style={estilos.destaque}>Privacidade. </Text>
            Não há cadastro. A sua localização nunca sai do aparelho: no modo “Minha localização”, a distância até os
            abrigos é calculada aqui. O servidor recebe, no máximo, o bairro e o número de pessoas.
          </Text>
          <Text style={texto.corpoCartao}>
            <Text style={estilos.destaque}>Em emergência real: </Text>
            199 (Defesa Civil) ou 193 (Bombeiros).
          </Text>
          <Text style={texto.apoio}>
            Projeto acadêmico da Global Solution 2026/2 (FIAP), sem ligação com órgãos públicos. Bairros, escolas e
            ginásios: © colaboradores do OpenStreetMap (ODbL). Versão {Constants.expoConfig?.version ?? '1.0.0'}.
          </Text>
        </View>
      </Secao>
    </Tela>
  );
}

const estilos = StyleSheet.create({
  secao: { ...cartao, gap: espaco.md, marginBottom: espaco.xs },
  divisoria: { height: 1, backgroundColor: cores.borda },
  itens: { gap: espaco.md },
  item: { gap: 2 },
  valor: { ...texto.corpoCartao, ...peso('600') },
  sobre: { gap: 10 },
  destaque: peso('700'),
  linhaDoAviso: { minHeight: 48, flexDirection: 'row', alignItems: 'center', gap: espaco.md },
  tituloDoAviso: { ...peso('600'), fontSize: 17, lineHeight: 22, color: cores.texto },
  // Chave: trilho verde quando ligada, cinza de controle quando desligada; bolinha branca.
  trilho: { width: 52, height: 32, borderRadius: raio.selo, padding: 3, justifyContent: 'center' },
  trilhoLigado: { backgroundColor: cores.primaria, alignItems: 'flex-end' },
  trilhoDesligado: { backgroundColor: cores.bordaControle, alignItems: 'flex-start' },
  bolinha: { width: 26, height: 26, borderRadius: raio.selo, backgroundColor: cores.superficie },
  textoDoAviso: { flex: 1, gap: 2 },
});
