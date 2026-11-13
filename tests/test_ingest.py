import gzip

import duckdb
import pytest

from radar.stages import ingest

COMENTARIOS = """comentario_id,publicacion_id,cuenta_id,fecha,texto,respuesta_a,me_gusta
c1,p1,u1,2026-09-01T07:32:30-03:00,Hola MUNDO,,3
c2,p1,u2,2026-09-01T10:32:30Z,"respuesta, con coma",c1,x
c2,p1,u2,2026-09-01T10:32:30Z,duplicado,c1,1
c3,p1,u9,fecha-rota,,c999,
c4,p1,u1,2026-09-01T08:00:00-03:00,ciclo a,c5,0
c5,p1,u2,2026-09-01T08:01:00-03:00,ciclo b,c4,0
"""
CUENTAS = """cuenta_id,usuario,fecha_creacion,seguidores,siguiendo
u1,ana,2020-01-01,10,20
u2,beto,2026-08-30,-5,abc
"""
PUBLICACIONES = """publicacion_id,fuente_id,fecha,titular
p1,f1,2026-09-01T07:30:00-03:00,Titular
"""


@pytest.fixture
def datos(tmp_path):
    d = tmp_path / "datos"
    d.mkdir()
    for nombre, contenido in [("comentarios", COMENTARIOS), ("cuentas", CUENTAS), ("publicaciones", PUBLICACIONES)]:
        with gzip.open(d / f"{nombre}.csv.gz", "wt", encoding="utf-8") as f:
            f.write(contenido)
    (d / "fuentes.csv").write_text("fuente_id,nombre,tipo\nf1,Diario,medio\n")
    return d


@pytest.fixture
def interim(datos, tmp_path):
    out = tmp_path / "interim"
    reporte = ingest.run(datos, out, {"tz": "-03:00"})
    return out, reporte


def _q(out, sql):
    return duckdb.sql(sql.replace("{d}", str(out))).fetchall()


def test_dedup_ids_conserva_el_primero(interim):
    out, rep = interim
    assert _q(out, "select texto from '{d}/comentarios.parquet' where comentario_id='c2'") == [("respuesta, con coma",)]
    assert rep["ids_duplicados"] == 1


def test_fechas_normalizadas_a_utc_y_rotas_no_rompen(interim):
    out, rep = interim
    rows = dict(_q(out, "select comentario_id, ts is null from '{d}/comentarios.parquet'"))
    assert rows["c3"] is True and rows["c1"] is False
    assert rep["fechas_invalidas"] == 1


def test_respuesta_huerfana_queda_nula(interim):
    out, _ = interim
    assert _q(out, "select respuesta_a from '{d}/comentarios.parquet' where comentario_id='c3'") == [(None,)]


def test_ciclo_de_respuestas_queda_roto(interim):
    out, _ = interim
    r = dict(_q(out, "select comentario_id, respuesta_a from '{d}/comentarios.parquet' where comentario_id in ('c4','c5')"))
    assert None in r.values()


def test_cortar_ciclos_puro():
    padre = {"a": "b", "b": "c", "c": "a", "d": "a", "e": None}
    assert ingest.cortar_ciclos(padre) == 1
    # sin ciclos: seguir la cadena desde cualquier nodo termina
    for inicio in padre:
        vistos, n = set(), inicio
        while n is not None:
            assert n not in vistos
            vistos.add(n)
            n = padre[n]


def test_me_gusta_invalido_es_cero_y_texto_nulo_es_vacio(interim):
    out, _ = interim
    r = dict(_q(out, "select comentario_id, me_gusta from '{d}/comentarios.parquet'"))
    assert r["c2"] == 0
    assert _q(out, "select texto, texto_norm from '{d}/comentarios.parquet' where comentario_id='c3'") == [("", "")]


def test_cuentas_sin_perfil_se_agregan_y_numeros_se_limpian(interim):
    out, _ = interim
    r = {row[0]: row[1:] for row in _q(out, "select cuenta_id, seguidores, siguiendo from '{d}/cuentas.parquet'")}
    assert "u9" in r
    assert r["u2"] == (None, None)


def test_texto_norm_y_hash(interim):
    out, _ = interim
    (norm, h), = _q(out, "select texto_norm, texto_hash from '{d}/comentarios.parquet' where comentario_id='c1'")
    assert norm == "hola mundo" and len(h) == 20


def test_fecha_sin_zona_se_lee_como_hora_argentina(tmp_path):
    d = tmp_path / "datos"
    d.mkdir()
    com = COMENTARIOS.splitlines()[0] + "\nz1,p1,u1,2026-09-01 07:00:00,sin zona,,0\nz2,p1,u1,2026-09-01T07:00:00-03:00,con zona,,0\n"
    for nombre, contenido in [("comentarios", com), ("cuentas", CUENTAS), ("publicaciones", PUBLICACIONES)]:
        with gzip.open(d / f"{nombre}.csv.gz", "wt", encoding="utf-8") as f:
            f.write(contenido)
    out = tmp_path / "interim"
    ingest.run(d, out, {"tz": "-03:00"})
    r = dict(_q(out, "select comentario_id, epoch(ts) from '{d}/comentarios.parquet'"))
    assert r["z1"] == r["z2"]  # 07:00 sin zona = 07:00-03:00 = 10:00 UTC (no 07:00 UTC)
