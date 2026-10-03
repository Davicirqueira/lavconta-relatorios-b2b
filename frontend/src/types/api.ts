/**
 * Tipos TypeScript que espelham os schemas Pydantic da API FastAPI.
 *
 * CONVENÇÃO DE DINHEIRO
 *   Valores monetários chegam como string decimal ("4.50"). Nunca converter
 *   para Number antes de exibir — usar formatarMoeda() de lib/dinheiro.ts.
 *
 * CONVENÇÃO DE DATA
 *   Datas chegam como string ISO YYYY-MM-DD. Exibir via paraExibicao() de
 *   lib/datas.ts — nunca passar por new Date().
 */

// ------------------------------------------------------------------ //
// Clientes                                                            //
// ------------------------------------------------------------------ //

/** Espelha `ClienteResposta` do backend — só estes três campos existem. */
export interface Cliente {
  id: string;
  nome: string;
  ativo: boolean;
}

// ------------------------------------------------------------------ //
// Itens (catálogo)                                                    //
// ------------------------------------------------------------------ //

/** Espelha `ItemResposta` do backend (v1.1: com o preço que vale hoje). */
export interface Item {
  id: string;
  cliente_id: string;
  nome: string;
  ativo: boolean;
  /** Null quando o item ainda não tem preço. */
  preco_atual: PrecoAtual | null;
}

/** Corpo de criação: nome e preço juntos (o preço é obrigatório). */
export interface ItemNovo {
  nome: string;
  /** Texto decimal ("4.50"), nunca número */
  valor_unitario: string;
}

// ------------------------------------------------------------------ //
// Preços (v1.1: o preço vale a partir de um dia até ser alterado)     //
// ------------------------------------------------------------------ //

export interface PrecoAtual {
  /** String decimal */
  valor_unitario: string;
  /** Dia em que o preço começou a valer (YYYY-MM-DD) */
  desde: string;
  /** Começou hoje: mudar e corrigir têm o mesmo efeito */
  e_hoje: boolean;
}

/** Como a alteração é aplicada. Pedidos já registrados não mudam em nenhum. */
export type ModoDeAlteracao = "a_partir_de_hoje" | "corrigir_atual";

export interface AlteracaoDePreco {
  valor_unitario: string;
  modo: ModoDeAlteracao;
}

export interface ImpactoDaAlteracao {
  pedidos_com_valor_anterior: number;
}

/** Preço de um item numa data (formulário de pedido). */
export interface ItemComPreco {
  item_id: string;
  nome: string;
  /** String decimal ou null quando sem preço */
  valor_unitario: string | null;
  desde: string | null;
  sem_preco: boolean;
}

export interface PrecosNaData {
  data: string;
  itens: ItemComPreco[];
}

// ------------------------------------------------------------------ //
// Lançamentos                                                         //
// ------------------------------------------------------------------ //

export interface LinhaEntrada {
  item_id: string;
  quantidade: number;
}

/** Corpo de criação e edição. O cliente nunca envia valor. */
export interface LancamentoEntrada {
  cliente_id: string;
  data: string; // YYYY-MM-DD
  comanda: string | null;
  linhas: LinhaEntrada[];
}

export interface LinhaLancamento {
  id: string;
  item_id: string;
  quantidade: number;
  valor_unitario_congelado: string;
  total: string;
}

export interface Lancamento {
  id: string;
  cliente_id: string;
  data: string;
  comanda: string | null;
  linhas: LinhaLancamento[];
  total_pecas: number;
  total_valor: string;
}

export interface LancamentoResumo {
  id: string;
  cliente_id: string;
  data: string;
  comanda: string | null;
  total_pecas: number;
  total_valor: string;
}

export interface PreviaEntrada {
  cliente_id: string;
  data: string;
  linhas: LinhaEntrada[];
  /** Ao editar: faz a prévia respeitar os valores congelados. */
  lancamento_id?: string;
}

export interface LinhaPrevia {
  item_id: string;
  quantidade: number;
  valor_unitario: string;
  total: string;
}

export interface PreviaResposta {
  linhas: LinhaPrevia[];
  total_pecas: number;
  total_valor: string;
  itens_sem_preco: string[];
}

// ------------------------------------------------------------------ //
// Relatório                                                           //
// ------------------------------------------------------------------ //

export interface ColunaItemRelatorio {
  item_id: string;
  nome: string;
}

export interface LinhaRelatorio {
  lancamento_id: string;
  data: string;
  comanda: string | null;
  /** item_id → quantidade. Item ausente = célula vazia. */
  quantidades: Record<string, number>;
  total_pecas: number;
  total_valor: string;
}

/** Um item a um valor por peça, somado no período (v1.1). */
export interface LinhaResumoItem {
  item_id: string;
  item_nome: string;
  valor_unitario: string;
  quantidade: number;
  subtotal: string;
}

/** Relatório de todos os clientes do período (v1.1, Req 5). */
export interface RelatorioGeral {
  periodo: { inicio: string; fim: string };
  secoes: {
    cliente: { id: string; nome: string };
    linhas: LinhaResumoItem[];
    total_pecas: number;
    total_valor: string;
  }[];
  total_pecas: number;
  total_valor: string;
}

export interface Relatorio {
  /** Peças e subtotal por item e valor por peça (v1.1) */
  resumo_por_item: LinhaResumoItem[];
  cliente: { id: string; nome: string };
  periodo: { inicio: string; fim: string };
  colunas_itens: ColunaItemRelatorio[];
  linhas: LinhaRelatorio[];
  totais: {
    por_item: Record<string, number>;
    total_pecas: number;
    total_valor: string;
  };
  resumo: {
    total_pecas: number;
    total_valor: string;
    quantidade_lancamentos: number;
    media_diaria_pecas: number;
  };
}

// ------------------------------------------------------------------ //
// Envelope de erro (espelhado em ErroDeApi de lib/api.ts)            //
// ------------------------------------------------------------------ //

export interface ErroApi {
  codigo: string;
  mensagem: string;
  detalhes?: Record<string, unknown>;
}
