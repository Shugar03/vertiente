"""E21 — Arista si (sync>=3 y norm>=a) o (sync>=2 y norm>=b): cuentas poco activas también pueden mostrar repetición."""
import yaml, pandas as pd, itertools
from pathlib import Path
from radar.stages import coordinacion as co
from radar.coordinacion import grafo
from radar.coordinacion.senales import respuestas_entre_cuentas, sincronias_alineadas
from radar.eval.puntaje import puntuar_coordinacion
cfg = yaml.safe_load(open("config.yaml")); I = Path("interim/practica")
v = pd.read_csv("datos/practica/verdad/cuentas.csv.gz", dtype=str, keep_default_na=False)
con = co.conectar(I, cfg); con.execute(f"""create table cm as select c.comentario_id, c.cuenta_id, c.publicacion_id, c.ts, c.respuesta_a,
    coalesce(a.narrativa,'') narrativa, coalesce(a.postura,'') postura from '{I}/comentarios.parquet' c left join '{I}/narrativas_asig.parquet' a using(comentario_id)""")
resp = respuestas_entre_cuentas(con, "cm")
for W in [20, 30, 45]:
    sync = sincronias_alineadas(con, "cm", W)
    for B in [0.5, 0.6, 0.8, 1.01]:
        s2 = sync[(sync.sync >= 3) & (sync.sync_n >= 0.15) | (sync.sync == 2) & (sync.sync_n >= B)]
        gd = grafo.detectar_grupos(s2, resp, 2, 0.0, 5, 0.3, 42)
        r = puntuar_coordinacion(v.to_dict("records"), [{"cuenta_id": a, "grupo": gd.get(a, "")} for a in v.cuenta_id])
        print(f"W={W} sync2_norm>={B} P={r['precision']:.3f} R={r['recall']:.3f} F1={r['f1']:.3f} grupos={r['grupos_bcubed_f1']:.3f} -> {r['puntos']}")
