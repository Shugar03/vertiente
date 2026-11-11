"""E23 — Selección robusta del detector de grupos: se optimiza el PROMEDIO (y el peor caso) sobre variantes de estrés.
Variantes: completo, submuestra75, primera_mitad, sin_colectivo, sin_hospital, solo_colectivo (trampa: sin campaña propia)."""
import itertools, sys, yaml
from pathlib import Path
import numpy as np, pandas as pd, igraph as ig, leidenalg as la
from radar.stages import coordinacion as co
from radar.coordinacion.senales import respuestas_entre_cuentas, sincronias_alineadas
from radar.eval.puntaje import puntuar_coordinacion
cfg = yaml.safe_load(open("config.yaml")); B = Path("salida/validacion")
VARS = ["completo", "submuestra75", "primera_mitad", "sin_colectivo", "sin_hospital", "solo_colectivo"]
datos = {}
for v in VARS:
    I = B / "interim" / v
    con = co.conectar(I, cfg); con.execute(f"""create table cm as select c.comentario_id, c.cuenta_id, c.publicacion_id, c.ts, c.respuesta_a,
        coalesce(a.narrativa,'') narrativa, coalesce(a.postura,'') postura from '{I}/comentarios.parquet' c left join '{I}/narrativas_asig.parquet' a using(comentario_id)""")
    verdad = pd.read_csv(B / "datos" / v / "verdad" / "cuentas.csv.gz", dtype=str, keep_default_na=False)
    datos[v] = {W: sincronias_alineadas(con, "cm", W) for W in [20, 30, 45]}, respuestas_entre_cuentas(con, "cm"), verdad

def grupos(sync, resp, MS, MN, metodo, G):
    e = sync[(sync.sync >= MS) & (sync.sync_n >= MN)]
    if e.empty: return {}
    e = e.merge(resp, on=["x", "y"], how="left").fillna({"resp": 0})
    nod = pd.Index(pd.unique(e[["x", "y"]].values.ravel()))
    g = ig.Graph(n=len(nod), edges=list(zip(nod.get_indexer(e.x), nod.get_indexer(e.y))))
    if metodo == "cpm":
        m = np.asarray(la.find_partition(g, la.CPMVertexPartition, resolution_parameter=G, seed=42).membership)
    else:
        m = np.asarray(la.find_partition(g, la.ModularityVertexPartition, seed=42).membership)
    out = {}
    for k in np.unique(m):
        idx = np.flatnonzero(m == k)
        if len(idx) >= 5 and g.induced_subgraph(idx).density() >= (G if metodo == "cpm" else 0.3):
            for i in idx: out[nod[i]] = f"g{k}"
    return out

res = []
for W, MS, MN, (met, G) in itertools.product([20, 30, 45], [2, 3], [0.1, 0.15, 0.2, 0.3],
                                              [("mod", 0.3), ("cpm", 0.2), ("cpm", 0.3), ("cpm", 0.4)]):
    pts = {}
    for v, (syncs, resp, verdad) in datos.items():
        gd = grupos(syncs[W], resp, MS, MN, met, G)
        pts[v] = puntuar_coordinacion(verdad.to_dict("records"), [{"cuenta_id": a, "grupo": gd.get(a, "")} for a in verdad.cuenta_id])["puntos"]
    res.append(dict(W=W, MS=MS, MN=MN, met=met, G=G, media=np.mean(list(pts.values())), peor=min(pts.values()), **pts))
R = pd.DataFrame(res).sort_values("media", ascending=False)
pd.set_option("display.width", 250); print(R.head(25).round(2).to_string(index=False))
R.to_csv("salida/validacion/e23.csv", index=False)
