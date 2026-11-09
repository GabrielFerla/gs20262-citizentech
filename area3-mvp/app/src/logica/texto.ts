/** Ajudas de texto: busca sem acento e primeira letra maiúscula. */
import type { Bairro } from '@/api/tipos';

/** "São João" → "sao joao" (para buscar sem se preocupar com acento e maiúscula). */
export function semAcento(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

/** Bairros cujo nome contém a busca (sem acento), em ordem alfabética. */
export function filtrarBairros(bairros: Bairro[], busca: string): Bairro[] {
  const termo = semAcento(busca);
  return bairros
    .filter((b) => !termo || semAcento(b.bairro).includes(termo))
    .sort((a, b) => a.bairro.localeCompare(b.bairro, 'pt-BR'));
}

/** "lotado" → "Lotado" (os motivos da API vêm em minúscula). */
export function capitalizar(texto: string): string {
  return texto ? texto[0].toUpperCase() + texto.slice(1) : texto;
}
