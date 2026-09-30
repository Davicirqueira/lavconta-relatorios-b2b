/**
 * RotaProtegida — verifica sessão Supabase e redireciona para /login se ausente.
 *
 * Também escuta o evento de expiração da sessão (token_refreshed com null)
 * e avisa o operador antes de redirecionar.
 *
 * Sem rota de cadastro: o Supabase está configurado com disable_signup=true
 * (verificado no design.md §18). Esta tela apenas guarda as rotas.
 */

import { useEffect, useState } from "react";
import { Outlet, Navigate } from "react-router";
import { supabase } from "@/lib/supabase";
import { useToast } from "@/components/Toast";

export function RotaProtegida() {
  const [sessaoVerificada, setSessaoVerificada] = useState(false);
  const [autenticado, setAutenticado] = useState(false);
  const { mostrar } = useToast();

  useEffect(() => {
    // Verifica sessão atual
    supabase.auth.getSession().then(({ data: { session } }) => {
      setAutenticado(!!session);
      setSessaoVerificada(true);
    });

    // Escuta mudanças de autenticação (expiração do token)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((evento, session) => {
      if (evento === "SIGNED_OUT" || (!session && sessaoVerificada)) {
        mostrar("Sua sessão expirou. Faça login novamente.", "alerta");
        setAutenticado(false);
      } else if (session) {
        setAutenticado(true);
      }
    });

    return () => subscription.unsubscribe();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!sessaoVerificada) {
    // Ainda verificando — renderiza vazio para evitar flash de rota errada
    return null;
  }

  if (!autenticado) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
