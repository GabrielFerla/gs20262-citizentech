/**
 * Aviso de alerta novo: com o app aberto, o vigia da API escala o Gravataí para "alerta" e o app
 * mostra a faixa e a notificação (uma vez só). O toque leva para "Onde ficar seguro".
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Notifications from 'expo-notifications';
import { act, fireEvent, renderRouter, screen, within } from 'expo-router/testing-library';

import type { RespostaAlertas } from '@/api/tipos';
import { dispensarAviso } from '@/estado/avisos';
import { limparHistorico } from '@/estado/historico';
import { CHAVE, reiniciarPreferencias } from '@/estado/preferencias';

import { copia, fixtures, rotasPadrao, simularApi } from '../test-utils/apiFalsa';

const agendar = Notifications.scheduleNotificationAsync as jest.Mock;

/** A resposta de /alertas depois que o vigia escalou o Gravataí de atenção para alerta. */
function gravataiEmAlerta(): RespostaAlertas {
  const r = copia(fixtures.alertasNavegantes);
  const aberto = r.vigia.abertos.find((a) => a.estacao_id === 'gra-sarandi')!;
  aberto.severidade = 2;
  const rio = r.rios_fora_do_normal.find((x) => x.previsao.estacao_id === 'gra-sarandi')!;
  rio.mensagens.push_titulo = 'Prepare-se: o rio vai subir';
  rio.mensagens.push_corpo =
    'Prepare-se para sair de casa. O Rio Gravataí deve subir muito em até 6 h. Emergência: 199 ou 193.';
  return r;
}

async function passar(ms: number) {
  await act(async () => {
    await jest.advanceTimersByTimeAsync(ms);
  });
}

async function abrirComOVigia(avisos: boolean, initialUrl = '/') {
  await AsyncStorage.setItem(
    CHAVE,
    JSON.stringify({ bairroId: 'navegantes', bairroNome: 'Navegantes', pessoas: 4, avisos }),
  );
  let alertas: RespostaAlertas = fixtures.alertasNavegantes;
  simularApi({ ...rotasPadrao(), '/alertas': () => alertas });
  await renderRouter('./src/app', { initialUrl });
  await screen.findByText(initialUrl === '/' ? 'Saia agora: risco de alagamento' : 'Vá para um destes');
  await passar(100);
  return {
    vigiaEscala: () => {
      alertas = gravataiEmAlerta();
    },
  };
}

beforeEach(async () => {
  jest.useFakeTimers();
  await AsyncStorage.clear();
  reiniciarPreferencias();
  limparHistorico();
  dispensarAviso();
  agendar.mockClear();
});

afterEach(() => {
  jest.useRealTimers();
});

it('o que já estava aberto ao abrir o app não vira aviso', async () => {
  await abrirComOVigia(true);
  await passar(3_500);
  expect(screen.queryByTestId('aviso-de-alerta-novo')).toBeNull();
  expect(agendar).not.toHaveBeenCalled();
});

it('alerta escalado com o app aberto: faixa e notificação, uma vez só', async () => {
  const { vigiaEscala } = await abrirComOVigia(true);

  vigiaEscala();
  await passar(3_500); // a próxima leitura de /alertas

  const faixa = await screen.findByTestId('aviso-de-alerta-novo');
  expect(within(faixa).getByText('Prepare-se: o rio vai subir')).toBeOnTheScreen();
  expect(within(faixa).getByText(/^Prepare-se para sair de casa\./)).toBeOnTheScreen();
  expect(agendar).toHaveBeenCalledTimes(1);
  expect(agendar).toHaveBeenCalledWith({
    content: {
      title: 'Prepare-se: o rio vai subir',
      body: expect.stringMatching(/^Prepare-se para sair de casa\./),
      data: { rota: '/abrigos' },
    },
    trigger: null,
  });

  await passar(7_000); // mais duas leituras com o mesmo alerta
  expect(agendar).toHaveBeenCalledTimes(1);
});

it('tocar na faixa leva para "Onde ficar seguro" e fecha a faixa', async () => {
  const { vigiaEscala } = await abrirComOVigia(true);
  vigiaEscala();
  await passar(3_500);

  const faixa = await screen.findByTestId('aviso-de-alerta-novo');
  await fireEvent.press(within(faixa).getByRole('button', { name: 'Onde ficar seguro' }));

  expect(screen).toHavePathname('/abrigos');
  expect(screen.queryByTestId('aviso-de-alerta-novo')).toBeNull();
});

it('o botão de fechar tira a faixa', async () => {
  const { vigiaEscala } = await abrirComOVigia(true);
  vigiaEscala();
  await passar(3_500);

  await fireEvent.press(await screen.findByRole('button', { name: 'Fechar o aviso' }));
  expect(screen.queryByTestId('aviso-de-alerta-novo')).toBeNull();
});

it('com os avisos desligados no Ajustes, não avisa', async () => {
  const { vigiaEscala } = await abrirComOVigia(false);
  vigiaEscala();
  await passar(3_500);

  expect(screen.queryByTestId('aviso-de-alerta-novo')).toBeNull();
  expect(agendar).not.toHaveBeenCalled();
});

it('quem já está em "Onde ficar seguro" recebe a notificação, sem a faixa por cima da lista', async () => {
  const { vigiaEscala } = await abrirComOVigia(true, '/abrigos');
  vigiaEscala();
  await passar(3_500);

  expect(agendar).toHaveBeenCalledTimes(1);
  expect(screen.queryByTestId('aviso-de-alerta-novo')).toBeNull();
  expect(screen.getByText('Vá para um destes')).toBeOnTheScreen();
});
