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

export interface Cliente {
  id: string;
  nome: string;
  ativo: boolean;
  criado_em: string;
  atualizado_em: string;
}

// ------------------------------------------------------------------ //
// Itens (catálogo)                                                    //
// ------------------------------------------------------------------ //

export interface Item {
  id: string;
  cliente_id: string;
  nome: string;
  ativo: boolean;
  criado_em: string;
  atualizado_em: string;
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
// Envelope de erro (espelhado em ErroDeApi de lib/api.ts)            //
// ------------------------------------------------------------------ //

export interface ErroApi {
  codigo: string;
  mensagem: string;
  detalhes?: Record<string, unknown>;
}
