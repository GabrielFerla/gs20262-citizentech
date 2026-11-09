/**
 * Telas "Onde ficar seguro" e "Detalhe do abrigo" com o roteador de verdade e as respostas reais
 * da API (cheia simulada: os abrigos perto de Navegantes em área de risco foram evitados).
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';
import { Linking } from 'react-native';

import { limparHistorico } from '@/estado/historico';
import { CHAVE, reiniciarPreferencias } from '@/estado/preferencias';

import { copia, fixtures, rotasPadrao, simularApi } from '../test-utils/apiFalsa';

async function comBairroSalvo(pessoas = 4) {
  await AsyncStorage.setItem(CHAVE, JSON.stringify({ bairroId: 'navegantes', bairroNome: 'Navegantes', pessoas }));
}

beforeEach(async () => {
  await AsyncStorage.clear();
  reiniciarPreferencias();
  limparHistorico();
});

describe('Onde ficar seguro', () => {
  it('sem bairro, pede para escolher; escolhendo Navegantes, mostra os recomendados e os evitados', async () => {
    const { urls } = simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/abrigos' });

    expect(await screen.findByText('Escolha o bairro para ver os abrigos seguros mais perto.')).toBeOnTheScreen();

    await fireEvent.press(screen.getByRole('button', { name: 'Escolher bairro' }));
    await fireEvent.changeText(await screen.findByLabelText('Buscar bairro'), 'naveg');
    await fireEvent.press(await screen.findByRole('button', { name: 'Navegantes, área de risco de cheia' }));

    expect(await screen.findByText('Vá para um destes')).toBeOnTheScreen();
    const recomendados = screen.getAllByRole('button', { name: /º recomendado:/ });
    expect(recomendados.map((r) => r.props.accessibilityLabel.split(',')[0])).toEqual([
      '1º recomendado: Escola Professora Maria Thereza da Silveira',
      '2º recomendado: Colégio Leonardo da Vinci Unidade Alfa',
      '3º recomendado: Escola Estadual Especial Cristo Redentor',
    ]);
    expect(screen.getByText('Evitamos estes, mais perto de você')).toBeOnTheScreen();
    expect(screen.getAllByText('Fica em área de risco e o rio da região está em alerta')).toHaveLength(2);
    expect(screen.getByText('Lotado')).toBeOnTheScreen();

    expect(urls).toContain('http://localhost:8000/abrigos/recomendacao?bairro=navegantes&pessoas=1');
    expect(JSON.parse((await AsyncStorage.getItem(CHAVE)) as string)).toMatchObject({
      bairroId: 'navegantes',
      bairroNome: 'Navegantes',
    });
  });

  it('o tamanho do grupo vai para a consulta (o abrigo precisa ter vaga para todos)', async () => {
    await comBairroSalvo(4);
    const { urls } = simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/abrigos' });
    await screen.findByText('Vá para um destes');

    await fireEvent.press(screen.getByRole('button', { name: 'Uma pessoa a mais' }));
    await screen.findByText('5 pessoas');
    await screen.findByText('Vá para um destes');
    expect(urls).toContain('http://localhost:8000/abrigos/recomendacao?bairro=navegantes&pessoas=5');
  });

  it('sem nenhum abrigo apto, diz o que fazer', async () => {
    await comBairroSalvo();
    const semNenhum = { ...copia(fixtures.recomendacaoNavegantes4), recomendados: [] };
    simularApi({ ...rotasPadrao(), '/abrigos/recomendacao': semNenhum });
    await renderRouter('./src/app', { initialUrl: '/abrigos' });

    expect(await screen.findByText('Nenhum abrigo seguro com vaga agora')).toBeOnTheScreen();
    expect(screen.getByText(/Procure um lugar alto e ligue 199/)).toBeOnTheScreen();
  });

  it('nenhuma chamada à API leva latitude ou longitude', async () => {
    await comBairroSalvo();
    const { urls } = simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/abrigos' });
    await screen.findByText('Vá para um destes');
    await fireEvent.press(screen.getAllByRole('button', { name: /º recomendado:/ })[0]);
    await screen.findByText('Caminho e risco');

    expect(urls.length).toBeGreaterThan(0);
    for (const url of urls) expect(url).not.toMatch(/lat|lon|-30\.|-51\./);
  });
});

describe('Detalhe do abrigo', () => {
  it('abre do 1º recomendado com vagas, caminho e "Como chegar" só com o destino', async () => {
    await comBairroSalvo(4);
    simularApi(rotasPadrao());
    const abrirUrl = jest.spyOn(Linking, 'openURL').mockResolvedValue(undefined);
    await renderRouter('./src/app', { initialUrl: '/abrigos' });

    await fireEvent.press((await screen.findAllByRole('button', { name: /º recomendado:/ }))[0]);

    expect(screen).toHavePathname('/abrigo/abr-10');
    expect(await screen.findByText('Recomendado para 4 pessoas')).toBeOnTheScreen();
    expect(screen.getByText('1 h 21 min a pé (4,2 km em linha reta)')).toBeOnTheScreen();
    expect(screen.getByText('150 vagas (0 de 150 lugares ocupados)')).toBeOnTheScreen();

    await fireEvent.press(screen.getByRole('button', { name: 'Como chegar' }));
    expect(abrirUrl).toHaveBeenCalledWith(
      'https://www.google.com/maps/dir/?api=1&destination=-30.02832%2C-51.18409&travelmode=walking',
    );
    abrirUrl.mockRestore();
  });

  it('abrigo evitado: diz que não é recomendado e por quê', async () => {
    await comBairroSalvo();
    simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/abrigo/abr-03?minutos=19&km=0.98&origem=bairro' });

    expect(await screen.findByText('Não recomendado agora')).toBeOnTheScreen();
    expect(screen.getByText('Fica em área de risco e o rio da região está em alerta.')).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: 'Como chegar mesmo assim' })).toBeOnTheScreen();
  });

  it('abrigo que lota antes de a pessoa chegar não é recomendado (conta feita no aparelho)', async () => {
    await comBairroSalvo();
    simularApi(rotasPadrao());
    // abr-20 lota em 8.400 min; a pé levaria mais que isso.
    await renderRouter('./src/app', { initialUrl: '/abrigo/abr-20?minutos=9000&origem=localizacao' });

    expect(await screen.findByText('Não recomendado agora')).toBeOnTheScreen();
    expect(screen.getByText('Deve lotar antes de você chegar.')).toBeOnTheScreen();
  });

  it('abrigo que não existe: mensagem clara', async () => {
    simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/abrigo/nao-existe' });
    expect(await screen.findByText('Não encontramos este abrigo.')).toBeOnTheScreen();
  });
});
