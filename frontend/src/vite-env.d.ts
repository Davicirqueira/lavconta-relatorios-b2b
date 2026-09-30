/// <reference types="vite/client" />

/**
 * Declarações de módulos para recursos importados pelo Vite que o
 * TypeScript não reconhece por padrão.
 */

// CSS Modules — cada import retorna um objeto de string
declare module "*.module.css" {
  const classes: Record<string, string>;
  export default classes;
}

// CSS simples (side-effect imports)
declare module "*.css" {
  const css: string;
  export default css;
}
