# Lean Memory

Um servidor MCP de memória local para ajudar assistentes de programação a retomar tarefas em outra conversa. Ele guarda **resumos curtos por tarefa** e permite recuperar somente o resumo relevante.

> Protótipo inicial. O armazenamento local foi testado, mas a integração MCP e a instalação ainda precisam de um teste completo. Ainda não há medição comparativa de consumo de tokens com o ai-memory. O consumo depende de como o assistente usa as ferramentas e escreve os resumos.

## Como funciona

1. O assistente salva um resumo da tarefa em andamento: objetivo, decisões, arquivos, testes, pendências e próximo passo.
2. Na próxima conversa, ele pesquisa por palavras-chave e recebe uma lista curta de possíveis tarefas, sem carregar todos os resumos.
3. Depois de identificar a tarefa correta, ele lê o resumo pelo ID e confirma o estado real do projeto antes de continuar.
4. Ao atualizar o resumo, informa a revisão atual para evitar sobrescrever uma alteração feita por outra sessão.

Os dados ficam em um banco SQLite local. A busca usa FTS5, sem embeddings, chamadas a modelos ou serviços de nuvem feitas pelo servidor. O seu assistente continua usando o modelo e pode ter custos próprios.

O servidor não lê conversas automaticamente, não sabe quando o contexto está acabando e não abre um novo chat. O comportamento depende do assistente seguir as instruções e ter acesso às ferramentas MCP. Um resumo incompleto também pode deixar informações de fora.

## Instalação

Requisitos: Python 3.10 ou superior com SQLite e FTS5, Git e um cliente que aceite servidores MCP via stdio. A instalação das dependências requer acesso ao PyPI.

Clone este repositório ou baixe seus arquivos. No diretório do projeto:

**Windows PowerShell:**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

**Linux/macOS:**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

O pacote usa a versão 1.x do SDK oficial MCP para Python. Mantenha a pasta do projeto e o ambiente virtual acessíveis ao cliente.

## Configurar no Codex

Adicione ao arquivo de configuração do Codex, substituindo os dois caminhos absolutos pelos seus. Exemplo Windows (`/` funciona nos caminhos do TOML):

```toml
[mcp_servers.lean_memory]
command = "C:/caminho/para/lean-memory/.venv/Scripts/python.exe"
args = ["-m", "lean_memory.server"]

[mcp_servers.lean_memory.env]
LEAN_MEMORY_DIR = "C:/caminho/privado/projeto-a/.lean-memory"
```

No Linux/macOS use, por exemplo, `/home/usuario/lean-memory/.venv/bin/python` e um diretório privado para os dados. Para manter projetos separados, configure um diretório de dados diferente para cada projeto. O caminho padrão, quando a variável não é definida, é `.lean-memory` no diretório em que o servidor é iniciado; dependendo do cliente, ele pode não ser a pasta do projeto. Reinicie ou recarregue o cliente e confirme que as ferramentas aparecem.

Outros clientes MCP podem ser compatíveis; use o mesmo executável, argumento e variável de ambiente na configuração do cliente. A integração real depende das permissões e do suporte de cada cliente.

## Instruções para o assistente

Inclua algo semelhante no `AGENTS.md` do projeto, ajustando para o seu fluxo:

```markdown
Ao começar ou retomar uma tarefa, procure checkpoints do mesmo assunto no
servidor lean_memory. Leia apenas o registro que corresponder à tarefa atual;
se houver dúvida, peça esclarecimento. Confira os arquivos e o estado atual
antes de continuar. Durante trabalho em andamento, salve um resumo conciso
com objetivo, decisões, arquivos, testes, pendências e próximo passo. Para
atualizar um registro, leia-o e use sua revisão atual. Não guarde senhas,
tokens, conversas completas ou informações pessoais desnecessárias.
```

Peça, por exemplo: “Procure o checkpoint da tarefa de cadastro e continue de onde paramos.” Para criar um primeiro registro: “Salve um resumo conciso do trabalho atual no Lean Memory.” As chamadas podem depender de confirmação no seu cliente.

## Ferramentas

| Ferramenta | Uso |
| --- | --- |
| `save_task` | Cria um checkpoint; para atualizar, exige o ID e a revisão lida anteriormente. O resumo completo substitui o anterior. |
| `search_tasks` | Pesquisa palavras em títulos e resumos e devolve até 10 resultados com metadados curtos. |
| `read_task` | Lê o checkpoint completo de um ID específico. |

Status disponíveis: `in_progress`, `blocked` e `completed`. Cada resumo aceita até 12.000 caracteres; a recomendação é usar bem menos e registrar apenas o que for necessário.

## Privacidade e limites

- Os resumos são armazenados localmente **sem criptografia fornecida pelo programa**. Pessoas e processos com acesso ao diretório podem lê-los.
- Não salve senhas, chaves, dados pessoais ou informações confidenciais sem necessidade. O programa não detecta nem remove segredos automaticamente.
- Mantenha `.lean-memory/` fora do Git e confira os arquivos antes de compartilhá-los. Se definir outro caminho, proteja-o e exclua-o de commits também.
- O banco não sincroniza entre computadores. Para mover ou fazer backup, encerre o servidor e copie o diretório de dados de forma segura; a cópia pode conter informações privadas.
- Guardar ou recuperar informação depende da ferramenta ser chamada. O sistema não garante memória perfeita ou que toda decisão será salva.

## Testes

Com as dependências instaladas, execute na pasta do repositório:

```bash
python -m unittest discover -s tests -v
```

Em Windows, use `.\.venv\Scripts\python.exe` no lugar de `python`; em Linux/macOS, `.venv/bin/python`. Os testes usam diretórios temporários e não acessam dados reais.
