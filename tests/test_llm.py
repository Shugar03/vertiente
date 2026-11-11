import json
from types import SimpleNamespace

from radar.llm import Profesor


class ClienteFalso:
    """Imita client.beta.messages.create y cuenta llamadas."""

    def __init__(self, respuesta: dict, falla: bool = False):
        self.respuesta, self.falla, self.llamadas = respuesta, falla, 0
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.llamadas += 1
        if self.falla:
            raise RuntimeError("caído")
        return SimpleNamespace(
            stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text=json.dumps(self.respuesta))],
            usage=SimpleNamespace(input_tokens=1000, output_tokens=100),
        )


def test_juicio_de_narrativa_usa_cache_y_cuenta_costo(tmp_path):
    cli = ClienteFalso({"afirmacion": "La mina se queda con el agua", "lado_que_afirma": "B", "confianza": 0.9})
    p = Profesor(cache_dir=tmp_path, modelo="claude-opus-5-5", precio_in=4.0, precio_out=20.0, cliente=cli)
    r1 = p.juzgar_narrativa(["el agua se corta hace 20 años"], ["la mina se seca las vegas"])
    r2 = p.juzgar_narrativa(["el agua se corta hace 20 años"], ["la mina se seca las vegas"])
    assert r1 == r2 and r1["lado_que_afirma"] == "B"
    assert cli.llamadas == 1                                   # la segunda vino de la caché
    assert p.uso["tokens"] == 1100
    assert p.uso["usd"] == (1000 * 4.0 + 100 * 20.0) / 1e6


def test_sin_cliente_ni_cache_devuelve_none(tmp_path):
    p = Profesor(cache_dir=tmp_path, modelo="x", precio_in=0, precio_out=0, cliente=None)
    assert p.juzgar_narrativa(["a"], ["b"]) is None


def test_cache_commiteada_funciona_sin_clave(tmp_path):
    con = Profesor(cache_dir=tmp_path, modelo="m", precio_in=0, precio_out=0,
                   cliente=ClienteFalso({"afirmacion": "x", "lado_que_afirma": "A", "confianza": 1.0}))
    con.juzgar_narrativa(["a"], ["b"])
    sin = Profesor(cache_dir=tmp_path, modelo="m", precio_in=0, precio_out=0, cliente=None)
    assert sin.juzgar_narrativa(["a"], ["b"])["lado_que_afirma"] == "A"


def test_falla_de_api_no_rompe(tmp_path):
    p = Profesor(cache_dir=tmp_path, modelo="m", precio_in=0, precio_out=0,
                 cliente=ClienteFalso({}, falla=True), reintentos=1)
    assert p.juzgar_narrativa(["a"], ["b"]) is None


def test_respuesta_invalida_se_descarta(tmp_path):
    p = Profesor(cache_dir=tmp_path, modelo="m", precio_in=0, precio_out=0,
                 cliente=ClienteFalso({"lado_que_afirma": "C"}))
    assert p.juzgar_narrativa(["a"], ["b"]) is None
