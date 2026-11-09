/**
 * Liga o vigia da API aos avisos do app: a cada leitura de GET /alertas (a cada 3 s), descobre os
 * alertas novos ou escalados e mostra a faixa na tela e a notificação do sistema (se permitida).
 */
import * as Notifications from 'expo-notifications';
import { usePathname, useRouter } from 'expo-router';
import { useEffect, useState, useSyncExternalStore } from 'react';
import { Platform } from 'react-native';

import { useAlertas } from '@/api/consultas';
import { avisoDoAlerta, DetectorDeAlertas, mostraFaixa, type Aviso } from '@/logica/alertas';

import { notificar, prepararNotificacoes } from './notificacoes';
import { usePreferencias } from './preferencias';

// ----------------------------------------------------------------------------- aviso na tela
let avisoAtual: Aviso | null = null;
const ouvintes = new Set<() => void>();

function mudar(novo: Aviso | null) {
  avisoAtual = novo;
  ouvintes.forEach((avisar) => avisar());
}

export function mostrarAviso(aviso: Aviso): void {
  mudar(aviso);
}

export function dispensarAviso(): void {
  mudar(null);
}

export function useAvisoAtual(): Aviso | null {
  return useSyncExternalStore(
    (avisar) => {
      ouvintes.add(avisar);
      return () => ouvintes.delete(avisar);
    },
    () => avisoAtual,
    () => avisoAtual,
  );
}

// ----------------------------------------------------------------------------- vigia → avisos
/** Fica na raiz do app: roda em qualquer tela. */
export function useAvisosDeAlerta(): void {
  const router = useRouter();
  const rotaAtual = usePathname();
  const { carregado, valores } = usePreferencias();
  // Mesma consulta da tela Agora (mesma chave): não faz chamada a mais.
  const alertas = useAlertas(carregado ? valores.bairroId : null);
  const [detector] = useState(() => new DetectorDeAlertas());
  const resposta = alertas.data;

  useEffect(() => {
    if (!resposta || !carregado) return;
    const novos = detector.novos(resposta.vigia.abertos);
    if (novos.length === 0 || !valores.avisos) return;
    const aviso = avisoDoAlerta(novos[0], resposta);
    if (mostraFaixa(aviso, rotaAtual)) mostrarAviso(aviso);
    void notificar(aviso, (rota) => router.push(rota));
    // rotaAtual muda ao navegar; aí o detector não acha nada novo, e nada acontece.
  }, [resposta, carregado, valores.avisos, detector, router, rotaAtual]);

  // Celular: tocar na notificação abre a tela certa.
  useEffect(() => {
    if (Platform.OS === 'web') return;
    prepararNotificacoes();
    const assinatura = Notifications.addNotificationResponseReceivedListener((resposta) => {
      const rota = resposta.notification.request.content.data?.rota;
      if (rota === '/abrigos' || rota === '/') {
        dispensarAviso();
        router.push(rota);
      }
    });
    return () => assinatura.remove();
  }, [router]);
}
