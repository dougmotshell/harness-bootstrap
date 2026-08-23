# Manual — Harness Bootstrap

Para quem vai preparar um projeto novo, ou auditar um já preparado.

## Instalar

Só Python 3.12 da stdlib. Nada para instalar.

```bash
git clone <url> ~/www/harness-bootstrap
```

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
| `--holder TITULAR` | placeholder aberto | titular do copyright no `LICENSE` |
| `--year ANO` | ano corrente | ano no `LICENSE` |
| `--dry-run` | desligado | lista o que criaria, sem escrever |
| `--check` | desligado | audita; sai `1` se faltar algo |
| `--no-sync` | desligado | não roda o gerador de superfícies no fim |

## Uso no dia a dia

### Preparar um projeto novo

```bash
python3 scripts/init-project.py ../meu-projeto --dry-run   # confira o plano
python3 scripts/init-project.py ../meu-projeto
```

Resultado esperado: `35 created, 0 left untouched`, seguido de `8 written, 8 total` do
gerador, e a lista de próximos passos em ordem.

Depois, no projeto-alvo, invoque `/bootstrap-ai-harness`. Ele detecta a stack, preenche os
quatro alvos de sensor do `Makefile`, completa o `AGENTS.md` com o que o código prova, e
verifica com `npx harness-score`.

### Auditar um projeto já preparado

```bash
python3 scripts/init-project.py ../meu-projeto --check ; echo "exit=$?"
```

`exit=0` significa completo. `exit=1` lista o que falta, sob o rótulo `missing`.

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

## Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `unknown key "$comment"` do harness-score | comentário dentro de `.harness-score.json` | remova; o formato não aceita chave desconhecida |
| `--check` do gerador falha com `orphan` | fonte renomeada, saída antiga ficou | `python3 scripts/sync-ai-surfaces.py --prune` |
| Hook de gate barra um arquivo legítimo | o arquivo tem banner `managed-by:` nas 12 primeiras linhas | edite a fonte em `skills/`, `.claude/agents/` ou `.claude/rules/` e rode o gerador |
| Hook de feedback não diz nada | `format-file`/`lint-file` ainda no stub `TODO` | é o comportamento correto; preencha os alvos |
| `refusing to bootstrap this repository over itself` | alvo é o próprio repositório de templates | aponte para outro diretório |
| `make test` falha com `TODO: fill` | sensores não preenchidos | é de propósito; sensor que passa em silêncio é pior que sensor nenhum |
