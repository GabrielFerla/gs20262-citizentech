/**
 * Telas Agora e Rio com o roteador de verdade (src/app) e as respostas reais da API
 * guardadas em __fixtures__/ (uma cheia simulada: Guaíba em inundação, Gravataí em atenção).
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';

import { limparHistorico } from '@/estado/historico';
import { CHAVE, reiniciarPreferencias } from '@/estado/preferencias';

import { copia, fixtures, rotasPadrao, simularApi } from '../test-utils/apiFalsa';

beforeEach(async () => {
  await AsyncStorage.clear();
  reiniciarPreferencias();
  limparHistorico();
});

describe('tela Agora', () => {
  it('mostra a faixa com a mensagem do rio mais grave e o botão "Onde ficar seguro"', async () => {
    simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/' });

    expect(await screen.findByText('Saia agora: risco de alagamento')).toBeOnTheScreen();
    expect(screen.getByText(/^Saia agora para um lugar alto\./)).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: 'Onde ficar seguro' })).toBeOnTheScreen();
  });

  it('mostra um cartão por rio, do mais grave para o menos grave', async () => {
    simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/' });

    const cartoes = await screen.findAllByRole('button', { name: / Toque para ver o gráfico\.$/ });
    expect(cartoes.map((c) => c.props.accessibilityLabel.split(':')[0])).toEqual([
      'Lago Guaíba',
      'Rio Gravataí',
      'Arroio Dilúvio',
    ]);
    expect(screen.getByText('0,68 m acima da cota de inundação', { exact: false })).toBeOnTheScreen();
  });

  it('destaca o alerta antecipado (a previsão pior que agora)', async () => {
    const previsao = copia(fixtures.previsao);
    Object.assign(previsao[1], { nivel_previsto_6h_m: 3.55, situacao_prevista: 'alerta', alerta_antecipado: true });
    simularApi({ ...rotasPadrao(), '/previsao': previsao });
    await renderRouter('./src/app', { initialUrl: '/' });

    expect(await screen.findByText('Alerta antecipado: alerta em até 6 h')).toBeOnTheScreen();
  });

  it('marca leitura atrasada e dados incompletos', async () => {
    const previsao = copia(fixtures.previsao);
    Object.assign(previsao[0], { leitura_velha: true, dados_incompletos: true });
    simularApi({ ...rotasPadrao(), '/previsao': previsao });
    await renderRouter('./src/app', { initialUrl: '/' });

    expect(await screen.findByText('Leitura atrasada: a previsão pode não valer')).toBeOnTheScreen();
    expect(screen.getByText('Dados incompletos: previsão igual ao nível de agora')).toBeOnTheScreen();
  });

  it('sem bairro salvo, convida a escolher; com bairro, pede os alertas daquele bairro', async () => {
    const { urls } = simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/' });
    expect(await screen.findByText('Qual é o seu bairro?')).toBeOnTheScreen();
    expect(urls).toContain('http://localhost:8000/alertas');

    screen.unmount();
    reiniciarPreferencias();
    await AsyncStorage.setItem(CHAVE, JSON.stringify({ bairroId: 'navegantes', bairroNome: 'Navegantes', pessoas: 4 }));
    const segunda = simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/' });
    await screen.findByText('Saia agora: risco de alagamento');
    expect(screen.queryByText('Qual é o seu bairro?')).toBeNull();
    expect(segunda.urls).toContain('http://localhost:8000/alertas?bairro=navegantes');
  });

  it('banco fora do ar (503): aviso amigável, não tela em branco', async () => {
    simularApi({ ...rotasPadrao(), '/previsao': { status: 503, corpo: { detail: 'banco de dados indisponível' } } });
    await renderRouter('./src/app', { initialUrl: '/' });

    expect(await screen.findByText('Não deu para carregar')).toBeOnTheScreen();
    expect(screen.getByText('O servidor de dados está fora do ar. Tentando de novo…')).toBeOnTheScreen();
  });

  it('o rodapé sempre avisa que os dados são simulados e dá os telefones de emergência', async () => {
    simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/' });
    expect(await screen.findByText(/^Dados simulados para demonstração/)).toBeOnTheScreen();
    expect(screen.getByText('Em emergência real, ligue 199 (Defesa Civil) ou 193 (Bombeiros).')).toBeOnTheScreen();
  });
});

describe('tela Rio', () => {
  it('abre ao tocar no cartão e mostra o gráfico, as cotas e a previsão', async () => {
    simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/' });

    await fireEvent.press(await screen.findByRole('button', { name: /^Lago Guaíba: agora/ }));

    expect(screen).toHavePathname('/rio/gua-cais');
    expect(await screen.findByText('Cotas deste rio')).toBeOnTheScreen();
    expect(screen.getByLabelText(/^Gráfico do Lago Guaíba\. Nível agora 3,68 m/)).toBeOnTheScreen();
    expect(screen.getByText('3,76 m')).toBeOnTheScreen(); // previsto para 6 h
    expect(screen.getByText(/IA \(random forest\)/)).toBeOnTheScreen();
  });

  it('no Dilúvio, explica que a previsão repete o nível de agora', async () => {
    simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/rio/dil-ipiranga' });

    expect(await screen.findByText(/a previsão repete o nível de agora/)).toBeOnTheScreen();
    // Dilúvio está normal: não manda procurar abrigo.
    expect(screen.queryByRole('button', { name: 'Onde ficar seguro' })).toBeNull();
  });

  it('rio que não existe: mensagem clara', async () => {
    simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/rio/nao-existe' });

    expect(await screen.findByText('Não encontramos o que você pediu.')).toBeOnTheScreen();
  });
});
