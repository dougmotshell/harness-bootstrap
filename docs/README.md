# Documentação — Harness Bootstrap

Índice. Todo documento mora em uma das quatro árvores abaixo, dentro da subárvore da sua
língua. Nunca solto na raiz, nunca dois padrões no mesmo arquivo.

Toda pasta sob `docs/` é lowercase, inclusive a da língua. pt-BR é a fonte da verdade; o
irmão en-US abre com um ponteiro para ele.

| Árvore | Padrão | Conteúdo |
|---|---|---|
| [`architecture/`](pt-br/architecture/) | C4 | [contexto](pt-br/architecture/01-context.md) · [containers](pt-br/architecture/02-container.md) |
| [`specs/`](pt-br/specs/) | SDD | [bootstrap de projetos](pt-br/specs/bootstrap-de-projetos.md) |
| [`decisions/`](pt-br/decisions/) | ADR (MADR) | [0001 copiar templates](pt-br/decisions/0001-copiar-templates-em-vez-de-gerar.md) · [0002 harness-score](pt-br/decisions/0002-harness-score-como-metrica.md) · [0003 merge por arquivo](pt-br/decisions/0003-merge-por-arquivo-em-projeto-existente.md) |
| [`manual/`](pt-br/manual/) | manual do usuário | [uso no dia a dia](pt-br/manual/index.md) · [tipos de projeto](pt-br/manual/tipos-de-projeto.md) |

## Deliberadamente ausente

- **C4 nível 3 e 4 (componentes e código).** Dois scripts de ~260 linhas cada, sem
  estado compartilhado. O nível 2 já mostra tudo; abrir a tampa seria narrar código.
- **Spec por template.** Os 32 templates são dados, não capacidades. O contrato de cada
  um está no manifesto de `templates/`.

## Regras

- Diagrama é texto: Mermaid cercado no Markdown.
- Cada documento C4 fica no seu nível.
- ADR é append-only: superado por um novo (`Status: superseded by NNNN`), nunca
  reescrito; número nunca é reusado.
- Ligação nos dois sentidos: spec nomeia os ADRs que a restringem, ADR nomeia o nível C4
  e as specs que move.
