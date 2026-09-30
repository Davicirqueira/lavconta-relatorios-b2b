/**
 * Tela "Redefinir senha" — nova senha + confirmar + botão "Salvar".
 * Acessada via link enviado por e-mail (o Supabase inclui o token na URL).
 */

import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { supabase } from "@/lib/supabase";
import { Campo } from "@/components/Campo";
import { Botao } from "@/components/Botao";
import styles from "./Login.module.css";

export function PaginaRedefinirSenha() {
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [erroGeral, setErroGeral] = useState("");
  const [carregando, setCarregando] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setErroGeral("");

    if (novaSenha !== confirmar) {
      setErroGeral("As senhas não coincidem.");
      return;
    }

    if (novaSenha.length < 8) {
      setErroGeral("A senha deve ter pelo menos 8 caracteres.");
      return;
    }

    setCarregando(true);
    const { error } = await supabase.auth.updateUser({ password: novaSenha });
    setCarregando(false);

    if (error) {
      setErroGeral("Não foi possível redefinir a senha. Solicite um novo link.");
      return;
    }

    navigate("/login", { replace: true });
  }

  return (
    <div className={styles.fundo}>
      <div className={styles.cartao}>
        <div className={styles.marca}>
          <h1 className={styles.logotipo}>Nova senha</h1>
        </div>

        {erroGeral && (
          <div className={styles.erro} role="alert">
            {erroGeral}
          </div>
        )}

        <form className={styles.form} onSubmit={handleSubmit} noValidate>
          <Campo
            rotulo="Nova senha"
            type="password"
            autoComplete="new-password"
            value={novaSenha}
            onChange={(e) => setNovaSenha(e.target.value)}
            dica="Mínimo de 8 caracteres."
            required
          />
          <Campo
            rotulo="Confirmar nova senha"
            type="password"
            autoComplete="new-password"
            value={confirmar}
            onChange={(e) => setConfirmar(e.target.value)}
            required
          />
          <div className={styles.acoes}>
            <Botao
              type="submit"
              variante="primario"
              tamanho="lg"
              carregando={carregando}
            >
              Salvar
            </Botao>
          </div>
        </form>
      </div>
    </div>
  );
}
