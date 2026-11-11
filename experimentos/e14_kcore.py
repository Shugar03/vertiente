"""E14 — Núcleo (k-core) por tipo de evidencia. Hipótesis: las campañas son núcleos densos; lo genuino queda disperso."""
import numpy as np, pandas as pd, igraph as ig
exec(open("experimentos/e09_comunidades.py").read().split("LIFT =")[0])
v = pd.read_csv("datos/practica/verdad/cuentas.csv.gz", dtype=str, keep_default_na=False); camp = dict(zip(v.cuenta_id, v.campana_id))
deg = con.execute("select * from deg").df().set_index("cuenta_id").d
E["mind"] = np.minimum(deg.reindex(E.x).values, deg.reindex(E.y).values)
E["raf_n"] = E.raf / E.mind; E["ov"] = E.obs / E.mind; E["lift"] = E.obs / E.esp.clip(lower=1e-6)
def core(mask, nombre):
    F = E[mask]; nodos = pd.Index(pd.unique(F[["x", "y"]].values.ravel()))
    g = ig.Graph(n=len(nodos), edges=list(zip(nodos.get_indexer(F.x), nodos.get_indexer(F.y))))
    k = pd.Series(g.coreness(), index=nodos)
    t = pd.DataFrame({"k": k, "c": [camp.get(a, "") for a in nodos]})
    print(f"\n== {nombre}: aristas={len(F)}")
    print(t.groupby("c").k.describe(percentiles=[.5, .9, .99, .999]).round(1).to_string())
    for kk in [5, 8, 10, 15, 20]:
        sel = t[t.k >= kk]; print(f"  k>={kk}: marcadas={len(sel)} campaña={(sel.c!='').sum()}", end="")
    print()
core((E.raf >= 2) & (E.raf_n >= 0.15), "rafagas normalizadas")
core((E.lift >= 4) & (E.obs >= 3) & (E.ov >= 0.3), "co-publicacion lift")
core(E.resp >= 1, "respuestas")
core(E.txt >= 2, "textos compartidos >=2")
core(((E.raf >= 2) & (E.raf_n >= 0.15)) | ((E.lift >= 4) & (E.obs >= 3) & (E.ov >= 0.3)) | (E.resp >= 1) | (E.txt >= 2), "union")
