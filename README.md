# FaeHub+ — Campus Vivo

Aplicação web de gestão escolar da ETESC/FAETEC Santa Cruz. O projeto reúne quatro experiências conectadas: a jornada do aluno, o portal da família, o estúdio de trabalho do professor e o observatório de gestão da Direção.

A chegada segue a direção de arte **Campus em vigília**: uma entrada cinematográfica pós-chuva, com profundidade, luz ambiente, reflexos e movimento sutil. O modo leve e a preferência do sistema por movimento reduzido desativam os efeitos sem prejudicar a navegação.

## Como iniciar

O jeito mais simples no Windows é dar dois cliques em `start_faehub.bat`. Na primeira execução, o arquivo cria o ambiente virtual e instala o Flask. Quando aparecer `FaeHub pronto`, mantenha o terminal aberto e use:

`http://127.0.0.1:5000`

Pelo terminal do VS Code:

```powershell
# Abra a pasta extraída no VS Code e use o terminal integrado nela.
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Requisitos: Windows com Python 3.10 ou superior e acesso à internet apenas na primeira instalação.

## Contas para apresentação

| Perfil | Usuário | Senha |
|---|---|---|
| Aluno — Thiago | `thiago.zotti` | `aluno@123` |
| Aluno — Jonathan | `jonathan.samuel` | `aluno@123` |
| Aluno — Pablo | `pablo.sousa` | `aluno@123` |
| Aluno — Marlon | `marlon.eduardo` | `aluno@123` |
| Professora | `aline` | `professora@123` |
| Direção | `gilberto` | `direcao@123` |
| Responsável de Thiago | `responsavel.thiago` | `responsavel@123` |

O perfil visual escolhido na entrada não altera permissões: a conta autenticada define o espaço correto.

## Roteiro curto de demonstração

1. Abra a chegada, clique em **Entrar no campus** e use Thiago.
2. Depois da identificação, clique em **Entrar no meu espaço** para mostrar a aproximação do prédio.
3. Percorra Painel, Boletim, Frequência, Horário, Avisos, Exercícios, Calendário, Secretaria, Notificações, Mensagens e Avatar.
4. Entre como `responsavel.thiago` para mostrar o acompanhamento restrito à matrícula vinculada.
5. Saia e entre como `aline` para mostrar turma 3110, notas, chamada, diário, atividades e anexos.
6. Entre como `gilberto` para mostrar **Estrutura** (anos, períodos, catálogo, turmas, matrículas e docentes), secretaria, coordenação, fechamento de períodos, calendário, notificações e relatórios CSV reais.
7. Abra **Histórico** como aluno, responsável ou Direção para demonstrar anos anteriores sem sobrescrever o ano atual.

## Banco de dados: Supabase PostgreSQL

O Supabase PostgreSQL é a única base operacional do aplicativo. O fallback automático para `faehub.db` foi removido: sem `FAEHUB_DATABASE_URL`, a inicialização para com uma mensagem de configuração em vez de abrir uma base local divergente.

O esquema Supabase inclui anos letivos, períodos, cursos, disciplinas, turmas, matrículas, horários, avaliações, notas por avaliação, aulas, frequência, diário de classe, documentos, responsáveis, acompanhamento pedagógico, notificações, calendário, recuperação de senha, anexos e oportunidades de estágio. As tabelas atuais foram preservadas durante a transição para que as telas existentes continuem funcionando.

O núcleo P0 usa as entidades normalizadas também no modo local: a turma 3110 e seus 34 estudantes são semeados em `students` e `enrollments`, a Direção opera a estrutura em `/estrutura`, e o histórico multi-anual fica em `/historico`. O código de compatibilidade continua apenas para não quebrar telas existentes durante a transição.

### Conectar um projeto Supabase

1. Crie um projeto no Supabase e, nesta pasta, copie `.env.example` como `.env`.
2. No painel do projeto, abra **Connect** e copie a connection string do **Session pooler** para `FAEHUB_DATABASE_URL`. Não publique o `.env` nem envie a senha para o GitHub.
3. Instale as dependências e autentique a CLI:

```powershell
python -m pip install -r requirements.txt
npx --yes supabase@latest login
npx --yes supabase@latest link --project-ref SEU_PROJECT_REF
```

4. Confira e aplique a estrutura versionada:

```powershell
npx --yes supabase@latest db push --dry-run --include-seed
npx --yes supabase@latest db push --include-seed
```

5. Faça uma única vez o inventário do SQLite legado e importe os dados. A importação integral cobre todas as tabelas, preserva IDs e anexos, é idempotente e roda em uma única transação:

```powershell
python scripts/migrate_sqlite_to_supabase.py
python scripts/migrate_sqlite_to_supabase.py --apply
python scripts/check_database.py
```

No Windows, o mesmo processo pode ser concluído com dois cliques em `migrate_to_supabase.bat`.

Depois da validação, `python app.py` inicia exclusivamente no Supabase. O SQLite legado pode ser guardado fora da pasta como cópia de contingência até a restauração do Supabase ser testada; ele não é mais lido pela aplicação.

### Segurança

As tabelas têm RLS ativado e não estão expostas às funções públicas `anon` e `authenticated`. Nesta primeira fase o acesso acontece somente pelo servidor Flask. A integração posterior com Supabase Auth poderá liberar políticas por perfil sem abrir os dados escolares indevidamente. Defina também `FAEHUB_SECRET_KEY` com uma chave longa e exclusiva. O servidor embutido do Flask é adequado para apresentação local; uma publicação na internet requer um servidor WSGI, HTTPS e política de backup.

## Testes

Com o ambiente ativado:

```powershell
python -m unittest discover -v
```
