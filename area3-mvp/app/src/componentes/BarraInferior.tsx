/**
 * Barra fixa embaixo: os telefones 199 e 193 (sempre à vista) e, nas abas, a navegação
 * Agora · Abrigos · Ajustes. As abas são as do expo-router (mesmo toque, link e acessibilidade);
 * aqui muda só o visual: aba ativa numa pílula verde-clara.
 */
import { Link } from 'expo-router';
import { BottomTabBar, type BottomTabBarProps, type BottomTabNavigationOptions } from 'expo-router/js-tabs';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ALVO_DE_TOQUE, cores, espaco, peso, raio, sombra, tabular, texto } from '@/tema';

import { Icone, type NomeDoIcone } from './Icones';

function Telefone({ numero, quem }: { numero: string; quem: string }) {
  return (
    <Link href={`tel:${numero}`} asChild>
      <Pressable
        accessibilityRole="link"
        accessibilityLabel={`Ligar ${numero}, ${quem}`}
        style={({ pressed }) => [estilos.telefone, pressed && { backgroundColor: cores.borda }]}
      >
        <Icone nome="telefone" cor={cores.primaria} tamanho={20} />
        <Text style={estilos.numero}>{numero}</Text>
        <Text style={estilos.quem} numberOfLines={1}>
          {quem}
        </Text>
      </Pressable>
    </Link>
  );
}

function Telefones() {
  return (
    <View style={estilos.telefones}>
      <Telefone numero="199" quem="Defesa Civil" />
      <Telefone numero="193" quem="Bombeiros" />
    </View>
  );
}

/** Barra das abas (use em `tabBar`). */
export function BarraInferior(props: BottomTabBarProps) {
  return (
    <View style={estilos.barra}>
      <Telefones />
      <BottomTabBar {...props} />
    </View>
  );
}

/** Só os telefones, para as telas fora das abas (Rio e Abrigo). */
export function BarraDeTelefones() {
  const { bottom } = useSafeAreaInsets();
  return (
    <View style={[estilos.barra, { paddingBottom: bottom + espaco.sm }]}>
      <Telefones />
    </View>
  );
}

/** Ícone da aba: na aba ativa, fica numa pílula verde-clara. */
export function IconeDaAba({ nome, ativa }: { nome: NomeDoIcone; ativa: boolean }) {
  return (
    <View style={[estilos.pilula, ativa && estilos.pilulaAtiva]}>
      <Icone nome={nome} cor={ativa ? cores.primaria : cores.textoSuave} tamanho={22} />
    </View>
  );
}

/** Visual das abas (o resto das opções continua em cada tela). */
export function opcoesDasAbas(baseDaTela: number): BottomTabNavigationOptions {
  return {
    tabBarActiveTintColor: cores.primariaEscura,
    tabBarInactiveTintColor: cores.textoSuave,
    tabBarItemStyle: estilos.aba,
    tabBarLabel: ({ focused, color, children }) => (
      <Text style={[focused ? texto.abaAtiva : texto.aba, { color }]}>{children}</Text>
    ),
    // A barra fica acima da área do gesto de "home" do celular.
    tabBarStyle: [estilos.abas, { height: 64 + baseDaTela }],
  };
}

const estilos = StyleSheet.create({
  barra: {
    backgroundColor: cores.superficie,
    borderTopWidth: 1,
    borderTopColor: cores.borda,
    ...sombra.barra,
  },
  telefones: {
    flexDirection: 'row',
    gap: espaco.sm,
    paddingHorizontal: espaco.margem,
    paddingTop: 10,
    paddingBottom: 6,
    width: '100%',
    maxWidth: 560,
    alignSelf: 'center',
  },
  telefone: {
    flex: 1,
    minWidth: 0,
    minHeight: ALVO_DE_TOQUE,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: espaco.sm,
    borderRadius: raio.controle,
    backgroundColor: cores.neutroFundo,
  },
  numero: { ...peso('800'), fontSize: 17, lineHeight: 22, color: cores.texto, ...tabular },
  quem: { ...peso('600'), fontSize: 15, lineHeight: 20, color: cores.textoSuave, flexShrink: 1 },
  // A sombra e a borda do topo ficam na barra inteira; a das abas some.
  abas: {
    backgroundColor: cores.superficie,
    borderTopWidth: 0,
    elevation: 0,
    shadowOpacity: 0,
    boxShadow: 'none',
  },
  aba: { paddingVertical: 6, gap: 4 },
  pilula: {
    width: 60,
    height: 30,
    borderRadius: raio.selo,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pilulaAtiva: { backgroundColor: cores.primariaClara },
});
