# Manual — verificar o harness

Duas perguntas diferentes, dois comandos diferentes. **Está ligado?** é o `--check` do
bootstrap. **Quanto vale?** é o [harness-score](https://github.com/paladini/harness-score),
que é a métrica que este repositório persegue — 36 checks, 108 pontos, níveis L0–L4,
determinístico e sem rede.

## 1. Está ligado? — `--check`

```bash
python3 scripts/init-project.py ../meu-projeto --check ; echo "exit=$?"
# ou, sem clone:
curl -fsSL https://raw.githubusercontent.com/dougmotshell/harness-bootstrap/main/install.sh | sh -s -- . --check
```

Audita **conteúdo**, não a existência do caminho: distingue `missing` de
`incomplete — needs …`. Hook no disco que nenhum `settings.json` chama é arquivo morto,
e é isso que essa auditoria pega. Sai `0` ligado, `1` com pendência.

## 2. Quanto vale? — harness-score

No projeto-alvo, o `Makefile` instalado já traz os alvos:

```bash
make harness                    # placar completo, com o que falta para o próximo nível
make harness-gate               # o mesmo scan como gate: falha abaixo de L3
make harness-gate MIN_LEVEL=4   # depois que os hooks de gate estiverem no lugar
make harness-report             # harness-report.md + harness-report.json
```

Direto pela CLI, sem passar pelo `make`:

```bash
npx harness-score                      # placar no terminal
npx harness-score --json               # o mesmo relatório, para script ou baseline
npx harness-score --md report.md       # markdown, para colar num PR
npx harness-score --badge badge.svg    # o selo do nível
npx harness-score --min-level 3        # gate: sai 1 se estiver abaixo
npx harness-score --diff base.json     # o que mudou desde um baseline
```

Códigos de saída: `0` passou, `1` o gate reprovou, `2` erro de uso ou scan incompleto.

Este repositório também se mede com a própria régua:

```bash
make harness      # placar deste repositório
make verify       # os testes e, em seguida, o placar
```

## 3. Em CI

O `ci.yml` instalado já tem o job `harness score`, em modo relatório. Para transformá-lo
em gate, defina a variável de repositório `HARNESS_MIN_LEVEL` — `3` quando os sensores
forem reais, `4` quando os hooks de gate estiverem no lugar. O job publica
`harness-report.md` como artefato em toda execução.

Há também a action oficial, se preferir não chamar o `npx` na mão:

```yaml
- uses: paladini/harness-score@v1
  with: { badge: 'harness-badge.svg' }
```

## 4. O que o placar não mede

O scanner é determinístico: ele verifica fatos do sistema de arquivos, não julgamento.
Ele não diz se os seus testes são bons, se as suas regras ainda são verdadeiras, nem se
o código funciona. Nota alta significa que a **infraestrutura** para trabalho confiável
existe — necessária, não suficiente. O
[modelo de maturidade](https://paladini.github.io/harness-score/guide/maturity-model)
explica cada limiar.

## A escada, medida

| | Pontos | Nível |
|---|---|---|
| Só documentos (contrato, skills, docs) | ~49/108 | L1 |
| `+ harness/` (hooks, CI, higiene) | **83/106** | **L2** |
| `+ sensores preenchidos e lockfile` | **106/106** | **L4** |

Hook não compra nível: **L3 exige `sensors ≥ 60%`**, e L4 só vem depois de L3. O gargalo
real são quatro alvos do `Makefile` mais o config da ferramenta. Números medidos com
`harness-score v1.6.3`, não estimados. Ver
[ADR 0002](../decisions/0002-harness-score-como-metrica.md).
