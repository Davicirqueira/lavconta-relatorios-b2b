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
// Linhas do formulário                                                //
// ------------------------------------------------------------------ //

/** Linha como o operador a edita. Quantidade é texto para aceitar digitação livre. */
export interface LinhaFormulario {
  chave: string;
  item_id: string;
  quantidade: string;
}

let contadorChave = 0;
export function novaLinha(item_id = "", quantidade = ""): LinhaFormulario {
  contadorChave += 1;
  return { chave: `linha-${contadorChave}`, item_id, quantidade };
}

/** Mantém só dígitos, até 6 — quantidade é inteiro positivo de peças. */
export function normalizarQuantidade(texto: string): string {
  return texto.replace(/\D/g, "").replace(/^0+(?=\d)/, "").slice(0, 6);
}

/** Stepper: soma `delta` respeitando o mínimo de 1 peça. */
export function passoQuantidade(atual: string, delta: number): string {
  const numero = Number(atual) || 0;
  return String(Math.max(1, Math.min(999_999, numero + delta)));
}

export type ProblemaLinha = "sem_item" | "sem_quantidade" | "duplicado";

export interface LinhasPreparadas {
  /** Linhas completas, prontas para a API. */
  linhas: LinhaEntrada[];
  /** Problema por chave de linha, para marcar em linha. */
  problemas: Map<string, ProblemaLinha>;
}

/**
 * Separa o que pode ir para a API do que ainda está incompleto.
 *
 * Linha totalmente vazia é ignorada (é a linha em branco esperando o próximo
 * item). Linha com item repetido é problema: a API recusaria o pedido inteiro
 * com ITEM_DUPLICADO_NO_LANCAMENTO.
 */
export function prepararLinhas(linhas: LinhaFormulario[]): LinhasPreparadas {
  const problemas = new Map<string, ProblemaLinha>();
  const vistos = new Map<string, string>(); // item_id → chave da primeira ocorrência
  const prontas: LinhaEntrada[] = [];

  for (const linha of linhas) {
    const quantidade = Number(linha.quantidade);
    const temItem = !!linha.item_id;
    const temQuantidade = linha.quantidade !== "" && quantidade > 0;

    if (!temItem && !temQuantidade) continue;
    if (!temItem) {
      problemas.set(linha.chave, "sem_item");
      continue;
    }
    if (!temQuantidade) {
      problemas.set(linha.chave, "sem_quantidade");
      continue;
    }
    if (vistos.has(linha.item_id)) {
      problemas.set(linha.chave, "duplicado");
      continue;
    }
    vistos.set(linha.item_id, linha.chave);
    prontas.push({ item_id: linha.item_id, quantidade });
  }

  return { linhas: prontas, problemas };
}

export const MENSAGEM_PROBLEMA: Record<ProblemaLinha, string> = {
  sem_item: "Selecione o item.",
  sem_quantidade: "Informe a quantidade.",
  duplicado: "Este item já está no lançamento.",
};

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
