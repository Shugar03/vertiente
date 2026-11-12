import gzip
import json
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import duckdb
import pytest

from radar import app
from radar.stages import ingest

COMENTARIOS = ("comentario_id,publicacion_id,cuenta_id,fecha,texto,respuesta_a,me_gusta\n"
               "c1,p1,u1,2026-09-01T07:32:30-03:00,Hola,,3\nc2,p1,u2,2026-09-01T07:40:00-03:00,No es así,c1,0\n")


@pytest.fixture
def servidor(tmp_path):
    llamadas = []

    def correr_falso(datos, salida):
        llamadas.append(datos)
        salida.mkdir(parents=True)
        (salida / "dashboard.html").write_text("<!doctype html>ok", encoding="utf-8")
        (salida / "costo.json").write_text("{}", encoding="utf-8")
        return {"comentarios": 2, "segundos": 0.1, "narrativas": 1, "operaciones": 0, "cuentas_marcadas": 0}

    cargas = app.Cargas(tmp_path, correr=correr_falso)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.crear_handler(cargas))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", cargas, llamadas
    srv.shutdown()
    srv.server_close()


def _pedir(url, metodo="GET", cuerpo=None):
    req = urllib.request.Request(url, data=cuerpo, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _json(url, metodo="GET", cuerpo=None):
    codigo, datos = _pedir(url, metodo, cuerpo)
    return codigo, json.loads(datos)


def test_pagina_de_carga(servidor):
    base, _, _ = servidor
    codigo, html = _pedir(base + "/")
    assert codigo == 200 and "Soltá acá los archivos" in html.decode("utf-8")


def test_flujo_completo_solo_con_comentarios(servidor):
    base, cargas, llamadas = servidor
    _, j = _json(base + "/api/lote", "POST")
    lote = j["lote"]
    assert _json(f"{base}/api/subir/{lote}/comentarios.csv.gz", "PUT", gzip.compress(COMENTARIOS.encode()))[0] == 200
    assert _pedir(f"{base}/r/{lote}/dashboard.html")[0] == 404  # todavía no está
    assert _json(f"{base}/api/procesar/{lote}", "POST")[0] == 202
    for _ in range(50):
        _, st = _json(f"{base}/api/estado/{lote}")
        if st["estado"] != "procesando":
            break
        time.sleep(0.05)
    assert st["estado"] == "listo" and st["resumen"]["comentarios"] == 2
    assert llamadas == [cargas.datos(lote)]
    # cuentas y publicaciones se completan vacías
    assert (cargas.datos(lote) / "cuentas.csv").read_text(encoding="utf-8").startswith("cuenta_id,")
    assert (cargas.datos(lote) / "publicaciones.csv").exists()
    codigo, html = _pedir(f"{base}/r/{lote}/dashboard.html")
    assert codigo == 200 and html.startswith(b"<!doctype html>")
    # un lote procesado no acepta más archivos
    assert _json(f"{base}/api/subir/{lote}/cuentas.csv", "PUT", b"x")[0] == 409


def test_sin_comentarios_o_columnas_faltantes_es_error_claro(servidor):
    base, _, _ = servidor
    lote = _json(base + "/api/lote", "POST")[1]["lote"]
    codigo, j = _json(f"{base}/api/procesar/{lote}", "POST")
    assert codigo == 400 and "comentarios" in j["error"]
    _json(f"{base}/api/subir/{lote}/comentarios.csv", "PUT", b"id,texto\n1,hola\n")
    codigo, j = _json(f"{base}/api/procesar/{lote}", "POST")
    assert codigo == 400 and "comentario_id" in j["error"] and "publicacion_id" in j["error"]


def test_nombres_y_lotes_invalidos(servidor):
    base, _, _ = servidor
    lote = _json(base + "/api/lote", "POST")[1]["lote"]
    assert _json(f"{base}/api/subir/{lote}/..%2F..%2Fconfig.yaml", "PUT", b"x")[0] == 400
    assert _json(f"{base}/api/subir/{lote}/otra_cosa.csv", "PUT", b"x")[0] == 400
    assert _json(f"{base}/api/subir/carga-20990101-000000/comentarios.csv", "PUT", b"x")[0] == 404
    assert _json(f"{base}/api/estado/../../etc", "GET")[0] == 404
    assert _pedir(f"{base}/r/{lote}/config.yaml")[0] == 404


def test_un_solo_procesamiento_a_la_vez(servidor):
    base, cargas, _ = servidor
    lote = _json(base + "/api/lote", "POST")[1]["lote"]
    _json(f"{base}/api/subir/{lote}/comentarios.csv", "PUT", COMENTARIOS.encode())
    cargas.ocupado.acquire()
    try:
        assert _json(f"{base}/api/procesar/{lote}", "POST")[0] == 409
    finally:
        cargas.ocupado.release()


def test_error_del_pipeline_se_muestra(tmp_path):
    def roto(datos, salida):
        raise ValueError("datos imposibles")

    cargas = app.Cargas(tmp_path, correr=roto)
    lote = cargas.nuevo()
    cargas.ocupado.acquire()
    cargas.procesar(lote)
    assert cargas.estado[lote]["estado"] == "error" and "datos imposibles" in cargas.estado[lote]["error"]
    assert cargas.ocupado.acquire(blocking=False)  # se liberó


def test_ingesta_con_cuentas_y_publicaciones_vacias(tmp_path):
    d = tmp_path / "datos"
    d.mkdir()
    (d / "comentarios.csv").write_text(COMENTARIOS, encoding="utf-8")
    for nombre, encabezado in app.VACIOS.items():
        (d / f"{nombre}.csv").write_text(encabezado, encoding="utf-8")
    out = tmp_path / "interim"
    rep = ingest.run(d, out, {})
    assert rep["comentarios_leidos"] == 2 and rep["cuentas_sin_perfil"] == 2
    assert duckdb.sql(f"select count(*) from '{out / 'cuentas.parquet'}'").fetchall() == [(2,)]
