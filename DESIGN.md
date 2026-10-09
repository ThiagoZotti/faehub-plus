---
version: "1.0"
name: "FaeHub+ Campus em Movimento — Electric"
description: "Um campus digital forte e jovial: azul profundo, cor elétrica e fotografia escolar."
colors:
  primary: "#144BFF"
  on-primary: "#FFFFFF"
  primary-tint: "#172747"
  secondary: "#23CEFF"
  tertiary: "#A890FF"
  tertiary-container: "#302349"
  error: "#FF6F85"
  surface: "#111B36"
  surface-bright: "#172747"
  background: "#070D24"
  on-background: "#F5F7FF"
  outline: "#2B3C63"
typography:
  sans:
    fontFamily: "Plus Jakarta Sans, Segoe UI, Arial, sans-serif"
  display:
    fontFamily: "Plus Jakarta Sans, Segoe UI, Arial, sans-serif"
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
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-background}"
    rounded: "{rounded.md}"
    height: "2.75rem"
---

# FaeHub+ Design System

## Overview

### Creative North Star

Um campus em movimento com força e juventude: o mockup enviado em 09/10/2026 é a referência visual fiel. Azul profundo, azul elétrico, ciano, violeta e verde-lima, títulos fortes e fotografia da escola recortada em diagonal. O usuário explicitamente rejeitou suavizar essa direção para uma interface discreta. A logo aprovada é a proposta inspirada na FaeNet, não a logo fragmentada do cartaz.

### Product context and register

- **Audience and primary job:** alunos consultam sua vida acadêmica; responsáveis acompanham matrículas vinculadas; professores operam turmas e registros; coordenação, secretaria e direção administram a instituição.
- **Target market(s) and evidence:** ensino técnico brasileiro, conforme ETESC/FAETEC, turma 3110 e conteúdo do repositório.
- **Locale(s) and language policy:** português do Brasil em toda a interface; textos institucionais devem ser revisados pelo responsável pelo projeto.
- **Usage scene:** uso recorrente em computador e celular, muitas vezes entre aulas; decisões principais precisam ser identificáveis rapidamente.
- **Register:** híbrido. Login e painel têm expressão de marca; formulários, listas, notas e frequência priorizam familiaridade de produto.
- **Memorable signature:** o campus é tratado como um lugar navegável; a fotografia aparece no login e como faixa contextual no painel. O painel do aluno usa um radar do dia — agenda, desempenho e prioridade — no lugar de personagens. A estrutura acadêmica mantém percurso e linha do tempo; operações escolares preservam protocolos e estados claros.
- **Restraint:** CRUD, campos, confirmação, busca e estados de erro permanecem previsíveis, legíveis e sem gestos escondidos.
- **Anti-references:** não reduzir o mockup a um kit claro genérico; não trocar identidade forte por neutralidade; não usar o cartaz em perspectiva como captura de interface funcional. Nenhuma marca d'água, texto ilegível ou número ilustrativo entra no produto.
- **Token ownership/runtime mapping:** modelo B, CSS é canônico. `static/campus-electric.css` é o owner da nova identidade do aluno, adaptando módulos sobre as camadas estruturais existentes. `--electric-blue` mapeia `colors.primary`; `--campus-accent` mapeia `colors.secondary`; painel/texto/linha mapeiam `colors.surface`, `on-background`, `outline`; `--font-body`/`--font-display` usam Plus Jakarta Sans local (WOFF2, licença OFL). Migração incremental: demais perfis e login preservam `campus-bright.css`/`arrival-bright.css` nesta etapa. Autorização e autenticação permanecem iguais.

## Colors

Os tokens acima descrevem a nova superfície do aluno: fundo azul profundo, painel azul-noite e superfície elevada azul. Azul elétrico identifica navegação ativa; ciano orienta ações e foco; violeta e verde-lima reforçam os indicadores acadêmicos. Atalhos vermelho e verde usam gradientes saturados como no mockup, sempre com texto. Erro mantém significado próprio. Fotografia fica no hero, nunca atrás de tabelas. Impressão mantém fundo branco. Paleta clara permanece nos fluxos ainda não migrados.

## Typography

