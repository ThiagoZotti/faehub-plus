# Campus Electric — primeira etapa

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
