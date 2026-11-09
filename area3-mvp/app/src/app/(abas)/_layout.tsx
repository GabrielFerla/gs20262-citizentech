/** Abas do app: Agora · Abrigos · Ajustes. */
import { Tabs } from 'expo-router/js-tabs';
import { StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { IconeAbrigo, IconeAjustes, IconeRio, Logo } from '@/componentes/Icones';
import { cores } from '@/tema';

function Marca() {
  return (
    <View style={estilos.marca} accessibilityRole="header" accessibilityLabel="Abriga">
      <Logo cor="#FFFFFF" tamanho={28} />
      <Text style={estilos.marcaTexto}>Abriga</Text>
    </View>
  );
}

export default function LayoutDasAbas() {
  // Barra de abas mais alta que o padrão: rótulo maior, mais fácil de tocar.
  const { bottom } = useSafeAreaInsets();

  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: cores.primaria },
        headerTintColor: '#FFFFFF',
        headerTitleStyle: { fontWeight: '700' },
        tabBarActiveTintColor: cores.primaria,
        tabBarInactiveTintColor: cores.textoSuave,
        tabBarLabelStyle: { fontSize: 13, fontWeight: '600' },
        tabBarStyle: { height: 68 + bottom, paddingTop: 4, paddingBottom: 4 + bottom },
        sceneStyle: { backgroundColor: cores.fundo },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Agora',
          headerTitle: () => <Marca />,
          tabBarAccessibilityLabel: 'Agora: situação dos rios',
          tabBarIcon: ({ color }) => <IconeRio cor={color} />,
        }}
      />
      <Tabs.Screen
        name="abrigos"
        options={{
          title: 'Abrigos',
          headerTitle: 'Onde ficar seguro',
          tabBarAccessibilityLabel: 'Abrigos: onde ficar seguro',
          tabBarIcon: ({ color }) => <IconeAbrigo cor={color} />,
        }}
      />
      <Tabs.Screen
        name="ajustes"
        options={{
          title: 'Ajustes',
          tabBarIcon: ({ color }) => <IconeAjustes cor={color} />,
        }}
      />
    </Tabs>
  );
}

const estilos = StyleSheet.create({
  marca: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  marcaTexto: { color: '#FFFFFF', fontSize: 22, fontWeight: '800', letterSpacing: 0.3 },
});
