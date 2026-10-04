# Roadmap oficial do FaeHub+

Este arquivo segue o roteiro aprovado em 25/09/2026. Ele é a fonte de verdade para prioridade e escopo.

## O que já existe

- Aluno: login individual, painel, boletim, agenda, horário, comunicados, exercícios, secretaria, estágios e mensagens.
- Professor: painel, turmas, chamada, notas, avisos, atividades, mensagens e estágios.
- Direção: usuários, turmas, vínculos docentes, relatórios e configurações.
- Dados: SQLite local como fallback e Supabase PostgreSQL com migrações versionadas.

## P0 — Fundação acadêmica e banco de dados

- Ano letivo, períodos, cursos, disciplinas, turmas e vínculos normalizados.
- Histórico de anos anteriores sem sobrescrever o ano atual.
- Migração segura do legado e banco único no Supabase.
- Criação completa de turmas, matrículas e vínculos pela Direção.

Status: **parcial — fundação ainda não concluída**. A auditoria de 03/10/2026 identificou estrutura normalizada com telas e testes, mas horários, notas e chamada ainda usam fontes e fluxos legados. PostgreSQL em produção e a importação integral não foram verificados nesta etapa.

Evidências, critérios de aceite e situação dos dez itens aprovados: [P0-AUDIT.md](P0-AUDIT.md).

Prioridades verificadas:

1. Impedir que a inicialização recrie matrículas encerradas e sobrescreva dados administrados.
2. Corrigir ativação de ano que fecha o anterior com período aberto; unificar fechamento/reabertura com justificativa e auditoria.
3. Aplicar autorização e bloqueio ao ano/período efetivamente alterado, incluindo notas normalizadas e sincronização do legado.
4. Remover dependências operacionais de `ALUNOS_DB`, `ROSTER` e `SCHEDULE_3110`, mantendo dados demonstrativos somente na carga inicial.
5. Implementar horários configuráveis com conflitos, avaliações com pesos/regras e frequência por aula/disciplina.
6. Atualizar o importador para todas as entidades e campos atuais; validar dados e anexos em homologação antes da troca para PostgreSQL.
7. Automatizar backup do banco/anexos e comprovar restauração.

A consulta multi-anual e a estrutura básica existem, mas isso não comprova imutabilidade do histórico nem conclusão do P0. A suíte local de 81 testes passou; foram reproduzidos problemas fora de sua cobertura atual.

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

A migração de estrutura P1 foi aplicada ao Supabase. Esta cópia local ainda usa SQLite: a conexão e a migração dos dados existentes dependem da configuração segura do banco. Não considerar a migração integral concluída.

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

- Integração com a rede social escolar FaeNet.
- Biblioteca, patrimônio, transporte, ocorrências e atendimentos.
- Avatares: removidos da versão atual por decisão anterior; não reintroduzir sem solicitação explícita.

## Trilha visual — Tela de login

- Preferir fotografia própria e licenciada da entrada da escola.
- Preservar as cores naturais da imagem e concentrar contraste atrás do conteúdo.
- Manter movimento sutil, modo leve e `prefers-reduced-motion`.
- Validar computador, tablet e celular.
