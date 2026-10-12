# FaeNet compartilhada e ajustes do aluno — 12/10/2026

Referência visual: `faenet-redirecionamento-v1.png`, enviada pelo usuário. A tela
foi implementada em HTML/CSS, não como imagem do mockup. Reutiliza a logo original
da FaeNet e a fotografia de campus existente, sem gerar outra arte.

## Entrega

- `/faenet` e entrada no menu de aluno, professor, direção/proprietário e responsável.
- Mesmo conteúdo e identidade Electric nos quatro perfis, com navegação e conta
  reais de cada um; demais telas do responsável conservam seu tema.
- Hero diagonal, recursos, bloco das duas plataformas e CTA inferior. Feed,
  mensagens, explorar e mapa apontam para rotas existentes da FaeNet, em nova aba.
- Sem SSO ou troca de dados entre aplicativos. Sem busca global fictícia,
  foto de pessoa ilustrativa, disponibilidade ou contadores inventados.
- Entrada principal confirmada em `https://faenet.onrender.com/` (HTTP 200).
  Os atalhos usam rotas verificadas no router da FaeNet. Mensagens/explorar/mapa
  responderam HTTP 200; duas checagens automáticas de `/feed` excederam 30s.
  Isso fica como limitação de disponibilidade externa, não como confirmação de
  funcionamento completo do outro aplicativo. O botão principal usa sua raiz.
- Card de comunicados do aluno mais compacto (204px no teste com dois atalhos),
  mantendo os links e textos. Em desktop baixo, o próprio painel adapta os espaços,
  sem `overflow:hidden` no documento ou cortes de conteúdo.
- Anexo de atividade usa o mesmo macro/estilo de mensagens, com seleção nativa,
  nome, tamanho, remover e erro. Selecionar não faz upload; envio continua por
  multipart com CSRF e validação existente do servidor, até 5 MB.
- A faixa de endereço ao passar sobre um link pertence ao navegador. Não foi
  escondida por troca de links por botões ou redirecionamentos JavaScript.

## Verificação

- Suíte completa: 152 testes passaram (200,979s). Após os últimos ícones e ajustes
  de metadados, 17 testes direcionados passaram novamente.
- Chrome headless isolado, banco descartável: FaeNet nos quatro perfis em
  1440×900, 390×844 e 320×740; sem overflow horizontal ou erros de JavaScript.
- Painel do aluno sem rolagem vertical em 1920×1080, 1440×900 e 1366×768,
  com dados de teste. Conteúdo longo, alertas extras, zoom e celular continuam
  naturalmente roláveis, sem perda de ações.
- Seletor de arquivo por clique e teclado; nome/tamanho; remoção; tipo inválido;
  erro; Escape; entrega real de TXT e link de download no banco local descartável.
- Regressão de login/professor/direção: 104 combinações página/largura, seis abas
  da estrutura e ações de busca, confirmação e diálogos passaram.
- Sintaxe JavaScript e `git diff --check` sem erros. Audit premium sem achados no
  escopo P0 do manifesto; isso não certifica acessibilidade global do aplicativo.
- Lint oficial de `DESIGN.md` continua pendente por restrição anterior à execução
  do pacote remoto; não foi contornada nem confundida com a auditoria local.

Capturas e relatórios locais ficam fora do repositório. Nenhuma entrega, conversa
ou arquivo escolar foi criado nos testes de produção; upload foi somente local.
