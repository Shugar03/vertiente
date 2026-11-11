"""Título y frases clave de cada narrativa sin LLM (respaldo): texto representativo + c-TF-IDF."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

# Stopwords y muletillas generales del español (no dependen del tema).
STOP = set("""a al algo algun alguna algunos ante antes aqui asi aun bien cada como con contra cual cuando de del desde
donde dos el ella ellos en entre era es esa ese eso esta estan este esto estos fue ha hay hace hasta la las le les lo
los mas me mi mientras mucho muy nada ni no nos o otra otro para pero poco por porque que quien se sea ser si sin sobre
solo son su sus tambien te tiene todo todos tu un una uno unos y ya yo vos ahora siempre nunca otra vez
che mira ojo escuchen sinceramente posta jaja jajaja te digo algo hay que decirlo lo que nadie dice para mi a ver
mira verguenza triste lamentable despierten abran los ojos asi estamos serio digo""".split())

_RELLENO_INICIO = re.compile(
    r"^(che|mira|mirá|ojo|escuchen|sinceramente|jaja\w*|a ver|te digo algo|hay que decirlo|lo que nadie dice es que|"
    r"para m[ií])[:,]?\s+", re.I)
_RELLENO_FIN = re.compile(r"[,.]?\s*(posta|lamentable|verg[uü]enza|triste|despierten|abran los ojos|as[ií] estamos|"
                          r"ojo|lo digo en serio\??)\.?\s*$", re.I)
_EMOJI = re.compile(r"[^\w\s,.;:¿?¡!'\"()%$#@/-]")


def limpiar_titulo(texto: str) -> str:
    t = _EMOJI.sub("", texto or "").strip()
    for _ in range(2):
        t = _RELLENO_INICIO.sub("", t).strip()
        t = _RELLENO_FIN.sub("", t).strip()
    t = t.rstrip(" ,;:")
    return (t[:1].upper() + t[1:]) if t else t


def titulo_representativo(textos: pd.Series) -> str:
    """El texto crudo más repetido (tras limpiar muletillas) del lado que apoya."""
    limpios = textos.map(limpiar_titulo)
    limpios = limpios[limpios.str.split().str.len() >= 5]
    return limpios.value_counts().index[0] if len(limpios) else ""


def frases_clave(docs: dict[str, str], top: int = 5) -> dict[str, list[str]]:
    """c-TF-IDF: cada narrativa es un documento; términos (1-2 gramas) más característicos frente al resto."""
    claves = list(docs)
    if not claves:
        return {}
    vec = TfidfVectorizer(ngram_range=(1, 2), stop_words=list(STOP), min_df=1, sublinear_tf=True,
                          token_pattern=r"(?u)\b[a-zñ]{3,}\b")
    M = vec.fit_transform([docs[k] for k in claves])
    vocab = np.array(vec.get_feature_names_out())
    out = {}
    for i, k in enumerate(claves):
        fila = M.getrow(i).toarray().ravel()
        orden = np.argsort(-fila)
        elegidas: list[str] = []
        for j in orden:
            if fila[j] <= 0 or len(elegidas) >= top:
                break
            term = vocab[j]
            if any(term in e or e in term for e in elegidas):
                continue
            elegidas.append(term)
        out[k] = elegidas
    return out
