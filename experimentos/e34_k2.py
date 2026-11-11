"""E34 — ¿El modo (a) detecta K2? ¿Por qué no lo detecta el modo actual? (diagnóstico, sin tocar parámetros)"""
import pandas as pd, yaml
from pathlib import Path
exec(open("experimentos/e33_campanas_nuevas.py").read().split("datos = {}")[0])
I, D = SETS["campanas_nuevas"]
con = co.conectar(Path(I), cfg)
con.execute(f"""create table cm as select c.comentario_id, c.cuenta_id, c.publicacion_id, c.ts, c.respuesta_a, c.texto,
    coalesce(a.narrativa,'') narrativa, coalesce(a.postura,'') postura, a.micro,
    len(string_split(c.texto_norm,' ')) n_pal from '{I}/comentarios.parquet' c left join '{I}/narrativas_asig.parquet' a using(comentario_id)""")
v = pd.read_csv(f"{D}/verdad/cuentas.csv.gz", dtype=str, keep_default_na=False); camp = dict(zip(v.cuenta_id, v.campana_id))
k2 = [a for a, c in camp.items() if c == "K2"]
print(con.execute(f"select narrativa, postura, count(*) from cm where cuenta_id in {tuple(k2)} group by 1,2").df())
for modo in ["narr", "micro"]:
    s = sync_sql(con, 30, modo); g = detectar_grupos(s, 2, 0.1, 3, 5, 0.3, 42, 0.5)
    print(modo, "K2 detectadas:", sum(1 for a in k2 if a in g), "/", len(k2))
