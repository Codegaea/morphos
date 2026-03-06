---
name: Bug Report
about: Something is broken or gives wrong results
title: "[BUG] "
labels: bug
---

## Description

What is wrong.

## Category structure (for topology/analogy bugs)

- Objects:
- Morphisms (source → target, truth_degree):
- Parameters (max_dim, t_norm, etc):

## Expected vs. Actual

**Expected:**

**Actual:**

## Reproduction

```python
from engine.kernel import ReasoningStore
store = ReasoningStore(":memory:")
# ...
```

## Environment

- Python version:
- GUDHI version: `python -c "import gudhi; print(gudhi.__version__)"`
- MORPHOS commit:

## Test output

```
python -m pytest tests/ -q
```
