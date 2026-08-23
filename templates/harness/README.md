# templates/harness/

O que o `basic-ai-directory-setup` **não** criava: hooks, sensores, CI e higiene.
Medido contra o [harness-score](https://github.com/paladini/harness-score) — 36 checks
determinísticos, 108 pontos, escada L0→L4, `npx harness-score`.

Os documentos (contrato, skills, agentes, docs) estão em `../contract/`, `../authored/`
e `../docs/`. Aqui fica o feedback: o que pega o agente no erro.

## Mapa

| Template | Destino | Checks |
|---|---|---|
| `settings.json.tpl` | `.claude/settings.json` | `HKS-01`, `HKS-02` |
| `hooks/gate-write.sh` | `.claude/hooks/gate-write.sh` | `HKS-03`, `HKS-05` |
| `hooks/gate-bash.sh` | `.claude/hooks/gate-bash.sh` | `HKS-03`, `HKS-05` |
| `hooks/feedback-edit.sh` | `.claude/hooks/feedback-edit.sh` | `HKS-04`, `HKS-05` |
| `makefile.tpl` | `Makefile` | interface neutra dos sensores |
| `ci.yml.tpl` | `.github/workflows/ci.yml` | `CI-01`, `CI-02`, `CI-03` |
| `pre-commit-config.yaml.tpl` | `.pre-commit-config.yaml` | `CI-04` |
| `gitignore.tpl` | `.gitignore` | `HYG-01`, `HYG-02` |
| `env.example.tpl` | `.env.example` | `HYG-03` |
| `harness-score.json.tpl` | `.harness-score.json` | exclusões declaradas (JSON sem comentário: o harness-score rejeita chave desconhecida, inclusive `$comment`) |
| `mcp.json.tpl` | `.mcp.json` | `HYG-04`, `HYG-08` |
| `license-mit.tpl` | `LICENSE` | `HYG-05` |
| `readme.md.tpl` | `README.md` | `CTX-07` |

## O que os hooks fazem

`gate-write.sh` (`PreToolUse`) barra, com `permissionDecision: deny`:

- escrita em arquivo cujo topo tem o banner `managed-by:` — a mensagem manda editar a
  fonte e rodar o gerador;
- `.env` e `.env.*` reais (`.env.example` e `.env.template` passam);
- qualquer caminho dentro de `.git/`;
- conteúdo com cara de credencial: valor opaco de 16+ caracteres atribuído a nome
  `api_key`/`secret`/`token`/`password`, cabeçalho de chave privada, `AKIA…`, `ghp_…`.

`gate-bash.sh` (`PreToolUse`) barra `rm -rf` em raiz/home/glob, `git push --force`,
`git reset --hard`, `filter-branch`, `rebase -i`, `curl | sh` e `chmod 777`. Passa
`rm -rf build/`, `git push` normal, `git reset --soft`, `chmod 755`.

`feedback-edit.sh` (`PostToolUse`) roda `make format-file` e `make lint-file` só no
arquivo editado e devolve a saída como `additionalContext`. Enquanto o alvo estiver no
stub `TODO`, o hook fica **em silêncio** — sensor vazio não vira ruído a cada edição.

Nenhum hook sai com código diferente de zero por erro próprio: gate quebrado não pode
travar a sessão.

## Sensores: preencher 4 alvos

O `Makefile` é a interface neutra — CI, pre-commit e o hook chamam alvos, não
ferramentas. Um alvo `TODO` **falha de propósito**: sensor que passa em silêncio é pior
que sensor nenhum.

| Alvo | Check | Python | Node/TS | Go |
|---|---|---|---|---|
| `test` | `SNS-01`, `SNS-05` (11 pts) | `pytest` | `vitest run` | `go test ./...` |
| `lint` | `SNS-02` (5 pts) | `ruff check .` | `eslint .` | `golangci-lint run` |
| `typecheck` | `SNS-03` (4 pts) | `mypy --strict .` | `tsc --noEmit` | nativo |
| `format` | `SNS-04` (3 pts) | `ruff format .` | `prettier -w .` | `gofmt -w .` |

O check exige o **config da ferramenta** no repositório, não só o alvo do Makefile:
`pyproject.toml`/`ruff.toml`/`mypy.ini`, ou `eslint.config.js`/`tsconfig.json` com
`strict: true`. Sem config, o alvo roda e o check não pontua.

## Onde isto chega

| Dimensão | Pts | Só documentos | Com harness, sensores vazios | Sensores preenchidos |
|---|---|---|---|---|
| Context & Guides | 20 | 19 | **20** | 20 |
| Skills & Commands | 17 | 17 | 17 | 17 |
| Hooks & Guardrails | 14 | 0 | **14** | 14 |
| Sensors & Feedback | 20 | 0 | 0 | **20** |
| CI Feedback | 14 | 0 | **~11** | **14** |
| Hygiene & Safety | 23 | ~13 | **20** | **23** |
| Total | 108 | ~49 | **~82** | **~108** |
| Nível | | L1 | **L2** | **L4** |

Atenção à escada: hook não compra nível. **L3 exige `sensors ≥ 60%` e `ci ≥ 50%`**, e
L4 só vem depois de L3. Com os sensores vazios o projeto fica em L2 apesar dos 14
pontos de hooks. Os quatro alvos do Makefile são o gargalo real — não os hooks.

## Gate no CI

O workflow roda em modo relatório e publica `harness-report.md` como artefato. Para
travar, defina a variável de repositório `HARNESS_MIN_LEVEL`: `3` quando os sensores
forem reais, `4` quando os hooks estiverem em uso. Códigos de saída do harness-score:
`0` passou, `1` gate falhou, `2` erro.

O job `surfaces` (`make sync-check`) é o único gate duro desde o dia um: não depende de
código do projeto, então nunca fica vermelho legitimamente.

## Exclusões

`.harness-score.json` desliga check no estilo ESLint. O check sai do numerador **e** do
denominador — nada é escondido nem penalizado. O template desliga só `HYG-05` (LICENSE),
para repositório interno fechado; se o projeto tem `LICENSE`, apague a linha. Os três
checks que detectam credencial viva não podem ser desligados.

## Placeholders

`{{PROJECT}}`, `{{YEAR}}`, `{{COPYRIGHT_HOLDER}}`. **Não** faça substituição cega de
`{{...}}` em `ci.yml.tpl`: `${{ vars.HARNESS_MIN_LEVEL }}` é sintaxe do GitHub Actions e
tem de sobreviver.

## Aviso

Gate não substitui revisão. `gate-write.sh` pega o formato óbvio de credencial — valor
opaco atribuído a nome suspeito, cabeçalho de chave privada, `AKIA…`, `ghp_…` — e nada
além disso. Leia o diff antes de comitar.
