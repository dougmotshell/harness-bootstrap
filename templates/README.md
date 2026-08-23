# templates/

Esqueletos que `/basic-ai-directory-setup` copia para o projeto-alvo, em vez de
reescrever tudo do zero a cada execução. Reescrever era a origem da divergência: o
mesmo gerador já existia em três projetos, com três md5 diferentes.

Todo `.tpl` é inerte de propósito — a extensão evita que `templates/AGENTS.md` seja
carregado como contrato aninhado por Codex ou Claude Code ao trabalhar nesta pasta.

## Mapa

| Template | Destino no projeto | Tipo |
|---|---|---|
| `sync-ai-surfaces.py` | `scripts/sync-ai-surfaces.py` | executável, copiar como está |
| `contract/agents.md.tpl` | `AGENTS.md` | autorado |
| `contract/claude.md.tpl` | `CLAUDE.md` | autorado (adaptador fino) |
| `contract/copilot-instructions.md.tpl` | `.github/copilot-instructions.md` | autorado (adaptador fino) |
| `authored/agent.md.tpl` | `.claude/agents/<n>.md` | autorado |
| `authored/skill.md.tpl` | `skills/<n>/SKILL.md` | autorado |
| `authored/rule.md.tpl` | `.claude/rules/<n>.md` | autorado |
| `authored/memory.md.tpl` | `memory/MEMORY.md` | autorado |
| `docs/readme.md.tpl` | `docs/README.md` | autorado |
| `docs/architecture/01-context.md.tpl` | `docs/<lang>/architecture/01-context.md` | autorado (C4) |
| `docs/architecture/02-container.md.tpl` | `docs/<lang>/architecture/02-container.md` | autorado (C4) |
| `docs/architecture/03-component.md.tpl` | `docs/<lang>/architecture/03-component.md` | autorado (C4) |
| `docs/architecture/04-code.md.tpl` | `docs/<lang>/architecture/04-code.md` | autorado (C4, opcional) |
| `docs/specs/spec.md.tpl` | `docs/<lang>/specs/<capacidade>.md` | autorado (SDD) |
| `docs/decisions/0000-adr.md.tpl` | `docs/<lang>/decisions/NNNN-kebab-title.md` | autorado (ADR/MADR) |
| `docs/manual/index.md.tpl` | `docs/<lang>/manual/index.md` | autorado (só com usuário final) |
| `docs/translation-stub.md.tpl` | qualquer arquivo ainda não traduzido | autorado |

Harness de execução — hooks, sensores, CI e higiene — em [`harness/`](harness/README.md):
`settings.json.tpl`, `hooks/gate-write.sh`, `hooks/gate-bash.sh`,
`hooks/feedback-edit.sh`, `makefile.tpl`, `ci.yml.tpl`,
`pre-commit-config.yaml.tpl`, `gitignore.tpl`, `env.example.tpl`,
`harness-score.json.tpl`, `mcp.json.tpl`, `license-mit.tpl` e `readme.md.tpl`.

`<lang>` é sempre lowercase: `pt-br`, `en-us`.

## Placeholders

Substitua ao copiar; nenhum pode sobreviver no projeto:

| Placeholder | Vira |
|---|---|
| `{{PROJECT}}` | nome do repositório |
| `{{AGENT_NAME}}`, `{{SKILL_NAME}}`, `{{RULE_NAME}}` | nome do artefato (kebab-case) |
| `{{CAPABILITY}}`, `{{DECISION_TITLE}}`, `{{TITLE}}` | título do documento |
| `{{RELATIVE_PATH}}` | caminho do arquivo pt-br correspondente |
| `{{YEAR}}`, `{{COPYRIGHT_HOLDER}}` | ano e titular no `LICENSE` |

O `sync-ai-surfaces.py` é a exceção: ele deriva o nome do projeto do diretório raiz,
então copia sem edição.

## Uso

```bash
cp templates/sync-ai-surfaces.py <projeto>/scripts/sync-ai-surfaces.py
chmod +x <projeto>/scripts/sync-ai-surfaces.py
sed 's/{{PROJECT}}/meu-projeto/g' templates/contract/agents.md.tpl > <projeto>/AGENTS.md
```

Depois: `python3 scripts/sync-ai-surfaces.py` para gerar as superfícies, e
`--check` no CI para falhar quando alguém editar uma saída à mão.

## Limites que os templates respeitam

- `AGENTS.md` + `CLAUDE.md` somados abaixo de 200 linhas (hoje 56 + 26 = 82).
- `AGENTS.md` abaixo de 32 KiB.
- `SKILL.md` abaixo de 5.000 palavras.
- `memory/MEMORY.md` abaixo de 200 linhas.

## Harness-score

Só os documentos levam o projeto a **L1 (~49/108)**. Com `harness/` aplicado vai a
**L2 (~82/108)**, e a **L4 (~108/108)** quando os quatro alvos de sensor do `Makefile`
tiverem ferramenta real configurada. Detalhe e mapa dos 36 checks em
[`harness/README.md`](harness/README.md).

## Aviso

Nenhum template carrega segredo, token, hostname real ou dado pessoal — e não deve passar
a carregar. Valor real vive em `.env`, que é ignorado; a forma vive em `.env.example`.
