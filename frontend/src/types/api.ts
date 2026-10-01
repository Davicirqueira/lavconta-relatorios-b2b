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

/** Espelha `ItemResposta` do backend. */
export interface Item {
  id: string;
  cliente_id: string;
  nome: string;
  ativo: boolean;
}

// ------------------------------------------------------------------ //
// Preços                                                              //
// ------------------------------------------------------------------ //

export interface ItemComPreco {
  item_id: string;
  nome: string;
  /** String decimal ou null quando sem preço */
  valor_unitario: string | null;
  /** Mês de origem do preço ("YYYY-MM") ou null */
  vigencia_origem: string | null;
  sem_preco: boolean;
}

export interface PrecosDoMes {
  /** Mês consultado no formato "YYYY-MM" */
  mes: string;
  itens: ItemComPreco[];
}

export interface PrecoResposta {
  id: string;
  cliente_id: string;
  item_id: string;
  /** Mês de vigência no formato "YYYY-MM" */
  vigencia_mes: string;
  /** String decimal */
  valor_unitario: string;
}

export interface VigenciaSugerida {
  /** Mês sugerido no formato "YYYY-MM" */
  vigencia_mes: string;
  e_primeiro_preco: boolean;
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

export interface Relatorio {
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
