import {
  distanciaDaCota,
  explicacaoDoModelo,
  ordenarPorGravidade,
  pedeParaSair,
  piorDoRio,
  resumoDosRios,
  severidade,
} from '@/logica/situacao';

import { copia, fixtures } from '../test-utils/apiFalsa';

const [diluvio, gravatai, guaiba] = fixtures.previsao; // ordem da API: dil, gra, gua

describe('situação dos rios', () => {
  it('usa a mesma escala da API (0 normal … 3 inundação)', () => {
    expect(['normal', 'atencao', 'alerta', 'inundacao'].map((s) => severidade(s as never))).toEqual([0, 1, 2, 3]);
  });

  it('a pior situação do rio considera agora e daqui a 6 h', () => {
    const rio = { ...copia(gravatai), situacao_atual: 'atencao' as const, situacao_prevista: 'alerta' as const };
    expect(piorDoRio(rio)).toBe('alerta');
  });

  it('ordena do mais grave para o menos grave (Guaíba em inundação primeiro)', () => {
    expect(ordenarPorGravidade(fixtures.previsao).map((r) => r.estacao_id)).toEqual([
      'gua-cais',
      'gra-sarandi',
      'dil-ipiranga',
    ]);
  });

  it('no empate, o alerta antecipado vem antes', () => {
    const a = { ...copia(diluvio), situacao_atual: 'alerta' as const, situacao_prevista: 'alerta' as const };
    const b = { ...copia(gravatai), situacao_prevista: 'alerta' as const, alerta_antecipado: true };
    expect(ordenarPorGravidade([a, b])[0].estacao_id).toBe('gra-sarandi');
  });

  it('só pede para sair a partir do alerta', () => {
    expect(pedeParaSair('atencao')).toBe(false);
    expect(pedeParaSair('alerta')).toBe(true);
    expect(pedeParaSair('inundacao')).toBe(true);
  });
});

describe('faixa do topo (resumo)', () => {
  it('usa a mensagem pronta da API para o rio mais grave', () => {
    const resumo = resumoDosRios(fixtures.previsao, fixtures.alertasNavegantes);
    expect(resumo.situacao).toBe('inundacao');
    expect(resumo.rio?.estacao_id).toBe('gua-cais');
    expect(resumo.titulo).toBe('Saia agora: risco de alagamento');
    expect(resumo.texto).toMatch(/^Saia agora para um lugar alto\./);
    expect(resumo.texto).toContain('199');
  });

  it('/previsao mais nova que /alertas: rio, título e texto continuam da mesma leitura (a faixa não pisca)', () => {
    // A leitura de /previsao já mostra o Dilúvio em inundação; a de /alertas ainda não tem mensagem para ele.
    const maisNova = copia(fixtures.previsao);
    Object.assign(maisNova[0], { situacao_atual: 'inundacao', situacao_prevista: 'inundacao' });
    const resumo = resumoDosRios(maisNova, fixtures.alertasNavegantes);
    expect(resumo.rio?.estacao_id).toBe('gua-cais');
    expect(resumo.titulo).toBe('Saia agora: risco de alagamento');
  });

  it('nunca usa a Defesa Civil como remetente (só os textos de push)', () => {
    const resumo = resumoDosRios(fixtures.previsao, fixtures.alertasNavegantes);
    expect(`${resumo.titulo} ${resumo.texto}`).not.toMatch(/DEFESA CIVIL:|\*Defesa Civil/);
  });

  it('sem a mensagem da API, monta um texto simples, inclusive para o alerta antecipado', () => {
    const rio = { ...copia(gravatai), situacao_prevista: 'alerta' as const, alerta_antecipado: true };
    const resumo = resumoDosRios([copia(diluvio), rio]);
    expect(resumo.titulo).toBe('Alerta de cheia');
    expect(resumo.texto).toBe('O Rio Gravataí deve chegar a alerta nas próximas 6 horas.');
  });

  it('tudo normal', () => {
    const normais = fixtures.previsao.map((r) => ({
      ...copia(r),
      situacao_atual: 'normal' as const,
      situacao_prevista: 'normal' as const,
    }));
    const resumo = resumoDosRios(normais);
    expect(resumo).toMatchObject({ situacao: 'normal', titulo: 'Rios normais', rio: null });
  });
});

describe('textos do cartão do rio', () => {
  it('diz quanto falta para a próxima cota', () => {
    expect(distanciaDaCota(gravatai)).toBe('Faltam 0,38 m para a cota de alerta'); // 3,12 → 3,50
    expect(distanciaDaCota(diluvio)).toBe('Faltam 0,36 m para a cota de atenção'); // 1,44 → 1,80
  });

  it('acima da última cota, diz quanto passou', () => {
    expect(distanciaDaCota(guaiba)).toBe('0,68 m acima da cota de inundação'); // 3,68 − 3,00
  });

  it('explica com franqueza quando o rio fica com a regra simples (Dilúvio)', () => {
    expect(explicacaoDoModelo(diluvio)).toMatch(/repete o nível de agora/);
    expect(explicacaoDoModelo(guaiba)).toMatch(/IA \(random forest\)/);
  });
});
