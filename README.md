# Harness Bootstrap

Base de partida para o *harness* de IA de qualquer projeto: contrato canônico, skills e
agentes autorados uma vez e projetados em todas as CLIs, documentação em quatro árvores,
e os gates que pegam o agente no erro — hooks, sensores, CI e higiene.

Um comando prepara um projeto novo do zero até **L2 · Guided (83/106)** no
[harness-score](https://github.com/paladini/harness-score), e o caminho até
**L4 · Self-correcting (106/106)** está medido e documentado.

```bash
python3 scripts/init-project.py ../meu-projeto
```

## O que ele instala

35 arquivos, em três camadas:

| Camada | O que é | Onde |
|---|---|---|
| **Contrato** | `AGENTS.md` canônico + dois adaptadores finos que só importam (`@AGENTS.md`) | raiz, `.github/` |
| **Fontes autoradas** | agentes, skills, regras por caminho, memória, `docs/` em `pt-br` e `en-us` | `.claude/`, `skills/`, `memory/`, `docs/` |
| **Harness de execução** | 3 hooks, `Makefile` de sensores, CI, pre-commit, `.gitignore`, `LICENSE` | `.claude/hooks/`, `.github/workflows/` |

Mais `scripts/sync-ai-surfaces.py`, que projeta as fontes nas superfícies que cada CLI
lê — Claude Code, Codex, Copilot, Cursor, Gemini — e falha o CI quando alguém edita uma
saída à mão.

## Por que existe

O mesmo gerador de superfícies já existia em três projetos, com **três md5 diferentes**:
cada execução de um prompt reescrevia o script do zero. Copiar um template testado
elimina a divergência; e o que sobra para o modelo é o que ele faz bem — ler o projeto e
transformar `TODO:` em fato.

Ver [ADR 0001](docs/pt-br/decisions/0001-copiar-templates-em-vez-de-gerar.md).

## Uso

```bash
python3 scripts/init-project.py ../meu-projeto --dry-run   # ver o plano
python3 scripts/init-project.py ../meu-projeto             # escrever
python3 scripts/init-project.py ../meu-projeto --check     # auditar; sai 1 se faltar algo
```

Não destrutivo sem exceção: arquivo existente é reportado como `exists` e nunca
sobrescrito. Rode duas vezes e a segunda não escreve nada.

Depois, no projeto-alvo, o comando `/bootstrap-ai-harness` faz a parte que o script não
faz: detectar a stack, preencher os quatro alvos de sensor do `Makefile`, completar o
`AGENTS.md` com o que o código prova, e verificar com `npx harness-score`.

## A escada

| | Pontos | Nível |
|---|---|---|
| Só documentos (contrato, skills, docs) | ~49/108 | L1 |
| `+ harness/` (hooks, CI, higiene) | **83/106** | **L2** |
| `+ sensores preenchidos e lockfile` | **106/106** | **L4** |

Hook não compra nível: **L3 exige `sensors ≥ 60%`**, e L4 só vem depois de L3. O
gargalo real são quatro alvos do `Makefile` mais o config da ferramenta — não os hooks.
Números medidos com `harness-score v1.6.3`, não estimados.

## Estrutura

| Caminho | O que é |
|---|---|
| `scripts/init-project.py` | o bootstrap: copia, substitui placeholders, semeia exemplos, roda o gerador |
| `templates/` | 30 templates — [manifesto](templates/README.md) |
| `templates/harness/` | hooks, sensores, CI, higiene — [detalhe e mapa dos 36 checks](templates/harness/README.md) |
| `bootstrap-ai-harness.prompt.md` | o comando que faz a parte de julgamento |
| `docs/` | arquitetura (C4), specs (SDD), decisões (ADR) e manual, em `pt-br/` e `en-us/` |

## Aviso

Os hooks barram escrita de credencial, mas gate não substitui revisão: confira o diff
antes de comitar, e mantenha valor real fora do repositório — `.env.example` documenta a
forma, `.env` fica no `.gitignore`.
