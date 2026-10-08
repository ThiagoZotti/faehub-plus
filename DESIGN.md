---
version: "1.0"
name: "FaeHub+ Campus em Movimento"
description: "Um campus digital escolar claro, orientado por conteúdo e pela fotografia da escola."
colors:
  primary: "#216BE4"
  on-primary: "#FFFFFF"
  primary-tint: "#EAF3FF"
  secondary: "#336BDD"
  tertiary: "#51C4EC"
  tertiary-container: "#FFF0E7"
  error: "#B63145"
  surface: "#FFFFFF"
  surface-bright: "#EAF1FA"
  background: "#D9E4F1"
  on-background: "#142744"
  outline: "#B5C8DF"
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
  nav-height: "5rem"
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
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-background}"
    rounded: "{rounded.md}"
    height: "2.75rem"
---

# FaeHub+ Design System

## Overview

### Creative North Star

Um campus em movimento: fotografia escolar reconhecível, luz natural, conteúdo acadêmico sobre superfícies claras e orientação em azul cobalto. A identidade vem da escola e da clareza das decisões, não de efeitos escuros ou cartões empilhados.

### Product context and register

- **Audience and primary job:** alunos consultam sua vida acadêmica; responsáveis acompanham matrículas vinculadas; professores operam turmas e registros; coordenação, secretaria e direção administram a instituição.
- **Target market(s) and evidence:** ensino técnico brasileiro, conforme ETESC/FAETEC, turma 3110 e conteúdo do repositório.
- **Locale(s) and language policy:** português do Brasil em toda a interface; textos institucionais devem ser revisados pelo responsável pelo projeto.
- **Usage scene:** uso recorrente em computador e celular, muitas vezes entre aulas; decisões principais precisam ser identificáveis rapidamente.
- **Register:** híbrido. Login e painel têm expressão de marca; formulários, listas, notas e frequência priorizam familiaridade de produto.
- **Memorable signature:** o campus é tratado como um lugar navegável; a fotografia aparece no login e como faixa contextual no painel. O painel do aluno usa um radar do dia — agenda, desempenho e prioridade — no lugar de personagens. A estrutura acadêmica mantém percurso e linha do tempo; operações escolares preservam protocolos e estados claros.
- **Restraint:** CRUD, campos, confirmação, busca e estados de erro permanecem previsíveis, legíveis e sem gestos escondidos.
- **Anti-references:** não imitar kits genéricos de SaaS, interfaces proprietárias de jogos, excesso de vidro/neon, fundo escuro em toda a aplicação ou mosaicos de cartões sem hierarquia.
- **Token ownership/runtime mapping:** este documento espelha a camada de migração `static/campus-bright.css`, carregada após `static/campus-system.css` para preservar compatibilidade com módulos existentes. `static/arrival-bright.css` é o owner do login claro; `static/dashboard-v2.css` e `static/academic.css` mantêm estrutura e comportamento. O objetivo de manutenção é absorver a camada clara nos módulos conforme cada fluxo for verificado, sem criar novas cores avulsas.

## Colors

`background` é o fundo estrutural claro; `surface` e `surface-bright` distinguem painéis e ênfase sem vidro. `on-background` e `outline` sustentam leitura e separação. `primary` representa ações, foco e seleção em todos os perfis; identidade de perfil pode aparecer em pequenos acentos secundários. `tertiary-container` sinaliza prazo/atenção e `error` fica reservado a falha ou ação de risco. A fotografia não fica atrás de tabelas ou formulários. Impressão mantém fundo branco.

## Typography

Segoe UI Variable Text é a fonte de leitura e controles; Segoe UI Variable Display cria títulos claros de peso 650–750. Cascadia Code identifica horários, códigos e pequenos rótulos técnicos dos módulos existentes. Títulos usam espaçamento negativo moderado; parágrafos mantêm altura de linha entre 1.5 e 1.8. Evitar caixa alta em frases longas.

## Layout

A navegação tem altura de `5rem` no computador. Páginas internas usam espaçamento lateral fluido entre `1.25rem` e `5rem`, sem largura máxima artificial para operações densas. A hierarquia padrão é cabeçalho, faixa de contexto, ferramentas e conteúdo. Em telas estreitas, duas colunas tornam-se uma, ações quebram linha e alvos permanecem com no mínimo 44px. Reservar espaço para estados de carregamento e mensagens evita deslocamentos.

## Elevation & Depth

