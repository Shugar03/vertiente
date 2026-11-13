"""Casos borde y ramas de error de los módulos de soporte."""
import gzip
import json
import subprocess
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from radar.llm import Profesor
from radar.narrativas.origen import origen_robusto
from radar.narrativas.postura import lado_apoya
from radar.stages import entrega
from radar.stages.narrativas import consultar_profesor, ejemplos_por_lado
from scripts import check_entrega


# --- origen / postura -------------------------------------------------------------------------------------------

def test_origen_sin_fechas_es_error_explicito():
    with pytest.raises(ValueError):
        origen_robusto(pd.Series([pd.NaT, pd.NaT]), 3, 5)


def test_narrativa_con_un_solo_bando():
    d = pd.DataFrame({"narr": [0, 0], "lado": [1, 1], "es_respuesta": [False, True], "texto_norm": ["a", "b"]})
    assert lado_apoya(d) == {0: 1}


# --- profesor dentro de la etapa ----------------------------------------------------------------------------------

def _c_con_lados():
    filas = []
    for lado, base in [(0, "la mina se queda con toda el agua del pueblo"), (1, "el agua se corta hace veinte años igual")]:
        for i in range(5):
            filas.append({"narr": 0, "lado": lado, "heredado": False, "respuesta_a": None, "texto": f"{base} {i}"})
    filas.append({"narr": 1, "lado": 0, "heredado": False, "respuesta_a": None, "texto": "solo un bando en esta narrativa"})
    return pd.DataFrame(filas)


def test_ejemplos_por_lado_y_consulta_al_profesor():
    c = _c_con_lados()
    ej = ejemplos_por_lado(c, 3)
    assert len(ej[0][0]) == 3 and len(ej[0][1]) == 3 and ej[1][1] == []

    class Prof:
        def juzgar_narrativa(self, a, b):
            return {"afirmacion": "La mina se queda con el agua", "lado_que_afirma": "B", "confianza": 0.9}

    lados, titulos = consultar_profesor(c, Prof(), {"ejemplos_por_lado": 3, "min_confianza": 0.6})
    assert lados == {0: 1} and titulos == {0: "La mina se queda con el agua"}   # narr 1 sin dos bandos: se omite


def test_profesor_con_poca_confianza_no_decide():
    class Prof:
        def juzgar_narrativa(self, a, b):
            return {"afirmacion": "x", "lado_que_afirma": "A", "confianza": 0.2}

    assert consultar_profesor(_c_con_lados(), Prof(), {"ejemplos_por_lado": 3, "min_confianza": 0.6}) == ({}, {})


# --- llm ------------------------------------------------------------------------------------------------------------

def test_profesor_desde_config_sin_clave(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("LLM_MODEL", "claude-haiku-5-5")
    p = Profesor.desde_config({"modelo": "claude-opus-5-5", "cache_dir": str(tmp_path), "timeout_s": 5, "reintentos": 1,
                               "precios_usd_por_millon": {"claude-haiku-5-5": {"in": 0.1, "out": 0.5}}})
    assert p.cliente is None and p.modelo == "claude-haiku-5-5" and p.precio_in == 0.1


def test_profesor_rechazo_y_reintento(tmp_path, monkeypatch):
    monkeypatch.setattr("radar.llm.time.sleep", lambda s: None)
    respuestas = iter([RuntimeError("timeout"),
                       SimpleNamespace(stop_reason="refusal", content=[], usage=SimpleNamespace(input_tokens=1, output_tokens=0))])

    def create(**kw):
        r = next(respuestas)
        if isinstance(r, Exception):
            raise r
        return r

    cli = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)))
    p = Profesor(tmp_path, "m", 1.0, 1.0, cliente=cli, reintentos=2)
    assert p.juzgar_narrativa(["a"], ["b"]) is None      # 1° intento falla, 2° es un rechazo
    assert p.uso["llamadas"] == 1


# --- entrega ------------------------------------------------------------------------------------------------------

def test_hardware_sin_sysctl(monkeypatch):
    def falla(*a, **k):
        raise OSError("sin sysctl")
    monkeypatch.setattr(subprocess, "run", falla)
    assert "núcleos" in entrega.hardware()


# --- validador de formato: cada error -----------------------------------------------------------------------------

def _gz(df, p):
    with gzip.open(p, "wt", encoding="utf-8") as f:
        df.to_csv(f, index=False)


@pytest.fixture
def datos(tmp_path):
    d = tmp_path / "datos"
    d.mkdir()
    _gz(pd.DataFrame({"comentario_id": ["c1", "c2"]}), d / "comentarios.csv.gz")
    _gz(pd.DataFrame({"cuenta_id": ["u1", "u2"]}), d / "cuentas.csv.gz")
    return d


def _entrega(tmp_path, com, nar, cue, costo):
    e = tmp_path / "e"
    e.mkdir(exist_ok=True)
    for nombre, df in [("comentarios.csv", com), ("narrativas.csv", nar), ("cuentas.csv", cue)]:
        if df is not None:
            df.to_csv(e / nombre, index=False)
    if costo is not None:
        (e / "costo.json").write_text(costo)
    return e


