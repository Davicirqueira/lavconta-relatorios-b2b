/**
 * CampoData — campo de data nativo (`type="date"`), com calendário.
 *
 * POR QUE O NATIVO RESPEITA A REGRA DE DATAS
 *   O valor de um `<input type="date">` é sempre texto ISO (YYYY-MM-DD), sem
 *   hora e sem fuso. Nada passa por `new Date()`; o que o operador escolhe é
 *   exatamente o dia que trafega para a API.
 *
 * FORMATO EXIBIDO
 *   Quem decide é o navegador, pelo idioma dele. Num navegador em português
 *   aparece dd/mm/aaaa. O atributo `lang` da página não altera isso.
 *
 * CONTRATO
 *   `aoMudar(iso)` com a data escolhida, ou `aoMudar("")` quando o campo fica
 *   incompleto ou vazio — o navegador só entrega valor para data válida.
 */

import { Campo, type PropsCampo } from "./Campo";

export interface PropsCampoData extends Omit<PropsCampo, "value" | "onChange" | "type"> {
  /** Valor em ISO (YYYY-MM-DD), ou "" quando vazio/incompleto. */
  valor: string;
  aoMudar: (iso: string) => void;
}

export function CampoData({ valor, aoMudar, ...rest }: PropsCampoData) {
  return (
    <Campo type="date" value={valor} onChange={(e) => aoMudar(e.target.value)} {...rest} />
  );
}
