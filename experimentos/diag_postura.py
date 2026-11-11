import pandas as pd
a = pd.read_parquet("interim/practica/narrativas_asig.parquet")
v = pd.read_csv("datos/practica/verdad/comentarios.csv.gz", dtype=str, keep_default_na=False)
c = pd.read_parquet("interim/practica/comentarios.parquet")[["comentario_id", "respuesta_a"]]
d = a.merge(v, on="comentario_id").merge(c, on="comentario_id"); d = d[d.narrativa_id != "ninguna"]
for n, g in d.groupby("narrativa_id"):
    acc = (g.postura_x == g.postura_y).mean()
    gh = g[~g.heredado]; acc_nh = (gh.postura_x == gh.postura_y).mean()
    print(n, "acierto=%.3f (sin heredados %.3f, heredados %.3f)" % (acc, acc_nh, (g[g.heredado].postura_x == g[g.heredado].postura_y).mean()), g.narrativa.mode()[0])
