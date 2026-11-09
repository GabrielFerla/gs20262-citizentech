/** Raiz do app: cliente das consultas, a pilha de telas (abas + detalhes) e o aviso de alerta novo. */
import { focusManager, QueryClientProvider } from '@tanstack/react-query';
import { Stack, useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { AppState, Platform } from 'react-native';

import { criarClienteDeConsultas } from '@/api/consultas';
import { AvisoDeAlertaNovo } from '@/componentes/AvisoDeAlertaNovo';
import { dispensarAviso, useAvisoAtual, useAvisosDeAlerta } from '@/estado/avisos';
import { cores } from '@/tema';

/** Acompanha o vigia em qualquer tela e mostra a faixa quando abre um alerta novo. */
function AvisosDeAlerta() {
  useAvisosDeAlerta();
  const aviso = useAvisoAtual();
  const router = useRouter();

  // A faixa some sozinha depois de 1 minuto (a situação continua na tela Agora).
  useEffect(() => {
    if (!aviso) return;
    const relogio = setTimeout(dispensarAviso, 60_000);
    return () => clearTimeout(relogio);
  }, [aviso]);

  if (!aviso) return null;
  return (
    <AvisoDeAlertaNovo
      aviso={aviso}
      aoFechar={dispensarAviso}
      aoAbrir={() => {
        dispensarAviso();
        router.navigate(aviso.rota);
      }}
    />
  );
}

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
      <AvisosDeAlerta />
    </QueryClientProvider>
  );
}
