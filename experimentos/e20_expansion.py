"""E20 — Expansión de grupos confirmados con evidencia débil (sync>=2) hacia una fracción de miembros."""
import yaml, pandas as pd
from pathlib import Path
from radar.stages import coordinacion as co
from radar.coordinacion.grafo import detectar_grupos, expandir_grupos
from radar.coordinacion.senales import respuestas_entre_cuentas, sincronias_alineadas
from radar.eval.puntaje import puntuar_coordinacion
cfg = yaml.safe_load(open("config.yaml")); I = Path("interim/practica")
v = pd.read_csv("datos/practica/verdad/cuentas.csv.gz", dtype=str, keep_default_na=False); camp = dict(zip(v.cuenta_id, v.campana_id))
con = co.conectar(I, cfg); con.execute(f"""create table cm as select c.comentario_id, c.cuenta_id, c.publicacion_id, c.ts, c.respuesta_a,
    coalesce(a.narrativa,'') narrativa, coalesce(a.postura,'') postura from '{I}/comentarios.parquet' c left join '{I}/narrativas_asig.parquet' a using(comentario_id)""")
resp = respuestas_entre_cuentas(con, "cm")
for W in [20, 30, 45]:
    sync = sincronias_alineadas(con, "cm", W)
    base = detectar_grupos(sync, resp, 3, 0.15, 5, 0.3, 42)
    for MS, MF in [(2, 0.2), (2, 0.3), (2, 0.4), (1, 0.3), (1, 0.5)]:
        gd = expandir_grupos(base, sync, MS, MF)
        r = puntuar_coordinacion(v.to_dict("records"), [{"cuenta_id": a, "grupo": gd.get(a, "")} for a in v.cuenta_id])
        print(f"W={W} exp sync>={MS} frac>={MF} P={r['precision']:.3f} R={r['recall']:.3f} F1={r['f1']:.3f} grupos={r['grupos_bcubed_f1']:.3f} -> {r['puntos']}")
falt = [a for a in v.cuenta_id if camp[a] and a not in gd]
print("faltantes:", pd.Series([camp[a] for a in falt]).value_counts().to_dict())
