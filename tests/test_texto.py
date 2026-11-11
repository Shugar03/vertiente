from radar.texto import es_pregunta, normalizar, solo_reaccion


def test_normaliza_mayusculas_acentos_y_signos():
    assert normalizar("LO QUE NADIE DICE: ¡la consulta previa es un DERECHO!") == \
        "lo que nadie dice la consulta previa es un derecho"


def test_normaliza_abreviaturas_de_chat():
    assert normalizar("x q tmb paran?") == "por que tambien paran"


def test_quita_urls_menciones_y_emojis_conserva_hashtag_como_palabra():
    assert normalizar("Miren @juan https://x.example/a 🙏 #ElLitioEsFuturo") == "miren ellitioesfuturo"


def test_texto_vacio_o_nulo():
    assert normalizar(None) == ""
    assert normalizar("   ") == ""
    assert normalizar("👀👀") == ""


def test_solo_reaccion():
    for t in ["👀", "Uhhh", "jajaja posta", "🙏🙏", "", "Comparto"]:
        assert solo_reaccion(t), t
    assert not solo_reaccion("las vegas estan secas por el bombeo")


def test_es_pregunta():
    assert es_pregunta("Alguien sabe si mañana hay paro?")
    assert not es_pregunta("Es un robo.")
