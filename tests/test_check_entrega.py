import csv
import gzip
import json

from scripts.check_entrega import validar


def _datos(tmp):
    d = tmp / "datos"
    d.mkdir()
    with gzip.open(d / "comentarios.csv.gz", "wt", encoding="utf-8") as f:
        f.write("comentario_id,texto\nc1,a\nc2,b\n")
    with gzip.open(d / "cuentas.csv.gz", "wt", encoding="utf-8") as f:
        f.write("cuenta_id\nu1\n")
    return d


def _entrega(tmp, fecha="2026-09-01T08:00:00-03:00", bom=False):
    e = tmp / "entrega"
    e.mkdir()
    enc = "utf-8-sig" if bom else "utf-8"
    with open(e / "comentarios.csv", "w", encoding=enc, newline="") as f:
        w = csv.writer(f)
        w.writerows([["comentario_id", "narrativa", "postura"], ["c1", "n01", "apoya"], ["c2", "", ""]])
    with open(e / "narrativas.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerows([["narrativa", "titulo", "frases_clave", "fecha_origen"], ["n01", "Algo, con coma", "a|b", fecha]])
    with open(e / "cuentas.csv", "w", encoding="utf-8", newline="") as f:
        f.write("cuenta_id,grupo\nu1,\n")
    (e / "costo.json").write_text(json.dumps({k: 0 for k in [
        "comentarios_procesados", "segundos", "tokens_ia", "usd_ia",
        "usd_por_mil_comentarios", "hardware", "almacenamiento", "notas"]}))
    return e


def test_valida(tmp_path):
    assert validar(_datos(tmp_path), _entrega(tmp_path)) == []


def test_fecha_sin_zona(tmp_path):
    errs = validar(_datos(tmp_path), _entrega(tmp_path, fecha="2026-09-01T08:00:00"))
    assert any("SIN zona" in e for e in errs)


def test_bom(tmp_path):
    errs = validar(_datos(tmp_path), _entrega(tmp_path, bom=True))
    assert any("BOM" in e for e in errs)
