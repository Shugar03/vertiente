"""Etapa de coordinación.

Entrada: interim/<set>/comentarios.parquet, cuentas.parquet, narrativas_asig.parquet.
Salida:  grupos.parquet (cuenta_id, grupo) y operaciones_meta.parquet (una fila por operación detectada: tamaño,
         narrativa y postura que empuja, perfil de sus cuentas). Ver radar/coordinacion/ y experimentos E07–E17.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import duckdb
import pandas as pd

from radar.coordinacion.grafo import detectar_grupos
from radar.coordinacion.senales import sincronias_alineadas

log = logging.getLogger(__name__)


def conectar(interim: Path, config: dict) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    tmp = interim / "duckdb_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    con.execute(f"set memory_limit='{config['duckdb']['memory_limit']}'")
    con.execute(f"set temp_directory='{tmp}'")
    con.execute(f"set max_temp_directory_size='{config['duckdb'].get('max_temp', '8GB')}'")
    con.execute("set TimeZone='UTC'")
    return con


def describir_operaciones(con: duckdb.DuckDBPyConnection, grupos: pd.DataFrame) -> pd.DataFrame:
    if grupos.empty:
        return pd.DataFrame(columns=["grupo", "cuentas", "comentarios", "narrativa", "postura", "foco",
                                     "antiguedad_mediana_dias", "frac_nocturna", "primera_actividad"])
    con.register("grupos_df", grupos)
    return con.execute("""
        with g as (select cm.*, gr.grupo from cm join grupos_df gr using(cuenta_id)),
        np_ as (select grupo, narrativa, postura, count(*) k,
                       row_number() over (partition by grupo order by count(*) desc) r
                from g where narrativa <> '' group by 1, 2, 3),
        tot as (select grupo, count(*) com, count(distinct cuenta_id) cuentas, min(ts) primera,
                       avg((hour(ts at time zone 'America/Argentina/Buenos_Aires') between 0 and 5)::int) noche
                from g group by 1),
        ant as (select gr.grupo, median(date_diff('day', k.fecha_creacion, (select min(ts)::date from cm))) antig
                from grupos_df gr join cu k using(cuenta_id) group by 1)
        select tot.grupo, tot.cuentas, tot.com comentarios, np_.narrativa, np_.postura,
               round(np_.k / tot.com, 3) foco, ant.antig antiguedad_mediana_dias, round(tot.noche, 3) frac_nocturna,
               tot.primera primera_actividad
        from tot left join np_ on np_.grupo = tot.grupo and np_.r = 1 left join ant on ant.grupo = tot.grupo
        order by tot.cuentas desc
    """).df()


def run(interim: Path, config: dict) -> dict:
    t0 = time.perf_counter()
    cfg = config["coordinacion"]
    con = conectar(interim, config)
    con.execute(f"""
        create table cm as select c.comentario_id, c.cuenta_id, c.publicacion_id, c.ts, c.respuesta_a,
               coalesce(a.narrativa, '') narrativa, coalesce(a.postura, '') postura
        from '{interim / 'comentarios.parquet'}' c left join '{interim / 'narrativas_asig.parquet'}' a using(comentario_id)
    """)
    con.execute(f"create table cu as select * from '{interim / 'cuentas.parquet'}'")
    sync = sincronias_alineadas(con, "cm", cfg["ventana_min"])
    grupos_d = detectar_grupos(sync, cfg["min_sincronias"], cfg["min_sincronia_norm"], cfg["min_vecinos_comunes"],
                               cfg["min_tamano"], cfg["min_densidad"], seed=config["seed"],
                               fraccion_nucleo=cfg["fraccion_nucleo"])
    grupos = pd.DataFrame({"cuenta_id": list(grupos_d), "grupo": list(grupos_d.values())})
    grupos.to_parquet(interim / "grupos.parquet")
    meta = describir_operaciones(con, grupos)
    meta.to_parquet(interim / "operaciones_meta.parquet")
    info = {"pares_sincronia": len(sync), "operaciones": int(grupos["grupo"].nunique()) if len(grupos) else 0,
            "cuentas_marcadas": len(grupos), "segundos": round(time.perf_counter() - t0, 1)}
    log.info("coordinacion: %s", info)
    return info
