"""CSV.gz -> Parquet (DuckDB): limpieza, zona -03:00, texto_norm, texto_hash, dedup.

Dueño: Fran. Contratos de entrada/salida: ver docs/PLAN.md.
"""

from __future__ import annotations

from pathlib import Path


def run(datos: Path, interim: Path, config: dict) -> None:
    raise NotImplementedError("ingest: pendiente (Fran)")
