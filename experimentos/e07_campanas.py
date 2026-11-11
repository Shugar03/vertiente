"""E07 — ¿Cómo se ven las campañas vs cuentas genuinas? (actividad, antigüedad, ráfagas, co-ocurrencias)"""
import duckdb
con = duckdb.connect()
con.execute("""create table c as select c.*, coalesce(v.campana_id,'') camp from 'interim/practica/comentarios.parquet' c
  left join read_csv('datos/practica/verdad/cuentas.csv.gz', all_varchar=true) v using(cuenta_id)""")
con.execute("""create table a as select k.*, coalesce(v.campana_id,'') camp from 'interim/practica/cuentas.parquet' k
  left join read_csv('datos/practica/verdad/cuentas.csv.gz', all_varchar=true) v using(cuenta_id)""")
q = lambda s: print(con.execute(s).df().to_string(), "\n")
q("""select camp, count(distinct cuenta_id) cuentas, count(*) com, count(*)/count(distinct cuenta_id) com_x_cuenta,
     count(distinct publicacion_id) posts, avg((hour(ts at time zone 'America/Argentina/Buenos_Aires') between 0 and 5)::int) noche,
     avg((respuesta_a is not null)::int) frac_resp, avg(length(texto)) largo
     from c group by 1 order by 1""")
q("""select camp, avg(date_diff('day', fecha_creacion, date '2026-09-01')) antig_dias, median(seguidores) seg, median(siguiendo) sig,
     quantile_cont(date_diff('day', fecha_creacion, date '2026-09-01'), 0.1) antig_p10 from a group by 1""")
q("""select quantile_cont(n, [0.5,0.9,0.99,0.999]) from (select cuenta_id, count(*) n from c where camp='' group by 1)""")
q("""select camp, quantile_cont(n,[0.1,0.5,0.9]) from (select camp, cuenta_id, count(*) n from c where camp<>'' group by 1,2) group by 1""")
q("""with ev as (select camp, publicacion_id, time_bucket(interval 15 minute, ts) b, count(distinct cuenta_id) k
     from c where camp<>'' group by 1,2,3) select camp, count(*) eventos, avg(k), max(k) from ev group by 1""")
q("""select camp='' genuina, count(*) from a where fecha_creacion >= date '2026-08-15' group by 1""")
