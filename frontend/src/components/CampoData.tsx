/**
 * CampoData — input de data no formato dd/mm/yyyy.
 *
 * REGRA: sem `new Date()` para data de negócio.
 * O campo trabalha em ISO (YYYY-MM-DD) para fora e em dd/mm/yyyy para o
 * operador. A conversão é manipulação de texto.
 *
 * CONTRATO
 *   - `aoMudar(iso)` quando a data digitada é válida no calendário.
 *   - `aoMudar("")` quando o texto está incompleto ou inválido — assim o pai
 *     sabe que não há data utilizável, em vez de manter silenciosamente a
 *     última data válida.
 *   - Mudança externa de `valor` (ex.: lançamento carregado para edição)
 *     atualiza o que é exibido.
 */

import { useEffect, useState, type ChangeEvent } from "react";
import { Campo, type PropsCampo } from "./Campo";
import { interpretarDataBr, paraExibicao } from "@/lib/datas";

export interface PropsCampoData
  extends Omit<PropsCampo, "value" | "onChange" | "type"> {
  /** Valor em ISO (YYYY-MM-DD), ou "" quando vazio/inválido. */
  valor: string;
  /** Recebe ISO válido, ou "" quando o texto não forma uma data válida. */
  aoMudar: (iso: string) => void;
}

/** Máscara dd/mm/yyyy: insere as barras enquanto o operador digita. */
function mascarar(texto: string): string {
  const digitos = texto.replace(/\D/g, "").slice(0, 8);
  if (digitos.length <= 2) return digitos;
  if (digitos.length <= 4) return `${digitos.slice(0, 2)}/${digitos.slice(2)}`;
  return `${digitos.slice(0, 2)}/${digitos.slice(2, 4)}/${digitos.slice(4)}`;
}

export function CampoData({ valor, aoMudar, rotulo, ...rest }: PropsCampoData) {
  const [exibicao, setExibicao] = useState<string>(valor ? paraExibicao(valor) : "");

  // Sincroniza com o pai sem apagar o que o operador está digitando: só
  // sobrescreve quando o pai traz uma data válida diferente da exibida.
  useEffect(() => {
    if (valor && interpretarDataBr(exibicao) !== valor) {
      setExibicao(paraExibicao(valor));
    }
    // `exibicao` fora das dependências de propósito: a sincronização reage
    // só a mudanças vindas do pai.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [valor]);

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const mascarado = mascarar(e.target.value);
    setExibicao(mascarado);
    aoMudar(interpretarDataBr(mascarado) ?? "");
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
