import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react-native';
import { Text } from 'react-native';

import { ErroApi } from '@/api/cliente';
import { EstadoDaConsulta } from '@/componentes/EstadoDaConsulta';

function Exemplo({ buscar }: { buscar: () => Promise<string> }) {
  const consulta = useQuery({ queryKey: ['exemplo'], queryFn: buscar });
  return <EstadoDaConsulta consulta={consulta}>{(valor) => <Text>valor: {valor}</Text>}</EstadoDaConsulta>;
}

function montar(buscar: () => Promise<string>) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
  return {
    cliente,
    tela: render(
      <QueryClientProvider client={cliente}>
        <Exemplo buscar={buscar} />
      </QueryClientProvider>,
    ),
  };
}

describe('EstadoDaConsulta (nunca tela em branco)', () => {
  it('mostra os dados quando a API responde', async () => {
    await montar(async () => 'ok').tela;
    expect(await screen.findByText('valor: ok')).toBeOnTheScreen();
  });

  it('banco fora do ar e nenhum dado ainda: aviso amigável com "Tentar de novo"', async () => {
    await montar(async () => {
      throw new ErroApi('servidor_indisponivel', 503);
    }).tela;
    expect(await screen.findByText('Não deu para carregar')).toBeOnTheScreen();
    expect(screen.getByText('O servidor de dados está fora do ar. Tentando de novo…')).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: 'Tentar de novo' })).toBeOnTheScreen();
  });

  it('API cai depois de já ter dado: continua mostrando o último dado, com aviso', async () => {
    let falhar = false;
    const { cliente, tela } = montar(async () => {
      if (falhar) throw new ErroApi('sem_conexao');
      return 'primeira leitura';
    });
    await tela;
    expect(await screen.findByText('valor: primeira leitura')).toBeOnTheScreen();

    falhar = true;
    await cliente.refetchQueries({ queryKey: ['exemplo'] });

    expect(await screen.findByText(/Sem conexão com o Abriga/)).toBeOnTheScreen();
    expect(screen.getByText(/Mostrando os últimos dados recebidos/)).toBeOnTheScreen();
    expect(screen.getByText('valor: primeira leitura')).toBeOnTheScreen();
  });
});
