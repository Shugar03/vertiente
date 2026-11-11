"""E03 — Estructura de respuestas. Hipótesis: toda respuesta hereda la narrativa del padre; algunas invierten postura."""
import duckdb
con = duckdb.connect()
con.execute("""create table j as select c.*, v.narrativa_id n, v.postura p from 'interim/practica/comentarios.parquet' c
  join read_csv('datos/practica/verdad/comentarios.csv.gz', all_varchar=true) v using(comentario_id)""")
con.execute("""create table r as select h.texto ht, h.texto_norm hn, h.n hn_, h.p hp, pa.n pn, pa.p pp,
  pa.respuesta_a is not null padre_es_resp, length(h.texto) largo from j h join j pa on h.respuesta_a = pa.comentario_id""")
q = lambda s: print(con.execute(s).df().to_string(max_colwidth=80), "\n")
q("""select count(*) respuestas, sum((hn_=pn)::int) misma_narr, sum((pn='ninguna')::int) padre_ruido,
     sum((hn_=pn and hp<>pp)::int) invertida, sum(padre_es_resp::int) padre_es_resp from r""")
q("select hn, hp=pp mismo, count(*) k from r where hn_=pn group by 1,2 order by 3 desc limit 30")
q("select hp=pp mismo, avg(largo), count(distinct hn) textos_distintos, count(*) from r group by 1")
q("select ht, hp, pp from r where hp<>pp order by random() limit 12")
q("select n='ninguna' ruido, (texto like '%?%') preg, count(*) from j where respuesta_a is null group by 1,2 order by 1,2")
q("select texto, n, count(*) k from j where respuesta_a is null and n<>'ninguna' and texto like '%?%' group by 1,2 order by 3 desc limit 8")
