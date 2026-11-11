"""E31 — ¿Qué narrativas eligen mal el lado 'apoya' en las variantes, y lo arreglaría 'el lado que empuja una operación'?"""
import pandas as pd
B = "salida/validacion"
for v in ["completo", "sin_litio", "primera_mitad", "submuestra75", "semilla_123"]:
    a = pd.read_parquet(f"{B}/interim/{v}/narrativas_asig.parquet")
    vc = pd.read_csv(f"{B}/datos/{v}/verdad/comentarios.csv.gz", dtype=str, keep_default_na=False)
    d = a.merge(vc, on="comentario_id"); d = d[(d.narrativa != "") & (d.narrativa_id != "ninguna")]
    malas = []
    for n, g in d.groupby("narrativa"):
        acc = (g.postura_x == g.postura_y).mean()
        if acc < 0.5: malas.append(f"{n}({g.narrativa_id.mode()[0]})")
    ops = pd.read_parquet(f"{B}/interim/{v}/operaciones_meta.parquet") if __import__("os").path.exists(f"{B}/interim/{v}/operaciones_meta.parquet") else pd.DataFrame()
    print(v, "lado mal:", malas, "| operaciones empujan:", ops[["narrativa", "postura"]].values.tolist() if len(ops) else [])
