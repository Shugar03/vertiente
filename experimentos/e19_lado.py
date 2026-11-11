"""E19 — Señales para elegir el lado 'apoya' (sobre la salida real; lado verdadero por mayoría)."""
import numpy as np, pandas as pd
from radar.narrativas.origen import origen_robusto
a = pd.read_parquet("interim/practica/narrativas_asig.parquet")
c = pd.read_parquet("interim/practica/comentarios.parquet")
v = pd.read_csv("datos/practica/verdad/comentarios.csv.gz", dtype=str, keep_default_na=False)
d = c.merge(a, on="comentario_id").merge(v, on="comentario_id"); d = d[(d.narrativa != "") & ~d.heredado]
pad = dict(zip(c.comentario_id, c.respuesta_a)); post = dict(zip(a.comentario_id, a.postura)); ts = dict(zip(c.comentario_id, c.ts))
NEG = r"\b(no|nunca|nadie|nada|mentira|falso|verso|exager\w*|invent\w*)\b"
filas = []
for n, g in d.groupby("narrativa"):
    s = {}
    for p in ["apoya", "rechaza"]:
        h = g[g.postura_x == p]
        s[p] = dict(vol=len(h), frac_resp=h.respuesta_a.notna().mean(), orig=origen_robusto(h.ts, 3, 5), neg=h.texto_norm.str.contains(NEG).mean(),
                    likes=h.me_gusta.mean(), largo=h.texto_norm.str.len().mean(), verdad=(h.postura_y == "apoya").mean())
    # primeras respuestas de inversión: ¿de qué lado es el padre?
    r = g[g.respuesta_a.notna()].sort_values("ts").head(30)
    padre_lado = r.respuesta_a.map(post).value_counts()
    A, R = s["apoya"], s["rechaza"]
    filas.append(dict(n=n, verdad_ok=A["verdad"] > 0.5, gap_h=(R["orig"] - A["orig"]).total_seconds() / 3600,
                      d_frac_resp=R["frac_resp"] - A["frac_resp"], d_vol=A["vol"] - R["vol"], d_neg=R["neg"] - A["neg"],
                      d_likes=A["likes"] - R["likes"], d_largo=A["largo"] - R["largo"],
                      primeras_padre_apoya=padre_lado.get("apoya", 0) - padre_lado.get("rechaza", 0)))
print(pd.DataFrame(filas).round(3).to_string())