def test_validador_reporta_cada_error(datos, tmp_path):
    com = pd.DataFrame({"comentario_id": ["c1", "c1"], "narrativa": ["n01", "n01"], "postura": ["apoya", "apoya"]})
    nar = pd.DataFrame({"narrativa": ["n09"], "titulo": ["t"], "frases_clave": ["a"], "fecha_origen": ["no-es-fecha"]})
    cue = pd.DataFrame({"cuenta_id": ["u1"], "grupo": [""]})
    errs = check_entrega.validar(datos, _entrega(tmp_path, com, nar, cue, '{"segundos": 1}'))
    texto = " | ".join(errs)
    for esperado in ["ids duplicados", "faltan 1 comentarios", "fecha_origen inválida", "faltan 1 etiquetas",
                     "faltan 1 cuentas", "costo.json: faltan campos"]:
        assert esperado in texto, esperado


def test_validador_posturas_invalidas_y_archivos_faltantes(datos, tmp_path):
    base = {"comentario_id": ["c1", "c2"]}
    casos = [
        (pd.DataFrame({**base, "narrativa": ["n01", ""], "postura": ["quizas", ""]}), "postura inválida"),
        (pd.DataFrame({**base, "narrativa": ["", ""], "postura": ["apoya", ""]}), "ruido con postura"),
        (pd.DataFrame({**base, "narrativa": ["n01", ""], "postura": ["", ""]}), "narrativa sin postura"),
        (pd.DataFrame({**base, "otra": ["x", "y"]}), "columnas"),
    ]
    for i, (com, esperado) in enumerate(casos):
        e = _entrega(tmp_path / str(i), com, None, None, "no es json") if (tmp_path / str(i)).mkdir() is None else None
        errs = " | ".join(check_entrega.validar(datos, e))
        assert esperado in errs, (esperado, errs)
        assert "falta narrativas.csv" in errs and "falta cuentas.csv" in errs and "costo.json inválido" in errs
    vacio = tmp_path / "vacio"
    vacio.mkdir()
    assert "falta costo.json" in " | ".join(check_entrega.validar(datos, vacio))


def test_validador_por_linea_de_comandos(datos, tmp_path, monkeypatch, capsys):
    vacio = tmp_path / "vacio2"
    vacio.mkdir()
    monkeypatch.setattr(sys, "argv", ["check", "--datos", str(datos), "--entrega", str(vacio)])
    with pytest.raises(SystemExit) as e:
        check_entrega.main()
    assert e.value.code == 1 and "error(es)" in capsys.readouterr().out


# --- CLI y demo -----------------------------------------------------------------------------------------------------

def test_cli_score_por_linea_de_comandos(tmp_path, monkeypatch, capsys):
    from radar import cli
    v = tmp_path / "verdad"
    v.mkdir()
    _gz(pd.DataFrame({"comentario_id": ["c1"], "narrativa_id": ["X"], "postura": ["apoya"]}), v / "comentarios.csv.gz")
    pd.DataFrame({"narrativa_id": ["X"], "emergente": ["no"], "fecha_origen": ["2026-09-01T00:00:00-03:00"]}) \
        .to_csv(v / "narrativas.csv", index=False)
    _gz(pd.DataFrame({"cuenta_id": ["u1"], "campana_id": [""]}), v / "cuentas.csv.gz")
    e = tmp_path / "e"
    e.mkdir()
    pd.DataFrame({"comentario_id": ["c1"], "narrativa": ["n0"], "postura": ["apoya"]}).to_csv(e / "comentarios.csv", index=False)
    pd.DataFrame({"narrativa": ["n0"], "fecha_origen": ["2026-09-01T00:00:00-03:00"]}).to_csv(e / "narrativas.csv", index=False)
    pd.DataFrame({"cuenta_id": ["u1"], "grupo": [""]}).to_csv(e / "cuentas.csv", index=False)
    monkeypatch.setattr(sys, "argv", ["radar", "score", "--verdad", str(v), "--entrega", str(e)])
    cli.main()
    assert "TOTAL AUTOMÁTICO" in capsys.readouterr().out


def test_demo_por_linea_de_comandos(tmp_path, monkeypatch):
    from radar import demo
    monkeypatch.setattr(demo, "datos", lambda interim: {"inicio": "2026-09-01T00:00:00-03:00", "bin_h": 6, "n_bins": 1,
                                                       "resumen": {}, "narrativas": [], "operaciones": [], "alertas": []})
    salida = tmp_path / "x" / "dash.html"
    monkeypatch.setattr(sys, "argv", ["demo", "--interim", str(tmp_path), "--salida", str(salida)])
    demo.main()
    assert salida.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert json.loads(salida.read_text(encoding="utf-8").split("const D = ")[1].split(";\n")[0])["n_bins"] == 1
