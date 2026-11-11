"""Genera el set sintético de prueba "campanas_nuevas".

Objetivo: medir si un detector de coordinación generaliza más allá de las tres
campañas del set de práctica (C1, C2, C3). Se parte de ``datos/practica`` y:

1. **Se quitan las campañas originales.** Se eliminan todas las cuentas con
   ``campana_id`` en la verdad, todos sus comentarios y, recursivamente, todo
   comentario cuya cadena de ``respuesta_a`` llegue a un comentario eliminado.
   Las cuentas genuinas que quedan sin ningún comentario también se quitan
   (``cuentas.csv.gz`` lista solo cuentas activas, como en el original).

2. **Se inyectan tres campañas nuevas, de estilos distintos a las originales:**

   * **K1 – L1 / rechaza** ("la mina NO se queda con el agua"). 35 cuentas
     viejas (creadas 2 a 6 años antes del período), seguidores/seguidos tomados
     de la distribución genuina. Horario diurno (09-20 h). Textos variados
     tomados del pool genuino de L1-rechaza con variaciones (ningún texto se
     repite más de dos veces dentro de la campaña). En 15 publicaciones de
     litio, grupos de 4 a 10 cuentas K1 comentan dentro de ~20 minutos; ~25 %
     de esos comentarios son respuestas cortas de apoyo ("tal cual",
     "exacto"...) a comentarios de otras cuentas K1 y algunos comentarios de
     contenido también responden a otra cuenta K1. Además cada cuenta K1 tiene
     4 a 8 comentarios de cobertura en otras publicaciones (textos genuinos de
     otras narrativas, ambas posturas, algo de ruido, horario genuino); la
     verdad los etiqueta con su narrativa/postura real.
   * **K2 – B3 / apoya** ("hay que llamar a licitación"). 8 cuentas creadas
     1 a 5 días antes del período, pocos seguidores, muchos seguidos. Una sola
     plantilla con variaciones mínimas, SIN hashtag. 6 ráfagas en 6
     publicaciones de colectivos, a horas aleatorias: las 8 cuentas dentro de
     ~10 minutos.
   * **K3 – H2 / apoya** ("faltan médicos"). 20 cuentas de antigüedad mixta
     (algunas de días, otras de años), baja actividad (3 a 5 comentarios cada
     una), horario vespertino/nocturno (19-02 h). En 5 publicaciones de
     hospital, grupos de 6 a 12 cuentas K3 comentan dentro de ~15 minutos; el
     resto de sus comentarios son sueltos, de noche, en otras publicaciones de
     hospital. Textos parafraseados (pool genuino de H2-apoya con variaciones).

   Toda respuesta corta de apoyo hereda narrativa y postura de su comentario
   padre (regla del README).

3. **Trampas genuinas (sin campana_id):**

   * **Ráfaga viral:** en una publicación muy activa se agregan 150
     comentarios de 150 cuentas genuinas existentes (que no habían comentado
     ahí) dentro de 30 minutos, con textos variados de las narrativas de esa
     publicación (y algo de ruido), etiquetados en la verdad.
   * **Frase copiada:** un eslogan de H1-apoya publicado por 80 cuentas
     genuinas existentes, repartidas en muchos días y publicaciones de
     hospital, en horario genuino.

Ids nuevos: cuentas desde ``u016116`` (mezcladas al azar entre campañas) y
comentarios desde ``c0200001`` (en orden temporal). En la verdad de narrativas
se conserva ``fecha_origen``/``publicacion_origen`` salvo que el comentario de
origen haya sido quitado (H3, que originaba C3): ahí pasa al primer comentario
genuino que queda. Ningún comentario inyectado precede al origen de su
narrativa. Se actualizan ``comentarios`` e ``impulsada_por`` = K1/K2/K3.
``resumen.json`` agrega, además de los campos originales, las ráfagas de cada
campaña y la ubicación de las trampas (``comentarios_campana`` = comentarios de
cuentas de campaña sobre su narrativa/postura empujada).

Uso::

    uv run python sinteticos/generar_campanas_nuevas.py
"""

from __future__ import annotations

import json
import random
import re
import shutil
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261111
RAIZ = Path(__file__).resolve().parents[1]
ORIGEN = RAIZ / "datos" / "practica"
DESTINO = RAIZ / "salida" / "sinteticos" / "campanas_nuevas"

INICIO = datetime(2026, 9, 1, 0, 0, 0)
FIN = datetime(2026, 9, 14, 23, 59, 59)
FMT = "%Y-%m-%dT%H:%M:%S-03:00"

K1_NARR, K1_POST = "L1", "rechaza"
K2_NARR, K2_POST = "B3", "apoya"
K3_NARR, K3_POST = "H2", "apoya"
ESLOGAN_NARR, ESLOGAN_POST = "H1", "apoya"
ESLOGAN = "Hospital sin terminar, plata sin aparecer."

rng = np.random.default_rng(SEED)
rnd = random.Random(SEED)


# --------------------------------------------------------------------------- utilidades
def leer(nombre: str) -> pd.DataFrame:
    return pd.read_csv(ORIGEN / nombre, dtype=str, keep_default_na=False)


