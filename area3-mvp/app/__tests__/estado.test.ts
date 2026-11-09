import AsyncStorage from '@react-native-async-storage/async-storage';

import { leiturasDe, limparHistorico, MAXIMO_DE_LEITURAS, registrarLeituras } from '@/estado/historico';
import {
  CHAVE,
  carregarPreferencias,
  limitarPessoas,
  PADRAO,
  reiniciarPreferencias,
  salvarPreferencias,
} from '@/estado/preferencias';

import { copia, fixtures } from '../test-utils/apiFalsa';

describe('histórico da sessão (linha do gráfico)', () => {
  beforeEach(limparHistorico);

  const leitura = (medidoEm: string, nivel: number) => ({
    ...copia(fixtures.previsao[2]),
    medido_em_utc: medidoEm,
    nivel_atual_m: nivel,
  });

  it('guarda cada leitura uma vez só, mesmo vindo de várias consultas', () => {
    registrarLeituras([leitura('2026-11-08T23:50:00Z', 3.1)]);
    registrarLeituras([leitura('2026-11-08T23:50:00Z', 3.1)]);
    registrarLeituras([leitura('2026-11-08T23:50:03Z', 3.2)]);
    expect(leiturasDe('gua-cais').map((l) => l.nivel)).toEqual([3.1, 3.2]);
  });

  it(`fica só com as últimas ${MAXIMO_DE_LEITURAS} leituras`, () => {
    for (let i = 0; i < MAXIMO_DE_LEITURAS + 10; i++) {
      registrarLeituras([leitura(new Date(Date.UTC(2026, 10, 8, 0, 0, i)).toISOString(), i)]);
    }
    const guardadas = leiturasDe('gua-cais');
    expect(guardadas).toHaveLength(MAXIMO_DE_LEITURAS);
    expect(guardadas[0].nivel).toBe(10);
  });

  it('ignora rio sem horário de leitura', () => {
    registrarLeituras([{ ...copia(fixtures.previsao[0]), medido_em_utc: null }]);
    expect(leiturasDe('dil-ipiranga')).toHaveLength(0);
  });
});

describe('preferências (só no aparelho)', () => {
  beforeEach(async () => {
    await AsyncStorage.clear();
    reiniciarPreferencias();
  });

  it('salva e carrega o bairro e as pessoas', async () => {
    await salvarPreferencias({ bairroId: 'navegantes', bairroNome: 'Navegantes', pessoas: 4 });
    reiniciarPreferencias();
    await carregarPreferencias();
    const salvo = JSON.parse((await AsyncStorage.getItem(CHAVE)) as string);
    expect(salvo).toEqual({ bairroId: 'navegantes', bairroNome: 'Navegantes', pessoas: 4, avisos: true });
  });

  it('um valor estragado no armazenamento não derruba o app: volta ao padrão', async () => {
    await AsyncStorage.setItem(CHAVE, JSON.stringify({ bairroId: 42, pessoas: 'muitas', avisos: 'sim' }));
    await carregarPreferencias();
    await salvarPreferencias({});
    expect(JSON.parse((await AsyncStorage.getItem(CHAVE)) as string)).toEqual(PADRAO);
  });

  it('o grupo fica entre 1 e 50 pessoas (o limite da API)', () => {
    expect(limitarPessoas(0)).toBe(1);
    expect(limitarPessoas(4.4)).toBe(4);
    expect(limitarPessoas(80)).toBe(50);
    expect(limitarPessoas(NaN)).toBe(1);
  });
});
