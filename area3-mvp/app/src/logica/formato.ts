/** Formatos em português do Brasil, sem depender do Intl do aparelho. */

const doisDigitos = (n: number) => String(n).padStart(2, '0');

/** 14:02:31 (hora local). */
export function horaCurta(data: Date): string {
  return `${doisDigitos(data.getHours())}:${doisDigitos(data.getMinutes())}:${doisDigitos(data.getSeconds())}`;
}

/** 3,08 m */
export function metros(valor: number): string {
  return `${valor.toFixed(2).replace('.', ',')} m`;
}

/** 81 min a pé · 1 h 21 min a pé */
export function minutosAPeTexto(minutos: number): string {
  if (minutos < 60) return `${minutos} min a pé`;
  const horas = Math.floor(minutos / 60);
  const resto = minutos % 60;
  return resto === 0 ? `${horas} h a pé` : `${horas} h ${resto} min a pé`;
}

/** 4,2 km · 850 m */
export function km(valor: number): string {
  if (valor < 1) return `${Math.round(valor * 1000)} m`;
  return `${valor.toFixed(1).replace('.', ',')} km`;
}
