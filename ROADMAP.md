# Roadmap oficial do FaeHub+

Este arquivo segue o roteiro aprovado em 25/09/2026. Ele é a fonte de verdade para prioridade e escopo.

## Situação revisada em 16/10/2026

- **Implementado em 16/10:** chamada por aula/disciplina/horário em modelo
  normalizado, revisão/auditoria e histórico diário separado; autenticador TOTP
  opcional com recuperação e proteção do login. Gmail ganhou diagnóstico privado;
  backup criptografado com manifesto, ferramenta de restauração isolada e envio
  ao Drive foi preparado. Ativação privada Gmail/MFA e backup real/agendamento
  dependem de configuração; não estão comprovados por testes simulados.
  Detalhes: [docs/attendance-security-backup.md](docs/attendance-security-backup.md).
- Corrigida a causa do deploy anterior falhar: restrição PostgreSQL dos dias da
  semana não correspondia ao código. Migração e teste com rollback aplicados.

- **Entregue nesta etapa:** Direção → Estrutura → Horários, com cadastro, edição,
  arquivamento/restauração, detecção de conflitos de turma/sala/docente,
  revisão contra edição desatualizada e auditoria. Painéis do aluno/professor e
  a grade semanal do aluno consultam os horários persistidos das suas turmas.
- A referência original de 3110/2026 é adotada uma única vez, sem sobrescrever
  grades já administradas. Outras turmas não herdam horários demonstrativos.
- Cadastro/nome/turma do aluno e acompanhamento do responsável vêm dos registros
  persistidos; notas, frequência e avisos não recebem valores de perfis fixos.
  Uma lista sem matrículas ativas permanece vazia, sem retorno ao `ROSTER`.
- Supabase PostgreSQL é a base operacional, sem fallback automático SQLite.
  SQLite é usado somente em testes descartáveis. A descrição antiga da auditoria
  de 03/10 permanece como referência histórica, não como estado atual do deploy.
- Redesign completo dos módulos de professor/direção, login em tela cheia,
  primeira otimização da navegação, tela compartilhada FaeNet e anexos de
  atividades já foram entregues. O atalho FaeNet não é login unificado.
- **Ainda pendentes:** avaliações/pesos e períodos explícitos,
  unificação dos bloqueios de fechamento e retirada das demais
  pontes legadas, entrega real de convites Gmail, configuração privada de MFA e
  política de backup com restauração comprovada. As demos continuam abertas por
  decisão explícita do usuário; esta atualização não muda contas ou senhas.

Detalhes operacionais e verificação: [docs/school-timetable.md](docs/school-timetable.md).

## O que já existe

- Aluno: login individual, painel, boletim, agenda, horário, comunicados, exercícios, secretaria, estágios e mensagens.
- Professor: painel, turmas, chamada, notas, avisos, atividades, mensagens e estágios.
- Direção: usuários, turmas, vínculos docentes, relatórios e configurações.
- Dados: Supabase PostgreSQL com migrações versionadas; SQLite somente em testes descartáveis.

## P0 — Fundação acadêmica e banco de dados

- Ano letivo, períodos, cursos, disciplinas, turmas e vínculos normalizados.
- Histórico de anos anteriores sem sobrescrever o ano atual.
- Migração segura do legado e banco único no Supabase.
- Criação completa de turmas, matrículas e vínculos pela Direção.

Status: **parcial — fundação ainda não concluída**. A estrutura normalizada, horários e nova chamada por aula estão implementados; notas ainda mantêm pontes legadas. O checklist histórico de 03/10 não deve ser usado para concluir o estado atual da migração.

Evidências, critérios de aceite e situação dos dez itens aprovados: [P0-AUDIT.md](P0-AUDIT.md).

Prioridades verificadas:

