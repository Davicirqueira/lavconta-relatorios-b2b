/**
 * Valor exibido num instante da contagem animada.
 *
 * É só apresentação: os quadros intermediários interpolam entre o número
 * anterior e o novo; o quadro final exibe o texto exato vindo da API.
 */
export function valorNoInstante(de: number, para: number, progresso: number): number {
  const p = Math.min(1, Math.max(0, progresso));
  // ease-out cúbico: rápido no início, assenta suave no valor final
  const suavizado = 1 - (1 - p) ** 3;
  return de + (para - de) * suavizado;
}
