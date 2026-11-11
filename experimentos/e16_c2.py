"""E16 — Firma de C2: concentración en una narrativa+postura, sincronía temporal y respuestas internas."""
import duckdb
con = duckdb.connect()
con.execute("""create table c as select c.*, coalesce(a.campana_id,'') camp, v.narrativa_id n, v.postura p
  from 'interim/practica/comentarios.parquet' c left join read_csv('datos/practica/verdad/cuentas.csv.gz', all_varchar=true) a using(cuenta_id)
  join read_csv('datos/practica/verdad/comentarios.csv.gz', all_varchar=true) v using(comentario_id)""")
q = lambda s: print(con.execute(s).df().to_string(), "\n")
# concentración: fracción de comentarios de la cuenta en su narrativa+postura más frecuente
q("""with t as (select cuenta_id, camp, n||'/'||coalesce(p,'') np, count(*) k, sum(count(*)) over (partition by cuenta_id) tot
     from c where n<>'ninguna' group by 1,2,3), m as (select cuenta_id, camp, max(k)/any_value(tot) conc, any_value(tot) tot,
     arg_max(np,k) top from t group by 1,2)
     select camp, avg(conc), quantile_cont(conc,0.9) p90, quantile_cont(conc,0.99) p99, mode(top) from m where tot>=10 group by 1""")
# sincronía: para pares de C2 en la misma publicación, diferencia de minutos; vs pares genuinos aleatorios
q("""with x as (select a.camp, abs(date_diff('minute', a.ts, b.ts)) dmin from c a join c b on a.publicacion_id=b.publicacion_id
     and a.cuenta_id<b.cuenta_id and a.camp=b.camp where a.camp='C2')
     select camp, count(*), quantile_cont(dmin,[0.1,0.25,0.5]) from x group by 1""")
q("""with s as (select * from c where camp='' using sample 20000 rows) select count(*), quantile_cont(abs(date_diff('minute', a.ts, b.ts)),[0.1,0.25,0.5])
     from s a join s b on a.publicacion_id=b.publicacion_id and a.cuenta_id<b.cuenta_id""")
# respuestas de C2: a quién responden
q("""select h.camp, pa.camp camp_padre, count(*) from c h join c pa on h.respuesta_a=pa.comentario_id where h.camp='C2' group by 1,2""")
# C2 por publicación: cuántas cuentas C2 por publicación que tocan
q("""select quantile_cont(k,[0.5,0.9]), max(k), count(*) from (select publicacion_id, count(distinct cuenta_id) k from c where camp='C2' group by 1)""")
