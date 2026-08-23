# SDD — Bootstrap de projetos

Preparar o harness de IA de um repositório em um comando, de forma repetível e
auditável.

| Campo | Valor |
|---|---|
| Estado | implementada |
| ADRs que a restringem | [0001](../decisions/0001-copiar-templates-em-vez-de-gerar.md), [0002](../decisions/0002-harness-score-como-metrica.md) |
| Nível C4 afetado | [02-container](../architecture/02-container.md) |

## Problema

Cada projeto novo recomeçava do zero a mesma configuração de IA. O mesmo gerador de
superfícies existia em três repositórios com três md5 diferentes — 194, 254 e 273 linhas,
docstrings em línguas distintas. Um deles versionava `__pycache__`. Ninguém sabia qual
era a versão boa, e nada media o resultado.

Custo: retrabalho por projeto, divergência silenciosa entre projetos, e nenhuma resposta
para "este repositório está bem preparado para agentes?".

## Escopo

Dentro: instalar contrato, adaptadores, fontes autoradas, `docs/` nas duas línguas,
hooks, sensores neutros, CI, pre-commit e higiene; instalar e rodar o gerador de
superfícies; auditar um projeto já semeado.

**Fora**: escolher a stack do alvo; preencher os `TODO:`; atualizar automaticamente um
projeto já semeado quando um template muda; medir qualidade de teste ou acerto de regra.

## Requisitos

| # | Requisito | Tipo | Aceitação |
|---|---|---|---|
| R1 | Nunca sobrescrever, truncar ou apagar arquivo existente | não-funcional | segunda execução reporta `0 created, 35 left untouched` |
| R2 | Idempotente | não-funcional | mesma entrada, mesma saída, sem escrita na repetição |
| R3 | Sem rede e sem dependência externa | não-funcional | só stdlib do Python 3.12 |
| R4 | Projeto resultante em L2 no harness-score | funcional | `npx harness-score` reporta `L2 · Guided 83/106` |
| R5 | Caminho até L4 aberto sem tocar nos templates | funcional | preencher 4 alvos do `Makefile` + configs + lockfile leva a `L4 106/106` |
| R6 | `docs/` com paridade entre línguas desde o primeiro commit | funcional | `diff` dos dois `find` volta vazio |
| R7 | Toda pasta sob `docs/` lowercase | funcional | `find docs -type d -name '*[A-Z]*'` volta vazio |
| R8 | Modo auditoria que falha quando falta algo | funcional | `--check` sai 1 e lista o que falta |

## Projeto

Um manifesto de `(template, destino, executável)` percorrido em ordem. Placeholders são
substituídos por chave conhecida, um a um — nunca varredura cega de `{{...}}`, porque
`${{ vars.HARNESS_MIN_LEVEL }}` é sintaxe do GitHub Actions e tem de sobreviver.

Os documentos de `docs/` são emitidos duas vezes: o esqueleto real em `pt-br/`, e um stub
com ponteiro em `en-us/`, garantindo R6 sem tradução automática.

```mermaid
sequenceDiagram
    autonumber
    participant Dev as Engenharia
    participant Init as init-project.py
    participant Tpl as templates/
    participant Tgt as Projeto-alvo
    participant Gen as sync-ai-surfaces.py

    Dev->>Init: init-project.py ../alvo
    Init->>Tgt: detecta stack pelos manifestos
    loop cada item do manifesto
        Init->>Tpl: lê template
        Init->>Init: substitui placeholders conhecidos
        alt destino existe
            Init-->>Dev: exists (não escreve)
        else
            Init->>Tgt: escreve, chmod 755 se executável
        end
    end
    Init->>Tgt: docs/pt-br esqueleto + docs/en-us stub
    Init->>Gen: invoca
    Gen->>Tgt: projeta 8 superfícies com banner
    Init-->>Dev: relatório + próximos passos em ordem
```

## Dados e contratos

- **Placeholders**: `{{PROJECT}}`, `{{YEAR}}`, `{{COPYRIGHT_HOLDER}}`, `{{AGENT_NAME}}`,
  `{{SKILL_NAME}}`, `{{RULE_NAME}}`, `{{CAPABILITY}}`, `{{DECISION_TITLE}}`, `{{TITLE}}`,
  `{{RELATIVE_PATH}}`. Placeholder remanescente é reportado, não silenciado.
- **Banner**: `<!-- managed-by:<repo>/sync-ai-surfaces — do not edit by hand -->`, na
  linha seguinte ao fechamento do frontmatter. Não na linha 1: parser de frontmatter só
  reconhece `---` na primeira linha.
- **Códigos de saída**: `0` sucesso; `1` só em `--check` com pendência.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Prompt gerando tudo do zero (desenho anterior) | produziu três implementações divergentes do mesmo contrato |
| Copiar com `cp -r` e um `sed` | não semeia exemplos, não monta as duas línguas, não é auditável, quebra o `${{ }}` do Actions |
| Template de repositório do GitHub | não funciona em repositório já existente, e não tem modo auditoria |
| `cookiecutter` / `copier` | dependência externa e uma linguagem de template a mais para manter; o manifesto aqui tem 35 entradas, não justifica |

## Plano de teste

Executado, com saída real:

- projeto novo → 35 arquivos, 44 no total após o gerador;
- segunda execução → `0 created, 35 left untouched`;
- `--dry-run` → não escreve;
- paridade `pt-br`/`en-us` → `diff` vazio;
- `find docs -type d -name '*[A-Z]*'` → vazio;
- `make sync-check` → `8 generated file(s) up to date`;
- `npx harness-score` → `L2 · Guided 83/106`;
- com sensores e lockfile preenchidos → `L4 · Self-correcting 106/106`;
- gate de escrita: 4 casos (barra superfície gerada, passa a fonte autorada, passa
  `AGENTS.md` que só menciona o banner em prosa);
- gate de bash: 14 casos, 8 bloqueios e 6 passagens.

## Questões abertas

- [ ] Como propagar mudança de template para projetos já semeados? Hoje é `--check` mais
      decisão humana.
- [ ] Vale um `--stack python|node|go` que já escreva os configs de sensor, em vez de
      deixar tudo neutro?
