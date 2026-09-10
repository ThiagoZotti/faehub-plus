# FaeHub+ — Campus Vivo

Aplicação web de gestão escolar da ETESC/FAETEC Santa Cruz. O projeto reúne três experiências conectadas: a jornada do aluno, o estúdio de trabalho do professor e o observatório de gestão da Direção.

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

O perfil visual escolhido na entrada não altera permissões: a conta autenticada define o espaço correto.

## Roteiro curto de demonstração

1. Abra a chegada, clique em **Entrar no campus** e use Thiago.
2. Depois da identificação, clique em **Entrar no meu espaço** para mostrar a aproximação do prédio.
3. Percorra Painel, Boletim, Frequência, Horário, Avisos, Exercícios, Mensagens e Avatar pelas setas inferiores.
4. Saia e entre como `aline` para mostrar turma 3110, lançamento de notas, chamada e correção de atividades.
5. Entre como `gilberto` para mostrar usuários, vínculos docentes, relatórios CSV e configurações institucionais.

## Dados e segurança

Os dados ficam em `faehub.db`. Antes de uma demonstração importante, copie esse arquivo para um local seguro. Defina `FAEHUB_SECRET_KEY` no ambiente em uma implantação compartilhada. O servidor embutido do Flask é adequado para apresentação local; uma publicação na internet requer um servidor WSGI e política de backup.

## Testes

Com o ambiente ativado:

```powershell
python -m unittest discover -v
```