Profundidade vem de cards brancos sobre fundo azul-acinzentado `#D9E4F1`, bordas definidas `#B5C8DF` e sombras discretas. Cabeçalhos do painel são faixas azuladas `#EAF1FA`, separadas do conteúdo branco. Tabelas densas e itens de lista permanecem opacos. Estado ativo deve ser comunicado também por borda, texto ou ícone.

## Shapes

Controles usam raio médio de `0.75rem`; cartões de módulo usam `1rem` a `1.375rem`. Pills ficam restritas a etiquetas curtas, filtros e estados. Divisores têm um pixel e baixo contraste. Ícones usam traço consistente, sem caixas decorativas quando o significado já está claro.

## Components

### Foundational visual states

Todo controle tem default, hover, foco visível, ativo, desabilitado e ocupado. Foco usa anel `focus` com offset. Erro usa `danger` e texto junto ao campo ou resumo do formulário; sucesso usa toast no live region compartilhado. Carregamento padrão mantém a geometria do botão e troca o rótulo por estado em andamento.

### Buttons and actions

Ação primária recebe preenchimento cobalto e texto branco em todos os perfis. Ações secundárias usam borda e fundo tonal. Arquivar/restaurar permanece secundário e exige confirmação própria do app. Botões com ícone também têm rótulo textual quando executam uma ação de negócio.

### Navigation and data display

A barra superior é sinalização de campus, com sublinhado ativo e carrossel inferior. Ela expõe no máximo sete destinos frequentes; módulos secundários permanecem no disclosure compartilhado “Mais”. Para alunos, a arquitetura agrupa presença e eventos em **Agenda**, avisos e notificações em **Comunicados**, e documentos e histórico em **Secretaria**. Listas de operação devem ter título, estado, metadados essenciais e uma ação principal clara. Etiquetas informam modalidade, prazo e arquivo; não substituem títulos.

O sistema não utiliza personagens ou personalização de avatar. A identificação da conta mantém nome e turma, acompanhados por uma fotografia circular opcional. Sem fotografia, são exibidas iniciais; não se atribui uma pessoa fictícia à conta. O menu de conta reúne envio/troca da fotografia, remoção confirmada e saída.

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

## Direção aprovada: Campus em movimento

O login usa uma divisão aproximadamente 60/40: fotografia clara da escola à esquerda e autenticação em superfície gelo à direita. O passo explícito **Entrar no campus** continua obrigatório após validar credenciais. O shell autenticado é claro em todos os perfis, com navegação branca e sublinhado cobalto. O carrossel inferior permanece no computador; até 600px, três destinos frequentes e o menu **Mais** formam a barra inferior. O painel concentra faixa da escola, boas-vindas, próximo movimento e ritmo acadêmico; pendências são um atalho contextual. O boletim apresenta as duas notas, média e situação em tabela, com filtros e simulador recolhido. Em celular, a tabela mantém comparação e rolagem horizontal explícita. Os módulos operacionais usam adaptadores claros no mesmo owner; suas estruturas permanecem compatíveis.

### Registro da migração visual

O refinamento aprovado em 08/10/2026 segue `exec-07dbf8f9-0d8a-4eda-be9b-9f01047430a7.png`: wordmark simples, seis destinos frequentes do aluno, menu **Mais** e perfil com foto à direita. O pager inferior é uma cápsula contínua com anterior, contador/módulo atual e próximo na mesma linha. A faixa do campus reutiliza a imagem original do mockup em `static/campus-approved-mockup.png`, recortada por CSS, preservando a arte aprovada. Dados acadêmicos continuam dinâmicos e o usuário mantém acesso a todos os módulos autorizados.

A pedido do usuário, o símbolo original `static/logo.svg` volta a acompanhar o wordmark no cabeçalho compartilhado, com tamanho reservado de 38px (32px no celular). O restante do refinamento aprovado permanece inalterado.

| Superfície | Owner | Compatibilidade preservada | Verificação |
| --- | --- | --- | --- |
| Login e confirmação | `static/arrival-bright.css` | credenciais, perfis, demo e entrada explícita | navegador e `test_arrival.py` |
| Shell e celular | `static/campus-bright.css` | destinos e autorização por perfil | navegador e `test_navigation_compaction.py` |
| Painel | `templates/aluno_painel.html` + tokens claros | grade, frequência, notas e trabalhos reais | navegador e `test_dashboard.py` |
| Boletim | `templates/aluno_boletim.html` + tokens claros | filtros, notas, simulação e impressão | navegador e suíte acadêmica |
| Demais perfis e operações | adaptadores em `static/campus-bright.css` | CRUD, comunicação e permissões | amostras no navegador e suíte existente |
