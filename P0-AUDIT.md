# Auditoria do P0 — FaeHub+

Data: 03/10/2026. Base: versão recuperada e publicada no commit `3328086e4add00ddd397534a449e00b2a5dff424`.

## Primeira implementação — 03/10/2026

Os problemas 1 e 2 abaixo foram corrigidos após a auditoria. A descrição original permanece como registro do diagnóstico da versão de referência.

- Carga acadêmica inicial protegida pelo marcador `academic_core_initial_v1`, gravado na mesma transação da carga. Instalações com estudantes/matrículas existentes recebem o marcador sem reaplicar o seed. Reinícios não recriam matrículas encerradas, não sobrescrevem nomes editados e não acrescentam disciplinas à grade automaticamente.
- Ativação de outro ano bloqueada se um ano ativo anterior tiver período aberto ou em planejamento. A validação ocorre antes das alterações; um destino inexistente é rejeitado. Com períodos fechados, a transição mantém matrículas/histórico e registra auditoria.
- **86 testes aprovados**, incluindo cinco novos testes que exercitam reinícios repetidos, quatro estados de encerramento, adoção de instalação antiga sem marcador, nomes editados, transições rejeitadas sem alterações parciais e ativação permitida após fechamento.

As correções impedem novas alterações indevidas; não tentam identificar ou desfazer matrículas que versões anteriores já possam ter recriado. A carga de outros módulos, a sincronização de notas legadas, permissões por período e integração real com PostgreSQL continuam fora desta entrega.

## Resultado

**O P0 está parcialmente implementado.** A estrutura acadêmica normalizada tem telas, persistência e testes locais, mas os fluxos de horários, notas e chamada ainda dependem do modelo legado. Não considerar a fundação concluída nem realizar a importação remota com o script atual.

Esta auditoria verificou código e testes locais. Não consultou o banco remoto nem confirmou o estado das migrações no Supabase. As verificações de comportamento usaram um SQLite isolado, sem alterar o banco de apresentação.

## Situação dos dez itens aprovados

| Item | Status | Evidência | Falta para concluir |
| --- | --- | --- | --- |
| PostgreSQL e migrações | Parcial | `database.py` oferece backend PostgreSQL; existem migrações e scripts de importação/verificação. A execução atual usa SQLite. | Atualizar importador para todo o esquema atual, testar PostgreSQL e reconciliar dados antes da troca. |
| Anos e períodos letivos | Parcial | `academic_core.mutate` cadastra anos/períodos e muda seus estados; `/estrutura` disponibiliza as ações. | Impedir encerramento indireto de ano com períodos abertos; unificar fechamento/reabertura e exigir justificativa em todos os caminhos. |
| Cursos, disciplinas, turmas e matrículas | Parcial | Entidades normalizadas, cadastro, capacidade, encerramento e busca/paginação existem. | Tornar seed não destrutivo; concluir edição de dados cadastrais, movimentações e vínculo de conta ao aluno; retirar dependências de perfis fixos. |
| Vínculos docentes | Parcial | `teacher_subjects`, criar/encerrar vínculos e ponte com `teacher_assignments`. | Usar vínculo normalizado como fonte dos fluxos, incluindo ano e vigência; garantir consistência ao encerrar/recriar vínculos. |
| Horários configuráveis | Pendente no fluxo | Existe `schedule_slots`, mas horário e próximas aulas usam `SCHEDULE_3110`. | Editor persistido por turma, professor e sala; validação de sobreposição; painéis usando essa fonte. |
| Avaliações configuráveis | Parcial no modelo | `assessments` e `assessment_scores` existem; `sync_grade` converte N1/N2 para o histórico. | CRUD de avaliações, pesos/fórmulas, rascunho/publicação e seleção explícita de período no lançamento. |
| Frequência por aula e disciplina | Pendente no fluxo | `lessons` e `attendance_records` existem; `/chamada` grava em `attendance` por aluno/data. | Registrar por aula/matrícula/disciplina, várias aulas no dia, situações e justificativas; recalcular indicadores e relatórios. |
| Histórico acadêmico por ano | Parcial | `/historico` consulta matrículas e avaliações normalizadas com restrição por aluno/responsável. | Preservar histórico ao reiniciar e fechar períodos; incluir frequência/carga horária e eliminar reescrita indevida de notas fechadas. |
| Permissões e auditoria | Parcial | Controle por perfil, escopo docente, tokens de formulário, `activity_log` e `period_closure_log`. | Aplicar autorização por ano/turma/disciplina em todos os fluxos e registrar valores anteriores/novos nas alterações acadêmicas críticas. |
| Backup e recuperação | Pendente como rotina | Foi criado backup manual durante a recuperação; não há rotina automatizada versionada identificada. | Backup consistente de banco e anexos, retenção, validação de integridade e restauração testada. GitHub preserva código, não dados locais. |

