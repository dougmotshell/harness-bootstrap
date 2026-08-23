# 0002 — Adotar o harness-score como métrica do harness

| Campo | Valor |
|---|---|
| Status | accepted |
| Data | 2026-08-23 |
| Nível C4 afetado | [01-context](../architecture/01-context.md) |
| Specs que move | [bootstrap-de-projetos](../specs/bootstrap-de-projetos.md) |

## Contexto

O harness instalado era bom em documentação e cego em feedback. Passando o conjunto pelos
36 checks do [harness-score](https://github.com/paladini/harness-score):

| Dimensão | Pts | Antes |
|---|---|---|
| Context & Guides | 20 | 19 |
| Skills & Commands | 17 | 17 |
| Hooks & Guardrails | 14 | **0** |
| Sensors & Feedback | 20 | **0** |
| CI Feedback | 14 | **0** |
| Hygiene & Safety | 23 | ~13 |

L1, teto L2. O setup dizia ao agente como se orientar e não instalava nada que o pegasse
no erro. Sem uma métrica externa isso passa despercebido: um `AGENTS.md` bem escrito dá a
sensação de projeto bem preparado.

## Decisão

Adotar o harness-score como métrica de referência do harness, e completar os templates
até fechar as dimensões que não dependem da stack do projeto: hooks, CI, higiene e
orientação.

O CI roda em **modo relatório** por padrão e publica `harness-report.md` como artefato.
Travar é decisão do projeto-alvo, pela variável de repositório `HARNESS_MIN_LEVEL`.
Este repositório é base de partida; fixar nível aqui deixaria projetos vermelhos no dia um.

## Consequências

**Boas**

- 83/106 (L2) medido, não estimado, num projeto recém-semeado.
- Caminho até 106/106 (L4) verificado: preencher quatro alvos do `Makefile`, adicionar os
  configs de ferramenta e comitar o lockfile.
- A métrica revelou o que a intuição não revelava: **hook não compra nível**. L3 exige
  `sensors ≥ 60%` e L4 só vem depois de L3, então 14 pontos de hooks convivem com L2
  enquanto os sensores estiverem vazios. O gargalo são os sensores.

**Ruins**

- Métrica de presença convida a *gaming*. O `.mcp.json` com `mcpServers: {}` valeu 3
  pontos (`HYG-08`) e é honestamente o lugar documentado da convenção — mas a linha entre
  "declarar a convenção" e "satisfazer o check" é fina, e precisa de vigilância em
  revisão.
- Dependência de `npx` na verificação; é a única parte do fluxo que usa rede.

**Neutras**

- `.harness-score.json` desliga `HYG-05` (LICENSE) por padrão, para repositório interno
  fechado. O check sai do numerador **e** do denominador — daí o total 106 e não 108.
- O harness-score rejeita chave desconhecida no config, `$comment` incluída: a explicação
  vive em `templates/harness/README.md`, não dentro do JSON.

## Alternativas

| Alternativa | Por que não |
|---|---|
| Checklist própria | seria autorreferente: mediríamos o que já decidimos fazer |
| Nenhuma métrica | foi o estado anterior, e escondeu três dimensões em zero |
| Travar o CI em L4 desde já | projeto sem sensor preenchido fica vermelho no dia um, e o gate perde credibilidade |
