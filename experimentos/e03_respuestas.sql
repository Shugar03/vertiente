-- E03 — ¿Cómo se comportan las respuestas? (hipótesis: todas heredan narrativa, algunas invierten postura)
create view v as select * from read_csv('datos/practica/verdad/comentarios.csv.gz', all_varchar=true);
create view j as select c.*, v.narrativa_id n, v.postura p from 'interim/practica/comentarios.parquet' c join v using(comentario_id);
create view r as select h.texto ht, h.texto_norm hn, h.n hn_, h.p hp, pa.n pn, pa.p pp, pa.respuesta_a is not null padre_es_resp
  from j h join j pa on h.respuesta_a = pa.comentario_id;
select 'respuestas' k, count(*) from r union all
select 'misma narrativa', sum((hn_=pn)::int) from r union all
select 'padre ruido', sum((pn='ninguna')::int) from r union all
select 'postura invertida', sum((hn_=pn and hp<>pp)::int) from r union all
select 'padre es respuesta', sum(padre_es_resp::int) from r;
select hn, hp=pp mismo, count(*) k from r where hn_=pn group by 1,2 order by 3 desc limit 40;
select ht, hn_, pn from r where hn_<>pn limit 10;
-- ruido que NO es respuesta vs narrativa no respuesta con texto corto
select n='ninguna' ruido, (texto like '%?%') preg, count(*) from j where respuesta_a is null group by 1,2 order by 1,2;
select texto, n, p, count(*) k from j where respuesta_a is null and n<>'ninguna' and texto like '%?%' group by 1,2,3 order by 4 desc limit 10;