1. **Concluído em 03/10/2026:** carga acadêmica inicial com marcador transacional; instalações existentes são adotadas sem reaplicar dados demonstrativos. Matrículas encerradas e dados cadastrais são preservados ao reiniciar.
2. **Correção inicial concluída em 03/10/2026:** ativar outro ano exige que todos os períodos dos anos ativos anteriores estejam fechados. Unificar os demais caminhos de fechamento/reabertura com justificativa e auditoria continua pendente.
3. Aplicar autorização e bloqueio ao ano/período efetivamente alterado, incluindo notas normalizadas e sincronização do legado.
4. **Concluído para os perfis/horários em 15/10:** removidas as leituras operacionais de `ALUNOS_DB` e o fallback de `ROSTER`; `SCHEDULE_3110` ficou somente na adoção inicial da referência. Demais pontes legadas ainda precisam ser retiradas.
5. **Horários entregues em 15/10:** concluir avaliações com pesos/regras e frequência por aula/disciplina.
6. Importador integral atualizado em 07/10. Manter reconciliação e testes de integração PostgreSQL a cada ampliação do esquema.
7. Automatizar backup do banco/anexos e comprovar restauração.

A consulta multi-anual e a estrutura básica existem, mas isso não comprova imutabilidade do histórico nem conclusão do P0. Após as primeiras correções, a suíte local de **86 testes passou**, incluindo cinco testes novos de integridade. As demais pendências permanecem abertas.

## P1 — Operação escolar completa

Status: primeira versão funcional entregue em 25/09/2026.

1. **Diário de classe** — professor registra conteúdo, objetivos, metodologia, recursos, tarefa e observações; coordenação valida ou devolve.
2. **Secretaria e documentos** — solicitação com protocolo, fluxo de atendimento, emissão imprimível e código de verificação.
3. **Portal do responsável** — conta própria, vínculo restrito ao estudante e visão de desempenho, frequência e serviços.
4. **Coordenação pedagógica** — radar de risco, plano de intervenção e acompanhamento de situação.
5. **Relatórios reais** — frequência, notas, diário, documentos e intervenções exportados dos registros persistidos.
6. **Notificações** — central persistente, público por perfil, badge de não lidas e links de contexto.
7. **Anexos** — PDF, PNG, JPG, TXT e ZIP em mensagens, atividades e entregas, até 5 MB, com autorização no download.
8. **Calendário escolar** — eventos, avaliações, reuniões, conselhos, feriados e recessos por público ou turma.
9. **Recuperação de senha** — solicitação, confirmação pela secretaria, código de uso único com expiração e revogação de sessões.
10. **Fechamento de períodos** — bloqueio de notas, chamada e diário; reabertura justificada com trilha de auditoria.

Limites desta entrega: o histórico imprimível é um extrato das notas registradas, não um histórico oficial multi-anual. A recuperação de senha depende da verificação manual pela secretaria, sem envio automático de e-mail. O fechamento bloqueia alterações, mas não cria um retrato histórico consolidado. Eventos restritos à turma não geram notificações gerais.

A migração de estrutura P1 foi aplicada ao Supabase. O aplicativo requer PostgreSQL; testes locais usam SQLite separado. Conferência de dados, anexos e restauração é uma etapa operacional distinta de publicar código.

Próximos reforços da P1: assinatura/verificação pública de documentos e integração de e-mail. As matrículas usadas pela aplicação já têm origem normalizada na P0.

## P2 — Experiência ampliada

### Estágios

- Professor publica, edita, arquiva e restaura oportunidades.
- Aluno consulta vagas ativas e segue link ou instruções de candidatura.
- Não armazena currículo nem candidatura nesta primeira versão.

Status: módulo funcional já entregue antecipadamente; classificado corretamente como P2.

### Cardápio semanal

- Cardápio diário e semanal, destaque automático do dia e estado sem publicação.
- Atualização pela gestão, sem alteração de código.

Status: aguardando o cardápio real da escola.

### Outras frentes P2

- Apresentação e atalhos para a FaeNet entregues; integração de identidade/sessões ainda não implementada.
- Biblioteca, patrimônio, transporte, ocorrências e atendimentos.
- Fotografia de perfil opcional entregue; não existe sistema de personagens.

## Trilha visual — Tela de login

- Preferir fotografia própria e licenciada da entrada da escola.
- Preservar as cores naturais da imagem e concentrar contraste atrás do conteúdo.
- Manter movimento sutil, modo leve e `prefers-reduced-motion`.
- Validar computador, tablet e celular.
