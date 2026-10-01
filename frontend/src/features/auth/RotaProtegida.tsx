/**
 * RotaProtegida — verifica sessão Supabase e redireciona para /login se ausente.
 *
 * Escuta a perda de sessão e, quando ela não foi pedida pelo operador,
 * avisa que a sessão expirou antes de redirecionar.
 *
 * Sem rota de cadastro: o Supabase está configurado com disable_signup=true
 * (verificado no design.md §18). Esta tela apenas guarda as rotas.
 */

import { useEffect, useState } from "react";
import { Outlet, Navigate } from "react-router";
import { supabase } from "@/lib/supabase";
import { useToast } from "@/components/Toast";
import { consumirSaidaVoluntaria } from "./saida";

export function RotaProtegida() {
  const [sessaoVerificada, setSessaoVerificada] = useState(false);
  const [autenticado, setAutenticado] = useState(false);
  const { mostrar } = useToast();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setAutenticado(!!session);
      setSessaoVerificada(true);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((evento, session) => {
      if (evento === "SIGNED_OUT") {
        if (!consumirSaidaVoluntaria()) {
          mostrar("Sua sessão expirou. Faça login novamente.", "alerta");
        }
        setAutenticado(false);
      } else if (session) {
        setAutenticado(true);
      }
    });

    return () => subscription.unsubscribe();
  }, [mostrar]);

  if (!sessaoVerificada) {
    // Ainda verificando — renderiza vazio para evitar flash de rota errada
    return null;
  }

  if (!autenticado) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
