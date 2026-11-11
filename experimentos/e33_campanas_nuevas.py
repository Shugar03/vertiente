"""E33 — Correcciones generales tras el set sintético de campañas nuevas.
(a) clave de alineación [corregido: el modo "prod" excluye el ruido como producción]: los comentarios de ruido se alinean por microgrupo semántico (una campaña que nadie discute
    no debe volverse invisible); (b) expansión de grupos confirmados con lazos débiles (sync>=1 o respuestas).
Se elige por promedio y peor caso sobre: práctica, variantes de estrés y el set sintético."""
import itertools, yaml
from pathlib import Path
import numpy as np, pandas as pd
from radar.stages import coordinacion as co
from radar.coordinacion.grafo import detectar_grupos
from radar.coordinacion.senales import respuestas_entre_cuentas
from radar.eval.puntaje import puntuar_coordinacion
cfg = yaml.safe_load(open("config.yaml"))
SETS = {"practica": ("interim/practica", "datos/practica"),
        "submuestra75": ("salida/validacion/interim/submuestra75", "salida/validacion/datos/submuestra75"),
        "primera_mitad": ("salida/validacion/interim/primera_mitad", "salida/validacion/datos/primera_mitad"),
        "sin_hospital": ("salida/validacion/interim/sin_hospital", "salida/validacion/datos/sin_hospital"),
        "campanas_nuevas": ("salida/sinteticos/_interim/campanas_nuevas", "salida/sinteticos/campanas_nuevas")}

def sync_sql(con, W, modo):
    clave = {"prod": "case when narrativa<>'' then narrativa||'/'||postura end",          # producción: ruido excluido
             "ruido1": "case when narrativa<>'' then narrativa||'/'||postura else 'ruido' end",  # ruido = una clase
             "micro": "case when narrativa<>'' then narrativa||'/'||postura when n_pal>=6 then 'm'||micro end"}[modo]
    return con.execute(f"""
        with n as (select *, {clave} k from cm where ts is not null), n2 as (select * from n where k is not null),
        act as (select cuenta_id, count(distinct publicacion_id) d from n2 group by 1),
        s as (select least(a.cuenta_id,b.cuenta_id) x, greatest(a.cuenta_id,b.cuenta_id) y, count(distinct a.publicacion_id) sync
              from n2 a join n2 b on a.publicacion_id=b.publicacion_id and a.k=b.k and a.cuenta_id<>b.cuenta_id
              and b.ts>=a.ts and b.ts<=a.ts + interval {W} minute group by 1,2)
        select s.x, s.y, s.sync, s.sync/least(ax.d,ay.d) sync_n from s join act ax on ax.cuenta_id=s.x join act ay on ay.cuenta_id=s.y""").df()

def expandir(g, sync, resp, frac, min_lazos):
    if not g: return g
    tam = pd.Series(g).value_counts()
    l = pd.concat([sync[sync.sync >= 1][["x", "y"]], resp[["x", "y"]]])
    l = pd.concat([l.rename(columns={"x": "c", "y": "m"}), l.rename(columns={"y": "c", "x": "m"})]).drop_duplicates()
    l = l[~l.c.isin(g.keys()) & l.m.isin(g.keys())]
    if l.empty: return g
    l["g"] = l.m.map(g); k = l.groupby(["c", "g"]).size().reset_index(name="k"); k["f"] = k.k / k.g.map(tam)
    k = k[(k.f >= frac) & (k.k >= min_lazos)].sort_values("f", ascending=False).drop_duplicates("c")
    return {**g, **dict(zip(k.c, k.g))}

datos = {}
for nombre, (I, D) in SETS.items():
    con = co.conectar(Path(I), cfg)
    con.execute(f"""create table cm as select c.comentario_id, c.cuenta_id, c.publicacion_id, c.ts, c.respuesta_a,
        coalesce(a.narrativa,'') narrativa, coalesce(a.postura,'') postura, a.micro,
        len(string_split(c.texto_norm,' ')) n_pal from '{I}/comentarios.parquet' c left join '{I}/narrativas_asig.parquet' a using(comentario_id)""")
    v = pd.read_csv(f"{D}/verdad/cuentas.csv.gz", dtype=str, keep_default_na=False)
    datos[nombre] = ({m: sync_sql(con, 30, m) for m in ["prod", "ruido1", "micro"]}, respuestas_entre_cuentas(con, "cm"), v)
    print("listo", nombre, flush=True)
res = []
for modo, (frac, ml) in itertools.product(["prod", "ruido1", "micro"], [(None, 0)]):
    pts = {}
    for nombre, (syncs, resp, v) in datos.items():
        g = detectar_grupos(syncs[modo], 2, 0.1, 3, 5, 0.3, 42, 0.5)
        if frac: g = expandir(g, syncs[modo], resp, frac, ml)
        pts[nombre] = puntuar_coordinacion(v.to_dict("records"), [{"cuenta_id": a, "grupo": g.get(a, "")} for a in v.cuenta_id])["puntos"]
    res.append(dict(modo=modo, expansion=f"{frac}/{ml}", media=np.mean(list(pts.values())), peor=min(pts.values()), **pts))
pd.set_option("display.width", 220); print(pd.DataFrame(res).round(2).sort_values("media", ascending=False).to_string(index=False))
