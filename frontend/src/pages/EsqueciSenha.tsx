/**
 * Tela "Esqueceu a senha" — campo de e-mail + botão "Enviar link".
 *
 * Após envio, mensagem NEUTRA: não revela se o e-mail existe no sistema
 * (evita enumeração de usuários, mesmo que seja uso interno).
 */

import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { supabase } from "@/lib/supabase";
import { Campo } from "@/components/Campo";
import { Botao } from "@/components/Botao";
import styles from "./Login.module.css"; // reutiliza os estilos da tela de login

export function PaginaEsqueciSenha() {
  const [email, setEmail] = useState("");
  const [enviado, setEnviado] = useState(false);
  const [carregando, setCarregando] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setCarregando(true);
    // Ignora erros deliberadamente — mensagem neutra independente do resultado
    await supabase.auth.resetPasswordForEmail(email.trim(), {
      redirectTo: `${window.location.origin}/redefinir-senha`,
    });
    setCarregando(false);
    setEnviado(true);
  }

  return (
    <div className={styles.fundo}>
      <div className={styles.cartao}>
        <div className={styles.marca}>
          <h1 className={styles.logotipo}>Recuperar acesso</h1>
        </div>

        {enviado ? (
          <div className={styles.sucesso} role="status">
            Se esse e-mail estiver cadastrado, você receberá um link em instantes.
            Verifique também a caixa de spam.
          </div>
        ) : (
          <form className={styles.form} onSubmit={handleSubmit} noValidate>
            <Campo
              rotulo="E-mail"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              dica="Enviaremos um link para redefinir sua senha."
              required
            />
            <div className={styles.acoes}>
              <Botao
                type="submit"
                variante="primario"
                tamanho="lg"
                carregando={carregando}
              >
                Enviar link
              </Botao>
            </div>
          </form>
        )}

        <Link to="/login" className={styles.linkEsqueci} style={{ marginTop: 20 }}>
          Voltar para o login
        </Link>
      </div>
    </div>
  );
}
