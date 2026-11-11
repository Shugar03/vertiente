"""Ingesta: CSV.gz -> Parquet limpio (DuckDB).

Contratos de salida (interim/<set>/):
  comentarios.parquet   comentario_id, publicacion_id, cuenta_id, ts (TIMESTAMPTZ), texto, texto_norm, texto_hash,
                        respuesta_a (nulo si huérfana, cíclica o posterior al hijo), me_gusta
  cuentas.parquet       cuenta_id, usuario, fecha_creacion, seguidores, siguiendo (incluye cuentas sin perfil)
  publicaciones.parquet publicacion_id, fuente_id, ts, titular
Devuelve un reporte de calidad de datos (para logs y README).
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

from radar.texto import hash_texto, normalizar

log = logging.getLogger(__name__)

_LEER = "read_csv('{}', all_varchar=true, header=true, quote='\"', escape='\"', strict_mode=false)"


def _csv(datos: Path, nombre: str) -> str:
    for cand in (datos / f"{nombre}.csv.gz", datos / f"{nombre}.csv"):
        if cand.exists():
            return _LEER.format(cand)
    raise FileNotFoundError(f"falta {nombre}.csv(.gz) en {datos}")


def cortar_ciclos(padre: dict[str, str | None]) -> int:
    """Pone en None el enlace que cierra cada ciclo de respuestas (in place). Devuelve cuántos cortó."""
    cortes = 0
    estado: dict[str, int] = {}  # 1 = en el recorrido actual, 2 = resuelto
    for inicio in list(padre):
        camino = []
        nodo = inicio
        while nodo is not None and nodo not in estado:
            estado[nodo] = 1
            camino.append(nodo)
            nodo = padre.get(nodo)
        if nodo is not None and estado.get(nodo) == 1:
            padre[camino[-1]] = None
            cortes += 1
        for n in camino:
            estado[n] = 2
    return cortes


def _comentarios(con: duckdb.DuckDBPyConnection, datos: Path) -> tuple[pd.DataFrame, dict]:
    con.execute(f"create table crudo as select *, row_number() over () as _fila from {_csv(datos, 'comentarios')}")
    total = con.execute("select count(*) from crudo").fetchone()[0]
    df = con.execute("""
        select trim(comentario_id) comentario_id, trim(publicacion_id) publicacion_id, trim(cuenta_id) cuenta_id,
               try_cast(trim(fecha) as timestamptz) ts, coalesce(texto, '') texto,
               nullif(trim(respuesta_a), '') respuesta_a,
               greatest(coalesce(try_cast(me_gusta as integer), 0), 0) me_gusta
        from crudo where coalesce(trim(comentario_id), '') <> ''
        qualify row_number() over (partition by trim(comentario_id) order by _fila) = 1
        order by _fila
    """).df()

    ids = set(df["comentario_id"])
    ts = dict(zip(df["comentario_id"], df["ts"]))
    con_padre_original = int(df["respuesta_a"].notna().sum())

    def padre_valido(hijo: str, p: str | None, t_hijo) -> str | None:
        if p is None or p not in ids or p == hijo:
            return None
        t_padre = ts[p]
        if pd.notna(t_hijo) and pd.notna(t_padre) and t_padre > t_hijo:
            return None
        return p

    padres = {r.comentario_id: padre_valido(r.comentario_id, r.respuesta_a, r.ts) for r in df.itertuples()}
    ciclos = cortar_ciclos(padres)
    df["respuesta_a"] = df["comentario_id"].map(padres)
    df["texto_norm"] = df["texto"].map(normalizar)
    df["texto_hash"] = df["texto_norm"].map(hash_texto)

    reporte = {
        "comentarios_leidos": int(total),
        "ids_duplicados": int(total - len(df)),
        "fechas_invalidas": int(df["ts"].isna().sum()),
        "respuestas_descartadas": con_padre_original - int(df["respuesta_a"].notna().sum()),
        "ciclos_cortados": ciclos,
        "textos_unicos": int(df["texto_hash"].nunique()),
    }
    return df, reporte


def run(datos: Path, interim: Path, config: dict) -> dict:
    interim.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"set memory_limit='{config.get('duckdb', {}).get('memory_limit', '4GB')}'")
    con.execute("set TimeZone='UTC'")

    df, reporte = _comentarios(con, datos)
    con.register("cdf", df)
    con.execute(f"copy (select * from cdf) to '{interim / 'comentarios.parquet'}' (format parquet)")

    con.execute(f"""
        create table cu as
        select trim(cuenta_id) cuenta_id, usuario, try_cast(fecha_creacion as date) fecha_creacion,
               case when try_cast(seguidores as integer) >= 0 then try_cast(seguidores as integer) end seguidores,
               case when try_cast(siguiendo as integer) >= 0 then try_cast(siguiendo as integer) end siguiendo
        from {_csv(datos, 'cuentas')}
        where coalesce(trim(cuenta_id), '') <> ''
        qualify row_number() over (partition by trim(cuenta_id)) = 1
    """)
    reporte["cuentas_sin_perfil"] = int(con.execute("""
        insert into cu select distinct cuenta_id, null, null, null, null from cdf
        where cuenta_id not in (select cuenta_id from cu)
    """).fetchone()[0] or 0)
    con.execute(f"copy cu to '{interim / 'cuentas.parquet'}' (format parquet)")

    con.execute(f"""
        copy (select trim(publicacion_id) publicacion_id, fuente_id, try_cast(fecha as timestamptz) ts, titular
              from {_csv(datos, 'publicaciones')}) to '{interim / 'publicaciones.parquet'}' (format parquet)
    """)
    log.info("ingest: %s", reporte)
    return reporte