def parse(s: str) -> datetime:
    return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")


def fmt(d: datetime) -> str:
    return d.strftime(FMT)


def sin_tildes(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


PREFIJOS = ["Mirá, ", "La verdad que ", "Ojo, ", "Para mí ", "A ver, ", "Y bueno, ",
            "Hay que decirlo: ", "Te digo algo: ", "Sinceramente ", "Che, "]
SUFIJOS = [" Abran los ojos.", " Así estamos.", " eh.", " Posta.", " 🙄", " 👏", " Basta de verso.",
           " Infórmense.", " Es así.", " 🤷"]
PREF_RE = re.compile(r"^(mir[aá],|la verdad q(ue)?|ojo,|para m[ií]|pa m[ií]|a ver,|y bueno,|hay q(ue)? decirlo:|"
                     r"te digo algo:|sinceramente|che,|escuchen:|lo que nadie dice es que|como siempre,|jaja)",
                     re.IGNORECASE)


def variar(texto: str, fuerza: float = 0.7) -> str:
    """Variación liviana estilo usuario: prefijo, sufijo, minúsculas, sin tildes, typo."""
    t = texto.strip()
    if rnd.random() < fuerza * 0.45 and not PREF_RE.match(t):
        t = rnd.choice(PREFIJOS) + t[0].lower() + t[1:]
    if rnd.random() < fuerza * 0.35:
        base = t.rstrip(" .!")
        t = base + "." + rnd.choice(SUFIJOS) if not base.endswith(("?", ")")) else t + rnd.choice(SUFIJOS)
    if rnd.random() < fuerza * 0.25:
        t = t.lower()
    if rnd.random() < fuerza * 0.2:
        t = sin_tildes(t)
    if rnd.random() < fuerza * 0.15:
        palabras = [i for i, w in enumerate(t.split(" ")) if len(w) > 5 and w.isalpha()]
        if palabras:
            ws = t.split(" ")
            i = rnd.choice(palabras)
            w = ws[i]
            j = rnd.randrange(1, len(w) - 2)
            ws[i] = w[:j] + w[j + 1] + w[j] + w[j + 2:]
            t = " ".join(ws)
    return t


NOMBRES = ["pocho", "lu", "beto", "pao", "negro", "lauti", "marce", "tano", "vale", "lucas", "cachi", "vicky",
           "pepa", "gonza", "fer", "flor", "mati", "caro", "nacho", "juli", "sofi", "santi", "agus", "romi",
           "checho", "mili", "facu", "tincho", "coco", "pato", "nico", "ana", "rocio", "dani", "eli", "gabi",
           "javi", "kari", "male", "migue", "naty", "oscar", "quique", "raul", "silvi", "tere", "walter"]
LUGARES = ["sur", "norte", "valle", "real", "salta", "zona", "tolar", "puna", "cerro", "andino", "salteño", "del.pueblo"]


def nuevo_usuario(existentes: set[str], estilo: str = "normal") -> str:
    while True:
        if estilo == "nuevo" and rnd.random() < 0.6:
            u = f"user{rnd.randint(10000, 999999)}"
        else:
            n = rnd.choice(NOMBRES)
            sep = rnd.choice(["", ".", "_"])
            r = rnd.random()
            if r < 0.35:
                u = f"{n}{sep}{rnd.choice(LUGARES)}{rnd.randint(1, 999) if rnd.random() < 0.6 else ''}"
            elif r < 0.7:
                u = f"{n}{sep}{rnd.randint(1, 99999)}"
            else:
                u = f"{n}{rnd.choice(['', '.', '_'])}{rnd.choice(NOMBRES)}{rnd.randint(1, 99)}"
        if u not in existentes:
            existentes.add(u)
            return u


# --------------------------------------------------------------------------- carga
def main() -> None:
    com = leer("comentarios.csv.gz")
    cue = leer("cuentas.csv.gz")
    pub = leer("publicaciones.csv.gz")
    v_com = leer("verdad/comentarios.csv.gz")
    v_cue = leer("verdad/cuentas.csv.gz")
    narr = leer("verdad/narrativas.csv")
    COLS_COM, COLS_CUE = list(com.columns), list(cue.columns)
    COLS_VCOM, COLS_VCUE, COLS_NARR = list(v_com.columns), list(v_cue.columns), list(narr.columns)

    n_com0, n_cue0 = len(com), len(cue)

    # ----------------------------------------------------------------------- 1. quitar campañas
    camp_cuentas = set(v_cue.loc[v_cue.campana_id != "", "cuenta_id"])
    removidos = set(com.loc[com.cuenta_id.isin(camp_cuentas), "comentario_id"])
    hijos: dict[str, list[str]] = {}
    for cid, padre in zip(com.comentario_id, com.respuesta_a):
        if padre:
            hijos.setdefault(padre, []).append(cid)
    pila = list(removidos)
    while pila:
        x = pila.pop()
        for h in hijos.get(x, []):
            if h not in removidos:
                removidos.add(h)
                pila.append(h)
    n_desc = len(removidos) - int(com.cuenta_id.isin(camp_cuentas).sum())
    com = com[~com.comentario_id.isin(removidos)].copy()
    v_com = v_com[v_com.comentario_id.isin(set(com.comentario_id))].copy()
    activas = set(com.cuenta_id)
    cue = cue[cue.cuenta_id.isin(activas)].copy()
    print(f"[quitar] cuentas de campaña: {len(camp_cuentas)}, comentarios quitados: {len(removidos)} "
          f"({n_desc} respuestas descendientes), cuentas genuinas sin actividad quitadas: "
          f"{n_cue0 - len(camp_cuentas) - len(cue)}")

    # tablas auxiliares
    m = com.merge(v_com, on="comentario_id")
    m["dt"] = pd.to_datetime(m.fecha.str[:19])
    pub["dt"] = pd.to_datetime(pub.fecha.str[:19])
    pf = dict(zip(pub.publicacion_id, pub.dt))
    temas = (m[m.narrativa_id != "ninguna"].assign(t=lambda d: d.narrativa_id.str[0])
             .groupby("publicacion_id").t.agg(lambda s: s.value_counts().idxmax()))
    pub["tema"] = pub.publicacion_id.map(temas).fillna("")
    posts_tema = {t: pub[pub.tema == t].publicacion_id.tolist() for t in "LBH"}
    n_por_post = com.publicacion_id.value_counts()

    # origen de cada narrativa: se conserva el original si su comentario sigue en el set; si no
    # (p. ej. H3, que originaba C3) pasa al primer comentario genuino que queda.
    ORIG: dict[str, tuple[datetime, str]] = {}
    for r in narr.itertuples():
        g = m[m.narrativa_id == r.narrativa_id]
        if ((g.fecha == r.fecha_origen) & (g.publicacion_id == r.publicacion_origen)).any():
            ORIG[r.narrativa_id] = (parse(r.fecha_origen), r.publicacion_origen)
        else:
            f0 = g.sort_values("dt").iloc[0]
            ORIG[r.narrativa_id] = (parse(f0.fecha), f0.publicacion_id)

    likes_emp = m.me_gusta.astype(int).to_numpy()
    mm = m.merge(pub[["publicacion_id", "dt"]].rename(columns={"dt": "pdt"}), on="publicacion_id")
    demoras_h = ((mm.dt - mm.pdt).dt.total_seconds() / 3600).to_numpy()
    horas_emp = m.dt.dt.hour.to_numpy()

    top = m[m.respuesta_a == ""]
    def pool(narrativa: str, postura: str, minlen: int = 25) -> list[str]:
        s = top[(top.narrativa_id == narrativa) & (top.postura == postura)].texto
        s = s[s.str.len() >= minlen].drop_duplicates()
        return s.sample(frac=1, random_state=int(rng.integers(1 << 30))).tolist()

    cortos = m[(m.respuesta_a != "") & (m.texto.str.len() < 25) & (m.narrativa_id != "ninguna")].texto
    cortos_vc = cortos.value_counts()
    cortos_vc = cortos_vc[cortos_vc >= 20]
    CORTOS = cortos_vc.index.tolist()
    CORTOS_P = (cortos_vc / cortos_vc.sum()).to_numpy()

    def corto() -> str:
        return CORTOS[int(rng.choice(len(CORTOS), p=CORTOS_P))]

    def likes(escala: float = 1.0, maximo: int | None = None) -> int:
        x = int(round(int(rng.choice(likes_emp)) * escala))
        return min(x, maximo) if maximo is not None else x

    def hora_genuina_tras(post: str, minimo: datetime | None = None) -> datetime:
        base = pf[post]
        for _ in range(200):
            d = base + timedelta(hours=float(rng.choice(demoras_h)))
            if d <= FIN and (minimo is None or d >= minimo):
                return d
        return min(base + timedelta(minutes=int(rng.integers(5, 120))), FIN)

    # ----------------------------------------------------------------------- cuentas nuevas
    usuarios = set(cue.usuario) | set(leer("cuentas.csv.gz").usuario)
    max_u = max(int(x[1:]) for x in leer("cuentas.csv.gz").cuenta_id)
    n_k = {"K1": 35, "K2": 8, "K3": 20}
    ids = [f"u{max_u + 1 + i:06d}" for i in range(sum(n_k.values()))]
    rnd.shuffle(ids)
    seg_emp = cue[["seguidores", "siguiendo"]].astype(int).to_numpy()
    nuevas_cuentas, cuentas_k = [], {}
    pos = 0
    for k, n in n_k.items():
        cuentas_k[k] = sorted(ids[pos:pos + n])
        pos += n
        for uid in cuentas_k[k]:
            if k == "K1":
                creada = INICIO - timedelta(days=int(rng.integers(2 * 365, 6 * 365)))
                s, g = seg_emp[int(rng.integers(len(seg_emp)))]
                s = max(0, int(s * rng.uniform(0.85, 1.15)))
                g = max(7, int(g * rng.uniform(0.85, 1.15)))
                user = nuevo_usuario(usuarios)
            elif k == "K2":
                creada = INICIO - timedelta(days=int(rng.integers(1, 6)))
                s = int(rng.integers(0, 15))
                g = int(rng.integers(900, 2600))
                user = nuevo_usuario(usuarios, "nuevo")
            else:
                if rng.random() < 0.45:
                    creada = INICIO - timedelta(days=int(rng.integers(2, 25)))
                    s = int(rng.integers(0, 40))
                    g = int(rng.integers(60, 600))
                    user = nuevo_usuario(usuarios, "nuevo")
                else:
                    creada = INICIO - timedelta(days=int(rng.integers(365, 8 * 365)))
                    s, g = seg_emp[int(rng.integers(len(seg_emp)))]
                    user = nuevo_usuario(usuarios)
            nuevas_cuentas.append(dict(cuenta_id=uid, usuario=user, fecha_creacion=creada.strftime("%Y-%m-%d"),
                                       seguidores=str(int(s)), siguiendo=str(int(g)), campana_id=k))

    # nuevos comentarios: lista de dicts con clave local "key" (luego se asigna id real)
    nuevos: list[dict] = []
    contador = [0]

    def agregar(post, cuenta, fecha, texto, narrativa, postura, padre="", me_gusta=None, origen=""):
        contador[0] += 1
        key = f"N{contador[0]:06d}"
        assert fecha >= pf[post], (post, fecha)
        assert fecha <= FIN
        assert narrativa == "ninguna" or fecha > ORIG[narrativa][0], (narrativa, fecha)
        nuevos.append(dict(key=key, publicacion_id=post, cuenta_id=cuenta, dt=fecha, texto=texto,
                           respuesta_a=padre, me_gusta=likes() if me_gusta is None else me_gusta,
                           narrativa_id=narrativa, postura=postura, origen=origen))
        return key

    # ----------------------------------------------------------------------- K1
    k1 = cuentas_k["K1"]
    pool_k1 = pool(K1_NARR, K1_POST, 30)
    usos_k1: dict[str, int] = {}

    def texto_k1() -> str:
        for _ in range(1000):
            t = variar(pool_k1.pop(), 0.8) if pool_k1 else None
            if t and usos_k1.get(t, 0) < 2:
                usos_k1[t] = usos_k1.get(t, 0) + 1
                return t
        raise RuntimeError("pool K1 agotado")

    usos_cortos: dict[str, int] = {}

    def corto_unico(max_usos: int = 2) -> str:
        for _ in range(500):
            t = corto()
            if rng.random() < 0.15:
                t = t + rnd.choice([" 👏", " 💯", "!", " eh"])
            if usos_cortos.get(t, 0) < max_usos:
                usos_cortos[t] = usos_cortos.get(t, 0) + 1
                return t
        return t

    cand_k1 = [p for p in posts_tema["L"] if n_por_post.get(p, 0) >= 80 and pf[p] < FIN - timedelta(days=1)]
    cand_k1.sort(key=lambda p: pf[p])
    # repartir en el período: 15 posts de días distintos cuando se pueda
    elegidos_k1 = []
    tramos = np.array_split(np.array(cand_k1), 15)
    for tr in tramos:
        elegidos_k1.append(str(rng.choice(tr)))
    k1_bursts = []
    for post in elegidos_k1:
        base = pf[post] + timedelta(minutes=float(rng.uniform(15, 300)))
        if not (9 <= base.hour < 20) or base.hour >= 19 and base.minute > 35:
            dia = base.date() if base.hour < 9 else base.date() + timedelta(days=1)
            base = datetime.combine(dia, datetime.min.time()) + timedelta(hours=float(rng.uniform(9.2, 19.3)))
        g = int(rng.integers(4, 11))
        miembros = rnd.sample(k1, g)
        n_cortos = max(1, int(round(g * 0.25)))
        n_cont = g - n_cortos
        offs = sorted(rng.uniform(0, 14, n_cont))
        claves = []
        for i, (cuenta, off) in enumerate(zip(miembros[:n_cont], offs)):
            padre = ""
            if i > 0 and rng.random() < 0.2:
                padre = rnd.choice(claves)[0]
            f = base + timedelta(minutes=float(off), seconds=int(rng.integers(0, 60)))
            if padre:
                f = max(f, dict((c, t) for c, t in claves)[padre] + timedelta(seconds=40))
            claves.append((agregar(post, cuenta, f, texto_k1(), K1_NARR, K1_POST, padre, origen="K1"), f))
        for cuenta in miembros[n_cont:]:
            padre, fp = rnd.choice(claves)
            f = fp + timedelta(seconds=int(rng.integers(30, 330)))
            agregar(post, cuenta, f, corto_unico(), K1_NARR, K1_POST, padre, me_gusta=likes(0.5), origen="K1")
        k1_bursts.append((post, fmt(base), g))
    # cobertura
    otros = top[(top.narrativa_id != K1_NARR) & (top.texto.str.len() >= 15)]
    for cuenta in k1:
        for _ in range(int(rng.integers(4, 9))):
            fila = otros.iloc[int(rng.integers(len(otros)))]
            if fila.narrativa_id == "ninguna":
                post = str(rng.choice(pub.publicacion_id[pub.dt < pd.Timestamp(FIN - timedelta(hours=2))]))
            else:
                post = str(rng.choice([p for p in posts_tema[fila.narrativa_id[0]] if pf[p] < FIN - timedelta(hours=2)
                                       and pf[p] > ORIG[fila.narrativa_id][0]]))
            agregar(post, cuenta, hora_genuina_tras(post), variar(fila.texto, 0.5), fila.narrativa_id, fila.postura,
                    origen="K1-cobertura")

    # ----------------------------------------------------------------------- K2
    k2 = cuentas_k["K2"]

    def texto_k2() -> str:
        a = rnd.choice(["Licitación ya", "Licitación YA", "licitación ya", "Licitacion ya", "LICITACIÓN YA"])
        b = rnd.choice(["veinte años", "20 años", "veinte años", "veinte años"])
        c = rnd.choice(["cada vez peor", "cada vez peor", "cada día peor"])
        d = rnd.choice([".", ".", "!", "!!", ". 👏", " 🚌", ""])
        return f"{a}: {b} con las mismas empresas y el servicio {c}, que entren otras{d}"

    cand_k2 = [p for p in posts_tema["B"] if pf[p] < FIN - timedelta(hours=12)]
    elegidos_k2 = [str(x) for x in rng.choice(cand_k2, 6, replace=False)]
    k2_bursts = []
    for post in elegidos_k2:
        base = pf[post] + timedelta(hours=float(rng.uniform(0.2, 10)))
        base = min(base, FIN - timedelta(minutes=30))
        offs = sorted(rng.uniform(0, 9.5, len(k2)))
        orden = rnd.sample(k2, len(k2))
        for cuenta, off in zip(orden, offs):
            agregar(post, cuenta, base + timedelta(minutes=float(off)), texto_k2(), K2_NARR, K2_POST,
                    me_gusta=int(rng.integers(0, 3)), origen="K2")
        k2_bursts.append((post, fmt(base), len(k2)))

    # ----------------------------------------------------------------------- K3
    k3 = cuentas_k["K3"]
    pool_k3 = pool(K3_NARR, K3_POST, 30)
    objetivo_k3 = {c: int(rng.integers(3, 6)) for c in k3}
    hechos_k3 = {c: 0 for c in k3}

    def noche(post: str, minimo_extra_h: float = 0.0) -> datetime:
        p0 = pf[post] + timedelta(hours=minimo_extra_h)
        for dias in range(0, 4):
            d = datetime.combine(p0.date() + timedelta(days=dias), datetime.min.time())
            h = float(rng.choice([19, 20, 21, 22, 23, 24, 25])) + float(rng.uniform(0, 0.75))
            f = d + timedelta(hours=h)
            if f >= p0 + timedelta(minutes=5) and f <= FIN - timedelta(minutes=20):
                return f
        return p0 + timedelta(minutes=10)

    cand_k3 = [p for p in posts_tema["H"] if pf[p] < FIN - timedelta(days=1)]
    elegidos_k3 = [str(x) for x in rng.choice(cand_k3, 5, replace=False)]
    k3_bursts = []
    for post in elegidos_k3:
        base = noche(post)
        g = int(rng.integers(6, 13))
        libres = sorted(k3, key=lambda c: (hechos_k3[c] - objetivo_k3[c], rnd.random()))
        miembros = [c for c in libres if hechos_k3[c] < objetivo_k3[c] - 1][:g]
        offs = sorted(rng.uniform(0, 14, len(miembros)))
        claves = []
        for cuenta, off in zip(miembros, offs):
            f = base + timedelta(minutes=float(off))
            if claves and rng.random() < 0.12:
                padre, fp = rnd.choice(claves)
                agregar(post, cuenta, max(f, fp + timedelta(seconds=45)), corto_unico(3), K3_NARR, K3_POST, padre,
                        me_gusta=likes(0.3, 6), origen="K3")
            else:
                claves.append((agregar(post, cuenta, f, variar(pool_k3.pop(), 0.6), K3_NARR, K3_POST,
                                       me_gusta=likes(0.4, 10), origen="K3"), f))
            hechos_k3[cuenta] += 1
        k3_bursts.append((post, fmt(base), len(miembros)))
    for cuenta in k3:
        while hechos_k3[cuenta] < objetivo_k3[cuenta]:
            post = str(rng.choice(cand_k3))
            agregar(post, cuenta, noche(post, float(rng.uniform(0, 30))), variar(pool_k3.pop(), 0.6),
                    K3_NARR, K3_POST, me_gusta=likes(0.4, 10), origen="K3")
            hechos_k3[cuenta] += 1

    # ----------------------------------------------------------------------- trampa: ráfaga viral
    cuentas_gen = sorted(cue.cuenta_id)
    viral_post = n_por_post[n_por_post.index.isin(posts_tema["B"])].index[0]
    ya = set(com.loc[com.publicacion_id == viral_post, "cuenta_id"])
    elegibles = [c for c in cuentas_gen if c not in ya]
    viral_cuentas = rnd.sample(elegibles, 150)
    viral_base = pf[viral_post] + timedelta(minutes=95)
    en_post = m[m.publicacion_id == viral_post]
    previos = en_post[(en_post.dt < viral_base) & (en_post.respuesta_a == "")]
    textos_post = en_post[(en_post.respuesta_a == "")]
    offs = sorted(rng.uniform(0, 29.5, 150))
    hechas = []
    for cuenta, off in zip(viral_cuentas, offs):
        f = viral_base + timedelta(minutes=float(off))
        r = rng.random()
        if r < 0.12 and len(previos):
            par = previos.iloc[int(rng.integers(len(previos)))]
            if par.narrativa_id != "ninguna":
                agregar(viral_post, cuenta, f, corto(), par.narrativa_id, par.postura, par.comentario_id,
                        origen="trampa-viral")
                continue
        if r < 0.2 and hechas:
            kp, fp, n_, p_ = rnd.choice(hechas)
            if n_ != "ninguna":
                agregar(viral_post, cuenta, max(f, fp + timedelta(seconds=20)), corto(), n_, p_, kp,
                        origen="trampa-viral")
                continue
        fila = textos_post.iloc[int(rng.integers(len(textos_post)))]
        key = agregar(viral_post, cuenta, f, variar(fila.texto, 0.6), fila.narrativa_id, fila.postura,
                      origen="trampa-viral")
        hechas.append((key, f, fila.narrativa_id, fila.postura))

    # ----------------------------------------------------------------------- trampa: frase copiada
    resto = [c for c in cuentas_gen if c not in set(viral_cuentas)]
    copia_cuentas = rnd.sample(resto, 80)
    cand_h = [p for p in posts_tema["H"] if pf[p] >= INICIO + timedelta(days=1) and pf[p] < FIN - timedelta(hours=3)]
    posts_copia = [str(x) for x in rng.choice(cand_h, 80, replace=len(cand_h) < 80)]
    for cuenta, post in zip(copia_cuentas, posts_copia):
        t = ESLOGAN
        r = rng.random()
        if r < 0.15:
            t = t.lower()
        elif r < 0.25:
            t = t.rstrip(".") + rnd.choice([" 👏", " 😡", "!", "..."])
        elif r < 0.32:
            t = sin_tildes(t)
        agregar(post, cuenta, hora_genuina_tras(post), t, ESLOGAN_NARR, ESLOGAN_POST, origen="trampa-frase")

    # ----------------------------------------------------------------------- ensamblar
    nv = pd.DataFrame(nuevos).sort_values(["dt", "key"]).reset_index(drop=True)
    max_c = max(int(x[1:]) for x in leer("comentarios.csv.gz").comentario_id)
    mapa = {k: f"c{max_c + 1 + i:07d}" for i, k in enumerate(nv.key)}
    nv["comentario_id"] = nv.key.map(mapa)
    nv["respuesta_a"] = nv.respuesta_a.map(lambda x: mapa.get(x, x))
    nv["fecha"] = nv.dt.map(fmt)
    nv["me_gusta"] = nv.me_gusta.astype(int).astype(str)
    nv["postura"] = nv.postura.fillna("")

    out_com = pd.concat([com[COLS_COM], nv[COLS_COM]], ignore_index=True)
    out_vcom = pd.concat([v_com[COLS_VCOM], nv[COLS_VCOM]], ignore_index=True)
    orden = out_com.assign(_d=pd.to_datetime(out_com.fecha.str[:19])).sort_values(["_d", "comentario_id"],
                                                                                kind="stable").index
    out_com = out_com.loc[orden].reset_index(drop=True)
    out_vcom = out_vcom.set_index("comentario_id").loc[out_com.comentario_id].reset_index()[COLS_VCOM]

    nc = pd.DataFrame(nuevas_cuentas)
    out_cue = pd.concat([cue[COLS_CUE], nc[COLS_CUE]], ignore_index=True).sort_values("cuenta_id").reset_index(drop=True)
    camp_map = dict(zip(nc.cuenta_id, nc.campana_id))
    out_vcue = pd.DataFrame({"cuenta_id": out_cue.cuenta_id,
                             "campana_id": out_cue.cuenta_id.map(lambda x: camp_map.get(x, ""))})[COLS_VCUE]

    # narrativas
    vm = out_com.merge(out_vcom, on="comentario_id")
    vm["_d"] = pd.to_datetime(vm.fecha.str[:19])
    cnt = vm.narrativa_id.value_counts()
    out_narr = narr.copy()
    cambios_origen = []
    for i, r in out_narr.iterrows():
        n_id = r.narrativa_id
        nueva_f, nueva_p = fmt(ORIG[n_id][0]), ORIG[n_id][1]
        if nueva_f != r.fecha_origen:
            cambios_origen.append((n_id, r.fecha_origen, nueva_f))
        out_narr.at[i, "fecha_origen"] = nueva_f
        out_narr.at[i, "publicacion_origen"] = nueva_p
        out_narr.at[i, "impulsada_por"] = {K1_NARR: "K1", K2_NARR: "K2", K3_NARR: "K3"}.get(n_id, "")
        out_narr.at[i, "comentarios"] = str(int(cnt.get(n_id, 0)))
    out_narr = out_narr[COLS_NARR]

    descr = {
        "K1": ("Cuentas antiguas (2-6 años) con cobertura en otros temas, textos variados de rechazo a L1, "
               "ráfagas diurnas de ~20 min en 15 publicaciones de litio con respuestas cortas de apoyo entre sí."),
        "K2": ("Cuentas creadas 1-5 días antes del período, pocos seguidores y muchos seguidos; una plantilla casi "
               "idéntica sin hashtag; 6 ráfagas de ~10 min (las 8 cuentas) a cualquier hora."),
        "K3": ("Cuentas de antigüedad mixta y baja actividad (3-5 comentarios), textos parafraseados; "
               "ráfagas nocturnas (19-02 h) de ~15 min con 6-12 cuentas en 5 publicaciones de hospital."),
    }
    out_camp = pd.DataFrame([
        dict(campana_id="K1", narrativa_id=K1_NARR, postura=K1_POST, cuentas=len(cuentas_k["K1"]), descripcion=descr["K1"]),
        dict(campana_id="K2", narrativa_id=K2_NARR, postura=K2_POST, cuentas=len(cuentas_k["K2"]), descripcion=descr["K2"]),
        dict(campana_id="K3", narrativa_id=K3_NARR, postura=K3_POST, cuentas=len(cuentas_k["K3"]), descripcion=descr["K3"]),
    ])
    k_narr = {"K1": (K1_NARR, K1_POST), "K2": (K2_NARR, K2_POST), "K3": (K3_NARR, K3_POST)}
    vm["camp"] = vm.cuenta_id.map(lambda x: camp_map.get(x, ""))
    en_camp = vm[vm.camp != ""]
    on_narr = sum(int(((en_camp.camp == k) & (en_camp.narrativa_id == n) & (en_camp.postura == p)).sum())
                  for k, (n, p) in k_narr.items())
    resumen = {
        "escenario": "campanas_nuevas",
        "dias": 14,
        "publicaciones": int(len(pub)),
        "comentarios": int(len(out_com)),
        "cuentas": int(len(out_cue)),
        "comentarios_ruido": int((out_vcom.narrativa_id == "ninguna").sum()),
        "comentarios_campana": on_narr,
        "comentarios_cuentas_campana": int(len(en_camp)),
        "cuentas_campana": {k: len(v) for k, v in cuentas_k.items()},
        "por_narrativa": {k: int(v) for k, v in cnt.items() if k != "ninguna"},
        "trampas": {
            "rafaga_viral": {"publicacion_id": viral_post, "inicio": fmt(viral_base), "minutos": 30,
                             "comentarios": 150, "cuentas": 150},
            "frase_copiada": {"texto": ESLOGAN, "narrativa_id": ESLOGAN_NARR, "postura": ESLOGAN_POST,
                              "cuentas": 80, "publicaciones": int(len(set(posts_copia)))},
        },
        "rafagas": {"K1": k1_bursts, "K2": k2_bursts, "K3": k3_bursts},
        "base": {"origen": "datos/practica", "campanas_quitadas": ["C1", "C2", "C3"],
                 "comentarios_quitados": len(removidos), "semilla": SEED},
    }

    # ----------------------------------------------------------------------- escribir
    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    (DESTINO / "verdad").mkdir(parents=True)
    out_com.to_csv(DESTINO / "comentarios.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    out_cue.to_csv(DESTINO / "cuentas.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    pub[leer("publicaciones.csv.gz").columns].to_csv(DESTINO / "publicaciones.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    shutil.copy(ORIGEN / "fuentes.csv", DESTINO / "fuentes.csv")
    out_vcom.to_csv(DESTINO / "verdad" / "comentarios.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    out_vcue.to_csv(DESTINO / "verdad" / "cuentas.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    out_narr.to_csv(DESTINO / "verdad" / "narrativas.csv", index=False)
    out_camp.to_csv(DESTINO / "verdad" / "campanas.csv", index=False)
    (DESTINO / "verdad" / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2))

    # ----------------------------------------------------------------------- autocontrol
    verificar(nv, cuentas_k, cambios_origen, n_com0)


def verificar(nv: pd.DataFrame, cuentas_k: dict, cambios_origen: list, n_com0: int) -> None:
    rd = lambda n: pd.read_csv(DESTINO / n, dtype=str, keep_default_na=False)  # noqa: E731
    c, a, p = rd("comentarios.csv.gz"), rd("cuentas.csv.gz"), rd("publicaciones.csv.gz")
    vc, va = rd("verdad/comentarios.csv.gz"), rd("verdad/cuentas.csv.gz")
    narr = rd("verdad/narrativas.csv")
    ref = {n: list(pd.read_csv(ORIGEN / n, nrows=1).columns) for n in
           ["comentarios.csv.gz", "cuentas.csv.gz", "publicaciones.csv.gz", "verdad/comentarios.csv.gz",
            "verdad/cuentas.csv.gz", "verdad/narrativas.csv"]}
    for n, cols in ref.items():
        assert list(rd(n).columns) == cols, n
    assert c.comentario_id.is_unique and a.cuenta_id.is_unique and a.usuario.is_unique
    assert set(c.comentario_id) == set(vc.comentario_id) and len(c) == len(vc), "verdad de comentarios"
    assert set(a.cuenta_id) == set(va.cuenta_id), "verdad de cuentas"
    assert set(c.cuenta_id) <= set(a.cuenta_id), "cuenta inexistente"
    assert set(a.cuenta_id) <= set(c.cuenta_id), "cuenta sin comentarios"
    assert set(c.publicacion_id) <= set(p.publicacion_id)
    assert c.comentario_id.str.fullmatch(r"c\d{7}").all() and a.cuenta_id.str.fullmatch(r"u\d{6}").all()
    assert c.fecha.str.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d-03:00").all()
    fe = dict(zip(c.comentario_id, pd.to_datetime(c.fecha.str[:19])))
    pfe = dict(zip(p.publicacion_id, pd.to_datetime(p.fecha.str[:19])))
    pub_c = dict(zip(c.comentario_id, c.publicacion_id))
    r = c[c.respuesta_a != ""]
    assert r.respuesta_a.isin(fe.keys()).all(), "respuesta_a inexistente"
    malos = sum(fe[x] < fe[y] for x, y in zip(r.comentario_id, r.respuesta_a))
    assert malos == 0, f"{malos} respuestas antes que su padre"
    assert all(pub_c[x] == pub_c[y] for x, y in zip(r.comentario_id, r.respuesta_a)), "respuesta en otra publicación"
    assert all(fe[x] >= pfe[pp] for x, pp in zip(nv.comentario_id, nv.publicacion_id))
    crea = dict(zip(a.cuenta_id, pd.to_datetime(a.fecha_creacion)))
    primer = c.assign(_d=c.comentario_id.map(fe)).groupby("cuenta_id")._d.min()
    assert all(primer[k] >= crea[k] for k in nv.cuenta_id.unique()), "comentario antes de crear la cuenta"
    vv = vc.merge(c, on="comentario_id")
    ok_post = ((vv.narrativa_id == "ninguna") & (vv.postura == "")) | (
        (vv.narrativa_id != "ninguna") & vv.postura.isin(["apoya", "rechaza"]))
    assert ok_post.all(), "postura inválida"
    # campañas
    vcamp = va[va.campana_id != ""].campana_id.value_counts().to_dict()
    assert vcamp == {k: len(v) for k, v in cuentas_k.items()}, vcamp
    vv = vv.merge(va, on="cuenta_id")
    vv["h"] = pd.to_datetime(vv.fecha.str[:19]).dt.hour
    print("\n[verificación] OK: ids únicos, verdad completa, cuentas válidas, respuestas válidas y en orden.")
    print(f"comentarios: {len(c)} (original {n_com0}), cuentas: {len(a)}, publicaciones: {len(p)}, "
          f"nuevos comentarios: {len(nv)}")
    for k in ["K1", "K2", "K3"]:
        g = vv[vv.campana_id == k]
        cabeza = g.groupby(["narrativa_id", "postura"]).size().sort_values(ascending=False)
        print(f"\n{k}: {g.cuenta_id.nunique()} cuentas, {len(g)} comentarios, "
              f"por cuenta min/max {g.cuenta_id.value_counts().min()}/{g.cuenta_id.value_counts().max()}, "
              f"respuestas {int((g.respuesta_a != '').sum())}")
        print("  narrativa/postura:", cabeza.head(5).to_dict())
        n_k, p_k = {"K1": ("L1", "rechaza"), "K2": ("B3", "apoya"), "K3": ("H2", "apoya")}[k]
        gk = g[(g.narrativa_id == n_k) & (g.postura == p_k)]
        print(f"  comentarios empujando {n_k}/{p_k}: {len(gk)}, publicaciones: {gk.publicacion_id.nunique()}, "
              f"horas: {gk.h.value_counts().sort_index().to_dict()}")
        print("  texto más repetido:", g.texto.value_counts().head(2).to_dict())
    print("\ntrampa viral:", nv[nv.origen == "trampa-viral"].publicacion_id.unique(),
          len(nv[nv.origen == "trampa-viral"]), "comentarios,",
          nv[nv.origen == "trampa-viral"].cuenta_id.nunique(), "cuentas,",
          nv[nv.origen == "trampa-viral"].dt.min(), "->", nv[nv.origen == "trampa-viral"].dt.max())
    fr = nv[nv.origen == "trampa-frase"]
    print("trampa frase:", len(fr), "comentarios,", fr.cuenta_id.nunique(), "cuentas,", fr.publicacion_id.nunique(),
          "publicaciones,", fr.dt.dt.date.nunique(), "días")
    print("cambios de fecha_origen:", cambios_origen)
    print(narr[["narrativa_id", "impulsada_por", "comentarios", "fecha_origen"]].to_string(index=False))
    print(f"\nEscrito en {DESTINO}")


if __name__ == "__main__":
    main()
