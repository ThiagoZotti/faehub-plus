# Horários configuráveis — primeira etapa de operação real

Em **Direção → Estrutura → Horários**, selecione turma/ano e cadastre dia, início,
término, disciplina da grade e sala opcional. A disciplina precisa estar na grade
da turma. Os docentes são os vínculos cadastrados, não os nomes ilustrativos.

Edite pelo link da linha. Arquivar remove a aula da consulta cotidiana sem apagar
o registro; restaurar exige disponibilidade. Não é permitido mudar grade de
ano/turma encerrados. Os intervalos são semanais e recorrentes: não é ainda um
motor de substituições, feriados, exceções de data ou distribuição de cotutoria.

## Integridade

- Conflitos por turma, sala (ignorando caixa/espaços externos) e docentes.
- Verificação nos dois sentidos: publicar aula e criar vínculo docente depois.
- Intervalos adjacentes são válidos; comparação de sobreposição é semiaberta.
- Sala vazia utiliza a sala cadastrada na turma.
- Atualizações com revisão antiga são rejeitadas, sem sobrescrever valores.
- Lock transacional compartilhado serializa as escritas de grade/vínculos.
- Auditoria em `activity_log` guarda antes/depois; arquivamento é reversível.
- Nenhum perfil, senha, convite ou permissão pública Supabase foi alterado.

Os painéis e a tela semanal leem o banco. Apenas a referência original de
3110/2026, transcrita anteriormente do material fornecido pelo usuário, é adotada
uma vez quando não existe grade administrada; um marcador impede a reposição
após edição/arquivamento. Não são criados nomes de docentes ou notas para isso.

Cadastro, turma, notas, frequência e acompanhamento familiar não consultam mais
os quatro perfis fixos. Notas e chamada ainda usam seus repositórios legados:
esta etapa não conclui avaliações com pesos, frequência por aula nem fechamento
unificado. Nenhum registro legado foi apagado ou convertido em nota presumida.

## Validação

`python tools/run_tests.py` executa a suíte inteira com banco SQLite temporário,
variáveis de produção neutralizadas e nenhuma conexão com dados escolares.
`test_school_timetable.py` cobre CRUD sem exclusão, conflitos, vigência, revisão,
restrição por perfil/CSRF, histórico encerrado, novas matrículas e responsáveis,
vazio real e inicializações repetidas. Dois testes de boletim agora gravam suas
fixtures explicitamente, em vez de depender de notas embutidas no aplicativo.

A revisão no Chrome isolado exercita criação, erro/preservação, edição,
cancelamento/arquivamento/restauração, 16 combinações de aba/largura
(1440/900/390/320px), filtro de dia do aluno e painéis de três perfis.
Suíte final: **166 testes passaram**, incluindo 13 específicos de horários.
Auditoria premium estrita no escopo P0: zero achados. Os tokens e a identidade
visual permanecem iguais; o owner compartilhado de tabelas corrige o fundo
branco herdado da camada clara nas células da P0.

## Implantação e continuação

A migração aditiva inclui `active` e `revision` em `schedule_slots`, preservando
RLS, grants e dados existentes. Aplicar antes do deploy do código consumidor.
Aplicada ao projeto FaeHub+ em 15/10/2026 como
`20261015212136_configurable_school_schedule.sql`; acesso `anon`/`authenticated`
permanece revogado. Advisors reportou somente informações de RLS sem políticas,
esperadas nesta arquitetura de servidor privado
([explicação do Supabase](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy)).
O GitHub armazena código; não substitui backup do banco/anexos.

Pendências posteriores: avaliações/pesos/períodos explícitos, frequência por
aula/disciplina, unificação dos fechamentos, fim das pontes legadas restantes,
validação do Gmail, autenticador/recuperação e backup/restauração operacional.
