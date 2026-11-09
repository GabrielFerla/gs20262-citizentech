/**
 * "Como chegar": abre o mapa do aparelho (ou do navegador) com o caminho a pé até o abrigo.
 * Vai SÓ o destino. O ponto de partida o próprio mapa pega da localização do aparelho;
 * o Abriga não envia a posição da pessoa a ninguém.
 */
export function urlComoChegar(lat: number, lon: number): string {
  const destino = `${lat.toFixed(5)},${lon.toFixed(5)}`;
  return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(destino)}&travelmode=walking`;
}
