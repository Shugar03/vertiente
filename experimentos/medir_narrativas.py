"""Corre la etapa de narrativas real sobre interim/<set> y puntúa con la réplica oficial."""
import logging, sys, yaml
from pathlib import Path
import pandas as pd
from radar.stages import narrativas
from radar.eval.puntaje import puntuar_narrativas
logging.basicConfig(level=logging.WARNING)
cfg = yaml.safe_load(open("config.yaml"))
for kv in sys.argv[1:]:
    k, v = kv.split("="); cfg["narrativas"][k] = type(cfg["narrativas"][k])(v)
I = Path("interim/practica")
info = narrativas.run(I, cfg)
a = pd.read_parquet(I / "narrativas_asig.parquet"); m = pd.read_parquet(I / "narrativas_meta.parquet")
m["fecha_origen"] = m.fecha_origen.map(lambda t: t.isoformat())
vc = pd.read_csv("datos/practica/verdad/comentarios.csv.gz", dtype=str, keep_default_na=False).to_dict("records")
vn = pd.read_csv("datos/practica/verdad/narrativas.csv", dtype=str, keep_default_na=False).to_dict("records")
r = puntuar_narrativas(vc, vn, a.to_dict("records"), m.to_dict("records"))
print(info["segundos"], "s", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
print(m[["narrativa", "titulo", "frases_clave", "fecha_origen", "apoya", "rechaza"]].to_string(max_colwidth=60))
