# Manual — instalar e remover

Duas direções, a mesma regra: o bootstrap só encosta no que é dele. A instalação nunca
sobrescreve conteúdo existente; a remoção nunca apaga o que o projeto escreveu.

## Instalar sem clonar

De dentro do projeto-alvo:

```bash
curl -fsSL https://raw.githubusercontent.com/dougmotshell/harness-bootstrap/main/install.sh | sh
```

O `install.sh` baixa este repositório como tarball num diretório temporário, roda o
`scripts/init-project.py` e apaga o temporário na saída — inclusive quando o bootstrap
falha. No projeto fica só o harness.

O primeiro argumento é o alvo (padrão: o diretório atual); todos os outros vão direto
para o `init-project.py`, então qualquer opção dele funciona pelo pipe:

```bash
curl -fsSL .../install.sh | sh -s -- ../meu-projeto --dry-run   # ver o plano
curl -fsSL .../install.sh | sh -s -- ../meu-projeto             # escrever e mesclar
curl -fsSL .../install.sh | sh -s -- . --check                  # auditar; sai 1 se faltar
```

| Variável | Padrão | O que faz |
|---|---|---|
| `HARNESS_BOOTSTRAP_REF` | `main` | branch, tag ou commit de onde instalar |
| `HARNESS_BOOTSTRAP_REPO` | `dougmotshell/harness-bootstrap` | repositório de origem (um fork, por exemplo) |

Requisitos no alvo: `python3`, `tar`, e `curl` ou `wget`. Nada além disso — o bootstrap é
stdlib e não tem passo de instalação.

O alvo precisa existir. Um caminho inexistente é recusado em vez de criado, antes mesmo
do download: erro de digitação não vira diretório com um harness dentro.

Com o repositório clonado, é o mesmo script pelas suas mãos:

```bash
python3 scripts/init-project.py ../meu-projeto --dry-run
python3 scripts/init-project.py ../meu-projeto
```

Como cada arquivo é mesclado quando o destino já existe está em
[usar em diferentes tipos de projeto](tipos-de-projeto.md).

## Remover

```bash
curl -fsSL https://raw.githubusercontent.com/dougmotshell/harness-bootstrap/main/uninstall.sh | sh -s -- . --dry-run
curl -fsSL https://raw.githubusercontent.com/dougmotshell/harness-bootstrap/main/uninstall.sh | sh
```

Ou, no clone: `python3 scripts/uninstall-project.py ../meu-projeto --dry-run`.

Comece sempre pelo `--dry-run`: esta é a direção que apaga arquivo.

Desinstalar é o lado difícil, porque a instalação mescla dentro de arquivos que o projeto
possui — um `rm` da lista levaria junto o `Makefile` dele. Cada modo é revertido pelo
inverso exato do merge que o escreveu:

| Modo | O que a remoção faz |
|---|---|
| `whole` | apaga o arquivo **só** se ele ainda for idêntico ao template renderizado |
| `block` / `make` | tira o bloco `# harness-bootstrap >>> … <<<`; apaga o arquivo se não sobrar nada |
| `json` | tira só as chaves cujo valor ainda é o do template; hooks casados por `command` |
| `import` | tira a linha `@AGENTS.md` e a nota que veio com ela |
| `advise` | nada foi escrito quando o arquivo já existia; nada a desfazer |
| superfícies geradas | apagadas pelo banner `managed-by:…/sync-ai-surfaces`, nunca pelo caminho |

O que ele **não** apaga, por definição:

- arquivo que o projeto mudou depois do bootstrap — sai como `differs from the template
  — kept`, e só o `--force` o remove;
- arquivo escrito à mão sob um caminho gerado (`.claude/commands/`, `.codex/`…): sem o
  banner do gerador, não é dele;
- diretório que não ficou vazio.

Duas honestidades sobre JSON: o merge da instalação **reformata** `settings.json` e
`.mcp.json` (indentação de dois espaços), e a remoção não desfaz formatação — o arquivo
volta igual no dado, não byte a byte. E um container que ficou vazio no topo é mantido:
`{"mcpServers": {}}` provavelmente era o que estava lá antes, e devolver `{}` seria
editar a configuração do projeto em silêncio.

A garantia que os testes cobrem: projeto novo instalado e removido volta a **diretório
vazio**; projeto que já existia volta com cada arquivo seu byte a byte igual.

```bash
make test   # inclui os dois round-trips
```
