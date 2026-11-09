/** Raiz do app: fonte Inter, cliente das consultas, a pilha de telas (abas + detalhes) e o aviso de alerta novo. */
import { Inter_400Regular } from '@expo-google-fonts/inter/400Regular';
import { Inter_500Medium } from '@expo-google-fonts/inter/500Medium';
import { Inter_600SemiBold } from '@expo-google-fonts/inter/600SemiBold';
import { Inter_700Bold } from '@expo-google-fonts/inter/700Bold';
import { Inter_800ExtraBold } from '@expo-google-fonts/inter/800ExtraBold';
import { focusManager, QueryClientProvider } from '@tanstack/react-query';
import { useFonts } from 'expo-font';
import { Stack, useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { AppState, Platform } from 'react-native';

import { criarClienteDeConsultas } from '@/api/consultas';
import { AvisoDeAlertaNovo } from '@/componentes/AvisoDeAlertaNovo';
import { Cabecalho } from '@/componentes/Cabecalho';
import { dispensarAviso, useAvisoAtual, useAvisosDeAlerta } from '@/estado/avisos';
import { cores, familias } from '@/tema';

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
  // Só os cinco pesos usados (importados um a um, para o build não levar os outros arquivos).
  const [fontesProntas, erroDasFontes] = useFonts({
    [familias['400']]: Inter_400Regular,
    [familias['500']]: Inter_500Medium,
    [familias['600']]: Inter_600SemiBold,
    [familias['700']]: Inter_700Bold,
    [familias['800']]: Inter_800ExtraBold,
  });

  // No celular, pausa a atualização automática com o app em segundo plano.
  // (No navegador, o TanStack Query já acompanha a aba visível.)
  useEffect(() => {
    if (Platform.OS === 'web') return;
    const assinatura = AppState.addEventListener('change', (estado) => {
      focusManager.setFocused(estado === 'active');
    });
    return () => assinatura.remove();
  }, []);

  // As fontes vêm junto com o app e carregam num instante. Se falharem, segue com a fonte do sistema.
  if (!fontesProntas && !erroDasFontes) return null;

  return (
    <QueryClientProvider client={cliente}>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          // Cabeçalho claro: "Voltar" quando há para onde voltar e o selo "Dados simulados".
          header: ({ navigation, back }) => <Cabecalho aoVoltar={back ? navigation.goBack : undefined} />,
          contentStyle: { backgroundColor: cores.fundo },
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
