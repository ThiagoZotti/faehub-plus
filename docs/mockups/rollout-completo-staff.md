# Rollout completo de professor e direção — 12/10/2026

O usuário confirmou explicitamente todas as páginas existentes de ambos os perfis, revogando o limite anterior de três telas. Referências: `professor-todas-telas-v2.png` e `diretor-todas-telas-v2.png`. Foram preservadas as funções e permissões reais; as pranchas não são usadas como imagem da interface.

## Cobertura

- Professor (11 rotas): painel, turmas, notas, chamada, diário, exercícios, mensagens, avisos, estágios, calendário e notificações.
- Direção (14 rotas): painel, usuários, estrutura, turmas, secretaria, coordenação, diário, histórico, relatórios, períodos, calendário, mensagens, notificações e configurações. Estrutura conserva suas seis abas e formulários.
- Conta/perfil: menu e diálogo de fotografia existentes, sem inventar preferências, autenticador ou uma nova página de perfil. O professor continua gerenciando oportunidades de estágio, não registros de supervisão/horas que só aparecem no mockup.
- Responsável, aluno, e-mails, ativação e recuperação não são redesenhados nesta etapa. O aluno conserva o tema Electric já entregue.

## Owners e comportamento

`campus-electric.css` mantém tokens e navegação compartilhados; `staff-modules.css` adapta todos os módulos docentes/administrativos. Listas, tabelas, campos, validação, seleção, confirmações, mensagens e modais usam superfícies escuras, ações cobalto e foco visível. Títulos indicam o módulo, sem repetir slogans em operações de edição. Listas/diálogos preservam sua própria rolagem e formulários permanecem na altura natural do documento.

`campus-actions.js` fornece a variante de confirmação/validação docente utilizada por `teacher-workspace.js` e `teacher-studio.js`. Substitui `alert/confirm` do navegador por diálogo do app, com Cancelar em foco, Escape, retorno ao acionador, mensagens associadas e prevenção de envio duplicado. Reenvio de formulário após validação acontece em outra tarefa do event loop, evitando bloqueio reentrante do navegador; timers são cancelados ao sair e BFCache restaura botões. Regras de substituir chamada/notas, aviso de outras edições não salvas, arquivar/restaurar e autorização do servidor são preservadas.

## Ajustes pedidos no login

O login ocupa toda a largura e ao menos a altura da janela, sem margem externa, borda ou cantos de cartão. Imagem, proporções, textos, perfis e credenciais são preservados. Usuário/senha não recebem outline interno; `field-shell:focus-within` mantém foco no contorno externo, inclusive em alto contraste. Páginas baixas ou celulares podem rolar naturalmente.

## Evidência

- `python -m unittest discover -q`: 139 testes passaram em 151,686s, em banco temporário e transporte de e-mail simulado. Testes de navegação agora cobrem todas as rotas dos dois perfis e garantem que o responsável continua fora do rollout.
- Playwright em Chrome headless isolado, somente localhost: 104 combinações de página/largura (login + 25 rotas, em 1440, 900, 390 e 320px), todas HTTP 200 e sem overflow horizontal do documento; seis abas de estrutura também passaram. Zero erros de JavaScript.
- Foco da senha: outline interno `none`, borda externa ciano mantida. Quadro começa em x=0/y=0 e ocupa a largura da janela. Limpar busca, vazio, confirmação de presença cancelada/aceita, diálogo de atividade e cancelamento de arquivamento foram exercitados.
- Sucesso de mutações reais apenas no banco descartável: notas 7/8 salvas e recuperadas; atividade publicada, arquivada e restaurada. Nenhuma conta/conversa de produção foi usada nem desbloqueada.
- Capturas desktop e celular de notas, chamada, atividades, usuários, estrutura, secretaria e períodos foram inspecionadas. Navegador e helpers usam perfil temporário, não a sessão do Chrome do usuário.
- `node --check` nos três scripts alterados e `git diff --check`: passaram. Auditoria estrita da skill limitada ao escopo P0 do manifesto não certifica acessibilidade de todo o app.

Limites: recursos ilustrativos inexistentes nas pranchas não foram implementados; não houve teste em aparelho físico ou teclado virtual. O lint externo de DESIGN.md continua pendente pelo bloqueio do pacote remoto, sem contorno. Deploy do Render não é confirmado por teste local. Helpers, logs, dependências, screenshots de fixtures e bancos descartáveis não são enviados ao GitHub. Reversão requer revert do commit, sem migração de dados.
