"""E08 — Pares de cuentas: publicaciones compartidas vs lo esperable (modelo de configuración) y respuestas mutuas."""
import duckdb, numpy as np
con = duckdb.connect()
con.execute("""create table c as select c.*, coalesce(v.campana_id,'') camp from 'interim/practica/comentarios.parquet' c
  left join read_csv('datos/practica/verdad/cuentas.csv.gz', all_varchar=true) v using(cuenta_id)""")
con.execute("create table ap as select distinct cuenta_id, publicacion_id from c")
con.execute("create table deg as select cuenta_id, count(*) d from ap group by 1")
con.execute("create table kp as select publicacion_id, count(*) k from ap group by 1")
S2 = float(con.execute("select sum(k*(k-1)::double) from kp").fetchone()[0]); S1 = float(con.execute("select sum(k::double) from kp").fetchone()[0])
con.execute(f"""create table pares as
  select a.cuenta_id x, b.cuenta_id y, count(*) obs, sum(1/ln(k.k+1)) obs_w
  from ap a join ap b on a.publicacion_id=b.publicacion_id and a.cuenta_id<b.cuenta_id
  join kp k on k.publicacion_id=a.publicacion_id
  join deg dx on dx.cuenta_id=a.cuenta_id join deg dy on dy.cuenta_id=b.cuenta_id
  where dx.d>=3 and dy.d>=3 group by 1,2 having count(*)>=2""")
con.execute(f"""create table sc as select p.*, dx.d dx, dy.d dy, dx.d*dy.d*{S2}/({S1}*{S1}) esperado,
  p.obs/(dx.d*dy.d*{S2}/({S1}*{S1})) lift from pares p join deg dx on dx.cuenta_id=p.x join deg dy on dy.cuenta_id=p.y""")
con.execute("create table cm as select distinct cuenta_id, camp from c")
con.execute("""create table r as select h.cuenta_id x, pa.cuenta_id y, count(*) n from c h join c pa on h.respuesta_a=pa.comentario_id
  where h.cuenta_id<>pa.cuenta_id group by 1,2""")
q = lambda s: print(con.execute(s).df().to_string(), "\n")
print("pares:", con.execute("select count(*) from sc").fetchone())
q("""select case when cx.camp<>'' and cx.camp=cy.camp then 'misma_camp' when cx.camp<>'' or cy.camp<>'' then 'mixto' else 'genuino' end tipo,
     count(*), avg(obs), avg(lift), quantile_cont(lift,0.5) med_lift, quantile_cont(lift,0.99) p99_lift
     from sc join cm cx on cx.cuenta_id=sc.x join cm cy on cy.cuenta_id=sc.y group by 1""")
q("""select cx.camp, count(*) pares_lift_alto from sc join cm cx on cx.cuenta_id=sc.x join cm cy on cy.cuenta_id=sc.y
     where lift>4 and obs>=4 group by 1""")
q("""select cx.camp cx, cy.camp cy, sum(n) respuestas from r join cm cx on cx.cuenta_id=r.x join cm cy on cy.cuenta_id=r.y
     where cx.camp<>'' or cy.camp<>'' group by 1,2 order by 3 desc limit 10""")
q("select quantile_cont(n,[0.5,0.99,0.999]), max(n) from (select least(x,y) a, greatest(x,y) b, sum(n) n from r group by 1,2)")
