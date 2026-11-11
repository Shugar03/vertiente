"""E18 — Ruido a nivel texto: textos frecuentes sin ninguna respuesta (ni dada ni recibida). ¿Cuánto ruido real captura y cuánto error?"""
import duckdb
con = duckdb.connect()
con.execute("""create table c as select c.*, v.narrativa_id n from 'interim/practica/comentarios.parquet' c
  join read_csv('datos/practica/verdad/comentarios.csv.gz', all_varchar=true) v using(comentario_id)""")
con.execute("""create table inv as select c.texto_hash, count(*) k,
  sum((c.respuesta_a is not null)::int) + sum((exists(select 1 from c h where h.respuesta_a=c.comentario_id))::int) inv,
  avg((n='ninguna')::int) frac_ruido from c group by 1""")
for kmin in [5, 10, 15, 20, 30]:
    print(kmin, con.execute(f"""select sum(k) filter (where frac_ruido>0.5) ruido_capturado, sum(k) filter (where frac_ruido<=0.5) narrativa_mal
      from inv where k>={kmin} and inv=0""").fetchone())
print(con.execute("select sum((n='ninguna')::int) from c").fetchone())
