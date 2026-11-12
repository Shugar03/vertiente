"""Punto de entrada.

    python -m radar run   --datos <dir> --salida <dir>     pipeline completo (un comando)
    python -m radar score --verdad <dir> --entrega <dir>   puntaje local (réplica del oficial)
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import yaml

from radar.stages import coordinacion, entrega, ingest, narrativas

log = logging.getLogger("radar")


def run(datos: Path, salida: Path, config: dict) -> dict:
    """ingest -> narrativas -> coordinación (usa las narrativas predichas) -> entrega."""
    interim = Path(config["interim_dir"]) / datos.resolve().name
    t0 = time.perf_counter()
    etapas = {"ingest": ingest.run(datos, interim, config)}
    etapas["narrativas"] = narrativas.run(interim, config)
    etapas["coordinacion"] = coordinacion.run(interim, config)
    uso_llm = etapas["narrativas"].get("llm", {"tokens": 0, "usd": 0.0})
    etapas["costo"] = entrega.run(interim, salida, config, segundos=time.perf_counter() - t0, uso_llm=uso_llm)
    (interim / "reporte.json").write_text(json.dumps(etapas, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    log.info("listo en %.1fs -> %s", time.perf_counter() - t0, salida)
    return etapas


def score(verdad: Path, entrega_dir: Path) -> dict:
    import pandas as pd

    from radar.eval.puntaje import puntuar_coordinacion, puntuar_narrativas

    leer = lambda p: pd.read_csv(p, dtype=str, keep_default_na=False).to_dict("records")  # noqa: E731
    n = puntuar_narrativas(leer(verdad / "comentarios.csv.gz"), leer(verdad / "narrativas.csv"),
                           leer(entrega_dir / "comentarios.csv"), leer(entrega_dir / "narrativas.csv"))
    c = puntuar_coordinacion(leer(verdad / "cuentas.csv.gz"), leer(entrega_dir / "cuentas.csv"))
    print(f"NARRATIVAS  B3-F1={n['bcubed_f1']:.3f} ruido={n['ruido_f1']:.3f} postura={n['postura_macro_f1']:.3f} "
          f"origen={n['origen']:.3f} -> {n['puntos']}/30")
    print(f"COORDINACIÓN P={c['precision']:.3f} R={c['recall']:.3f} F1={c['f1']:.3f} grupos={c['grupos_bcubed_f1']:.3f}"
          f" -> {c['puntos']}/25")
    print(f"TOTAL AUTOMÁTICO: {round(n['puntos'] + c['puntos'], 2)}/55")
    return {"narrativas": n, "coordinacion": c}


def main() -> None:
    ap = argparse.ArgumentParser(prog="radar")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--datos", required=True, type=Path)
    r.add_argument("--salida", required=True, type=Path)
    r.add_argument("--config", default=Path("config.yaml"), type=Path)
    s = sub.add_parser("score")
    s.add_argument("--verdad", required=True, type=Path)
    s.add_argument("--entrega", required=True, type=Path)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    if a.cmd == "run":
        run(a.datos, a.salida, yaml.safe_load(a.config.read_text(encoding="utf-8")))
    else:
        score(a.verdad, a.entrega)


if __name__ == "__main__":
    main()
