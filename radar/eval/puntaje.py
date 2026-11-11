"""Réplica del puntaje automático oficial (evaluacion/puntuar.py del desafío) como funciones puras.

Sirve para medir sin ejecutar código externo, y para validación por partes (p. ej. dejando un tema afuera).
`make score` sigue usando el script oficial como fuente de verdad; tests cruzados verifican que coincidan.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime

VACIO = {"", "ninguna", "none", "null"}


def es_vacio(etiqueta: str | None) -> bool:
    return (etiqueta or "").strip().lower() in VACIO


def bcubed(truth: dict[str, str], pred: dict[str, str]) -> tuple[float, float, float]:
    pares: Counter = Counter()
    tam_t: Counter = Counter()
    tam_p: Counter = Counter()
    for item, t in truth.items():
        p = pred.get(item, "")
        p = f"__solo__{item}" if es_vacio(p) else p
        pares[(p, t)] += 1
        tam_t[t] += 1
        tam_p[p] += 1
    n = len(truth)
    if n == 0:
        return 0.0, 0.0, 0.0
    prec = sum(c * c / tam_p[p] for (p, _), c in pares.items()) / n
    rec = sum(c * c / tam_t[t] for (_, t), c in pares.items()) / n
    return prec, rec, (2 * prec * rec / (prec + rec) if prec + rec else 0.0)


def f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def _fecha(v: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat((v or "").strip())
    except ValueError:
        return None


def origen_score(real: datetime, estimada: datetime | None) -> float:
    if estimada is None:
        return 0.0
    err_h = abs((estimada - real).total_seconds()) / 3600
    return 1.0 if err_h <= 3 else max(0.0, 1 - (err_h - 3) / 45)


def puntuar_narrativas(verdad_c: list[dict], verdad_n: list[dict], pred_c: list[dict], pred_n: list[dict]) -> dict:
    etiqueta = {r["comentario_id"]: (r.get("narrativa") or "").strip() for r in pred_c}
    postura = {r["comentario_id"]: (r.get("postura") or "").strip().lower() for r in pred_c}
    narr = {r["comentario_id"]: r["narrativa_id"] for r in verdad_c if r["narrativa_id"] != "ninguna"}
    b_p, b_r, b_f1 = bcubed(narr, etiqueta)

    tp = fp = fn = 0
    for r in verdad_c:
        es_ruido = r["narrativa_id"] == "ninguna"
        dijo_ruido = es_vacio(etiqueta.get(r["comentario_id"], ""))
        tp += es_ruido and dijo_ruido
        fp += (not es_ruido) and dijo_ruido
        fn += es_ruido and not dijo_ruido
    ruido = f1(tp, fp, fn)[2]

    f1s = []
    for cls in ("apoya", "rechaza"):
        tp = fp = fn = 0
        for r in verdad_c:
            if r["narrativa_id"] == "ninguna":
                continue
            es = r["postura"] == cls
            dijo = postura.get(r["comentario_id"], "") == cls
            tp += es and dijo
            fp += (not es) and dijo
            fn += es and not dijo
        f1s.append(f1(tp, fp, fn)[2])
    post = sum(f1s) / 2

    origen_por = {r.get("narrativa", "").strip(): _fecha(r.get("fecha_origen")) for r in pred_n}
    solape: dict[str, Counter] = defaultdict(Counter)
    for cid, t in narr.items():
        p = etiqueta.get(cid, "")
        if not es_vacio(p):
            solape[t][p] += 1
    origenes = {}
    for n in verdad_n:
        if n.get("emergente") != "si":
            continue
        mejor = solape[n["narrativa_id"]].most_common(1)
        est = origen_por.get(mejor[0][0]) if mejor else None
        real = _fecha(n["fecha_origen"])
        origenes[n["narrativa_id"]] = origen_score(real, est) if real else 0.0
    origen = sum(origenes.values()) / len(origenes) if origenes else 0.0

    comb = 0.5 * b_f1 + 0.15 * ruido + 0.2 * post + 0.15 * origen
    return {"bcubed_precision": b_p, "bcubed_recall": b_r, "bcubed_f1": b_f1, "ruido_f1": ruido,
            "postura_macro_f1": post, "origen": origen, "origen_por_narrativa": origenes,
            "combinado": comb, "puntos": round(30 * comb, 2)}


def puntuar_coordinacion(verdad: list[dict], pred: list[dict]) -> dict:
    grupo = {r["cuenta_id"]: (r.get("grupo") or "").strip() for r in pred}
    tp = fp = fn = 0
    for r in verdad:
        coord = bool(r["campana_id"])
        marcada = not es_vacio(grupo.get(r["cuenta_id"], ""))
        tp += coord and marcada
        fp += (not coord) and marcada
        fn += coord and not marcada
    p, rc, f = f1(tp, fp, fn)
    _, _, g = bcubed({r["cuenta_id"]: r["campana_id"] for r in verdad if r["campana_id"]}, grupo)
    comb = 0.7 * f + 0.3 * g
    return {"precision": p, "recall": rc, "f1": f, "marcadas": tp + fp, "grupos_bcubed_f1": g,
            "combinado": comb, "puntos": round(25 * comb, 2)}
