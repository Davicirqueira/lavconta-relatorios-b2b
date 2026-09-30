/**
 * Cliente Supabase — autenticação única do frontend.
 *
 * Só `VITE_SUPABASE_URL` e `VITE_SUPABASE_PUBLISHABLE_KEY` vão ao bundle.
 * São públicas por design: a publishable key identifica o projeto, não
 * concede acesso direto a dados. O Data API está desligado; ela serve
 * apenas para autenticação via Supabase Auth.
 *
 * A chave `service_role` NUNCA aparece aqui — fica somente no backend.
 */

import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string;
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string;

if (!supabaseUrl || !supabaseKey) {
  throw new Error(
    "Variáveis VITE_SUPABASE_URL e VITE_SUPABASE_PUBLISHABLE_KEY são obrigatórias. " +
      "Copie frontend/.env.example para frontend/.env e preencha os valores.",
  );
}

export const supabase = createClient(supabaseUrl, supabaseKey, {
  auth: {
    // Persiste a sessão no localStorage para sobreviver ao recarregamento
    persistSession: true,
    autoRefreshToken: true,
  },
});

/** Obtém o token JWT da sessão atual, ou null se não autenticado. */
export async function obterToken(): Promise<string | null> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}
