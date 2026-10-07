---
version: "1.0"
name: "FaeHub+ Campus Vivo"
description: "Um campus digital escolar inspirado na sinalização de uma escola técnica ao entardecer."
colors:
  primary: "#70E4DC"
  on-primary: "#06252C"
  primary-tint: "#9CEEF2"
  secondary: "#8CC9FF"
  tertiary: "#B7EBD0"
  tertiary-container: "#FFD19A"
  error: "#FFB798"
  surface: "#112438"
  surface-bright: "#172E43"
  background: "#091522"
  on-background: "#F3F8FF"
  outline: "#B4C8DC"
typography:
  sans:
    fontFamily: "Segoe UI Variable Text, Segoe UI, Arial, sans-serif"
  display:
    fontFamily: "Segoe UI Variable Display, Segoe UI, Arial, sans-serif"
  mono:
    fontFamily: "Cascadia Code, Cascadia Mono, Consolas, monospace"
rounded:
  DEFAULT: "1rem"
  sm: "0.375rem"
  md: "0.75rem"
  lg: "1.375rem"
spacing:
  section-gap: "1.875rem"
  page-inline: "clamp(1.25rem, 4vw, 5rem)"
  nav-height: "4.75rem"
components:
  button:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.sans}"
    rounded: "{rounded.md}"
    height: "2.75rem"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-background}"
    rounded: "{rounded.lg}"
    padding: "1.5rem"
  dialog:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-background}"
    rounded: "{rounded.lg}"
    width: "46rem"
  input:
    backgroundColor: "{colors.background}"
    textColor: "{colors.on-background}"
    rounded: "{rounded.md}"
    height: "2.75rem"
---

# FaeHub+ Design System

## Overview

### Creative North Star

A sinalização de um campus técnico ao entardecer: orientação clara, superfícies azul-marinho, luzes funcionais e detalhes luminosos que indicam caminho e estado. A expressão visual vem do cenário do campus e de uma única metáfora por módulo, não de ornamentos aleatórios.

### Product context and register

- **Audience and primary job:** alunos consultam sua vida acadêmica; responsáveis acompanham matrículas vinculadas; professores operam turmas e registros; coordenação, secretaria e direção administram a instituição.
- **Target market(s) and evidence:** ensino técnico brasileiro, conforme ETESC/FAETEC, turma 3110 e conteúdo do repositório.
- **Locale(s) and language policy:** português do Brasil em toda a interface; textos institucionais devem ser revisados pelo responsável pelo projeto.
- **Usage scene:** uso recorrente em computador e celular, muitas vezes entre aulas; decisões principais precisam ser identificáveis rapidamente.
- **Register:** híbrido. Login e painel têm expressão de marca; formulários, listas, notas e frequência priorizam familiaridade de produto.
- **Memorable signature:** o campus é tratado como um lugar navegável; cada módulo recebe uma peça de sinalização ou instrumento próprio. O painel do aluno usa um radar do dia — agenda, desempenho e prioridade — no lugar de personagens. Na P0, a estrutura acadêmica é um mapa vivo com percurso numerado, inventário e linha do tempo do estudante. Na P1, operações escolares usam a linguagem de uma mesa de controle: trilhas, protocolos, linhas do tempo e estados luminosos.
- **Restraint:** CRUD, campos, confirmação, busca e estados de erro permanecem previsíveis, legíveis e sem gestos escondidos.
- **Anti-references:** não imitar kits genéricos de SaaS, interfaces proprietárias de jogos, excesso de vidro/neon ou mosaicos de cartões sem hierarquia.
- **Token ownership/runtime mapping:** este documento espelha os tokens canônicos de `static/campus-system.css` e `static/academic.css`; a P0 deriva esses tokens em `static/p0/academic-core.css`. Mudanças visuais compartilhadas devem alterar primeiro os arquivos canônicos e depois atualizar este contrato.

## Colors

`background` é o fundo estrutural; `surface` e `surface-bright` criam profundidade tonal; `on-background` e `outline` formam a hierarquia de leitura. `primary` representa ações e estados positivos do aluno, `tertiary` identifica o espaço docente, `tertiary-container` sinaliza prazo/atenção e `error` fica reservado a falha ou ação de risco. `primary-tint` desenha foco visível. A experiência autenticada é escura; impressão converte módulos acadêmicos para fundo claro.

## Typography

Segoe UI Variable é a fonte de leitura e controles. Bahnschrift cria títulos compactos e institucionais. Cascadia Code identifica horários, números, códigos e pequenos rótulos técnicos. Títulos usam peso alto e espaçamento negativo moderado; parágrafos mantêm altura de linha entre 1.5 e 1.8. Evitar caixa alta em frases longas.

## Layout

