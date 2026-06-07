# Data Model Specification: Ledger Detail Edit & Delete Modal (CRUD)

## Entity Relationship Diagram (ERD)

```text
[User] 1 <------- 0..N [Ledger] 1 <------- 0..N [LedgerItem]
                         (with category)         (CASCADE on Delete)
```

## Schema Changes

### 1. `Ledger` Model (`apps.ledgers.models.Ledger`)

We will add a `category` column to categorize transactions.

```python
class Ledger(models.Model):
    # ... existing fields ...
    category = models.CharField(max_length=100, default="미분류", db_index=True)
    # ...
```

* **Attributes**:
  - `category`: `models.CharField(max_length=100, default="미분류")`
  - Indexed for future statistic query optimizations.
* **Migration Strategy**:
  - Generate a new migration file via Django `makemigrations` and apply it via `migrate`.
  - Existing database rows will be populated with the default value `"미분류"`.

### 2. `LedgerItem` Model (`apps.ledgers.models.LedgerItem`)

No schema updates are required for `LedgerItem`.
* **Behavior Validation**:
  - The foreign key relationship `ledger = models.ForeignKey(Ledger, on_delete=models.CASCADE, related_name="items")` automatically handles deletion.
  - When a `Ledger` row is deleted via the API, all corresponding `LedgerItem` rows are purged atomically by the RDBMS engine.
