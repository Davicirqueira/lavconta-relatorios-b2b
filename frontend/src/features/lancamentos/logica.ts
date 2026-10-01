/**
 * Lógica do formulário de lançamento, sem React — testável em isolamento.
 *
 * NADA AQUI CALCULA VALOR. Preço, total de linha e totais vêm sempre da API
 * (prévia ou salvamento). O que fica no frontend é preparar a entrada e
 * interpretar a resposta.
 */

import { ErroDeApi } from "@/lib/api";
import type { Item, LinhaEntrada } from "@/types/api";

// ------------------------------------------------------------------ //
// Quantidades do pedido                                               //
//                                                                     //
// O formulário lista todos os itens do catálogo; cada um tem uma       //
// quantidade em texto (aceita digitação livre). Item vazio ou zero não //
// entra no pedido. Como cada item aparece uma vez, repetição de item   //
// é impossível por construção.                                         //
// ------------------------------------------------------------------ //

/** item_id → quantidade digitada (texto; "" = fora do pedido). */
export type Quantidades = Record<string, string>;

/** Mantém só dígitos, até 6 — quantidade é inteiro positivo de peças. */
export function normalizarQuantidade(texto: string): string {
  return texto.replace(/\D/g, "").replace(/^0+(?=\d)/, "").slice(0, 6);
}

/**
 * Stepper: soma `delta` à quantidade.
 *
 * Descer de 1 tira o item do pedido (""), em vez de travar em 1: com todos os
 * itens listados, o "−" é também a forma de desfazer.
 */
export function passoQuantidade(atual: string, delta: number): string {
  const numero = Math.min(999_999, (Number(atual) || 0) + delta);
  return numero > 0 ? String(numero) : "";
}

/**
 * Linhas do pedido para a API: só itens com quantidade positiva, na ordem em
 * que o catálogo os exibe.
 */
export function linhasDoPedido(quantidades: Quantidades, ordem: string[]): LinhaEntrada[] {
  return ordem
    .map((item_id) => ({ item_id, quantidade: Number(quantidades[item_id] ?? "") }))
    .filter((linha) => Number.isInteger(linha.quantidade) && linha.quantidade > 0);
}

// ------------------------------------------------------------------ //
// Agendamento da prévia: debounce + cancelamento                      //
// ------------------------------------------------------------------ //

export interface AgendadorPrevia<A> {
  agendar: (argumentos: A) => void;
  cancelar: () => void;
}

/**
 * Agenda uma chamada após `atrasoMs` de silêncio e cancela a anterior.
 *
 * Duas garantias (design §11):
 *   1. Debounce: só a última alteração dentro da janela dispara requisição.
 *   2. Resposta atrasada nunca sobrescreve valor mais novo: ao agendar de
 *      novo, a requisição em voo é abortada e qualquer resultado dela é
 *      descartado — mesmo que o servidor responda depois do cancelamento.
 */
export function criarAgendador<A, R>(opcoes: {
  executar: (argumentos: A, sinal: AbortSignal) => Promise<R>;
  atrasoMs: number;
  aoIniciar?: () => void;
  aoResultado: (resultado: R) => void;
  aoErro: (erro: unknown) => void;
}): AgendadorPrevia<A> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  let emVoo: AbortController | null = null;

  function cancelar() {
    clearTimeout(timer);
    emVoo?.abort();
    emVoo = null;
  }

  function agendar(argumentos: A) {
    cancelar();
    timer = setTimeout(() => {
      const controle = new AbortController();
      emVoo = controle;
      opcoes.aoIniciar?.();
      opcoes.executar(argumentos, controle.signal).then(
        (resultado) => {
          if (!controle.signal.aborted) opcoes.aoResultado(resultado);
        },
        (erro) => {
          if (!controle.signal.aborted) opcoes.aoErro(erro);
        },
      );
    }, opcoes.atrasoMs);
  }

  return { agendar, cancelar };
}

// ------------------------------------------------------------------ //
// Erro de salvamento → campo                                          //
// ------------------------------------------------------------------ //

export interface ErroInterpretado {
  /** Mensagem junto ao campo de data. */
  data?: string;
  /** Mensagem junto ao campo de comanda. */
  comanda?: string;
  /** Mensagem no banner do topo do formulário. */
  geral?: string;
  /** Itens (por id) a marcar em linha. */
  itensMarcados: string[];
}

/**
 * Decide onde cada erro da API aparece.
 *
 * Regra de interface: erro de campo junto ao campo; erro da operação inteira
 * no banner. A mensagem é sempre a da API (em português), não reescrita aqui.
 *
 * ITENS_SEM_PRECO e ITEM_DUPLICADO trazem NOMES de item nos detalhes; são
 * convertidos em ids pelo catálogo para marcar as linhas certas.
 */
export function interpretarErroDeSalvamento(erro: unknown, catalogo: Item[]): ErroInterpretado {
  if (!(erro instanceof ErroDeApi)) {
    return { geral: "Ocorreu um erro inesperado. Tente novamente.", itensMarcados: [] };
  }

  const idsPorNome = (nomes: unknown): string[] => {
    const lista = Array.isArray(nomes) ? nomes : typeof nomes === "string" ? [nomes] : [];
    return catalogo.filter((item) => lista.includes(item.nome)).map((item) => item.id);
  };

  switch (erro.codigo) {
    case "LANCAMENTO_DUPLICADO":
    case "DATA_FUTURA":
      return { data: erro.message, itensMarcados: [] };
    case "COMANDA_DUPLICADA":
      return { comanda: erro.message, itensMarcados: [] };
    case "ITENS_SEM_PRECO":
      return { geral: erro.message, itensMarcados: idsPorNome(erro.detalhes?.itens) };
    case "ITEM_DUPLICADO_NO_LANCAMENTO":
      return { geral: erro.message, itensMarcados: idsPorNome(erro.detalhes?.item) };
    default:
      return { geral: erro.message, itensMarcados: [] };
  }
}
