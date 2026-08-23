# 0003 — Merge por arquivo, em vez de pular o que já existe

| Campo | Valor |
|---|---|
| Status | accepted |
| Data | 2026-08-23 |
| Nível C4 afetado | [02-container](../architecture/02-container.md) |
| Specs que move | [bootstrap-de-projetos](../specs/bootstrap-de-projetos.md) |
| Restringido por | [0001 copiar templates](0001-copiar-templates-em-vez-de-gerar.md) |

## Contexto

A regra era: existe → pula, sem exceção. Ela protege o projeto-alvo e torna a segunda
execução um no-op, e por isso parecia suficiente.

Medindo numa fixture com `CLAUDE.md`, `Makefile`, `.gitignore`, `.claude/settings.json`
e `.github/workflows/ci.yml` próprios: **31 arquivos criados, 5 pulados** — e os cinco
pulados eram os cinco que carregam o harness.

| Pulado | Consequência |
|---|---|
| `.claude/settings.json` | os três hooks foram copiados com bit 755 e nunca são chamados |
| `CLAUDE.md` | `AGENTS.md` criado como canônico, e a CLI lendo um contrato que não o importa |
| `.gitignore` | sem `.env` nem `*.pem` — a higiene de credencial não entrou |
| `Makefile` | sem os quatro sensores e sem `sync-check`, que o CI invoca |
| `ci.yml` | sem o job anti-drift, que é a garantia que justifica o gerador existir |

Pior: `--check` respondia `0 missing`, **exit 0**. O comando que deveria dizer a verdade
aprovava um projeto em que nada estava ligado, porque comparava existência de caminho.

E o gerador tratava tudo sob `.claude/skills/`, `.claude/commands/`, `.github/prompts/`
e `.codex/` como propriedade sua: uma skill escrita à mão — no diretório canônico do
Claude Code — era rotulada `orphan` com a sugestão `use --prune`. Seguir a mensagem do
próprio programa apagava o arquivo.

## Decisão

Manter "nunca sobrescrever" como invariante e abandoná-la como **unidade de decisão**.
Cada entrada do manifesto declara o merge que o destino sobrevive: `whole`, `block`,
`make` (só os alvos ausentes), `json` (chaves, hooks casados por `command`), `import`
(`@AGENTS.md` na linha 1) e `advise` (imprime o trecho, não toca no arquivo). O workflow
vai para `harness.yml` ao lado do `ci.yml` do projeto em vez de disputar o nome.

`--check` passa a aferir conteúdo: cada entrada declara o que o destino precisa conter
para o harness estar **ligado**.

No gerador, a posse é decidida pelo banner `managed-by:`. Sem banner o arquivo é
`foreign` — nunca podado, nunca sobrescrito; fonte que projeta sobre caminho de humano
é `conflict` e sai `2` sem escrever.

## Consequências

**Boas**

- O mesmo comando serve para diretório vazio e para projeto de anos. Verificado: o
  `test:` do projeto continua rodando o recipe dele, o hook próprio sobrevive ao merge,
  a skill artesanal sobrevive a `--prune`.
- `--check` virou útil em vez de decorativo: pega hook morto, contrato órfão e sensor
  ausente.
- Idempotência real, e não por acidente de existência: marcadores de bloco entram também
  na criação, verificado em três execuções nos dois cenários.

**Ruins**

- Seis modos de merge são seis caminhos de código a manter, contra um. Mitigado pelas
  fixtures golden — que passaram a existir por causa desta decisão.
- Bloco delimitado é ruído em `.gitignore` de projeto novo: duas linhas de comentário
  que só fazem sentido na segunda execução.
- `.pre-commit-config.yaml` continua manual. Mesclar YAML às cegas quebra o arquivo, e
  um parser de YAML violaria "só stdlib".

**Neutras**

- Projeto novo recebe `ci.yml` e projeto com CI recebe `harness.yml`: o baseline medido
  em [0002](0002-harness-score-como-metrica.md) fica intacto.
- `--holder` passou a cair para `git config user.name`. Um `LICENSE` com placeholder
  literal não é licença.

## Alternativas

| Alternativa | Por que não |
|---|---|
| Sobrescrever com `.bak` | joga a reconciliação para o usuário, e um `.bak` esquecido é pior que um merge explícito |
| Só avisar e não mesclar nada | é o estado anterior com mensagem melhor: o harness continua desligado |
| Gerar patch para o usuário aplicar | trabalho manual em todo projeto, e o script perde a idempotência |
| Parser de YAML para mesclar o pre-commit | dependência externa num script cuja premissa é rodar em clone limpo |
