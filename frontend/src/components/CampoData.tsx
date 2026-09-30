/**
 * CampoData — input de data no formato dd/mm/yyyy.
 *
 * REGRA: sem `new Date()` para data de negócio.
 * O campo armazena e emite sempre YYYY-MM-DD (formato ISO), mas exibe
 * e aceita entrada do usuário em dd/mm/yyyy, que é o padrão brasileiro.
 *
 * `valor` e `aoMudar` trabalham com ISO; a máscara de exibição é interna.
 */

import { useState, type ChangeEvent } from "react";
import { Campo, type PropsCampo } from "./Campo";
import { paraExibicao, paraIso } from "@/lib/datas";

export interface PropsCampoData
  extends Omit<PropsCampo, "value" | "onChange" | "type"> {
  /** Valor em formato ISO (YYYY-MM-DD) */
  valor: string;
  /** Emite o valor em formato ISO (YYYY-MM-DD) */
  aoMudar: (iso: string) => void;
}

/** Máscara simples dd/mm/yyyy: insere barras automaticamente */
function mascarar(texto: string): string {
  const so_digitos = texto.replace(/\D/g, "").slice(0, 8);
  if (so_digitos.length <= 2) return so_digitos;
  if (so_digitos.length <= 4)
    return `${so_digitos.slice(0, 2)}/${so_digitos.slice(2)}`;
  return `${so_digitos.slice(0, 2)}/${so_digitos.slice(2, 4)}/${so_digitos.slice(4)}`;
}

function eDataValida(br: string): boolean {
  if (br.length !== 10) return false;
  const [dia, mes, ano] = br.split("/").map(Number);
  if (!dia || !mes || !ano) return false;
  if (mes < 1 || mes > 12) return false;
  if (dia < 1 || dia > 31) return false;
  if (ano < 2000 || ano > 2099) return false;
  return true;
}

export function CampoData({ valor, aoMudar, rotulo, ...rest }: PropsCampoData) {
  // Exibição em br; sincroniza com o valor ISO do pai
  const [exibicao, setExibicao] = useState<string>(
    valor ? paraExibicao(valor) : "",
  );

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const mascarado = mascarar(e.target.value);
    setExibicao(mascarado);
    if (eDataValida(mascarado)) {
      aoMudar(paraIso(mascarado));
    }
  }

  return (
    <Campo
      rotulo={rotulo}
      type="text"
      inputMode="numeric"
      placeholder="dd/mm/aaaa"
      maxLength={10}
      value={exibicao}
      onChange={handleChange}
      {...rest}
    />
  );
}
