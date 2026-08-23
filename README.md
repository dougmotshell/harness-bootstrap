# Harness Bootstrap

Base de partida para o *harness* de IA de qualquer projeto: contrato canônico, skills e
agentes autorados uma vez e projetados em todas as CLIs, documentação em quatro árvores,
e os gates que pegam o agente no erro — hooks, sensores, CI e higiene.

Um comando prepara um projeto novo do zero até **L2 · Guided (83/106)** no
[harness-score](https://github.com/paladini/harness-score), e o caminho até
**L4 · Self-correcting (106/106)** está medido e documentado.

```bash
cd meu-projeto
curl -fsSL https://raw.githubusercontent.com/dougmotshell/harness-bootstrap/main/install.sh | sh
```

Serve igualmente a um projeto que já existe: cada arquivo declara o merge que sobrevive
ao que já está lá — o `Makefile` ganha só os alvos ausentes, o `settings.json` é
mesclado por chave, o `CLAUDE.md` ganha `@AGENTS.md` na linha 1. Nada é sobrescrito, e
`--check` afere conteúdo, não a existência do caminho.

## O que ele instala

36 arquivos, em três camadas:

| Camada | O que é | Onde |
|---|---|---|
| **Contrato** | `AGENTS.md` canônico + dois adaptadores finos que só importam (`@AGENTS.md`) | raiz, `.github/` |
| **Fontes autoradas** | agentes, skills, regras por caminho, memória, `docs/` em `pt-br` e `en-us` | `.claude/`, `skills/`, `memory/`, `docs/` |
| **Harness de execução** | 3 hooks, `Makefile` de sensores, CI, pre-commit, `.gitignore`, `LICENSE` | `.claude/hooks/`, `.github/workflows/` |

Mais `scripts/sync-ai-surfaces.py`, que projeta as fontes nas superfícies que cada CLI
lê — Claude Code, Codex, Copilot, Cursor, Gemini — e falha o CI quando alguém edita uma
saída à mão.

Depois, no projeto-alvo, o comando `/bootstrap-ai-harness` faz a parte que o script não
faz: detectar a stack, preencher os quatro alvos de sensor do `Makefile`, completar o
`AGENTS.md` com o que o código prova, e verificar com `npx harness-score`.

## Uso

| Quero… | Comando | Detalhe |
|---|---|---|
| ver o plano antes | `curl -fsSL .../install.sh \| sh -s -- . --dry-run` | [instalar e remover](docs/pt-br/manual/instalar-e-remover.md) |
| instalar | `curl -fsSL .../install.sh \| sh` | idem |
| saber se está ligado | `curl -fsSL .../install.sh \| sh -s -- . --check` | [verificar o harness](docs/pt-br/manual/verificar-harness.md) |
| medir o nível | `make harness` · `npx harness-score` | idem |
| remover | `curl -fsSL .../uninstall.sh \| sh -s -- . --dry-run` | [instalar e remover](docs/pt-br/manual/instalar-e-remover.md) |
| adaptar ao meu tipo de projeto | — | [tipos de projeto](docs/pt-br/manual/tipos-de-projeto.md) |

Com o repositório clonado, os mesmos passos saem por
`python3 scripts/init-project.py ../meu-projeto` e
`python3 scripts/uninstall-project.py ../meu-projeto`.

Não destrutivo nas duas direções: a instalação nunca sobrescreve, trunca ou apaga
conteúdo existente, e a remoção tira só o que ela mesma escreveu — bloco delimitado,
chave mesclada, linha de import. Arquivo que o projeto mudou depois fica onde está.
Projeto novo instalado e removido volta a diretório vazio; projeto que já existia volta
com cada arquivo seu igual. As duas coisas são testadas.

## Por que existe

O mesmo gerador de superfícies já existia em três projetos, com **três md5 diferentes**:
cada execução de um prompt reescrevia o script do zero. Copiar um template testado
elimina a divergência; e o que sobra para o modelo é o que ele faz bem — ler o projeto e
transformar `TODO:` em fato.

Ver [ADR 0001](docs/pt-br/decisions/0001-copiar-templates-em-vez-de-gerar.md).

## A escada

| | Pontos | Nível |
|---|---|---|
| Só documentos (contrato, skills, docs) | ~49/108 | L1 |
| `+ harness/` (hooks, CI, higiene) | **83/106** | **L2** |
| `+ sensores preenchidos e lockfile` | **106/106** | **L4** |

Hook não compra nível: **L3 exige `sensors ≥ 60%`**, e L4 só vem depois de L3. O
gargalo real são quatro alvos do `Makefile` mais o config da ferramenta — não os hooks.
Números medidos com `harness-score v1.6.3`, não estimados. Como medir:
[verificar o harness](docs/pt-br/manual/verificar-harness.md).

## Estrutura

| Caminho | O que é |
|---|---|
| `install.sh` · `uninstall.sh` | os instaladores de uma linha: baixam o tarball, rodam o script, limpam o temporário |
| `scripts/init-project.py` | o bootstrap: copia, substitui placeholders, semeia exemplos, roda o gerador |
| `scripts/uninstall-project.py` | a volta: reverte cada modo de merge pelo seu inverso |
| `templates/` | 30 templates — [manifesto](templates/README.md) |
| `templates/harness/` | hooks, sensores, CI, higiene — [detalhe e mapa dos 36 checks](templates/harness/README.md) |
| `bootstrap-ai-harness.prompt.md` | o comando que faz a parte de julgamento |
| `tests/` | 32 testes golden, stdlib, `make test` — projeto novo, projeto existente, remoção, posse do gerador |
| `docs/` | arquitetura (C4), specs (SDD), decisões (ADR) e manual, em `pt-br/` e `en-us/` |

## Testes

```bash
make test        # 32 casos, só stdlib, sem passo de instalação
make verify      # os testes e, em seguida, o placar do harness-score
make fixtures    # semeia os dois cenários em /tmp para inspecionar à mão
```

## Créditos

A régua deste repositório é o [**harness-score**](https://github.com/paladini/harness-score),
de [Fernando Paladini](https://github.com/paladini) — um scanner determinístico de
maturidade de harness: 36 checks, 108 pontos, níveis L0–L4, sem chamada de LLM e sem
rede. Os alvos `harness`, `harness-gate` e `harness-report`, o job de CI e a escada
acima existem porque ele mede; o
[guia de harness engineering](https://paladini.github.io/harness-score/) é a fonte dos
conceitos de *guides*, *sensors* e *guardrails* usados aqui. Projeto sob licença MIT,
independente deste.

## Aviso

Os hooks barram escrita de credencial, mas gate não substitui revisão: confira o diff
antes de comitar, e mantenha valor real fora do repositório — `.env.example` documenta a
forma, `.env` fica no `.gitignore`.
