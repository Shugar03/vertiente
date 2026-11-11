"""Normalización de texto y señales léxicas GENÉRICAS (independientes del tema).

Regla del proyecto: nada de palabras de los temas de práctica acá. Solo español coloquial general.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

_URL = re.compile(r"https?://\S+|www\.\S+")
_MENCION = re.compile(r"@\w+")
_NO_ALFANUM = re.compile(r"[^a-z0-9ñ\s]")
_ESPACIOS = re.compile(r"\s+")
_RISA = re.compile(r"^(j[aeiou]){2,}j?$|^(ha){2,}h?$|^x?d+$")

# Abreviaturas de chat del español rioplatense/general.
_ABREV = {
    "q": "que", "k": "que", "x": "por", "xq": "porque", "pq": "porque", "porq": "porque",
    "tmb": "tambien", "tb": "tambien", "tbn": "tambien", "pa": "para", "d": "de",
    "dsp": "despues", "bn": "bien", "msj": "mensaje", "xa": "para", "sta": "esta",
}

# Muletillas y reacciones sin contenido proposicional.
_REACCIONES = {
    "uh", "uhh", "uhhh", "ah", "oh", "eh", "wow", "posta", "comparto", "jaja", "jajaja", "jajajaja",
    "ok", "okey", "dale", "fuerza", "ya fue", "che", "uff", "ufff", "mmm", "ehh", "naaa", "na",
}


def _sin_acentos(s: str) -> str:
    # Conserva la ñ; quita tildes y diéresis.
    s = s.replace("ñ", "\0")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s.replace("\0", "ñ")


def normalizar(texto: str | None) -> str:
    if not texto:
        return ""
    s = _URL.sub(" ", texto.lower())
    s = _MENCION.sub(" ", s)
    s = _sin_acentos(s)
    s = _NO_ALFANUM.sub(" ", s)
    tokens = [_ABREV.get(t, t) for t in _ESPACIOS.split(s) if t]
    return " ".join(tokens)


def hash_texto(texto_norm: str) -> str:
    return hashlib.blake2b(texto_norm.encode(), digest_size=10).hexdigest()


def solo_reaccion(texto: str | None) -> bool:
    """Emoji, risa, muletilla o vacío: no afirma nada por sí mismo."""
    n = normalizar(texto)
    if not n:
        return True
    if n in _REACCIONES:
        return True
    return all(_RISA.match(t) or t in _REACCIONES for t in n.split())


def es_pregunta(texto: str | None) -> bool:
    return bool(texto) and ("?" in texto or "¿" in texto)
