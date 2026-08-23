# Manual — usar em diferentes tipos de projeto

O bootstrap decide **por arquivo**, não por projeto: cada template declara o único
merge que o destino sobrevive. Por isso o mesmo comando serve para um diretório vazio e
para um projeto de cinco anos com `Makefile`, `CLAUDE.md` e `.claude/` próprios — o que
muda é o que ele encosta.

Duas perguntas antes de rodar:

1. **O alvo já tem harness?** Se existe `CLAUDE.md`, `AGENTS.md`, `.claude/` ou
   `Makefile`, o cabeçalho da execução imprime `existing harness` em vez de
   `from scratch`.
2. **Qual a stack?** O cabeçalho detecta pelo manifesto (`package.json`,
   `pyproject.toml`, `go.mod`, `Cargo.toml`, `composer.json`, `*.csproj`). É o que
   decide o [preenchimento dos sensores](#6-preencher-os-sensores-por-stack).

Sempre comece pelo plano:

```bash
python3 scripts/init-project.py ../alvo --dry-run
```

Sem o repositório clonado, os exemplos abaixo viram o mesmo comando pelo pipe — o
primeiro argumento é o alvo, o resto vai para o `init-project.py`:

```bash
curl -fsSL https://raw.githubusercontent.com/dougmotshell/harness-bootstrap/main/install.sh | sh -s -- . --dry-run
```

## Como cada arquivo é tratado

Nenhum arquivo é sobrescrito, truncado ou apagado, em nenhum modo. O que muda é o que
acontece quando o destino **já existe**:

| Modo | Arquivos | Destino já existe → |
|---|---|---|
| `whole` | `AGENTS.md`, `README.md`, `LICENSE`, `docs/**`, hooks, sementes autoradas | não toca |
| `block` | `.gitignore`, `.env.example` | acrescenta um bloco delimitado, uma vez |
| `make` | `Makefile` | acrescenta **só** os alvos que o projeto não define |
| `json` | `.claude/settings.json`, `.mcp.json` | mescla chaves; hooks casados por `command` |
| `import` | `CLAUDE.md`, `.github/copilot-instructions.md` | garante `@AGENTS.md` na linha 1 |
| `advise` | `.pre-commit-config.yaml` | não toca e imprime o trecho a colar |
| ao lado | `.github/workflows/ci.yml` | escreve `harness.yml` ao lado |

O bloco delimitado é o que torna a segunda execução um no-op:

```
# harness-bootstrap >>>
...
# harness-bootstrap <<<
```

Editar dentro do bloco é seguro — o marcador só é procurado, nunca reescrito.

## 1. Diretório vazio

O caso simples.

```bash
mkdir ../meu-projeto && cd ../meu-projeto && git init
python3 ~/www/harness-bootstrap/scripts/init-project.py .
```

Esperado: `36 written or merged, 0 left untouched`, seguido de `8 written, 8 total` do
gerador. Depois, `/bootstrap-ai-harness` no projeto-alvo para preencher os `TODO:`.

## 2. Projeto com código, sem harness de IA

O caso mais comum. O que vale conferir depois, na ordem:

```bash
python3 ~/www/harness-bootstrap/scripts/init-project.py .
python3 ~/www/harness-bootstrap/scripts/init-project.py . --check   # o que ficou de fora
git diff Makefile .gitignore .claude/settings.json                  # o que foi mesclado
make -n test                                                        # ainda é o seu recipe?
```

O `--check` audita **conteúdo**, não caminho: um `Makefile` sem `sync-check`, ou um
`settings.json` que não chama os hooks, aparece como `incomplete — needs ...` e sai `1`.
Um hook no disco que nenhum `settings.json` invoca é arquivo morto, e é exatamente o
que essa auditoria existe para pegar.

Se o projeto já tem `.pre-commit-config.yaml`, ele é o único que fica por sua conta:
YAML com um segundo `repos:` quebra o arquivo, então o script imprime o hook
`ai-surfaces` para você colar.

## 3. Projeto que já tem `.claude/` escrito à mão

O `.claude/skills/`, `.claude/commands/`, `.github/prompts/` e `.codex/` são território
do gerador — mas ele só se considera dono do que tem o banner `managed-by:`. Cada
arquivo sem banner cai em uma de duas situações:

| Situação | Significado | O que o gerador faz |
|---|---|---|
| `foreign` | escrito à mão, nenhuma fonte projeta ali | mantém, nunca poda; conviver é legítimo |
| `conflict` | escrito à mão **no caminho** que uma fonte projeta | não escreve nada e sai `2` |

Para trazer uma skill artesanal para dentro do gerador — **adoção**:

```bash
mkdir -p skills/deploy
git mv .claude/skills/deploy/SKILL.md skills/deploy/SKILL.md
python3 scripts/sync-ai-surfaces.py
```

A fonte passa a ser `skills/deploy/SKILL.md`, e a partir dela saem as superfícies de
todas as CLIs. O frontmatter precisa de `name:` e `description:`; regra por caminho
precisa de `paths:`; agente precisa de `description:`.

Diante de um `conflict`, renomeie um dos dois lados. `--force` sobrescreve, e só faz
sentido quando você já concluiu que o arquivo à mão era lixo.

## 4. Monorepo

Duas topologias funcionam, porque o gerador resolve tudo a partir da própria
localização (`scripts/sync-ai-surfaces.py` → raiz um nível acima).

**Harness na raiz — o padrão.** Um contrato, um conjunto de skills, sensores que
delegam:

```make
test:
	npm test --workspaces
```

**Harness por pacote.** Rode o bootstrap apontando para o pacote. Funciona, com três
ressalvas que não são do bootstrap e sim das ferramentas:

- `.github/workflows/` só é lido na **raiz** do repositório. Um `ci.yml` dentro de
  `packages/web/` é inerte — mova o job para a raiz, ou rode o bootstrap com
  `--no-sync` e monte o workflow você.
- `.pre-commit-config.yaml` idem: raiz.
- `.claude/settings.json` de um subdiretório só vale quando a CLI é aberta com aquele
  pacote como raiz do projeto.

Na dúvida: harness na raiz, sensores delegando por workspace.

## 5. Projeto de terceiros, fork ou clone que você não publica

O harness é infraestrutura sua, não do upstream. Mantenha-o num branch seu, ou não
comite `AGENTS.md`, `.claude/` e `docs/` — mas então **também** não comite as
superfícies geradas, e aceite que quem clonar não tem o harness. Metade comitada é o
pior dos dois: o `--check` do gerador falha no CI de quem não tem as fontes.

## 6. Preencher os sensores, por stack

É aqui que está o nível, não nos hooks: **L3 exige `sensors ≥ 60%`**, e L4 vem depois
de L3. Quatro alvos do `Makefile` mais o config da ferramenta em disco — o alvo sem o
config roda e não pontua.

| Alvo | Python | Node/TS | Go | Rust | PHP | .NET |
|---|---|---|---|---|---|---|
| `test` | `pytest` | `vitest run` | `go test ./...` | `cargo test` | `vendor/bin/phpunit` | `dotnet test` |
| `lint` | `ruff check .` | `eslint .` | `golangci-lint run` | `cargo clippy -- -D warnings` | `vendor/bin/phpcs` | `dotnet format --verify-no-changes` |
| `typecheck` | `mypy --strict .` | `tsc --noEmit` | nativo (`go build ./...`) | nativo (`cargo check`) | `vendor/bin/phpstan analyse` | nativo (`dotnet build`) |
| `format` | `ruff format .` | `prettier -w .` | `gofmt -w .` | `cargo fmt` | `vendor/bin/php-cs-fixer fix` | `dotnet format` |
| config esperado | `pyproject.toml`, `mypy.ini` | `eslint.config.js`, `tsconfig.json` com `strict: true` | `.golangci.yml` | `Cargo.toml`, `rustfmt.toml` | `phpstan.neon`, `.php-cs-fixer.php` | `.editorconfig` |

Os pontos por alvo e as três primeiras colunas estão medidos em
[`templates/harness/README.md`](../../../templates/harness/README.md); as três últimas
são o comando idiomático de cada stack, não uma pontuação verificada.

Preencha também `lint-file` e `format-file`, que recebem `FILE=` e são o que o hook
`PostToolUse` chama depois de cada edição. Mantenha-os rápidos: eles rodam a cada
escrita do agente.

WordPress e PHP legado sem `composer.json`: o `detect_stack` acha `wp-config.php`, mas
não há sensor útil sem ferramenta instalada. Vale mais um `lint` com `php -l` em loop
do que um alvo `TODO` eterno.

## 7. Biblioteca, aplicação, CLI

As quatro árvores de `docs/` não pesam igual em todo projeto:

| Tipo | Vale preencher | Pode ficar stub |
|---|---|---|
| Biblioteca | `manual/` (a API é o produto), `decisions/` | `architecture/03-04` |
| Aplicação com usuário | `manual/`, `architecture/01-02`, `specs/` | — |
| CLI ou script interno | `manual/` curto, `decisions/` | `specs/`, `architecture/03-04` |
| Infra e automação | `decisions/`, `architecture/02` | `manual/` |

Deixar um documento como stub é uma decisão legítima; deixá-lo com o `TODO:` original é
dívida. O `docs/README.md` deste repositório tem uma seção
**Deliberadamente ausente** — copie o hábito.

## Quando algo não fecha

| Sintoma | Causa | O que fazer |
|---|---|---|
| `--check` sai `1` com `incomplete — needs sync-check:` | `Makefile` do projeto sem os alvos do harness | rode o bootstrap de novo; se o alvo existir com outro nome, é decisão sua |
| `--check` sai `1` apontando `gate-write.sh` | `settings.json` não chama os hooks | rode o bootstrap de novo; se você removeu de propósito, o hook é dívida |
| gerador sai `2` com `conflict` | arquivo à mão no caminho de uma fonte | renomeie um dos lados |
| gerador lista `foreign` para sempre | skill artesanal fora do gerador | é normal; adote com `git mv` se quiser projetá-la |
| `harness.yml` e `ci.yml` lado a lado | o projeto já tinha CI | esperado; mova os jobs para um só arquivo quando quiser |
| segunda execução acrescenta bloco de novo | marcador `harness-bootstrap` foi removido do arquivo | recoloque ou aceite a duplicata |

Mais sintomas em [`index.md`](index.md).
