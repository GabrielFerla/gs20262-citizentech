import { buscarJson, ErroApi, mensagemDoErro, tipoPorStatus, urlBaseDaApi } from '@/api/cliente';
import { api } from '@/api/abriga';

function respostaJson(corpo: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => corpo,
  } as Response;
}

/** Espera a promessa falhar e devolve o erro (o teste falha se ela der certo). */
async function falhaDe(promessa: Promise<unknown>): Promise<ErroApi> {
  try {
    await promessa;
  } catch (erro) {
    return erro as ErroApi;
  }
  throw new Error('era para ter falhado');
}

const fetchFalso = jest.fn<Promise<Response>, [string, RequestInit?]>();

beforeEach(() => {
  fetchFalso.mockReset();
  globalThis.fetch = fetchFalso as unknown as typeof fetch;
});

describe('endereço da API', () => {
  it('usa o endereço gravado no build, sem barra no fim', () => {
    expect(urlBaseDaApi('/api/', 'web', null)).toBe('/api');
    expect(urlBaseDaApi('http://10.0.0.5:8000', 'ios', 'x')).toBe('http://10.0.0.5:8000');
  });

  it('no navegador em desenvolvimento, usa localhost:8000', () => {
    expect(urlBaseDaApi(undefined, 'web', '192.168.0.15:8081')).toBe('http://localhost:8000');
  });

  it('no Expo Go, usa o IP do computador que roda o Metro', () => {
    expect(urlBaseDaApi(undefined, 'android', '192.168.0.15:8081')).toBe('http://192.168.0.15:8000');
    expect(urlBaseDaApi(undefined, 'ios', '192.168.0.15:8081/--/abrigos')).toBe('http://192.168.0.15:8000');
  });
});

describe('erros viram mensagens simples', () => {
  it.each([
    [503, 'servidor_indisponivel'],
    [502, 'servidor_indisponivel'],
    [504, 'servidor_indisponivel'],
    [404, 'nao_encontrado'],
    [422, 'invalido'],
    [500, 'outro'],
  ])('HTTP %i → %s', (status, tipo) => {
    expect(tipoPorStatus(status)).toBe(tipo);
  });

  it('banco fora do ar (503) não mostra detalhe técnico na tela', async () => {
    fetchFalso.mockResolvedValue(
      respostaJson({ detail: 'banco de dados indisponível; tente de novo em instantes' }, 503),
    );
    const erro = await falhaDe(buscarJson('/previsao'));
    expect(erro).toBeInstanceOf(ErroApi);
    expect(erro.tipo).toBe('servidor_indisponivel');
    expect(erro.passageiro).toBe(true);
    expect(mensagemDoErro(erro)).toBe('O servidor de dados está fora do ar. Tentando de novo…');
    expect(erro.detalhe).toContain('banco de dados indisponível');
  });

  it('sem rede: "sem conexão"', async () => {
    fetchFalso.mockRejectedValue(new TypeError('Network request failed'));
    const erro = await falhaDe(buscarJson('/previsao'));
    expect(erro.tipo).toBe('sem_conexao');
    expect(erro.message).toMatch(/Sem conexão/);
  });

  it('404 não é repetido (não é passageiro)', async () => {
    fetchFalso.mockResolvedValue(respostaJson({ detail: "bairro 'xyz' não encontrado" }, 404));
    const erro = await falhaDe(buscarJson('/abrigos/recomendacao?bairro=xyz'));
    expect(erro.tipo).toBe('nao_encontrado');
    expect(erro.passageiro).toBe(false);
  });

  it('erro que não veio da API ganha mensagem genérica', () => {
    expect(mensagemDoErro(new Error('qualquer'))).toBe('Algo deu errado. Tentando de novo…');
  });
});

describe('rotas', () => {
  it('monta as URLs com o bairro codificado e nunca com coordenadas', async () => {
    fetchFalso.mockResolvedValue(respostaJson([]));
    await api.recomendacao('são joão', 4);
    await api.abrigos(2);
    await api.alertas(null);
    const urls = fetchFalso.mock.calls.map(([url]) => url);
    expect(urls).toEqual([
      'http://localhost:8000/abrigos/recomendacao?bairro=s%C3%A3o%20jo%C3%A3o&pessoas=4',
      'http://localhost:8000/abrigos?pessoas=2',
      'http://localhost:8000/alertas',
    ]);
    for (const url of urls) expect(url).not.toMatch(/lat|lon/i);
  });
});
