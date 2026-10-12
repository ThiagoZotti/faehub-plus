# Campus Electric — rollout do espaço do aluno

Direção aprovada pelo usuário em 09/10/2026: visual forte e jovial do mockup, mantendo a logo inspirada na FaeNet já escolhida.

## Escopo entregue

- Painel do aluno: boas-vindas em ciano, fotografia diagonal, próxima aula com contador, cards de próximas aulas, anel da média real, frequência, atalhos de comunicados e pendências.
- Shell do aluno: sidebar no desktop, barra inferior abaixo de 760px, todos os destinos autorizados preservados, menu da conta com foto/iniciais.
- Nova logo no shell compartilhado, login, ativação e erros. A imagem foi reencodificada sem perda; nenhuma alteração de pixels ou geração de nova logo.
- Fonte Plus Jakarta Sans variável local, 27 KB, com licença OFL incluída.
- Módulos do aluno recebem os adaptadores escuros. Direção/professor/família continuam com seus layouts anteriores nesta migração; nenhum fluxo de cadastro, autorização ou banco foi alterado.

O cartaz em perspectiva é referência visual, não uma imagem usada como interface. A fotografia vem do asset já existente; não se incorporam marca d'água ou dados do cartaz.

## Verificação

- Suíte completa: `python -m unittest discover -v`, em bancos temporários e transporte de e-mail simulado. 132 testes passaram antes da inclusão do teste adicional de painel vazio; os testes finais de navegação cobrem também esse estado.
- Auditoria estática da skill frontend-design-premium, `audit_project.py --mode strict`: sem achados no escopo do manifesto `premium-ui.json` (P0). Não representa certificação de acessibilidade de todo o app.
- Navegador local: 1440px, 900px, 390px e 320px; sem overflow horizontal no painel. Logo e fonte carregadas. Menu Mais e diálogo de perfil fecham com Escape e restauram foco. Filtro Em recuperação do boletim funciona; células de disciplina permanecem legíveis em fundo escuro.
- Conferidos também agenda, chat vazio, contrastes e elementos adjacentes. A prévia usa exclusivamente dados descartáveis de teste.
- `git diff --check`: sem erros.
- O lint oficial externo de DESIGN.md não foi executado: o ambiente bloqueou `pnpm dlx @google/design.md` por exigir execução de pacote remoto com acesso ao projeto. Não houve contorno do bloqueio; esse passo requer autorização explícita do usuário.

## Continuidade e retorno

O owner `static/campus-electric.css` é carregado somente para aluno. Próximas etapas: adaptar os painéis operacionais de professor/direção/família e redesenhar o login quando seu layout for aprovado. Não anunciar como migração visual completa de todos os perfis.

Para reverter esta etapa, reverter o commit da migração visual; nenhuma migração de dados é necessária. A política de acesso e a configuração de e-mail permanecem intactas.

## Segunda etapa — módulos do aluno, concluída em 12/10/2026

Referência original preservada em `student-screens-mockup.png` (1792×1008). O cartaz não é distribuído como asset da interface; sua marca d'água, textos gerados e métricas ilustrativas não foram incorporados. A logo aprovada continua a mesma.

- Boletim: tabela escura com médias legíveis, barras derivadas dos valores reais, filtros e impressão preservados.
- Agenda e Horário: calendário de presenças/eventos, estados sem registro, grade semanal e seleção de dia recebem superfícies e acentos consistentes.
- Exercícios: lista compacta responsiva com situação, prazo, materiais e entrega; busca com limpar e foco restaurado, erro de resposta vazia associado ao campo e prevenção de envio duplicado.
- Comunicados: painéis escuros, situações lida/não lida, descarte e restauração preservados. A regra de ler antes de descartar não muda.
- Secretaria, histórico, Estágios e Mensagens: formulários, listas, balões, menus e diálogos adaptados ao mesmo tema; sem novos fluxos administrativos ou dados fictícios.
- Módulos continuam no documento com altura natural. Tabela, diálogos e menus preservam a própria rolagem. O HUD intermediário de navegação do aluno foi removido, sem alterar o carregamento real das páginas.
- CSS e JavaScript alterados têm versões novas para não reutilizar recursos antigos do cache.

### Evidência de validação

A revisão de navegador de 09/10/2026 utilizou somente localhost e banco temporário. Os nove destinos principais foram medidos em 320px, 390px e 900px sem overflow horizontal do documento. Boletim e atividades foram inspecionados em 1440px. Foram exercitados filtro de recuperação, busca sem resultados/limpar, erro de entrega vazia, entrega válida com feedback de sucesso, calendário sem chamada, seletor nativo de documento aberto e protocolo local persistido. No chat, uma mensagem curta foi enviada ao grupo local, seu menu foi aberto e a confirmação de apagar foi cancelada com foco inicial em Cancelar. Nenhuma conta ou conversa de produção foi usada.

Verificação final de 12/10/2026: `python -m unittest discover -q`, 136 testes passaram em 154,602s, com banco temporário isolado; `node --check static/campus-modules.js` e `git diff --check` passaram. `audit_project.py --mode strict` retornou zero achados no escopo P0 do manifesto. Os novos testes cobrem as doze rotas do aluno, dados reais nos módulos, versão dos assets e preservação de login/professor; `/usuarios` continua retornando 403 para aluno.

Na retomada de 12/10/2026, o controle do navegador não estava disponível. Não foi feita nova inspeção visual, impressão real, teste em aparelho físico, emulação runtime de alto contraste/movimento reduzido ou confirmação do deploy do Render; as regras CSS dessas variantes permanecem preservadas. A validação final automatizada e o envio ao GitHub são registrados na entrega. O lint externo de DESIGN.md continua pendente pelo bloqueio descrito acima; não foi contornado. A auditoria estática continua limitada às superfícies P0 do manifesto, não certifica todos os módulos.

Login, professores, direção e responsáveis continuam fora desta etapa. A área de perfil mantém fotografia/iniciais e menu existente; recursos ilustrados como preferências e autenticação adicional não são anunciados como implementados. Reverter o commit desta segunda etapa restaura somente código visual e testes, sem migração do banco.
