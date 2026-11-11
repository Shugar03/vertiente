from datetime import datetime, timedelta, timezone

import duckdb
import pandas as pd
import pytest

from radar.coordinacion.grafo import detectar_grupos
from radar.coordinacion.senales import respuestas_entre_cuentas, sincronias_alineadas

T0 = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)


def _comentarios():
    filas, i = [], 0

    def add(cuenta, post, minutos, narr="n01", post_="apoya", resp=None):
        nonlocal i
        i += 1
        filas.append(dict(comentario_id=f"c{i}", cuenta_id=cuenta, publicacion_id=post,
                          ts=T0 + timedelta(minutes=minutos), narrativa=narr, postura=post_, respuesta_a=resp))
        return f"c{i}"

    # operación: 6 cuentas, mismas 4 publicaciones, misma narrativa/postura, a minutos de distancia
    for p in range(4):
        for k in range(6):
            add(f"op{k}", f"p{p}", p * 600 + k * 3)
    # pico viral genuino: 30 cuentas en una sola publicación, a la vez (una sola vez)
    for k in range(30):
        add(f"v{k}", "pv", 100 + k)
    # genuinos: misma narrativa entre ellos, pero cada uno en momentos distintos en cada publicación
    for k in range(20):
        for p in range(3):
            add(f"g{k}", f"p{p}", p * 600 + 100 + (k * 37 + p * 113) % 480, narr="n02", post_="rechaza")
    return pd.DataFrame(filas)


@pytest.fixture
def con():
    c = duckdb.connect()
    c.register("cm", _comentarios())
    return c


def test_sincronias_alineadas_cuenta_publicaciones_distintas(con):
    s = sincronias_alineadas(con, "cm", ventana_min=30)
    par = s[(s.x == "op0") & (s.y == "op1")].iloc[0]
    assert par.sync == 4 and par.sync_n == pytest.approx(1.0)
    viral = s[s.x.str.startswith("v") & s.y.str.startswith("v")]
    assert (viral.sync <= 1).all()


def test_sincronias_ignoran_narrativa_distinta(con):
    s = sincronias_alineadas(con, "cm", ventana_min=30)
    assert s[(s.x.str.startswith("g") & s.y.str.startswith("op")) | (s.x.str.startswith("op") & s.y.str.startswith("g"))].empty


def test_ruido_se_alinea_como_una_clase_propia():
    c = duckdb.connect()
    filas = [dict(comentario_id=f"c{p}{k}", cuenta_id=f"r{k}", publicacion_id=f"p{p}",
                  ts=T0 + timedelta(minutes=p * 600 + k), narrativa="", postura="", respuesta_a=None)
             for p in range(3) for k in range(3)]
    c.register("cm", pd.DataFrame(filas))
    s = sincronias_alineadas(c, "cm", ventana_min=30)
    assert s[(s.x == "r0") & (s.y == "r1")].sync.item() == 3


def test_detectar_grupos_encuentra_la_operacion_y_no_el_pico_viral(con):
    s = sincronias_alineadas(con, "cm", ventana_min=30)
    grupos = detectar_grupos(s, min_sincronias=2, min_sincronia_norm=0.1, min_vecinos_comunes=3,
                             min_tamano=5, min_densidad=0.3, seed=1)
    assert {k for k in grupos} == {f"op{k}" for k in range(6)}
    assert len(set(grupos.values())) == 1


def test_filtrar_por_vecinos_comunes_quita_aristas_sueltas():
    from radar.coordinacion.grafo import filtrar_vecinos_comunes
    clique = [(f"a{i}", f"a{j}") for i in range(5) for j in range(i + 1, 5)]
    sueltas = [("a0", "z1"), ("z1", "z2")]  # sin triángulos
    e = pd.DataFrame(clique + sueltas, columns=["x", "y"])
    out = filtrar_vecinos_comunes(e, min_comunes=2)
    assert set(map(tuple, out[["x", "y"]].values)) == set(clique)


def test_nucleo_rescata_operacion_con_cuentas_pegadas():
    import igraph as ig
    import numpy as np
    from radar.coordinacion.grafo import nucleo_si_hace_falta
    clique = [(a, b) for a in range(10) for b in range(a + 1, 10)]
    pegadas = [(10 + i, i % 10) for i in range(40)]  # 40 cuentas genuinas con un lazo cada una
    g = ig.Graph(n=50, edges=clique + pegadas)
    assert g.induced_subgraph(range(50)).density() < 0.3
    assert sorted(nucleo_si_hace_falta(g, np.arange(50), 0.3, 0.5).tolist()) == list(range(10))


def test_detectar_grupos_es_independiente_del_orden(con):
    s = sincronias_alineadas(con, "cm", ventana_min=30)
    a = detectar_grupos(s, 2, 0.1, 3, 5, 0.3, 1)
    b = detectar_grupos(s.sample(frac=1, random_state=3), 2, 0.1, 3, 5, 0.3, 1)
    assert a == b


def test_detectar_grupos_sin_aristas():
    vacio = pd.DataFrame(columns=["x", "y", "sync", "sync_n"])
    assert detectar_grupos(vacio, 2, 0.1, 3, 5, 0.3, 1) == {}
