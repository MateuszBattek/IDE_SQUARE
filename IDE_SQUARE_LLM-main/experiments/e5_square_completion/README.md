# E5: Square Completion Accuracy

Eksperyment badający dokładność dopełniania kwadratu opozycji z częściowych danych wejściowych.

## Scenariusze

| ID     | Scenariusz | Wejście       | Wyjście do inferowania |
| ------ | ---------- | ------------- | ---------------------- |
| **C1** | 1 corner   | Tylko A/E/I/O | 3 pozostałe rogi       |
| **C2** | 2 corners  | Para rogów    | 2 pozostałe rogi       |
| **C3** | 3 corners  | 3 rogi        | 1 brakujący róg        |

## Metryki

- **Relation Accuracy** - % poprawnie inferowanych relacji
- **Status Accuracy** - % poprawnych statusów (TRUE/FALSE/UNDETERMINED)

## Przypadki testowe

6 predefiniowanych przypadków z różnych domen:

- `order_complete` - zamówienia e-commerce
- `cancelled_not_active` - anulowane zamówienia
- `some_priority` - priorytetowe zamówienia
- `not_all_shipped` - częściowa wysyłka
- `active_verified` - konta użytkowników
- `rejected_not_approved` - dokumenty workflow

## Uruchomienie

```bash
# Pełny eksperyment
python -m experiments.e5_square_completion

# Konkretny scenariusz
python -m experiments.e5_square_completion --scenario C1

# Verbose output
python -m experiments.e5_square_completion --verbose
```

## Struktura

```
e5_square_completion/
├── __init__.py           # Eksport publiczny
├── __main__.py           # Entry point
├── main.py               # Runner eksperymentu
├── corner_scenarios.py   # Generator scenariuszy 1/2/3-corner
├── models.py             # Dataclasses wyników
└── README.md             # Dokumentacja
```

## Wyniki

Zapisywane do `experiments/output/e5_results.json`
