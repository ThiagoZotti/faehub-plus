# Roadmap do FaeHub+

Pendências acordadas para as próximas etapas. Elas ficam registradas aqui para que a evolução do projeto não dependa da memória da conversa.

## P0 — Fundação acadêmica e banco de dados

### PostgreSQL, anos letivos, turmas e histórico

- Migrar a persistência de SQLite para PostgreSQL com migrações versionadas.
- Transformar o ano letivo em uma entidade real do sistema.
- Permitir que a Direção crie turmas, matricule alunos e vincule professores.
- Associar notas, frequência, atividades, avisos e vínculos à turma e ao ano correspondentes.
- Preservar anos encerrados para consulta histórica, sem misturar ou sobrescrever dados.
- Migrar os dados atuais sem perda e manter os fluxos já existentes.

## P1 — Módulo de estágios — concluído em 25/09/2026

- Professor publica, edita e arquiva oportunidades de estágio.
- Aluno consulta vagas ativas, abre o anúncio completo e segue o link ou as instruções para inscrição.
- Links externos devem abrir com segurança.
- A primeira versão não armazenará currículo nem acompanhará candidaturas dentro do FaeHub+.

Entregue com publicação, edição, arquivamento e restauração pelo professor; consulta segura pelo aluno; filtros locais; validação de prazo e links; persistência compatível com SQLite e Supabase; testes de permissão e fluxo completo.

## P1 — Cardápio semanal

- Exibir o almoço de cada dia e destacar automaticamente o cardápio de hoje.
- Permitir a consulta da semana completa em computador e celular.
- Exibir um estado claro quando a escola ainda não tiver publicado o cardápio.
- A atualização semanal será feita pelos dados do sistema, sem editar o código.
- O cardápio real será inserido quando for fornecido pela escola.

## Trilha visual — Tela de login

- Substituir o cenário atual por uma fotografia realista da entrada da escola.
- Reduzir filtros e camadas escuras globais para preservar as cores naturais da foto.
- Concentrar contraste apenas atrás dos textos e do cartão de acesso.
- Manter movimento sutil, modo leve e suporte a `prefers-reduced-motion`.
- Validar enquadramento tanto no computador quanto no celular.

Uma foto tirada por vocês é a opção preferencial: evita dúvidas de licença e permite fotografar já pensando no enquadramento do login. Uma imagem encontrada na internet só deverá ser usada se houver autorização clara de uso.
