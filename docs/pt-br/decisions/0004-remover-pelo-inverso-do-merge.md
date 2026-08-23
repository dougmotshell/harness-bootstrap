# 0004 — Remover pelo inverso do merge, sem arquivo de recibo

| Campo | Valor |
|---|---|
| Status | accepted |
| Data | 2026-08-23 |
| Nível C4 afetado | [02-container](../architecture/02-container.md) |
| Specs que move | [bootstrap-de-projetos](../specs/bootstrap-de-projetos.md) |
| Restringido por | [0003 merge por arquivo](0003-merge-por-arquivo-em-projeto-existente.md) |

## Contexto

A instalação por arquivo de [0003](0003-merge-por-arquivo-em-projeto-existente.md)
tornou o bootstrap seguro em projeto que já existe — e tornou a remoção difícil pela
mesma razão. O `Makefile` do projeto ganhou alvos dentro de um bloco; o `settings.json`
dele ganhou chaves; o `CLAUDE.md` dele ganhou uma linha no topo. Um `rm` da lista de 36
destinos levaria junto os três.

Duas informações não existem no disco depois da instalação: **quais arquivos o bootstrap
criou** (em vez de encontrar) e **como o arquivo estava antes do merge**.

## Decisão

Reverter cada modo pelo seu inverso exato, e decidir posse por conteúdo, não por
caminho:

- o arquivo ainda idêntico ao template renderizado é do bootstrap — apagado;
- bloco delimitado sai inteiro; se não sobrar nada no arquivo, o arquivo sai também;
- chave JSON sai só quando o valor ainda é o do template, e hook sai casado por
  `command`, exatamente como o merge o inseriu;
- linha `@AGENTS.md` e a nota que veio com ela saem; o resto do arquivo fica;
- superfície gerada sai pelo banner `managed-by:…/sync-ai-surfaces`, nunca pelo caminho;
- o que não bate com nada disso é reportado `kept`, e só `--force` o remove.

Um guard fecha o caso ambíguo: uma reversão nunca reduz a `{}` um arquivo JSON que o
projeto possui. `{"mcpServers": {}}` era provavelmente o que o merge encontrou, e
devolver `{}` é editar configuração alheia em silêncio.

**Sem arquivo de recibo.** Um `.harness-bootstrap.json` gravando o que foi criado
resolveria as duas incógnitas de forma exata — e adicionaria um 37º arquivo ao alvo,
que precisa ser versionado, que fica obsoleto quando alguém edita à mão, e que não
existe nos projetos já semeados. O ganho seria distinguir "arquivo que eu criei e você
editou" de "arquivo que já era seu": nos dois casos a resposta correta é **não apagar**.

## Consequências

**Boas**

- Round-trip verificado nos dois cenários: projeto novo volta a diretório vazio;
  projeto que já existia volta com cada arquivo seu byte a byte igual.
- A remoção funciona em projeto semeado por qualquer versão anterior, porque não depende
  de estado gravado na instalação.
- O `--dry-run` é um plano legível: cada linha diz o verbo que será aplicado.

**Ruins**

- JSON volta igual no dado, não nos bytes: o merge da instalação reformata
  `settings.json` e `.mcp.json`, e a remoção não desfaz formatação.
- Um arquivo que o projeto editou depois fica para trás e exige decisão humana. É o
  preço de não ter recibo — e o comportamento certo mesmo com um.
- O desinstalador importa o manifesto do `init-project.py`: um modo novo lá exige o
  inverso aqui, ou o teste de round-trip falha.

**Neutras**

- `--force` existe e destrói trabalho. É a única porta destrutiva do repositório, e a
  saída padrão diz isso em voz alta.

## Alternativas

| Alternativa | Por que não |
|---|---|
| Arquivo de recibo no alvo | 37º arquivo, versionável, obsoleto ao primeiro `git revert`, e não muda a decisão nos casos ambíguos |
| `git checkout` do que o bootstrap tocou | exige repositório limpo no momento da instalação; e projeto sem git ficaria sem remoção |
| Backup `.bak` na instalação | inverte o problema: sujeira em todo projeto para servir a um comando raro |
| Não oferecer remoção | um harness que não sai é um harness que não se experimenta |
