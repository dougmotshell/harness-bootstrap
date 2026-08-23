# 0001 — Copiar templates testados em vez de gerar código a cada execução

| Campo | Valor |
|---|---|
| Status | accepted |
| Data | 2026-08-23 |
| Nível C4 afetado | [02-container](../architecture/02-container.md) |
| Specs que move | [bootstrap-de-projetos](../specs/bootstrap-de-projetos.md) |

## Contexto

O desenho anterior era um único prompt de 173 linhas que instruía o agente a **escrever**
`scripts/sync-ai-surfaces.py` do zero dentro do projeto-alvo, prevendo até a falha: se
não conseguisse, deveria deixar um stub que sai com código diferente de zero.

O resultado observado em três repositórios:

| Projeto | Linhas | md5 |
|---|---|---|
| `product-kpi-live-4-migration` | 194 | `661d0646…` |
| `voice-clone` | 254 | `b566e6fe…` |
| `cli-voice-bridge` | 273 | `68023e80…` |

Três md5, três docstrings, duas línguas de comentário, e um deles versionando
`__pycache__`. O `voice-clone` era subconjunto estrito do `cli-voice-bridge`; o de
`product-kpi-live-4-migration` usava `mode:` no frontmatter do Copilot — chave depreciada que a própria checklist do
prompt mandava sinalizar.

Um contrato descrito em prosa e reimplementado a cada execução divergirá sempre. Não é
falha do modelo: é o que "reescreva isto do zero" significa.

## Decisão

O contrato passa a ser **código versionado**, não prosa. `templates/` guarda a
implementação de referência; `scripts/init-project.py` copia e substitui placeholders de
forma determinística; e o prompt fica com o que só um modelo faz — ler o projeto, detectar
a stack, ligar os sensores e transformar `TODO:` em fato.

A divisão é uma linha só: **determinístico vira script, julgamento vira prompt.**

## Consequências

**Boas**

- Uma implementação, um md5. Divergência entre projetos deixa de ser possível.
- O script é testável fora de um agente: 14 casos no gate de bash, 4 no de escrita,
  idempotência verificada.
- O prompt caiu de 173 para 112 linhas e ficou mais afiado, porque parou de descrever o
  que a máquina faz melhor.
- Modo auditoria (`--check`) sai de graça: comparar manifesto com disco é trivial.

**Ruins**

- Aparece um passo de manutenção que não existia: template que muda não se propaga para
  projetos já semeados. Hoje isso é `--check` mais decisão humana, e é a principal
  questão aberta da spec.
- O repositório de templates passa a ser dependência de bootstrap dos outros. O prompt
  precisa do caminho absoluto dele na máquina.

**Neutras**

- Placeholders exigem cuidado: `${{ vars.… }}` do GitHub Actions tem de sobreviver, então
  a substituição é por chave conhecida e nunca varredura de `{{...}}`.

## Alternativas

| Alternativa | Por que não |
|---|---|
| Manter a geração e só apertar a especificação no prompt | já era detalhada; a divergência veio da reimplementação, não de ambiguidade |
| `cookiecutter` / `copier` | dependência externa e uma linguagem de template a mais para 35 entradas de manifesto |
| Template repository do GitHub | não serve para repositório existente nem tem modo auditoria |