A navegação tem altura de `4.75rem`. Páginas internas usam espaçamento lateral fluido entre `1.25rem` e `5rem`, sem largura máxima artificial para operações densas. A hierarquia padrão é cabeçalho, faixa de contexto, ferramentas e conteúdo. Em telas estreitas, duas colunas tornam-se uma, ações quebram linha e alvos permanecem com no mínimo 44px. Reservar espaço para estados de carregamento e mensagens evita deslocamentos.

## Elevation & Depth

Profundidade vem de tons, bordas translúcidas e uma sombra ampla apenas nos elementos principais. Blur é permitido em superfícies sobre o cenário do campus, mas não em tabelas densas nem em cada item de lista. Estado ativo deve ser comunicado também por borda, texto ou ícone.

## Shapes

Controles usam raio médio de `0.75rem`; cartões de módulo usam `1rem` a `1.375rem`. Pills ficam restritas a etiquetas curtas, filtros e estados. Divisores têm um pixel e baixo contraste. Ícones usam traço consistente, sem caixas decorativas quando o significado já está claro.

## Components

### Foundational visual states

Todo controle tem default, hover, foco visível, ativo, desabilitado e ocupado. Foco usa anel `focus` com offset. Erro usa `danger` e texto junto ao campo ou resumo do formulário; sucesso usa toast no live region compartilhado. Carregamento padrão mantém a geometria do botão e troca o rótulo por estado em andamento.

### Buttons and actions

Ação primária recebe preenchimento com o acento do perfil. Ações secundárias usam borda e fundo tonal. Arquivar/restaurar permanece secundário e exige confirmação própria do app. Botões com ícone também têm rótulo textual quando executam uma ação de negócio.

### Navigation and data display

A barra superior é sinalização de campus, com sublinhado ativo e carrossel inferior. Ela expõe no máximo sete destinos frequentes; módulos secundários permanecem no disclosure compartilhado “Mais”. Para alunos, a arquitetura agrupa presença e eventos em **Agenda**, avisos e notificações em **Comunicados**, e documentos e histórico em **Secretaria**. Listas de operação devem ter título, estado, metadados essenciais e uma ação principal clara. Etiquetas informam modalidade, prazo e arquivo; não substituem títulos.

O sistema não utiliza avatares ou personalização de personagem. A identificação da conta é textual e o painel resume o dia acadêmico com a mesma estrutura de página dos demais módulos.

O painel do aluno é deliberadamente enxuto: boas-vindas, **Seu próximo movimento** e **Seu ritmo acadêmico** são os únicos blocos editoriais. As pendências do resumo são uma navegação direta para a lista de atividades já filtrada. Mensagens usam a metáfora de conversa direta — pessoas, histórico em balões e compositor contextual — em vez de caixa de e-mail. O compositor apresenta anexo como ação nomeada, mostra prévia antes do envio e mantém fotos dentro do fluxo da conversa; exclusão usa confirmação própria e estado restaurável.

### Forms and overlays

Campos têm rótulos persistentes. Seleção e data usam controles nativos aceitos pelo contrato de UX. Diálogos têm título, fechamento explícito, fundo modal e foco gerenciado pelo navegador. A confirmação de arquivamento nunca usa `window.confirm`.

### Iconography

Ícones SVG de linha são mantidos no mapa `ICONS` de `app.py`, normalmente em 18–22px. Usar `currentColor`, terminação arredondada e alinhamento óptico. Ícones não substituem rótulos de navegação.

### Motion

Feedback local usa 160–240ms; entrada de conteúdo pode usar até 500ms com a curva `--campus-ease`. Movimento comunica mudança de módulo, expansão, filtro ou confirmação. `prefers-reduced-motion` remove transições e animações não essenciais.

### Content and data visualization

A voz é direta, encorajadora e escolar, sem mencionar IA, mockup ou implementação. Datas são exibidas no padrão brasileiro e valores técnicos usam a fonte mono. Toda visualização deve manter uma alternativa textual com o mesmo dado.

## Do's and Don'ts

- **Do:** usar o cenário e a sinalização do campus como contexto visual reconhecível.
- **Do:** reutilizar tokens, navegação, foco e feedback já existentes.
- **Don't:** transformar cada informação em um cartão de vidro independente.
- **Don't:** esconder operações essenciais em hover, gesto ou ícone sem nome.

## Refinamento Campus moderno

A entrada preserva a fotografia escolar, com título editorial moderado e formulário sóbrio. O shell usa fundo azul sólido; a fotografia fica concentrada na recepção do aluno. Superfícies, bordas e tipografia vêm do owner existente `static/campus-system.css`. A agenda usa uma lista cronológica legível, sem radar animado. Textos operacionais usam 12–16 px e ações mantêm pelo menos 44 px. `static/arrival.css` é o owner público e `static/dashboard-v2.css` o owner do resumo do aluno.
