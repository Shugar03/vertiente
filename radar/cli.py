"""Punto de entrada: python -m radar run --datos <dir> --salida <dir>"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import yaml

from radar.stages import coordinacion, entrega, ingest, narrativas

log = logging.getLogger("radar")


def run(datos: Path, salida: Path, config: dict) -> None:
    interim = Path(config["interim_dir"]) / datos.name
    t0 = time.perf_counter()
    ingest.run(datos, interim, config)          # Fran
    # TODO(Fran): correr narrativas y coordinación en paralelo (procesos separados)
    narrativas.run(interim, config)             # Sebastián
    coordinacion.run(interim, config)           # Antony
    entrega.run(interim, salida, config, segundos=time.perf_counter() - t0)
    log.info("listo en %.1fs -> %s", time.perf_counter() - t0, salida)


def main() -> None:
    ap = argparse.ArgumentParser(prog="radar")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--datos", required=True, type=Path)
    r.add_argument("--salida", required=True, type=Path)
    r.add_argument("--config", default=Path("config.yaml"), type=Path)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    run(a.datos, a.salida, yaml.safe_load(a.config.read_text()))


if __name__ == "__main__":
    main()
