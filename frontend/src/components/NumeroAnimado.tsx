/**
 * NumeroAnimado — contagem de 400ms entre o valor anterior e o novo.
 *
 * APRESENTAÇÃO, NÃO CÁLCULO
 *   Os quadros intermediários interpolam números só para a animação. O quadro
 *   final exibe `textoFinal`, que é o valor formatado vindo da API — o número
 *   exibido em repouso é sempre o do servidor, nunca uma conta do navegador.
 *
 * Com `prefers-reduced-motion`, troca direto para o valor final.
 */

import { useEffect, useRef, useState } from "react";
import { valorNoInstante } from "@/lib/animacao";

const DURACAO_MS = 400;

function preferirMenosMovimento(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

interface PropsNumeroAnimado {
  /** Valor numérico de destino, usado só para interpolar a animação. */
  valor: number;
  /** Texto exato a exibir quando a animação termina (vindo da API). */
  textoFinal: string;
  /** Formata os quadros intermediários. */
  formatar: (n: number) => string;
  className?: string;
}

export function NumeroAnimado({ valor, textoFinal, formatar, className }: PropsNumeroAnimado) {
  const [texto, setTexto] = useState(textoFinal);
  const anterior = useRef(valor);

  useEffect(() => {
    const de = anterior.current;
    anterior.current = valor;

    if (de === valor || preferirMenosMovimento()) {
      setTexto(textoFinal);
      return;
    }

    const inicio = performance.now();
    let quadro = 0;
    const passo = (agora: number) => {
      const progresso = (agora - inicio) / DURACAO_MS;
      if (progresso >= 1) {
        setTexto(textoFinal);
        return;
      }
      setTexto(formatar(valorNoInstante(de, valor, progresso)));
      quadro = requestAnimationFrame(passo);
    };
    quadro = requestAnimationFrame(passo);

    // valor novo no meio da animação: cancela e recomeça do ponto atual
    return () => cancelAnimationFrame(quadro);
    // `formatar` costuma ser uma função inline; não deve reiniciar a animação
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [valor, textoFinal]);

  // Os quadros da animação ficam fora da árvore de acessibilidade: o leitor
  // de tela lê só o valor final, sem anunciar cada passo da contagem.
  return (
    <span className={className}>
      <span aria-hidden="true">{texto}</span>
      <span className="sr-only">{textoFinal}</span>
    </span>
  );
}
