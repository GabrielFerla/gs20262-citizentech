/**
 * Notificações de alerta, só locais (geradas no próprio aparelho com o app aberto):
 * - celular (Expo Go ou build): expo-notifications, canal Android "alertas";
 * - navegador: a Notification API (localhost é contexto seguro).
 * Push de servidor (com o app fechado) está fora do escopo do MVP.
 */
import * as Notifications from 'expo-notifications';
import { AndroidImportance } from 'expo-notifications';
import { Platform } from 'react-native';

import type { Aviso } from '@/logica/alertas';

const CANAL = 'alertas';
const NO_NAVEGADOR = Platform.OS === 'web';

export type EstadoDaPermissao = 'permitida' | 'negada' | 'nao_perguntada' | 'indisponivel';

let preparado = false;

/** Celular: mostra a notificação mesmo com o app aberto e cria o canal do Android. */
export function prepararNotificacoes(): void {
  if (NO_NAVEGADOR || preparado) return;
  preparado = true;
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });
  if (Platform.OS === 'android') {
    void Notifications.setNotificationChannelAsync(CANAL, {
      name: 'Alertas de cheia',
      importance: AndroidImportance.MAX,
    });
  }
}

function notificacaoDoNavegador(): typeof Notification | null {
  return typeof globalThis.Notification === 'function' ? globalThis.Notification : null;
}

function doNavegador(permissao: NotificationPermission): EstadoDaPermissao {
  return permissao === 'granted' ? 'permitida' : permissao === 'denied' ? 'negada' : 'nao_perguntada';
}

export async function estadoDaPermissao(): Promise<EstadoDaPermissao> {
  try {
    if (NO_NAVEGADOR) {
      const N = notificacaoDoNavegador();
      return N ? doNavegador(N.permission) : 'indisponivel';
    }
    const { status, canAskAgain } = await Notifications.getPermissionsAsync();
    if (status === 'granted') return 'permitida';
    return canAskAgain ? 'nao_perguntada' : 'negada';
  } catch {
    return 'indisponivel';
  }
}

/** Pede a permissão (no navegador, só funciona a partir de um toque da pessoa). */
export async function pedirPermissao(): Promise<EstadoDaPermissao> {
  try {
    if (NO_NAVEGADOR) {
      const N = notificacaoDoNavegador();
      return N ? doNavegador(await N.requestPermission()) : 'indisponivel';
    }
    prepararNotificacoes();
    const { status } = await Notifications.requestPermissionsAsync();
    return status === 'granted' ? 'permitida' : 'negada';
  } catch {
    return 'indisponivel';
  }
}

/** Mostra a notificação do sistema, se houver permissão. Sem ela, fica só o aviso dentro do app. */
export async function notificar(aviso: Aviso, aoTocar: (rota: Aviso['rota']) => void): Promise<void> {
  try {
    if (NO_NAVEGADOR) {
      const N = notificacaoDoNavegador();
      if (!N || N.permission !== 'granted') return;
      const notificacao = new N(aviso.titulo, { body: aviso.corpo, tag: aviso.chave, icon: '/favicon.ico' });
      notificacao.onclick = () => {
        globalThis.focus?.();
        aoTocar(aviso.rota);
        notificacao.close();
      };
      return;
    }
    const { status } = await Notifications.getPermissionsAsync();
    if (status !== 'granted') return;
    await Notifications.scheduleNotificationAsync({
      content: { title: aviso.titulo, body: aviso.corpo, data: { rota: aviso.rota } },
      trigger: Platform.OS === 'android' ? { channelId: CANAL } : null,
    });
  } catch {
    // Sem notificação do sistema, o aviso dentro do app continua aparecendo.
  }
}
