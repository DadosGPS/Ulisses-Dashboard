/** Configuração do tema partilhada entre servidor e cliente. */
export const CHAVE_TEMA = "lm-tema";

/** Script inline para o <head>: aplica o tema guardado ANTES do primeiro
 * desenho, para não haver um "flash" do tema errado ao abrir a página. */
export const scriptTemaInicial = `try{var t=localStorage.getItem("${CHAVE_TEMA}");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t;}catch(e){}`;
