/** Ajustes. (Etapa 1: só a situação do sistema; bairro, pessoas e avisos chegam na etapa 4.) */
import { StyleSheet, Text, View } from 'react-native';

import { urlBaseDaApi } from '@/api/cliente';
import { useSaude } from '@/api/consultas';
import { EstadoDaConsulta } from '@/componentes/EstadoDaConsulta';
import { Tela } from '@/componentes/Tela';
import { horaCurta } from '@/logica/formato';
import { cores, espaco, raio, texto } from '@/tema';

function Item({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <View style={estilos.item}>
      <Text style={texto.suave}>{rotulo}</Text>
      <Text style={[texto.corpo, estilos.valor]}>{valor}</Text>
    </View>
  );
}

export default function Ajustes() {
  const saude = useSaude();

  return (
    <Tela>
      <Text style={texto.titulo}>Situação do sistema</Text>
      <EstadoDaConsulta consulta={saude} carregando="Consultando o servidor…">
        {(s) => (
          <View style={estilos.cartao}>
            <Item rotulo="Servidor" valor={s.status === 'ok' ? 'No ar' : s.status} />
            <Item rotulo="Banco de dados" valor={s.banco ? 'Acessível' : 'Fora do ar'} />
            <Item rotulo="Previsão" valor={`${s.modelo.estacoes.length} rios, ${s.modelo.horizonte_h} h à frente`} />
            <Item
              rotulo="Vigia de alertas (última rodada)"
              valor={s.vigia.ultima_rodada_utc ? horaCurta(new Date(s.vigia.ultima_rodada_utc)) : 'ainda não rodou'}
            />
            {s.vigia.ultimo_erro ? <Item rotulo="Último erro do vigia" valor={s.vigia.ultimo_erro} /> : null}
          </View>
        )}
      </EstadoDaConsulta>
      <Item rotulo="Endereço da API" valor={urlBaseDaApi()} />
    </Tela>
  );
}

const estilos = StyleSheet.create({
  cartao: {
    backgroundColor: cores.superficie,
    borderRadius: raio.lg,
    padding: espaco.lg,
    gap: espaco.md,
    borderWidth: 1,
    borderColor: cores.borda,
  },
  item: { gap: 2 },
  valor: { fontWeight: '600' },
});
