"""Señales de coordinación entre pares de cuentas (SQL en DuckDB).

Hallazgo central (E07–E17): coincidir en tiempo NO alcanza (todos comentan cuando sale una publicación, y los
usuarios intensivos coinciden con todos). Lo que delata a una operación es la **sincronía alineada repetida**:
las mismas cuentas, en la misma publicación, empujando la misma narrativa con la misma postura, a minutos de
distancia, en varias publicaciones distintas. Se normaliza por la actividad de la cuenta menos activa.
"""

from __future__ import annotations

import duckdb
import pandas as pd


def sincronias_alineadas(con: duckdb.DuckDBPyConnection, tabla: str, ventana_min: int) -> pd.DataFrame:
    """Pares (x<y) con: sync = publicaciones distintas con sincronía alineada; sync_n = sync / publicaciones (con
    narrativa) de la cuenta menos activa.

    `tabla`: comentario_id, cuenta_id, publicacion_id, ts, narrativa, postura.
    Clave de alineación: narrativa+postura; los comentarios de ruido forman UNA clase propia (E33–E34: una campaña
    cuyo texto termina como ruido —nadie la discute— no debe volverse invisible; mejoró promedio y peor caso).
    """
    return con.execute(f"""
        with n as (select *, case when coalesce(narrativa, '') <> '' then narrativa || '/' || coalesce(postura, '')
                                  else 'ruido' end as clave
                   from {tabla} where ts is not null),
        act as (select cuenta_id, count(distinct publicacion_id) d from n group by 1),
        s as (
            select least(a.cuenta_id, b.cuenta_id) x, greatest(a.cuenta_id, b.cuenta_id) y,
                   count(distinct a.publicacion_id) sync
            from n a join n b
              on a.publicacion_id = b.publicacion_id and a.clave = b.clave
             and a.cuenta_id <> b.cuenta_id
             and b.ts >= a.ts and b.ts <= a.ts + interval {int(ventana_min)} minute
            group by 1, 2)
        select s.x, s.y, s.sync, s.sync / least(ax.d, ay.d) sync_n
        from s join act ax on ax.cuenta_id = s.x join act ay on ay.cuenta_id = s.y
    """).df()


def respuestas_entre_cuentas(con: duckdb.DuckDBPyConnection, tabla: str) -> pd.DataFrame:
    """Pares (x<y) y cuántas veces se respondieron entre sí (en cualquier dirección)."""
    return con.execute(f"""
        select least(h.cuenta_id, p.cuenta_id) x, greatest(h.cuenta_id, p.cuenta_id) y, count(*) resp
        from {tabla} h join {tabla} p on h.respuesta_a = p.comentario_id
        where h.cuenta_id <> p.cuenta_id group by 1, 2
    """).df()
