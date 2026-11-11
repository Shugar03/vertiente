"""Junta los contratos y escribe la entrega oficial: comentarios.csv, narrativas.csv, cuentas.csv y costo.json.

Garantías (las trampas del script oficial, ver docs/EVALUACION.md):
- UTF-8 sin BOM; CSV escrito con el módulo csv (títulos con comas, frases con '|').
- Todos los comentarios y todas las cuentas (las ausentes contarían como ruido / genuinas).
- fecha_origen ISO con zona horaria -03:00.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path

import pandas as pd

TZ = "America/Argentina/Buenos_Aires"


def hardware() -> str:
    try:
        cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True,
                             timeout=2).stdout.strip()
        ram = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=2).stdout) / 2**30
        return f"{cpu}, {ram:.0f} GB RAM, {os.cpu_count()} núcleos, {platform.system()}"
    except (OSError, ValueError, subprocess.SubprocessError):
        return f"{platform.processor() or platform.machine()}, {os.cpu_count()} núcleos, {platform.system()}"


def _csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8")


def run(interim: Path, salida: Path, config: dict, segundos: float, uso_llm: dict | None = None) -> dict:
    salida.mkdir(parents=True, exist_ok=True)
    uso_llm = uso_llm or {"tokens": 0, "usd": 0.0}

    com = pd.read_parquet(interim / "comentarios.parquet", columns=["comentario_id"])
    asig = pd.read_parquet(interim / "narrativas_asig.parquet", columns=["comentario_id", "narrativa", "postura"])
    com = com.merge(asig, on="comentario_id", how="left").fillna({"narrativa": "", "postura": ""})
    _csv(com[["comentario_id", "narrativa", "postura"]], salida / "comentarios.csv")

    meta = pd.read_parquet(interim / "narrativas_meta.parquet")
    meta["fecha_origen"] = pd.to_datetime(meta["fecha_origen"], utc=True).dt.tz_convert(TZ) \
        .map(lambda t: t.isoformat(timespec="seconds"))
    _csv(meta[["narrativa", "titulo", "frases_clave", "fecha_origen"]], salida / "narrativas.csv")

    cuentas = pd.read_parquet(interim / "cuentas.parquet", columns=["cuenta_id"])
    grupos = pd.read_parquet(interim / "grupos.parquet")
    cuentas = cuentas.merge(grupos, on="cuenta_id", how="left").fillna({"grupo": ""})
    _csv(cuentas[["cuenta_id", "grupo"]], salida / "cuentas.csv")

    n = len(com)
    costo = {
        "comentarios_procesados": n,
        "segundos": round(segundos, 1),
        "tokens_ia": int(uso_llm["tokens"]),
        "usd_ia": round(float(uso_llm["usd"]), 6),
        "usd_por_mil_comentarios": round(float(uso_llm["usd"]) / n * 1000, 6) if n else 0.0,
        "hardware": hardware(),
        "almacenamiento": "DuckDB (en proceso) sobre Parquet local; caché de embeddings por hash de texto",
        "notas": ("embeddings locales (multilingual-e5-small) solo sobre textos únicos; narrativas por grafo de "
                  "similitud + respuestas; coordinación por sincronía alineada repetida en SQL. "
                  + ("LLM solo como profesor (elección de postura y títulos), con caché."
                     if uso_llm["tokens"] else "Sin LLM: todas las decisiones son locales.")),
    }
    (salida / "costo.json").write_text(json.dumps(costo, ensure_ascii=False, indent=2), encoding="utf-8")
    return costo
