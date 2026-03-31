# E4: Algorithm Ablation Study

Eksperyment badający wpływ poszczególnych komponentów systemu MAS-LLM na jakość generowanych maszyn stanowych.

## Warianty ablacyjne

| ID     | Nazwa       | Opis                              |
| ------ | ----------- | --------------------------------- |
| **V1** | Full System | Pełny pipeline (baseline)         |
| **V2** | No Prover   | Bez weryfikacji Z3                |
| **V3** | No Verifier | Bez sprawdzania spójności         |
| **V4** | No Square   | Bez dopełniania kwadratu opozycji |

## Metryki

- **F1 States** - dopasowanie stanów do referencyjnych
- **Contradictions** - liczba wykrytych sprzeczności
- **Models Rejected** - liczba odrzuconych modeli
- **Stability** - wariancja F1 między uruchomieniami (próg ≤ 0.05)

## Uruchomienie

```bash
# Pełny eksperyment
python -m experiments.e4_algorithm_ablation

# Pojedynczy model
python -m experiments.e4_algorithm_ablation --model order_lifecycle

# Z testem stabilności (3 uruchomienia per wariant)
python -m experiments.e4_algorithm_ablation --stability
```

## Struktura

```
e4_algorithm_ablation/
├── __init__.py      # Eksport publiczny
├── __main__.py      # Entry point
├── main.py          # Runner eksperymentu
├── variants.py      # Implementacje V1-V4
├── models.py        # Dataclasses wyników
└── README.md        # Dokumentacja
```

## Wyniki

Zapisywane do `experiments/output/e4_results.json`
