/** Raiz do app: cliente das consultas e a pilha de telas (abas + detalhes). */
import { focusManager, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { AppState, Platform } from 'react-native';

import { criarClienteDeConsultas } from '@/api/consultas';
import { cores } from '@/tema';

export default function Raiz() {
  const [cliente] = useState(criarClienteDeConsultas);

  // No celular, pausa a atualização automática com o app em segundo plano.
  // (No navegador, o TanStack Query já acompanha a aba visível.)
  useEffect(() => {
    if (Platform.OS === 'web') return;
    const assinatura = AppState.addEventListener('change', (estado) => {
      focusManager.setFocused(estado === 'active');
    });
    return () => assinatura.remove();
  }, []);

  return (
    <QueryClientProvider client={cliente}>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: cores.primaria },
          headerTintColor: '#FFFFFF',
          headerTitleStyle: { fontWeight: '700' },
          contentStyle: { backgroundColor: cores.fundo },
          headerBackTitle: 'Voltar',
        }}
      >
        <Stack.Screen name="(abas)" options={{ headerShown: false, title: 'Abriga' }} />
        <Stack.Screen name="abrigo/[id]" options={{ title: 'Abrigo' }} />
        <Stack.Screen name="rio/[id]" options={{ title: 'Rio' }} />
      </Stack>
    </QueryClientProvider>
  );
}
