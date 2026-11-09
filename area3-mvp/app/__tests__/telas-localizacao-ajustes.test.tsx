/**
 * Modo "Minha localização" (a conta é feita no aparelho; a posição não sai dele) e a tela Ajustes.
 * O GPS é de mentira: o teste diz onde a pessoa está.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';

import { limparHistorico } from '@/estado/historico';
import { esquecerPosicao } from '@/estado/posicao';
import { CHAVE, reiniciarPreferencias } from '@/estado/preferencias';

import { rotasPadrao, simularApi } from '../test-utils/apiFalsa';

jest.mock('expo-location', () => ({
  requestForegroundPermissionsAsync: jest.fn(),
  getCurrentPositionAsync: jest.fn(),
  Accuracy: { Balanced: 3 },
}));

const permissao = Location.requestForegroundPermissionsAsync as jest.Mock;
const gps = Location.getCurrentPositionAsync as jest.Mock;

function estouEm(lat: number, lon: number) {
  permissao.mockResolvedValue({ status: 'granted' });
  gps.mockResolvedValue({ coords: { latitude: lat, longitude: lon } });
}

const NAVEGANTES = { lat: -29.99363, lon: -51.20077 };

beforeEach(async () => {
  await AsyncStorage.clear();
  reiniciarPreferencias();
  limparHistorico();
  esquecerPosicao();
  permissao.mockReset();
  gps.mockReset();
  await AsyncStorage.setItem(CHAVE, JSON.stringify({ bairroId: 'navegantes', bairroNome: 'Navegantes', pessoas: 4 }));
});

describe('Onde ficar seguro: minha localização', () => {
  it('calcula no aparelho os recomendados e os evitados, iguais aos da IA para o mesmo ponto', async () => {
    estouEm(NAVEGANTES.lat, NAVEGANTES.lon);
    const { urls } = simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/abrigos' });

    expect(await screen.findByRole('radio', { name: 'Meu bairro' })).toBeChecked();
    await fireEvent.press(screen.getByRole('radio', { name: 'Minha localização' }));

    expect(await screen.findByText('Sua localização fica só neste aparelho.')).toBeOnTheScreen();
    expect(screen.getByRole('radio', { name: 'Minha localização' })).toBeChecked();
    expect(screen.getByRole('radio', { name: 'Meu bairro' })).not.toBeChecked();
    await screen.findByText('Vá para um destes');
    const recomendados = screen.getAllByRole('button', { name: /º recomendado:/ });
    expect(recomendados.map((r) => r.props.accessibilityLabel.split(',')[0])).toEqual([
      '1º recomendado: Escola Professora Maria Thereza da Silveira',
      '2º recomendado: Colégio Leonardo da Vinci Unidade Alfa',
      '3º recomendado: Escola Estadual Especial Cristo Redentor',
    ]);
    // Os mesmos evitados que a API deu para o centro de Navegantes (__fixtures__/recomendacao-navegantes-4.json).
    expect(screen.getAllByText('Fica em área de risco e o rio da região está em alerta')).toHaveLength(2);
    expect(screen.getByText('Lotado')).toBeOnTheScreen();
    // O abrigo de demonstração (Wokwi) nem aparece.
    expect(screen.queryByText('Abrigo de demonstração (Wokwi)')).toBeNull();

    expect(urls).toContain('http://localhost:8000/abrigos?pessoas=4');
    for (const url of urls) expect(url).not.toMatch(/lat|lon|-29\.|-51\./);
  });

  it('o detalhe refaz a distância na memória: nada da posição vai para o endereço da tela', async () => {
    estouEm(NAVEGANTES.lat, NAVEGANTES.lon);
    simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/abrigos' });
    await fireEvent.press(await screen.findByRole('radio', { name: 'Minha localização' }));
    await screen.findByText('Vá para um destes');

    await fireEvent.press(screen.getAllByRole('button', { name: /º recomendado:/ })[0]);

    expect(screen).toHavePathname('/abrigo/abr-10');
    expect(screen).toHaveSearchParams({ id: 'abr-10', origem: 'localizacao' });
    expect(await screen.findByText('A pé, de onde você está')).toBeOnTheScreen();
    expect(screen.getByText('1 h 21 min a pé (4,2 km em linha reta)')).toBeOnTheScreen();
  });

  it('sem permissão: avisa e volta para o bairro', async () => {
    permissao.mockResolvedValue({ status: 'denied' });
    simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/abrigos' });

    await fireEvent.press(await screen.findByRole('radio', { name: 'Minha localização' }));

    expect(await screen.findByText(/Sem permissão para usar a localização/)).toBeOnTheScreen();
    expect(screen.getByRole('radio', { name: 'Meu bairro' })).toBeChecked();
    expect(await screen.findByText('Vá para um destes')).toBeOnTheScreen(); // pelo bairro salvo
    expect(gps).not.toHaveBeenCalled();
  });

  it('fora de Porto Alegre: diz a distância e usa o bairro', async () => {
    estouEm(-23.5505, -46.6333); // São Paulo
    simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/abrigos' });

    await fireEvent.press(await screen.findByRole('radio', { name: 'Minha localização' }));

    expect(await screen.findByText(/Você está a \d+ km do centro de Porto Alegre/)).toBeOnTheScreen();
    expect(screen.getByRole('radio', { name: 'Meu bairro' })).toBeChecked();
  });

  it('GPS falhou: mensagem simples, sem travar', async () => {
    permissao.mockResolvedValue({ status: 'granted' });
    gps.mockRejectedValue(new Error('Location request timed out'));
    simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/abrigos' });

    await fireEvent.press(await screen.findByRole('radio', { name: 'Minha localização' }));

    expect(await screen.findByText(/Não deu para pegar a sua localização agora/)).toBeOnTheScreen();
  });
  it('detalhe aberto de novo sem a posição na memória: não promete vaga em abrigo que está enchendo', async () => {
    simularApi(rotasPadrao());
    // abr-20 está apto, mas lota em 8.400 min; sem saber de onde a pessoa sai, não dá para garantir a vaga.
    await renderRouter('./src/app', { initialUrl: '/abrigo/abr-20?origem=localizacao' });

    expect(await screen.findByText('Tem vaga agora, mas está enchendo')).toBeOnTheScreen();
    expect(screen.queryByText(/^Recomendado para/)).toBeNull();
    expect(screen.getByText(/foi apagada quando o app recarregou/)).toBeOnTheScreen();
  });

  it('sem a posição, abrigo que não está enchendo continua recomendado', async () => {
    simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/abrigo/abr-12?origem=localizacao' });

    expect(await screen.findByText('Recomendado para 4 pessoas')).toBeOnTheScreen();
  });
});

describe('Ajustes', () => {
  it('mostra bairro, grupo, avisos, situação do sistema e o aviso de dados simulados', async () => {
    simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/ajustes' });

    expect(await screen.findByRole('button', { name: 'Bairro: Navegantes. Toque para trocar' })).toBeOnTheScreen();
    expect(screen.getByText('4 pessoas')).toBeOnTheScreen();
    expect(screen.getByRole('switch', { name: 'Avisar quando abrir um alerta' })).toBeOnTheScreen();
    expect(await screen.findByText('No ar')).toBeOnTheScreen();
    expect(screen.getByText('Acessível')).toBeOnTheScreen();
    expect(screen.getByText(/Não use o app numa emergência real/)).toBeOnTheScreen();
    expect(screen.getByText(/A sua localização nunca sai do aparelho/)).toBeOnTheScreen();
  });

  it('desligar os avisos e mudar o grupo fica salvo no aparelho', async () => {
    simularApi(rotasPadrao());
    await renderRouter('./src/app', { initialUrl: '/ajustes' });

    const interruptor = await screen.findByRole('switch', { name: 'Avisar quando abrir um alerta' });
    expect(interruptor).toBeChecked();
    await fireEvent.press(interruptor);
    expect(interruptor).not.toBeChecked();
    await fireEvent.press(screen.getByRole('button', { name: 'Uma pessoa a menos' }));

    expect(await screen.findByText('3 pessoas')).toBeOnTheScreen();
    expect(JSON.parse((await AsyncStorage.getItem(CHAVE)) as string)).toMatchObject({ avisos: false, pessoas: 3 });
  });

  it('servidor fora do ar: a situação do sistema mostra o aviso', async () => {
    simularApi({ ...rotasPadrao(), '/saude': { status: 503, corpo: { detail: 'banco de dados indisponível' } } });
    await renderRouter('./src/app', { initialUrl: '/ajustes' });

    expect(await screen.findByText('O servidor de dados está fora do ar. Tentando de novo…')).toBeOnTheScreen();
  });
});