## Problemas reproduzidos e riscos confirmados

### 1. Seed recria matrícula encerrada ao reiniciar — crítico

Em `academic_core._seed`, qualquer estudante do `ROSTER` sem matrícula ativa recebe uma matrícula ativa na 3110/2026. A rotina executa novamente na inicialização.

Reprodução isolada: encerrar a matrícula de `23081`, executar `init_academic_core()` e consultar matrículas ativas. Resultado: uma matrícula ativa foi recriada, mantendo a encerrada no histórico. Isso também pode afetar estudantes transferidos, desistentes ou concluintes.

Aceite: inicializações repetidas não alteram situação, turma, nome ou trajetória de registros administrados; carga inicial deve ter marcador e regras explícitas.

### 2. Ativação de ano ignora a regra de encerramento — alta prioridade

`mutate('year_status', status='active')` fecha outros anos ativos diretamente. A validação de períodos abertos só ocorre no caminho explícito `status='closed'`.

Reprodução isolada: 2026 tinha um período aberto; ao ativar 2027, 2026 ficou `closed` e seu período continuou `open`.

Aceite: todas as transições passam pelas mesmas regras; não pode haver encerramento implícito sem validação. Reabertura exige motivo e auditoria.

### 3. Importador integral — corrigido em 07/10/2026

`scripts/migrate_sqlite_to_supabase.py` agora descobre as colunas compatíveis, migra as 48 tabelas na ordem de dependências, preserva IDs e anexos, atualiza sequências e valida integridade e contagens antes do commit. A carga é idempotente e transacional. A execução remota dos dados continua sendo uma etapa operacional feita com a connection string privada da instituição.

### 4. Notas e fechamento ainda usam critérios diferentes — alta prioridade

`/notas` verifica o período da data atual, enquanto `sync_grade` grava N1/N2 nos períodos 1 e 2. `period_is_closed` seleciona período por data sem filtrar ano/turma. A inicialização também executa `sync_all_legacy_grades`, sem verificar fechamento dos períodos de destino.

Evidência estática; não foi executada uma tentativa HTTP de alteração de nota fechada nesta auditoria.

Aceite: lançamento referencia avaliação e período explícitos; autorização e bloqueio se aplicam ao destino real; inicialização não modifica retratos acadêmicos encerrados.

### 5. Fontes fixas continuam nos fluxos principais

`current_aluno` parte de `ALUNOS_DB` para perfis conhecidos; `live_roster` volta ao `ROSTER` quando a consulta não retorna matrículas; horário e painéis usam `SCHEDULE_3110`. O encerramento de todas as matrículas, por exemplo, deve resultar em estado vazio, sem reintroduzir a lista demonstrativa.

Aceite: toda turma/aluno cadastrado pela Direção funciona nos mesmos fluxos; dados demonstrativos ficam apenas na carga inicial; nenhuma turma/ano depende de constante para uso diário.

## Próxima ordem de execução

1. Corrigir seed e transições acadêmicas, com regressões para matrícula encerrada e troca de ano.
2. Unificar períodos, autorização e auditoria dos fluxos de notas/chamada/diário.
3. Fazer as telas consumirem exclusivamente a estrutura normalizada, mantendo estados vazios reais.
4. Implementar horários persistidos e conflitos.
5. Implementar avaliações configuráveis e frequência por aula.
6. Completar importador e validar a migração em homologação.
7. Automatizar backup e testar restauração; então planejar a troca para PostgreSQL.

## Validação disponível e limites

- A versão de código auditada passou nos 81 testes `unittest` executados em 03/10/2026 com SQLite separado, antes desta atualização documental.
- A auditoria executou duas verificações adicionais de comportamento em base isolada e comparou o inventário do importador com o esquema local.
- Os testes de backend atuais verificam tradução de SQL e compatibilidade de valores; não equivalem a testes de integração com PostgreSQL real.
- Na etapa original de auditoria não houve mudança funcional nem aplicação de migrações. Os problemas eram pendências da versão auditada; o status das primeiras correções está no início deste documento.
