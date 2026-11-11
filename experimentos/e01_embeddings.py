"""E01 — ¿Qué modelo de embeddings separa mejor las narrativas? (tiempo + pureza kNN)

Hipótesis: EmbeddingGemma 2 separa mejor que e5-small, a costa de ~3x tiempo.
Métrica proxy: pureza kNN (k=10) sobre comentarios con narrativa: % de vecinos con la misma narrativa,
y con la misma (narrativa, postura). Solo textos únicos.
"""
import sys, time, logging
from pathlib import Path
import duckdb, numpy as np, torch
from radar.embed import Embedder

logging.basicConfig(level=logging.INFO)
modelo = sys.argv[1]
I = Path("interim/practica")
df = duckdb.sql(f"""
  select c.texto_hash, any_value(c.texto_norm) t, mode(v.narrativa_id) n, mode(v.postura) p
  from '{I}/comentarios.parquet' c join read_csv('datos/practica/verdad/comentarios.csv.gz', all_varchar=true) v using(comentario_id)
  group by 1""").df()
X, info = Embedder(modelo, Path("interim/cache_emb"), batch=128).embeber(df.texto_hash.tolist(), df.t.tolist())
mask = (df.n != "ninguna").to_numpy()
Xn = torch.from_numpy(X[mask]); n = df.n.to_numpy()[mask]; np_ = (df.n + df.p.fillna("")).to_numpy()[mask]
rng = np.random.default_rng(0); idx = rng.choice(len(Xn), 3000, replace=False)
S = Xn[idx] @ Xn.T; S[torch.arange(3000), torch.from_numpy(idx)] = -1
nn = S.topk(10, dim=1).indices.numpy()
print(modelo, info, "pureza_narrativa=%.3f" % (n[nn] == n[idx][:, None]).mean(),
      "pureza_narr_postura=%.3f" % (np_[nn] == np_[idx][:, None]).mean())
