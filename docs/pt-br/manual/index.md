# Manual — Harness Bootstrap

Para quem vai preparar um projeto novo, ou auditar um já preparado. Para as
particularidades de cada caso — projeto existente, monorepo, adoção de um `.claude/`
artesanal, sensores por stack — veja
[usar em diferentes tipos de projeto](tipos-de-projeto.md).

## Instalar

Só Python 3.12 da stdlib. Nada para instalar. De dentro do projeto-alvo, sem clonar:

```bash
curl -fsSL https://raw.githubusercontent.com/dougmotshell/harness-bootstrap/main/install.sh | sh
```

Com clone, para trabalhar nos templates:

```bash
git clone <url> ~/www/harness-bootstrap
```

Detalhes das duas direções — variáveis, requisitos, e como remover o harness de volta —
em [instalar e remover](instalar-e-remover.md).

Para ter o comando de julgamento em qualquer projeto, instale o prompt no nível de
usuário e preencha o caminho do repositório dentro dele:

```bash
cp bootstrap-ai-harness.prompt.md ~/.claude/commands/bootstrap-ai-harness.md
# edite TEMPLATES_REPO para o caminho absoluto deste clone
```

## Configurar

| Opção | Padrão | O que faz |
|---|---|---|
| `--project NOME` | nome do diretório-alvo | nome que aparece nos banners e no `LICENSE` |
| `--holder TITULAR` | `git config user.name` | titular do copyright no `LICENSE` |
| `--year ANO` | ano corrente | ano no `LICENSE` |
| `--dry-run` | desligado | lista o que faria, sem escrever |
| `--check` | desligado | audita o **conteúdo**; sai `1` se algo não estiver ligado |
| `--no-sync` | desligado | não roda o gerador de superfícies no fim |

## Uso no dia a dia

### Preparar um projeto novo

```bash
python3 scripts/init-project.py ../meu-projeto --dry-run   # confira o plano
python3 scripts/init-project.py ../meu-projeto
```

Resultado esperado: `36 written or merged, 0 left untouched`, seguido de
`8 written, 8 total` do gerador, e a lista de próximos passos em ordem.

Depois, no projeto-alvo, invoque `/bootstrap-ai-harness`. Ele detecta a stack, preenche os
quatro alvos de sensor do `Makefile`, completa o `AGENTS.md` com o que o código prova, e
verifica com `npx harness-score`.

### Auditar um projeto já preparado

O placar do harness-score e o gate em CI estão em
[verificar o harness](verificar-harness.md).

```bash
python3 scripts/init-project.py ../meu-projeto --check ; echo "exit=$?"
```

`exit=0` significa ligado. `exit=1` lista cada arquivo como `missing` (não existe) ou
`incomplete — needs ...` (existe e não cumpre o que o harness precisa dele). A segunda
categoria é a que importa em projeto que já existia: hook no disco que nenhum
`settings.json` chama, `Makefile` sem `sync-check`, `CLAUDE.md` sem `@AGENTS.md`.

### Subir de L2 para L4

Nesta ordem, porque é a ordem em que os pontos aparecem:

1. quatro alvos do `Makefile` (`test`, `lint`, `typecheck`, `format`) com comando real;
2. o config que cada ferramenta exige em disco — `pytest`/`ruff`/`mypy`, ou
   `vitest`/`eslint`/`tsconfig` com `strict: true`;
3. pelo menos um arquivo de teste de verdade;
4. o lockfile comitado;
5. `pre-commit install`;
6. remover `continue-on-error: true` do job `sensors` no `ci.yml`;
7. definir a variável de repositório `HARNESS_MIN_LEVEL` (`3`, depois `4`).

### Depois de mudar um template

Um template novo **não** se propaga sozinho. Rode `--check` nos projetos já semeados e
decida caso a caso; o script nunca sobrescreve nada por conta própria.

### Rodar os testes deste repositório

```bash
make test        # 32 testes de stdlib: projeto novo, projeto existente, remoção, posse do gerador
make fixtures    # semeia os dois cenários em /tmp para inspecionar à mão
```

## Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `unknown key "$comment"` do harness-score | comentário dentro de `.harness-score.json` | remova; o formato não aceita chave desconhecida |
| `--check` do gerador falha com `orphan` | fonte renomeada, saída antiga ficou | `python3 scripts/sync-ai-surfaces.py --prune` |
| gerador imprime `foreign` | arquivo à mão sob um caminho gerado | mantido de propósito; `--prune` nunca o apaga |
| gerador sai `2` com `conflict` | arquivo à mão no caminho exato de uma fonte | renomeie um dos lados, ou `--force` |
| Hook de gate barra um arquivo legítimo | o arquivo tem banner `managed-by:` nas 12 primeiras linhas | edite a fonte em `skills/`, `.claude/agents/` ou `.claude/rules/` e rode o gerador |
| Hook de feedback não diz nada | `format-file`/`lint-file` ainda no stub `TODO` | é o comportamento correto; preencha os alvos |
| `refusing to bootstrap this repository over itself` | alvo é o próprio repositório de templates | aponte para outro diretório |
| `make test` falha com `TODO: fill` | sensores não preenchidos | é de propósito; sensor que passa em silêncio é pior que sensor nenhum |
