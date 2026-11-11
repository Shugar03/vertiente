"""Herramienta de robustez: armado de variantes y ensuciado de datos (sin correr el pipeline)."""
import gzip

import pandas as pd

from radar.eval import validar


def _gz(df, p):
    with gzip.open(p, "wt", encoding="utf-8") as f:
        df.to_csv(f, index=False)


def _practica(tmp_path):
    d = tmp_path / "practica"
    (d / "verdad").mkdir(parents=True)
    com = pd.DataFrame({
        "comentario_id": [f"c{i}" for i in range(40)], "publicacion_id": ["pL"] * 20 + ["pB"] * 20,
        "cuenta_id": [f"u{i % 10}" for i in range(40)],
        "fecha": [f"2026-09-0{1 + i % 9}T10:00:00-03:00" for i in range(40)],
        "texto": ["el agua de la mina se acaba"] * 20 + ["el boleto esta carisimo"] * 20,
        "respuesta_a": [""] * 40, "me_gusta": ["1"] * 40})
    _gz(com, d / "comentarios.csv.gz")
    _gz(pd.DataFrame({"cuenta_id": [f"u{i}" for i in range(12)], "usuario": "x", "fecha_creacion": "2020-01-01",
                      "seguidores": "1", "siguiendo": "1"}), d / "cuentas.csv.gz")
    _gz(pd.DataFrame({"publicacion_id": ["pL", "pB", "pZ"], "fuente_id": "f1", "fecha": "2026-09-01T09:00:00-03:00",
                      "titular": "t"}), d / "publicaciones.csv.gz")
    (d / "fuentes.csv").write_text("fuente_id,nombre,tipo\nf1,x,medio\n")
    _gz(pd.DataFrame({"comentario_id": com.comentario_id, "narrativa_id": ["L1"] * 20 + ["B1"] * 20,
                      "postura": "apoya"}), d / "verdad" / "comentarios.csv.gz")
    _gz(pd.DataFrame({"cuenta_id": [f"u{i}" for i in range(12)], "campana_id": ["C1"] * 3 + [""] * 9}),
        d / "verdad" / "cuentas.csv.gz")
    pd.DataFrame({"narrativa_id": ["L1", "B1"], "emergente": "no", "fecha_origen": "2026-09-01T10:00:00-03:00"}) \
        .to_csv(d / "verdad" / "narrativas.csv", index=False)
    return d


def test_variante_sin_tema_filtra_datos_y_verdad_en_conjunto(tmp_path):
    d = _practica(tmp_path)
    v = validar.variantes(d)
    assert {"completo", "sin_litio", "solo_colectivo", "submuestra75", "primera_mitad"} <= set(v)
    out = validar.armar_variante(d, tmp_path / "sin_litio", v["sin_litio"])
    com = pd.read_csv(out / "comentarios.csv.gz")
    assert set(com.publicacion_id) == {"pB"}
    assert set(pd.read_csv(out / "verdad" / "comentarios.csv.gz").narrativa_id) == {"B1"}
    assert set(pd.read_csv(out / "verdad" / "narrativas.csv").narrativa_id) == {"B1"}
    assert set(pd.read_csv(out / "cuentas.csv.gz").cuenta_id) == set(com.cuenta_id)       # solo cuentas usadas
    assert set(pd.read_csv(out / "publicaciones.csv.gz").publicacion_id) == {"pB"}


def test_ensuciado_agrega_duplicados_y_rompe_campos_sin_perder_filas(tmp_path):
    d = _practica(tmp_path)
    com = pd.read_csv(d / "comentarios.csv.gz", dtype=str, keep_default_na=False)
    sucio = validar._ensuciar(pd.concat([com] * 30, ignore_index=True), seed=1)   # 1.200 filas
    assert len(sucio) > 1200                                  # duplicados agregados
    assert (sucio["fecha"] == "fecha-invalida").any() and (sucio["me_gusta"] == "N/A").any()
