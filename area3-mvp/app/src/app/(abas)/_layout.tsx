/** Abas do app: Agora · Abrigos · Ajustes, com o cabeçalho claro e a barra inferior (199, 193 e abas). */
import { Tabs } from 'expo-router/js-tabs';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { BarraInferior, IconeDaAba, opcoesDasAbas } from '@/componentes/BarraInferior';
import { Cabecalho } from '@/componentes/Cabecalho';
import { cores } from '@/tema';

export default function LayoutDasAbas() {
  // A barra fica acima da área do gesto de "home" do celular.
  const { bottom } = useSafeAreaInsets();

  return (
    <Tabs
      tabBar={(props) => <BarraInferior {...props} />}
      screenOptions={{
        header: () => <Cabecalho />,
        sceneStyle: { backgroundColor: cores.fundo },
        ...opcoesDasAbas(bottom),
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Agora',
          tabBarAccessibilityLabel: 'Agora: situação dos rios',
          tabBarIcon: ({ focused }) => <IconeDaAba nome="abaAgora" ativa={focused} />,
        }}
      />
      <Tabs.Screen
        name="abrigos"
        options={{
          title: 'Abrigos',
          tabBarAccessibilityLabel: 'Abrigos: onde ficar seguro',
          tabBarIcon: ({ focused }) => <IconeDaAba nome="abaAbrigos" ativa={focused} />,
        }}
      />
      <Tabs.Screen
        name="ajustes"
        options={{
          title: 'Ajustes',
          tabBarIcon: ({ focused }) => <IconeDaAba nome="abaAjustes" ativa={focused} />,
        }}
      />
    </Tabs>
  );
}
