import numpy as np
import pandas as pd
import pytest

from radar.narrativas.grafo import knn_aristas, microgrupos
from radar.narrativas.origen import origen_robusto
from radar.narrativas.postura import bipartir, lado_apoya
from radar.narrativas.respuestas import heredar, textos_acompanamiento


def test_knn_aristas_conecta_vecinos_mas_parecidos():
    X = np.array([[1, 0], [0.99, 0.14], [0, 1], [0.14, 0.99]], dtype=np.float32)
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    src, dst, w = knn_aristas(X, k=1, dispositivo="cpu")
    pares = {tuple(sorted(p)) for p in zip(src, dst)}
    assert pares == {(0, 1), (2, 3)}
    assert all(x > 0.9 for x in w)


def test_microgrupos_separa_dos_bloques():
    edges = [(0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5), (2, 3)]
    m = microgrupos(6, [e[0] for e in edges], [e[1] for e in edges], [1.0] * 7, resolucion=1.0, seed=1)
    assert m[0] == m[1] == m[2] and m[3] == m[4] == m[5] and m[0] != m[3]


def test_bipartir_grafo_de_inversion():
    # 0,1 de un lado; 2,3 del otro: las aristas (respuestas que contradicen) cruzan de lado
    E = {(0, 2): 5, (0, 3): 4, (1, 2): 6, (1, 3): 3, (0, 1): 1}  # una arista "ruidosa" dentro del mismo lado
    lado = bipartir([0, 1, 2, 3], E)
    assert lado[0] == lado[1] != lado[2] == lado[3]


def test_bipartir_un_solo_nodo():
    assert bipartir([7], {}) == {7: 0}


def _lados(resp0, resp1, neg0, neg1, n=100):
    filas = []
    for lado, r, ng in [(0, resp0, neg0), (1, resp1, neg1)]:
        for i in range(n):
            filas.append({"narr": 0, "lado": lado, "es_respuesta": i < r * n,
                          "texto_norm": "no es asi nada que ver" if i < ng * n else "el agua es de la gente"})
    return pd.DataFrame(filas)


def test_lado_apoya_es_el_de_menor_proporcion_de_respuestas():
    assert lado_apoya(_lados(0.10, 0.20, 0.3, 0.3)) == {0: 0}


def test_lado_apoya_desempata_por_refutacion_si_las_respuestas_no_deciden():
    # proporción de respuestas casi igual; el lado 0 niega mucho más => apoya es el lado 1
    assert lado_apoya(_lados(0.15, 0.15, 0.8, 0.2)) == {0: 1}


def test_origen_robusto_ignora_comentario_aislado_previo():
    ts = pd.to_datetime(["2026-09-01T03:00:00-03:00"] + [f"2026-09-07T08:{m:02d}:00-03:00" for m in range(10, 20)])
    o = origen_robusto(pd.Series(ts), ventana_h=3, minimo=5)
    assert o == pd.Timestamp("2026-09-07T08:10:00-03:00")


def test_origen_robusto_con_pocos_datos_devuelve_el_primero():
    ts = pd.Series(pd.to_datetime(["2026-09-02T10:00:00-03:00", "2026-09-03T10:00:00-03:00"]))
    assert origen_robusto(ts, ventana_h=3, minimo=5) == ts.min()


@pytest.fixture
def hilo():
    # c1 narrativa A lado 0; c2 "tal cual" responde a c1; c3 "coincido" responde a c2 (cadena); c4 "tal cual" sin padre
    return pd.DataFrame({
        "comentario_id": ["c1", "c2", "c3", "c4"],
        "respuesta_a": [None, "c1", "c2", None],
        "texto_hash": ["h1", "hA", "hB", "hA"],
        "narr": [3, -1, -1, -1], "lado": [0, -1, -1, -1],
    })


def test_heredar_cadena_de_acompanamiento(hilo):
    out = heredar(hilo, acomp={"hA", "hB"}, profundidad_max=10)
    assert out.loc[1, ["narr", "lado"]].tolist() == [3, 0]
    assert out.loc[2, ["narr", "lado"]].tolist() == [3, 0]


def test_heredar_acompanamiento_sin_padre_es_ruido(hilo):
    out = heredar(hilo, acomp={"hA", "hB"}, profundidad_max=10)
    assert out.loc[3, "narr"] == -1


def test_umbral_frecuencia_ruido_se_adapta_a_la_tasa_de_respuestas():
    from radar.narrativas.respuestas import umbral_frecuencia_ruido
    assert umbral_frecuencia_ruido(0.25, alfa=0.02) == 14
    assert umbral_frecuencia_ruido(0.05, alfa=0.02) > 50
    assert umbral_frecuencia_ruido(0.0, alfa=0.02) == 10**9


def test_textos_sin_vida_de_respuestas():
    from radar.narrativas.respuestas import textos_sin_respuestas
    c = pd.DataFrame({
        "comentario_id": [f"g{i}" for i in range(20)] + ["a", "b"],
        "respuesta_a": [None] * 20 + [None, "a"],
        "texto_hash": ["gracias"] * 20 + ["arg", "arg2"],
    })
    assert textos_sin_respuestas(c, min_frecuencia=15) == {"gracias"}


def test_textos_acompanamiento_son_cortos_y_responden_a_muchos_grupos():
    c = pd.DataFrame({
        "comentario_id": [f"p{i}" for i in range(6)] + [f"r{i}" for i in range(6)] + ["x"],
        "respuesta_a": [None] * 6 + [f"p{i}" for i in range(6)] + ["p0"],
        "texto_hash": [f"t{i}" for i in range(6)] + ["tal"] * 6 + ["largo"],
        "texto_norm": [f"texto {i}" for i in range(6)] + ["tal cual"] * 6 + ["un argumento largo y con contenido propio aca"],
        "micro": list(range(6)) + [9] * 6 + [8],
    })
    assert textos_acompanamiento(c, min_dispersion=5, max_palabras=4) == {"tal"}
