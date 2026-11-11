"""Valida el formato de una entrega antes de commitear (las trampas que hacen caer o penalizan al script oficial).

Uso: python scripts/check_entrega.py --datos datos/practica --entrega salida/practica
Sale con código 1 si hay errores.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from datetime import datetime
from pathlib import Path

RESERVADAS = {"", "ninguna", "none", "null"}
POSTURAS = {"", "apoya", "rechaza"}
COSTO_CAMPOS = {
    "comentarios_procesados", "segundos", "tokens_ia", "usd_ia",
    "usd_por_mil_comentarios", "hardware", "almacenamiento", "notas",
}


def leer_csv(path: Path) -> tuple[list[str], list[dict]]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"{path.name}: tiene BOM UTF-8 (el script oficial no reconoce la primera columna)")
    with open(path, encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames or []), list(r)


def ids_de(datos: Path, archivo: str, col: str) -> set[str]:
    p = datos / archivo
    with gzip.open(p, "rt", encoding="utf-8", newline="") as f:
        return {row[col] for row in csv.DictReader(f)}


def validar(datos: Path, entrega: Path) -> list[str]:
    err: list[str] = []

    def columnas(nombre: str, esperadas: list[str]) -> list[dict] | None:
        p = entrega / nombre
        if not p.exists():
            err.append(f"falta {nombre}")
            return None
        try:
            cols, filas = leer_csv(p)
        except ValueError as e:
            err.append(str(e))
            return None
        if not set(esperadas) <= set(cols):
            err.append(f"{nombre}: columnas {cols}, se esperaban {esperadas}")
            return None
        return filas

    com = columnas("comentarios.csv", ["comentario_id", "narrativa", "postura"])
    nar = columnas("narrativas.csv", ["narrativa", "titulo", "frases_clave", "fecha_origen"])
    cue = columnas("cuentas.csv", ["cuenta_id", "grupo"])

    etiquetas_usadas: set[str] = set()
    if com is not None:
        ids = [r["comentario_id"] for r in com]
        if len(ids) != len(set(ids)):
            err.append("comentarios.csv: ids duplicados")
        faltan = ids_de(datos, "comentarios.csv.gz", "comentario_id") - set(ids)
        if faltan:
            err.append(f"comentarios.csv: faltan {len(faltan)} comentarios (cuentan como ruido)")
        for r in com:
            n = (r["narrativa"] or "").strip()
            p = (r["postura"] or "").strip()
            if p not in POSTURAS:
                err.append(f"postura inválida {p!r} en {r['comentario_id']}")
                break
            if n.lower() in RESERVADAS:
                if p:
                    err.append(f"{r['comentario_id']}: ruido con postura {p!r}")
                    break
            else:
                etiquetas_usadas.add(n)
                if not p:
                    err.append(f"{r['comentario_id']}: narrativa sin postura")
                    break

    if nar is not None:
        definidas = set()
        for r in nar:
            definidas.add(r["narrativa"].strip())
            try:
                t = datetime.fromisoformat(r["fecha_origen"].strip())
            except ValueError:
                err.append(f"narrativas.csv: fecha_origen inválida en {r['narrativa']}")
                continue
            if t.tzinfo is None:
                err.append(f"narrativas.csv: fecha_origen SIN zona horaria en {r['narrativa']} (el script se cae)")
        sin_def = etiquetas_usadas - definidas
        if sin_def:
            err.append(f"narrativas.csv: faltan {len(sin_def)} etiquetas usadas en comentarios.csv")

    if cue is not None:
        faltan = ids_de(datos, "cuentas.csv.gz", "cuenta_id") - {r["cuenta_id"] for r in cue}
        if faltan:
            err.append(f"cuentas.csv: faltan {len(faltan)} cuentas")

    p = entrega / "costo.json"
    if not p.exists():
        err.append("falta costo.json")
    else:
        try:
            faltan = COSTO_CAMPOS - set(json.loads(p.read_text(encoding="utf-8")))
            if faltan:
                err.append(f"costo.json: faltan campos {sorted(faltan)}")
        except json.JSONDecodeError as e:
            err.append(f"costo.json inválido: {e}")
    return err


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", required=True, type=Path)
    ap.add_argument("--entrega", required=True, type=Path)
    a = ap.parse_args()
    errores = validar(a.datos, a.entrega)
    for e in errores:
        print(f"ERROR  {e}")
    print("OK: formato válido" if not errores else f"{len(errores)} error(es)")
    sys.exit(1 if errores else 0)


if __name__ == "__main__":
    main()
