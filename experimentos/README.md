# Experimentos

Cada archivo `eNN_*.py` prueba una hipótesis: la pregunta está en su docstring y el resultado y la decisión en
[docs/VALIDACION.md](../docs/VALIDACION.md#bitácora-de-hipótesis-experimentos). Se corren desde la raíz con
`PYTHONPATH=. uv run python experimentos/<archivo>` después de `make run` (usan `interim/practica`). Algunos usan la
verdad del set de práctica solo para medir; el pipeline (`radar/`) nunca la lee.
