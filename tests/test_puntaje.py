from datetime import datetime

import pytest

from radar.eval.puntaje import bcubed, origen_score, puntuar_coordinacion, puntuar_narrativas


def test_bcubed_perfecto_independiente_de_nombres():
    truth = {"a": "X", "b": "X", "c": "Y"}
    assert bcubed(truth, {"a": "1", "b": "1", "c": "2"}) == pytest.approx((1.0, 1.0, 1.0))


def test_bcubed_todo_junto_baja_precision():
    truth = {"a": "X", "b": "X", "c": "Y", "d": "Y"}
    p, r, _ = bcubed(truth, {k: "1" for k in truth})
    assert r == pytest.approx(1.0)
    assert p == pytest.approx(0.5)


def test_bcubed_vacio_o_ruido_es_singleton():
    truth = {"a": "X", "b": "X"}
    p, r, _ = bcubed(truth, {"a": "", "b": "ninguna"})
    assert p == pytest.approx(1.0)
    assert r == pytest.approx(0.5)


def test_origen_tolerancia():
    t = datetime.fromisoformat("2026-09-07T08:00:00-03:00")
    assert origen_score(t, datetime.fromisoformat("2026-09-07T10:59:00-03:00")) == 1.0
    assert origen_score(t, datetime.fromisoformat("2026-09-09T08:00:00-03:00")) == pytest.approx(0.0)
    assert origen_score(t, None) == 0.0


def test_narrativas_combinado():
    verdad_c = [
        {"comentario_id": "1", "narrativa_id": "A", "postura": "apoya"},
        {"comentario_id": "2", "narrativa_id": "A", "postura": "rechaza"},
        {"comentario_id": "3", "narrativa_id": "ninguna", "postura": ""},
    ]
    verdad_n = [{"narrativa_id": "A", "emergente": "si", "fecha_origen": "2026-09-01T00:00:00-03:00"}]
    pred_c = [
        {"comentario_id": "1", "narrativa": "n1", "postura": "apoya"},
        {"comentario_id": "2", "narrativa": "n1", "postura": "rechaza"},
        {"comentario_id": "3", "narrativa": "", "postura": ""},
    ]
    pred_n = [{"narrativa": "n1", "fecha_origen": "2026-09-01T01:00:00-03:00"}]
    r = puntuar_narrativas(verdad_c, verdad_n, pred_c, pred_n)
    assert r["combinado"] == pytest.approx(1.0)
    assert r["puntos"] == pytest.approx(30.0)


def test_comentario_ausente_cuenta_como_ruido():
    verdad_c = [{"comentario_id": "1", "narrativa_id": "ninguna", "postura": ""}]
    r = puntuar_narrativas(verdad_c, [], [], [])
    assert r["ruido_f1"] == pytest.approx(1.0)


def test_coordinacion():
    verdad = [{"cuenta_id": c, "campana_id": g} for c, g in
              [("a", "C1"), ("b", "C1"), ("c", "C2"), ("d", ""), ("e", "")]]
    pred = [{"cuenta_id": "a", "grupo": "g1"}, {"cuenta_id": "b", "grupo": "g1"},
            {"cuenta_id": "c", "grupo": "g2"}, {"cuenta_id": "d", "grupo": ""}]
    r = puntuar_coordinacion(verdad, pred)
    assert r["f1"] == pytest.approx(1.0)
    assert r["puntos"] == pytest.approx(25.0)