Plus Jakarta Sans variável 400–800, auto-hospedada, conduz títulos e controles do aluno; fallback Segoe UI/Arial durante o carregamento. Títulos do painel têm peso 800 e espaçamento negativo. Cascadia Code continua disponível para códigos técnicos. Demais perfis preservam Segoe UI nesta etapa. Caixa alta é restrita a rótulos curtos.

## Layout

No aluno, cabeçalho de 76px e navegação lateral persistente de 224px (190px até 1200px); abaixo de 760px, cabeçalho de 68px e barra inferior com três destinos e Mais. Painel usa hero diagonal e grade principal 1,55:1. Abaixo de 980px, os blocos se reorganizam; abaixo de 540px, ficam em coluna. Documentos longos continuam rolando na página; somente sidebar e menu limitam a própria rolagem. Demais perfis preservam navegação anterior.

## Elevation & Depth

Cards azul-noite sobre azul profundo, bordas definidas e brilho azul nos destaques. Próxima aula usa bloco azul saturado; índice acadêmico usa anel cromático calculado com a média real. Superfícies são opacas para leitura, sem blur contínuo de tela inteira. Estado ativo usa `aria-current`, borda e preenchimento. Movimento reduzido desativa decoração animada.

## Shapes

Controles usam raio médio de `0.75rem`; cartões de módulo usam `1rem` a `1.375rem`. Pills ficam restritas a etiquetas curtas, filtros e estados. Divisores têm um pixel e baixo contraste. Ícones usam traço consistente, sem caixas decorativas quando o significado já está claro.

## Components

### Foundational visual states

Todo controle tem default, hover, foco visível, ativo, desabilitado e ocupado. Foco usa anel `focus` com offset. Erro usa `danger` e texto junto ao campo ou resumo do formulário; sucesso usa toast no live region compartilhado. Carregamento padrão mantém a geometria do botão e troca o rótulo por estado em andamento.

### Buttons and actions

Ação primária recebe preenchimento cobalto e texto branco em todos os perfis. Ações secundárias usam borda e fundo tonal. Arquivar/restaurar permanece secundário e exige confirmação própria do app. Botões com ícone também têm rótulo textual quando executam uma ação de negócio.

### Navigation and data display

A navegação do aluno expõe todos os destinos autorizados na sidebar; no celular, secundários permanecem no disclosure compartilhado Mais. Cabeçalho mantém foto/conta e atalhos reais de mensagens e comunicados. A arquitetura segue agrupando presença/eventos em Agenda, avisos/notificações em Comunicados, documentos/histórico em Secretaria. Carrossel legado permanece nas demais áreas nesta migração.

O sistema não utiliza personagens ou personalização de avatar. A identificação da conta mantém nome e turma, acompanhados por uma fotografia circular opcional. Sem fotografia, são exibidas iniciais; não se atribui uma pessoa fictícia à conta. O menu de conta reúne envio/troca da fotografia, remoção confirmada e saída.

O painel mantém boas-vindas, Seu próximo movimento e Seu ritmo acadêmico, com atalhos coloridos de Comunicados e pendências conforme o mockup aprovado. Pendências abrem atividades já filtradas; mensagem nova aponta para conversas. Dados acadêmicos continuam no backend existente. Mensagens preservam a metáfora de conversa direta e suas confirmações canônicas.

### Forms and overlays

Campos têm rótulos persistentes. Seleção e data usam controles nativos aceitos pelo contrato de UX. Diálogos têm título, fechamento explícito, fundo modal e foco gerenciado pelo navegador. A confirmação de arquivamento nunca usa `window.confirm`.

Primeiro acesso permanece compacto, com a nova logo aprovada, card branco, títulos claros e ações cobalto no owner `static/campus-bright.css`. Cadastro por convite reutiliza diálogos e controles da direção. Estados de envio e ativação continuam escritos por extenso. O redesenho do login e dos fluxos administrativos não pertence a esta primeira migração do painel.

Convites preservam o template claro `templates/emails/invitation.html`, sem downloads de imagens ou rastreamento. A logo aprovada `static/logo-faehub.webp` aparece no cabeçalho compartilhado, no login, na ativação e no erro; a imagem é reencodificação lossless da proposta aprovada, sem alteração de pixels. Dimensões reservadas evitam deslocamentos e texto alternativo identifica a marca. Nenhum envio de e-mail é alterado nesta etapa.

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

## Histórico: direção anterior de 08/10/2026

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
