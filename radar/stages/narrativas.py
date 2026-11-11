"""Etapa de narrativas.

Entrada: interim/<set>/comentarios.parquet.
Salida:  narrativas_asig.parquet (comentario_id, narrativa, postura, micro, heredado)
         narrativas_meta.parquet (narrativa, titulo, frases_clave, fecha_origen, apoya, rechaza, total)

Método (ver docs/PLAN.md y experimentos E04–E06):
 1. embeddings de textos únicos (caché por hash) y microgrupos Leiden sobre kNN;
 2. textos de acompañamiento (respuestas cortas sin tema) se excluyen del agrupamiento;
 3. grafo de microgrupos unido por respuestas con contenido (siempre misma narrativa, postura opuesta);
 4. ruido = microgrupos sin vida de respuestas o hechos de reacciones;
 5. narrativas = comunidades del grafo de respuestas; postura = bipartición espectral + lado que apoya;
 6. herencia de acompañamiento; origen robusto; título y frases clave.
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from pathlib import Path

import igraph as ig
import leidenalg as la
import numpy as np
import pandas as pd

from radar.embed import Embedder
from radar.narrativas.descripcion import frases_clave, titulo_representativo
from radar.narrativas.grafo import knn_aristas, microgrupos
from radar.narrativas.origen import origen_robusto
from radar.narrativas.postura import bipartir, lado_apoya
from radar.narrativas.respuestas import (heredar, tasa_participacion, textos_acompanamiento, textos_sin_respuestas,
                                         umbral_frecuencia_ruido)
from radar.texto import solo_reaccion

log = logging.getLogger(__name__)
TZ = "America/Argentina/Buenos_Aires"


def _aristas_inversion(c: pd.DataFrame, acomp: set[str]) -> Counter:
    micro_de = dict(zip(c["comentario_id"], c["micro"]))
    resp = c[c["respuesta_a"].notna() & ~c["texto_hash"].isin(acomp)]
    E: Counter = Counter()
    for a, p in zip(resp["micro"], resp["respuesta_a"].map(micro_de)):
        if pd.notna(p) and a != p:
            E[tuple(sorted((int(a), int(p))))] += 1
    return E


def _microgrupos_ruido(c: pd.DataFrame, E: Counter, n_micro: int, excluir: set[str], umbral: float) -> np.ndarray:
    grado = np.zeros(n_micro)
    for (a, b), w in E.items():
        grado[a] += w
        grado[b] += w
    con_tema = c[~c["texto_hash"].isin(excluir)]
    tam = con_tema.groupby("micro").size().reindex(range(n_micro), fill_value=0).to_numpy()
    reac = (con_tema.assign(r=con_tema["texto"].map(solo_reaccion)).groupby("micro")["r"].mean()
            .reindex(range(n_micro), fill_value=1.0).to_numpy())
    return (grado / np.maximum(tam, 1) < umbral) | (reac > 0.5)


def _narrativas_de_microgrupos(E: Counter, n_micro: int, ruido: np.ndarray, seed: int) -> tuple[np.ndarray, np.ndarray]:
    validos = np.flatnonzero(~ruido)
    pos = {v: i for i, v in enumerate(validos)}
    aristas = [(pos[a], pos[b]) for a, b in E if a in pos and b in pos]
    g = ig.Graph(n=len(validos), edges=aristas)
    g.es["weight"] = [E[(validos[a], validos[b])] if (validos[a], validos[b]) in E else E[(validos[b], validos[a])]
                      for a, b in aristas]
    memb = np.asarray(la.find_partition(g, la.ModularityVertexPartition, weights="weight", seed=seed).membership)
    narr = -np.ones(n_micro, int)
    narr[validos] = memb
    lado = np.zeros(n_micro, int)
    for k in np.unique(memb):
        nodos = [int(v) for v in validos[memb == k]]
        for v, s in bipartir(nodos, E).items():
            lado[v] = s
    return narr, lado


def asignar(c: pd.DataFrame, X: np.ndarray, hashes: list[str], cfg: dict, seed: int) -> pd.DataFrame:
    """Núcleo puro (testeable): devuelve c con columnas narr (-1 = ruido), postura, heredado, micro."""
    src, dst, w = knn_aristas(X, k=cfg["knn_k"], dispositivo=cfg.get("dispositivo", "auto"))
    micro_txt = microgrupos(len(hashes), src, dst, w, resolucion=cfg["resolucion"], seed=seed)
    c = c.merge(pd.DataFrame({"texto_hash": hashes, "micro": micro_txt}), on="texto_hash", how="left")
    n_micro = int(micro_txt.max()) + 1

    acomp = textos_acompanamiento(c, cfg["acomp_min_dispersion"], cfg["acomp_max_palabras"])
    k_min = umbral_frecuencia_ruido(tasa_participacion(c), cfg["ruido_alfa"])
    ruido_txt = textos_sin_respuestas(c, k_min) - acomp
    E = _aristas_inversion(c, acomp)
    ruido = _microgrupos_ruido(c, E, n_micro, acomp | ruido_txt, cfg["umbral_ruido"])
    narr_m, lado_m = _narrativas_de_microgrupos(E, n_micro, ruido, seed)

    c["narr"] = narr_m[c["micro"].to_numpy()]
    c["lado"] = lado_m[c["micro"].to_numpy()]
    c.loc[c["texto_hash"].isin(acomp | ruido_txt), ["narr", "lado"]] = -1
    c = heredar(c, acomp, cfg["herencia_profundidad_max"])

    nucleo = c[(c["narr"] >= 0) & ~c["heredado"]].assign(es_respuesta=lambda d: d["respuesta_a"].notna())
    apoya = lado_apoya(nucleo)
    c["postura"] = np.where(c["narr"] < 0, "",
                            np.where(c["lado"].to_numpy() == c["narr"].map(apoya).to_numpy(), "apoya", "rechaza"))
    log.info("narrativas: microgrupos=%d acompañamiento=%d textos_ruido=%d (k>=%d) ruido_micro=%d narrativas=%d",
             n_micro, len(acomp), len(ruido_txt), k_min, int(ruido.sum()), c.loc[c["narr"] >= 0, "narr"].nunique())
    return c


def describir(c: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    filas, docs = [], {}
    for n, g in c[c["narr"] >= 0].groupby("narr"):
        etiqueta = f"n{int(n):02d}"
        nucleo = g[~g["heredado"]]
        origen = origen_robusto(nucleo["ts"] if len(nucleo) else g["ts"], cfg["origen_ventana_h"], cfg["origen_minimo"])
        filas.append({"narrativa": etiqueta,
                      "titulo": titulo_representativo(nucleo.loc[(nucleo["postura"] == "apoya") & nucleo["respuesta_a"].isna(), "texto"]),
                      "fecha_origen": origen.tz_convert(TZ),
                      "apoya": int((g["postura"] == "apoya").sum()), "rechaza": int((g["postura"] == "rechaza").sum()),
                      "total": len(g)})
        docs[etiqueta] = " ".join(nucleo.loc[nucleo["postura"] == "apoya", "texto_norm"].tolist())
    meta = pd.DataFrame(filas)
    if meta.empty:
        return pd.DataFrame(columns=["narrativa", "titulo", "frases_clave", "fecha_origen", "apoya", "rechaza", "total"])
    claves = frases_clave(docs)
    meta["frases_clave"] = meta["narrativa"].map(lambda k: "|".join(claves.get(k, [])))
    return meta.sort_values("total", ascending=False).reset_index(drop=True)


def run(interim: Path, config: dict) -> dict:
    t0 = time.perf_counter()
    cfg = config["narrativas"]
    c = pd.read_parquet(interim / "comentarios.parquet")
    unicos = c.drop_duplicates("texto_hash")[["texto_hash", "texto_norm"]].sort_values("texto_hash")  # determinístico
    emb = Embedder(config["embeddings"]["modelo"], Path(config["embeddings"]["cache_dir"]),
                   batch=config["embeddings"]["batch"], dispositivo=config["embeddings"]["dispositivo"])
    X, info_emb = emb.embeber(unicos["texto_hash"].tolist(), unicos["texto_norm"].tolist())

    c = asignar(c, X, unicos["texto_hash"].tolist(), cfg, seed=config["seed"])
    meta = describir(c, cfg)
    c["narrativa"] = np.where(c["narr"] >= 0, c["narr"].map(lambda n: f"n{int(n):02d}" if n >= 0 else ""), "")
    c[["comentario_id", "narrativa", "postura", "micro", "heredado"]].to_parquet(interim / "narrativas_asig.parquet")
    meta.to_parquet(interim / "narrativas_meta.parquet")
    info = {"narrativas": len(meta), "ruido": int((c["narrativa"] == "").sum()), "embeddings": info_emb,
            "segundos": round(time.perf_counter() - t0, 1)}
    log.info("narrativas: %s", info)
    return info
