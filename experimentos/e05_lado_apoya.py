"""E05 — ¿Qué señal agnóstica identifica el lado 'apoya' de una narrativa? Se mide sobre la verdad (13 narrativas).
Candidatas: volumen, primero en aparecer, quién responde a quién, proporción de respuestas, me_gusta, léxico de refutación,
cuentas nuevas, comentarios en la publicación de origen."""
import duckdb
con = duckdb.connect()
con.execute("""create table j as select c.*, v.narrativa_id n, v.postura p from 'interim/practica/comentarios.parquet' c
  join read_csv('datos/practica/verdad/comentarios.csv.gz', all_varchar=true) v using(comentario_id) where v.narrativa_id<>'ninguna'""")
con.execute("create table k as select * from 'interim/practica/cuentas.parquet'")
q = lambda s: print(con.execute(s).df().to_string(), "\n")
q("""with base as (
  select n, p, count(*) vol, min(ts) primero, avg((respuesta_a is not null)::int) frac_resp, avg(me_gusta) likes,
         avg(regexp_matches(texto_norm, '\\b(mentira|falso|no es (asi|cierto|verdad)|verso|nada que ver|exager|invent|fake|no se robo|operacion|lean bien|no es poca)')::int) refut,
         avg(regexp_matches(texto_norm, '\\b(no|nunca|nadie|nada)\\b')::int) negacion
  from j group by 1,2)
  select a.n, a.vol>r.vol vol, a.primero<r.primero primero, a.frac_resp<r.frac_resp menos_resp, a.likes>r.likes likes,
         a.refut<r.refut menos_refut, a.negacion<r.negacion menos_neg
  from base a join base r on a.n=r.n and a.p='apoya' and r.p='rechaza' order by 1""")
q("""select h.p hijo, pa.p padre, count(*) from j h join j pa on h.respuesta_a=pa.comentario_id
     where h.p<>pa.p group by 1,2""")
q("""select p, avg((respuesta_a is null)::int) top_level from j group by 1""")
