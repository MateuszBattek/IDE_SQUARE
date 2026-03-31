# E2: Baseline vs Square-Bot Comparison

Eksperyment porównujący trzy podejścia do generowania maszyn stanowych z wymagań NL.

## Podejścia

| ID | Nazwa | Opis |
|----|-------|------|
| **B1** | Single-LLM | Jeden prompt do LLM, bez walidacji |
| **B2** | Manual Square | Czyste heurystyki + reguły Square (bez LLM) |
| **S** | Square-Bot | Pełny pipeline MAS-LLM z agentami |

## Metryki

- **F1 States** - dopasowanie stanów do referencyjnych
- **Disjointness %** - procent przejść testów rozłączności
- **Iterations** - liczba iteracji do stabilnego modelu

## Uruchomienie

```bash
source .env.template  # załaduj OPENAI_API_KEY
python -m experiments.e2_baseline_comparison
```

## Struktura

```
e2_baseline_comparison/
├── approaches.py    # B1, B2, S implementacje
├── disjointness.py  # weryfikacja rozłączności
├── heuristics.py    # STATE_KEYWORDS, LIFECYCLE_ORDER
├── main.py          # runner eksperymentu
└── models.py        # dataclasses wyników
```

## Wyniki

Zapisywane do `experiments/output/e2_results.json`
