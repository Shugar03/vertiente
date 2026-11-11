"""E35 — Campañas que rotan subgrupos (K1, Q2): ningún par coincide 2 veces. Hipótesis: ponderar cada coincidencia
por 1/(tamaño del evento): coincidir con pocos en 30 min es más raro que entre 80 en un posteo viral.
Arista = sync>=2 (actual) O peso >= tau. Se elige por promedio y peor caso sobre 6 sets."""
import itertools, yaml
from pathlib import Path
import numpy as np, pandas as pd
from radar.stages import coordinacion as co
from radar.coordinacion.grafo import detectar_grupos
from radar.eval.puntaje import puntuar_coordinacion
cfg = yaml.safe_load(open("config.yaml"))
SETS = {"practica": ("interim/practica", "datos/practica"),
        "submuestra75": ("salida/validacion/interim/submuestra75", "salida/validacion/datos/submuestra75"),
        "primera_mitad": ("salida/validacion/interim/primera_mitad", "salida/validacion/datos/primera_mitad"),
        "sin_hospital": ("salida/validacion/interim/sin_hospital", "salida/validacion/datos/sin_hospital"),
        "campanas_nuevas": ("salida/sinteticos/_interim/campanas_nuevas", "salida/sinteticos/campanas_nuevas"),
        "temas_nuevos": ("salida/sinteticos/_interim/temas_nuevos", "salida/sinteticos/temas_nuevos")}
W = 30
def pares(con):
    return con.execute(f"""
      with n as (select *, case when narrativa<>'' then narrativa||'/'||postura else 'ruido' end clave from cm where ts is not null),
      tam as (select a.comentario_id, count(distinct b.cuenta_id) k from n a join n b on a.publicacion_id=b.publicacion_id
              and a.clave=b.clave and b.ts between a.ts - interval {W} minute and a.ts + interval {W} minute group by 1),
      act as (select cuenta_id, count(distinct publicacion_id) d from n group by 1),
      s as (select least(a.cuenta_id,b.cuenta_id) x, greatest(a.cuenta_id,b.cuenta_id) y, count(distinct a.publicacion_id) sync,
                   sum(1.0/greatest(t.k-1,1)) peso
            from n a join n b on a.publicacion_id=b.publicacion_id and a.clave=b.clave and a.cuenta_id<>b.cuenta_id
            and b.ts>=a.ts and b.ts<=a.ts + interval {W} minute join tam t on t.comentario_id=a.comentario_id group by 1,2)
      select s.*, s.sync/least(ax.d,ay.d) sync_n from s join act ax on ax.cuenta_id=s.x join act ay on ay.cuenta_id=s.y""").df()
datos = {}
for nombre, (I, D) in SETS.items():
    con = co.conectar(Path(I), cfg)
    con.execute(f"""create table cm as select c.comentario_id, c.cuenta_id, c.publicacion_id, c.ts,
        coalesce(a.narrativa,'') narrativa, coalesce(a.postura,'') postura from '{I}/comentarios.parquet' c
        left join '{I}/narrativas_asig.parquet' a using(comentario_id)""")
    datos[nombre] = (pares(con), pd.read_csv(f"{D}/verdad/cuentas.csv.gz", dtype=str, keep_default_na=False))
    print("listo", nombre, len(datos[nombre][0]), flush=True)
res = []
for tau, vc in itertools.product([None, 0.1, 0.15, 0.2, 0.3], [3, 4]):
    pts = {}
    for nombre, (s, v) in datos.items():
        s2 = s.copy()
        if tau is not None:  # una arista fuerte por peso: se la marca como sync=2 para reutilizar el detector
            fuerte = (s2.peso >= tau) & (s2.sync < 2)
            s2.loc[fuerte, "sync"] = 2; s2.loc[fuerte, "sync_n"] = np.maximum(s2.loc[fuerte, "sync_n"], 0.1)
        g = detectar_grupos(s2, 2, 0.1, vc, 5, 0.3, 42, 0.5)
        pts[nombre] = puntuar_coordinacion(v.to_dict("records"), [{"cuenta_id": a, "grupo": g.get(a, "")} for a in v.cuenta_id])["puntos"]
    res.append(dict(tau=tau, vecinos=vc, media=np.mean(list(pts.values())), peor=min(pts.values()), **pts))
pd.set_option("display.width", 240); print(pd.DataFrame(res).round(2).sort_values("media", ascending=False).to_string(index=False))
