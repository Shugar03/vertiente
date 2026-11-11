"""Corre la etapa real de coordinación (con narrativas PREDICHAS) y barre parámetros para ver estabilidad."""
import itertools, logging, sys, yaml
from pathlib import Path
import pandas as pd
from radar.stages import coordinacion as co
from radar.coordinacion.grafo import detectar_grupos
from radar.coordinacion.senales import respuestas_entre_cuentas, sincronias_alineadas
from radar.eval.puntaje import puntuar_coordinacion
logging.basicConfig(level=logging.WARNING)
cfg = yaml.safe_load(open("config.yaml")); I = Path("interim/practica")
v = pd.read_csv("datos/practica/verdad/cuentas.csv.gz", dtype=str, keep_default_na=False)
info = co.run(I, cfg); g = pd.read_parquet(I / "grupos.parquet"); gd = dict(zip(g.cuenta_id, g.grupo))
r = puntuar_coordinacion(v.to_dict("records"), [{"cuenta_id": a, "grupo": gd.get(a, "")} for a in v.cuenta_id])
print("CONFIG", info, {k: round(x, 3) if isinstance(x, float) else x for k, x in r.items()})
print(pd.read_parquet(I / "operaciones_meta.parquet").to_string())
if "--barrer" in sys.argv:
    con = co.conectar(I, cfg); con.execute(f"""create table cm as select c.comentario_id, c.cuenta_id, c.publicacion_id, c.ts, c.respuesta_a,
        coalesce(a.narrativa,'') narrativa, coalesce(a.postura,'') postura from '{I}/comentarios.parquet' c left join '{I}/narrativas_asig.parquet' a using(comentario_id)""")
    resp = respuestas_entre_cuentas(con, "cm")
    for W in [20, 30, 45]:
        sync = sincronias_alineadas(con, "cm", W)
        for MS, MN, D in itertools.product([2, 3, 4], [0.1, 0.15, 0.2, 0.3], [0.3]):
            gd = detectar_grupos(sync, resp, MS, MN, 5, D, 42)
            r = puntuar_coordinacion(v.to_dict("records"), [{"cuenta_id": a, "grupo": gd.get(a, "")} for a in v.cuenta_id])
            print(f"W={W} sync>={MS} norm>={MN} P={r['precision']:.3f} R={r['recall']:.3f} F1={r['f1']:.3f} grupos={r['grupos_bcubed_f1']:.3f} -> {r['puntos']}", flush=True)
