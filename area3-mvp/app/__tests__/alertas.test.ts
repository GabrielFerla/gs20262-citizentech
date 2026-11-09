import type { AlertaDoVigia } from '@/api/tipos';
import { avisoDoAlerta, chaveDoAlerta, DetectorDeAlertas, faixaDosAvisos, mostraFaixa } from '@/logica/alertas';

import { copia, fixtures } from '../test-utils/apiFalsa';

const alerta = (estacao_id: string, severidade: number, aberto_em = '2026-11-08T20:00:00Z'): AlertaDoVigia => ({
  estacao_id,
  severidade,
  aberto_em,
  atualizado_em: aberto_em,
  nivel_previsto_m: 3,
  pico_previsto_m: 3,
  antecipado: true,
  mensagem_sms: null,
});

describe('quando avisar (alerta novo do vigia)', () => {
  it('o que já estava aberto quando o app abriu não vira notificação', () => {
    const detector = new DetectorDeAlertas();
    expect(detector.novos([alerta('gua-cais', 3)])).toEqual([]);
    expect(detector.novos([alerta('gua-cais', 3)])).toEqual([]);
  });

  it('alerta que abre com o app aberto avisa uma vez só', () => {
    const detector = new DetectorDeAlertas();
    detector.novos([]);
    expect(detector.novos([alerta('gra-sarandi', 1)]).map(chaveDoAlerta)).toEqual([
      'gra-sarandi:1:2026-11-08T20:00:00Z',
    ]);
    expect(detector.novos([alerta('gra-sarandi', 1)])).toEqual([]);
  });

  it('escalar (atenção → alerta) avisa de novo', () => {
    const detector = new DetectorDeAlertas();
    detector.novos([alerta('gra-sarandi', 1)]);
    expect(detector.novos([alerta('gra-sarandi', 2)])).toHaveLength(1);
  });

  it('fechou e abriu de novo: é outro alerta (outro horário de abertura)', () => {
    const detector = new DetectorDeAlertas();
    detector.novos([alerta('gua-cais', 2)]);
    detector.novos([]);
    expect(detector.novos([alerta('gua-cais', 2, '2026-11-08T21:00:00Z')])).toHaveLength(1);
  });

  it('vários novos ao mesmo tempo: o mais grave primeiro', () => {
    const detector = new DetectorDeAlertas();
    detector.novos([]);
    const novos = detector.novos([alerta('gra-sarandi', 1), alerta('gua-cais', 3)]);
    expect(novos.map((a) => a.estacao_id)).toEqual(['gua-cais', 'gra-sarandi']);
  });
});

describe('texto do aviso', () => {
  it('usa o push da API e leva para "Onde ficar seguro" a partir do alerta', () => {
    const aviso = avisoDoAlerta(alerta('gua-cais', 3), fixtures.alertasNavegantes);
    expect(aviso).toMatchObject({
      titulo: 'Saia agora: risco de alagamento',
      rota: '/abrigos',
    });
    expect(aviso.corpo).toMatch(/^Saia agora para um lugar alto\./);
    expect(`${aviso.titulo} ${aviso.corpo}`).not.toMatch(/DEFESA CIVIL:/);
  });

  it('atenção leva para a tela Agora (ainda não é para sair)', () => {
    expect(avisoDoAlerta(alerta('gra-sarandi', 1), fixtures.alertasNavegantes)).toMatchObject({
      titulo: 'Atenção: rio acima do normal',
      rota: '/',
    });
  });

  it('sem a mensagem da API, um texto simples', () => {
    const semRios = { ...copia(fixtures.alertasNavegantes), rios_fora_do_normal: [] };
    const aviso = avisoDoAlerta(alerta('dil-ipiranga', 2), semRios);
    expect(aviso.titulo).toBe('Alerta: um rio deve subir');
    expect(aviso.corpo).toMatch(/Abra o Abriga/);
  });
});

describe('onde a faixa aparece', () => {
  const sair = avisoDoAlerta(alerta('gua-cais', 3), fixtures.alertasNavegantes);
  const atencao = avisoDoAlerta(alerta('gra-sarandi', 1), fixtures.alertasNavegantes);

  it('em qualquer tela, menos onde a pessoa já procura abrigo', () => {
    expect(['/', '/rio/gua-cais', '/ajustes'].every((rota) => mostraFaixa(sair, rota))).toBe(true);
    expect(mostraFaixa(sair, '/abrigos')).toBe(false);
    expect(mostraFaixa(sair, '/abrigo/abr-10')).toBe(false);
  });

  it('o aviso de atenção (que leva para Agora) aparece até na tela de abrigos', () => {
    expect(mostraFaixa(atencao, '/abrigos')).toBe(true);
  });
});

describe('vários alertas na mesma leitura', () => {
  it('a faixa mostra o mais grave e cita os outros rios', () => {
    const avisos = [alerta('gua-cais', 3), alerta('gra-sarandi', 1)].map((a) =>
      avisoDoAlerta(a, fixtures.alertasNavegantes),
    );
    const faixa = faixaDosAvisos(avisos);
    expect(faixa).toMatchObject({ titulo: 'Saia agora: risco de alagamento', rota: '/abrigos' });
    expect(faixa.tambem).toBe('Também: Rio Gravataí (atenção).');
  });

  it('com um alerta só, a faixa é o próprio aviso', () => {
    const aviso = avisoDoAlerta(alerta('gua-cais', 3), fixtures.alertasNavegantes);
    expect(faixaDosAvisos([aviso])).toBe(aviso);
  });
});
