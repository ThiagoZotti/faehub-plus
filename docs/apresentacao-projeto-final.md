# Apresentação de projeto final: FaeHub+

Integrantes: **Thiago Souza Zotti** e **Jonathan Samuel Martins Tannes**.

Arquivos prontos: [PowerPoint editável](apresentacao/FaeHub-Projeto-Final.pptx), [PDF](apresentacao/FaeHub-Projeto-Final.pdf) e [imagens dos seis slides](apresentacao/FaeHub-Slides-PNG.zip). O PowerPoint inclui notas para os apresentadores. O PDF é uma versão visual dos slides.

Os slides foram renderizados e revisados individualmente. O PowerPoint passou nas verificações de estrutura, geometria, fontes e reimportação do Artifact Tool. Isso não equivale a um ensaio da aplicação nem a uma execução no Microsoft PowerPoint.

Os cinco primeiros slides seguem o modelo solicitado. O sexto orienta a demonstração prática. Conteúdo conferido no README, nas rotas e permissões de `app.py` e na estrutura acadêmica de `academic_core.py`. Os diagramas são recortes didáticos do sistema implementado.

## Slide 1: Título do projeto e logo

**FaeHub+**
Sistema web de gestão escolar
Projeto final de Desenvolvimento de Sistemas
Contexto: ETESC / FAETEC Santa Cruz

Thiago Souza Zotti
Jonathan Samuel Martins Tannes

Usar a logo existente em `static/logo-faehub.webp`.

Fala sugerida de Thiago: “Somos Thiago Souza Zotti e Jonathan Samuel Martins Tannes. Nosso projeto é o FaeHub+, um sistema web que reúne o acompanhamento escolar e as rotinas de gestão em espaços próprios para cada perfil.”

## Slide 2: Objetivo

**Objetivo geral**
Centralizar o acompanhamento acadêmico e as rotinas escolares em uma aplicação web com acesso por perfil.

**Objetivos específicos**

- Permitir a consulta de boletim, frequência e horários.
- Apoiar o professor no lançamento de notas, chamada e atividades.
- Organizar turmas, matrículas e períodos letivos.
- Reunir comunicados, mensagens e acompanhamento familiar.

Fala sugerida de Thiago: “A proposta é reunir essas tarefas em um mesmo ambiente. O aluno consulta sua vida acadêmica, o professor registra o trabalho de sala de aula, a direção organiza a estrutura escolar e a família acompanha o estudante vinculado.”

## Slide 3: Justificativa

**Problema que o projeto busca enfrentar**
Informações escolares distribuídas em diferentes registros e canais dificultam a consulta e o acompanhamento.

**Relevância**
Um ambiente central facilita o acesso ao histórico acadêmico, organiza registros e aproxima a comunicação entre escola e família.

**Contexto de aplicação**
Projeto desenvolvido para o contexto da ETESC / FAETEC Santa Cruz, com fluxos para alunos, responsáveis, professores e direção.

A dispersão de informações é a motivação de projeto, não uma conclusão de pesquisa de campo. Não afirmar adoção institucional, redução de erros ou ganho medido de produtividade sem evidência.

Fala sugerida de Thiago: “Nossa motivação é facilitar o acesso às informações e reduzir a necessidade de procurar cada registro em um lugar diferente. O projeto usa o contexto escolar da ETESC e busca atender os principais participantes dessa rotina.”

## Slide 4: Diagrama de casos de uso

Inserir o diagrama gerado a partir de `diagramas/casos-de-uso-projeto-final.puml`.

- Aluno: consultar boletim e frequência, consultar horários e enviar atividades.
- Responsável: consultar boletim e frequência do estudante vinculado.
- Professor: registrar notas e chamada e publicar atividades.
- Direção: gerenciar estrutura e usuários e consultar relatórios.

Autenticação é uma precondição comum. O diagrama mostra os casos principais e não representa todos os módulos. O responsável acessa somente os dados permitidos do estudante vinculado.

Fala sugerida de Jonathan: “As linhas mostram quais ações cada ator pode realizar dentro do FaeHub+. O acesso depende da conta autenticada. Por exemplo, o professor registra notas e chamada, enquanto o aluno consulta os resultados. O responsável acompanha apenas o estudante vinculado.”

## Slide 5: Diagrama de banco de dados

Inserir o diagrama gerado a partir de `diagramas/banco-projeto-final.puml`.

Recorte do núcleo acadêmico persistido em PostgreSQL no Supabase. PK identifica a chave primária. FK identifica a chave estrangeira. `1` e `0..*` representam cardinalidades.

- `students` se liga a `classes` por `enrollments`.
- `classes` se liga a `subjects` por `class_subjects`.
- `assessments` pertence a uma oferta de disciplina e a um período letivo.
- `assessment_scores` associa uma avaliação à matrícula do estudante.

O recorte omite usuários, anos letivos, aulas, frequência, mensagens e outras tabelas. Os nomes de campos apresentados correspondem ao código. As cardinalidades indicam os vínculos possíveis no modelo, não quantidades de registros existentes.

Fala sugerida de Jonathan: “A matrícula relaciona o estudante à turma. A tabela class_subjects representa a disciplina oferecida em uma turma. Cada avaliação está ligada a essa oferta e a um período. A nota fica associada à avaliação e à matrícula, preservando o contexto acadêmico do estudante.”

## Slide 6: Demonstração prática

**Thiago: jornada do aluno e da família**

1. Entrar com uma conta de demonstração de aluno.
2. Mostrar boletim, frequência e horário.
3. Abrir atividades e comunicados.
4. Mostrar o acompanhamento de um responsável vinculado.

**Jonathan: professor e direção**

1. Entrar com uma conta de demonstração de professor.
2. Mostrar notas, chamada e atividades de uma turma autorizada.
3. Entrar com uma conta de demonstração da direção.
4. Mostrar estrutura acadêmica e relatórios.

Divisão de falas sugerida: Thiago apresenta slides 1 a 3; Jonathan apresenta slides 4 e 5; ambos participam da demonstração. Ajustar conforme a preferência do grupo.

## Preparação e contingência

- Ensaiar o roteiro e conferir os fluxos escolhidos antes da apresentação.
- Usar contas e registros de demonstração, sem expor dados pessoais de terceiros.
- Confirmar acesso ao banco remoto: o aplicativo exige PostgreSQL configurado e não tem fallback operacional para SQLite.
- Levar slides exportados e uma gravação curta da demonstração em pendrive para contingência de rede. A gravação não substitui a demonstração ao vivo quando ela for possível.
- Guardar backup do banco separadamente do código, conforme a política do projeto.
- Não incluir senhas, tokens, `.env` ou conexão do banco nos slides.

## Fontes internas

- `README.md`: escopo, perfis, execução e roteiro de demonstração.
- `app.py`: navegação, rotas e controle de acesso.
- `academic_core.py`: entidades e vínculos do núcleo acadêmico.
- `supabase/migrations/20260925151550_initial_school_schema.sql`: esquema PostgreSQL.
- `supabase/migrations/20260926133712_complete_p0_academic_core.sql`: restrições de integridade.
