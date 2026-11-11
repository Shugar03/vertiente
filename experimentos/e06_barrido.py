"""E06 — Barrido de resolución + coloreo espectral + lado por proporción de respuestas + origen robusto + ruido por grupo."""
import sys, time
from collections import Counter
from pathlib import Path
import duckdb, numpy as np, pandas as pd, torch, igraph as ig, leidenalg as la
from radar.embed import Embedder
from radar.eval.puntaje import puntuar_narrativas
from radar.texto import solo_reaccion

c0 = duckdb.sql("select * from 'interim/practica/comentarios.parquet'").df()
u0 = c0.groupby("texto_hash").agg(t=("texto_norm", "first"), traw=("texto", "first")).reset_index()
X, _ = Embedder("intfloat/multilingual-e5-small", Path("interim/cache_emb")).embeber(u0.texto_hash.tolist(), u0.t.tolist())
Xt = torch.from_numpy(X).to("mps")
vc = pd.read_csv("datos/practica/verdad/comentarios.csv.gz", dtype=str, keep_default_na=False).to_dict("records")
vn = pd.read_csv("datos/practica/verdad/narrativas.csv", dtype=str, keep_default_na=False).to_dict("records")

def knn(K):
    src, dst, w = [], [], []
    for i in range(0, len(Xt), 4096):
        S = Xt[i:i+4096] @ Xt.T
        S[torch.arange(S.shape[0]), torch.arange(i, i+S.shape[0])] = -1
        v, idx = S.topk(K, dim=1)
        src += np.repeat(np.arange(i, i+S.shape[0]), K).tolist(); dst += idx.flatten().cpu().tolist(); w += v.flatten().cpu().tolist()
    g = ig.Graph(n=len(u0), edges=list(zip(src, dst))); g.es["weight"] = w; g.simplify(combine_edges="max"); return g

def correr(g, RES, UMBRAL_RUIDO, VENT_H=3, MIN_ORIG=5, verbose=False):
    u = u0.copy(); c = c0.copy()
    u["micro"] = la.find_partition(g, la.RBConfigurationVertexPartition, weights="weight", resolution_parameter=RES, seed=42).membership
    c = c.merge(u[["texto_hash", "micro"]], on="texto_hash")
    mic = dict(zip(c.comentario_id, c.micro))
    resp = c[c.respuesta_a.notna()].copy(); resp["mp"] = resp.respuesta_a.map(mic)
    corto = c.texto_norm.str.split().str.len().fillna(0) <= 4
    disp = resp.groupby("texto_hash").mp.nunique()
    acomp = set(disp[disp >= 5].index) & set(c[corto].texto_hash)
    E = Counter()
    for a, b, h in zip(resp.micro, resp.mp, resp.texto_hash):
        if h not in acomp and a != b: E[tuple(sorted((a, b)))] += 1
    nm = u.micro.max() + 1
    gm = ig.Graph(n=nm, edges=list(E)); gm.es["weight"] = list(E.values())
    deg = np.array(gm.strength(weights="weight"))
    sin_acomp = c[~c.texto_hash.isin(acomp)]
    tam = sin_acomp.groupby("micro").size().reindex(range(nm), fill_value=0).to_numpy()
    reac = sin_acomp.assign(r=sin_acomp.texto.map(solo_reaccion)).groupby("micro").r.mean().reindex(range(nm), fill_value=1).to_numpy()
    ruido_m = (deg / np.maximum(tam, 1) < UMBRAL_RUIDO) | (reac > 0.5)
    sub = gm.induced_subgraph(np.where(~ruido_m)[0])
    ids = np.where(~ruido_m)[0]
    pm = la.find_partition(sub, la.ModularityVertexPartition, weights="weight", seed=42).membership
    narr_m = -np.ones(nm, int); narr_m[ids] = pm
    lado = np.zeros(nm, int)
    for k in set(pm):
        nodos = ids[np.array(pm) == k]
        if len(nodos) == 1: continue
        W = np.zeros((len(nodos), len(nodos))); pos = {v: i for i, v in enumerate(nodos)}
        for (a, b), w in E.items():
            if a in pos and b in pos: W[pos[a], pos[b]] = W[pos[b], pos[a]] = w
        d = W.sum(1) + 1e-9; N = W / np.sqrt(np.outer(d, d))
        vals, vecs = np.linalg.eigh(N); s = vecs[:, 0]
        lado[nodos] = (s > 0).astype(int)
    c["narr"] = c.micro.map(lambda m: narr_m[m]); c["lado"] = c.micro.map(lambda m: lado[m])
    idx = dict(zip(c.comentario_id, range(len(c)))); narr = c.narr.to_numpy().copy(); ld = c.lado.to_numpy().copy()
    th = c.texto_hash.to_numpy(); pad = c.respuesta_a.to_numpy(); es_ac = np.isin(th, list(acomp))
    heredado = np.zeros(len(c), bool)
    def res(i, p=0):
        if es_ac[i] and pad[i] is not None and p < 10:
            j = idx[pad[i]]; res(j, p+1); narr[i], ld[i] = narr[j], ld[j]; heredado[i] = True
    for i in np.where(pd.notna(pad))[0]: res(i)
    narr[es_ac & pd.isna(pad)] = -1
    c["narr"], c["lado"] = narr, ld
    nucleo = c[(c.narr >= 0) & ~heredado]
    fr = nucleo.groupby(["narr", "lado"]).respuesta_a.apply(lambda s: s.notna().mean()).reset_index()
    apoya = fr.sort_values("respuesta_a").groupby("narr").lado.first().to_dict()
    c["postura"] = [("apoya" if l == apoya.get(n) else "rechaza") if n >= 0 else "" for n, l in zip(c.narr, c.lado)]
    c["narrativa"] = [f"n{n:03d}" if n >= 0 else "" for n in c.narr]
    pred_n = []
    for n, g_ in nucleo.groupby("narr"):
        t = g_.ts.sort_values().reset_index(drop=True)
        cnt = np.searchsorted(t.values, (t + pd.Timedelta(hours=VENT_H)).values) - np.arange(len(t))
        i0 = int(np.argmax(cnt >= MIN_ORIG)) if (cnt >= MIN_ORIG).any() else 0
        pred_n.append({"narrativa": f"n{n:03d}", "fecha_origen": t[i0].tz_convert("America/Argentina/Buenos_Aires").isoformat()})
    r = puntuar_narrativas(vc, vn, c[["comentario_id", "narrativa", "postura"]].to_dict("records"), pred_n)
    print(f"RES={RES} UMB={UMBRAL_RUIDO} micro={nm} narr={len(set(pm))} bF1={r['bcubed_f1']:.3f} ruido={r['ruido_f1']:.3f} "
          f"postura={r['postura_macro_f1']:.3f} origen={r['origen']:.2f} -> {r['puntos']}", flush=True)
    return c

for K in [10]:
    g = knn(K)
    for RES in [0.5, 1, 2, 4]:
        for U in [0.01, 0.03]:
            correr(g, RES, U)
