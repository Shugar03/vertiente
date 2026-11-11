import numpy as np
import pytest

from radar.embed import PROMPTS, Embedder, dispositivo


class ModeloFalso:
    """Vector determinístico por texto; registra qué se le pidió embeber."""

    def __init__(self):
        self.pedidos = []

    def encode(self, textos, **kw):
        self.pedidos.extend(textos)
        v = np.array([[len(t), t.count("a") + 1, 1.0, 2.0] for t in textos], dtype=np.float32)
        return v / np.linalg.norm(v, axis=1, keepdims=True)


@pytest.fixture
def emb(tmp_path, monkeypatch):
    m = ModeloFalso()
    e = Embedder("intfloat/multilingual-e5-small", tmp_path / "cache", batch=2)
    monkeypatch.setattr(Embedder, "_modelo", lambda self: m)
    return e, m


def test_embebe_solo_unicos_con_prefijo_y_respeta_el_orden(emb):
    e, m = emb
    X, info = e.embeber(["h1", "h2", "h1"], ["casa", "agua azul", "casa"])
    assert X.shape == (3, 4) and X.dtype == np.float32
    np.testing.assert_allclose(X[0], X[2])
    assert info["nuevos"] == 2
    assert all(p.startswith(PROMPTS["intfloat/multilingual-e5-small"]) for p in m.pedidos)


def test_la_cache_evita_reembeber(emb):
    e, m = emb
    e.embeber(["h1"], ["casa"])
    m.pedidos.clear()
    X, info = e.embeber(["h1", "h2"], ["casa", "otra"])
    assert info["nuevos"] == 1 and info["en_cache"] == 1
    assert len(m.pedidos) == 1


def test_texto_vacio_no_rompe(emb):
    e, _ = emb
    X, _ = e.embeber(["h0"], [""])
    assert np.isfinite(X).all()


def test_truncado_matryoshka_renormaliza(emb):
    e, _ = emb
    e.dims = 2
    X, info = e.embeber(["h1"], ["casa"])
    assert X.shape == (1, 2) and info["dims"] == 2
    assert np.linalg.norm(X[0]) == pytest.approx(1.0, rel=1e-5)


def test_dispositivo_explicito():
    assert dispositivo("cpu") == "cpu"
    assert dispositivo("auto") in {"cpu", "mps", "cuda"}
