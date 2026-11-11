"""Modo degradado (sin respuestas) recorrido por la etapa real `asignar`, con embeddings sintéticos."""
import numpy as np
import pandas as pd

from radar.narrativas.semantico import centroides, microgrupos_ruido_semantico
from radar.stages.narrativas import asignar

CFG = {"knn_k": 4, "resolucion": 1.0, "acomp_min_dispersion": 5, "acomp_max_palabras": 4, "umbral_ruido": 0.01,
       "ruido_alfa": 0.02, "herencia_profundidad_max": 10, "origen_ventana_h": 3, "origen_minimo": 5,
       "min_tasa_respuestas": 0.03, "semantico_knn": 3, "semantico_min_frac_tamano": 0.0, "dispositivo": "cpu"}


def _datos():
    rng = np.random.default_rng(0)
    bases = {"A+": [1, 0, 0, 0, .3], "A-": [1, 0, 0, 0, -.3], "B+": [0, 1, 0, 0, .3], "B-": [0, 1, 0, 0, -.3],
             "R": [0, 0, 1, 0, 0]}
    textos = {"A+": "la obra esta parada hace meses", "A-": "no es asi la obra avanza bien",
              "B+": "el boleto es impagable para todos", "B-": "el boleto no es caro comparado",
              "R": "jaja"}
    filas, hashes, X = [], [], []
    for k, v in bases.items():
        for i in range(6):
            h = f"{k}{i}"
            hashes.append(h)
            X.append(np.array(v) + rng.normal(0, 0.01, 5))
            texto = ["jaja", "jajaja", "uhh", "👀", "posta", "comparto"][i] if k == "R" else textos[k] + f" {i}"
            for j in range(3):
                filas.append({"comentario_id": f"c{h}{j}", "texto_hash": h, "texto": texto,
                              "texto_norm": texto, "respuesta_a": None,
                              "ts": pd.Timestamp("2026-09-01T10:00:00Z") + pd.Timedelta(minutes=i * 10 + j)})
    X = np.array(X, dtype=np.float32)
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    return pd.DataFrame(filas), X, hashes


def test_sin_respuestas_usa_el_modo_semantico_y_no_colapsa():
    c, X, hashes = _datos()
    out = asignar(c, X, hashes, CFG, seed=1)
    tema = out["texto_hash"].str[0]
    con_narr = out[out["narr"] >= 0]
    assert not out["heredado"].any()
    assert set(out.loc[tema == "R", "narr"]) == {-1}                    # reacciones = ruido
    for t in "AB":                                                      # cada tema es una narrativa
        assert con_narr.loc[con_narr["texto_hash"].str[0] == t, "narr"].nunique() == 1
    assert set(con_narr["postura"]) == {"apoya", "rechaza"}


def test_centroides_y_ruido_semantico():
    c, X, hashes = _datos()
    c["micro"] = c["texto_hash"].str[0].map({"A": 0, "B": 1, "R": 2})
    C = centroides(c, X, hashes, 3)
    np.testing.assert_allclose(np.linalg.norm(C, axis=1), 1.0, rtol=1e-5)
    ruido = microgrupos_ruido_semantico(c, 3, min_frac_tamano=0.0)
    assert ruido.tolist() == [False, False, True]
    assert microgrupos_ruido_semantico(c, 3, min_frac_tamano=0.9).all()  # todo diminuto => ruido
