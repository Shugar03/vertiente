"""E02 — Throughput de embeddings por dispositivo y batch (5.000 textos reales, modelo ya descargado)."""
import sys, time, duckdb, torch
from sentence_transformers import SentenceTransformer
modelo, dev, batch = sys.argv[1], sys.argv[2], int(sys.argv[3])
kw = {"config_kwargs": {"vision_config": None, "audio_config": None}} if "gemma-2" in modelo else {}
t = duckdb.sql("select distinct texto_norm from 'interim/practica/comentarios.parquet' limit 5000").df().texto_norm.tolist()
m = SentenceTransformer(modelo, device=dev, **kw)
if dev == "cpu": torch.set_num_threads(10)
m.encode(t[:256], batch_size=batch)
t0 = time.perf_counter(); m.encode(t, batch_size=batch, normalize_embeddings=True); s = time.perf_counter() - t0
print(f"{modelo} {dev} batch={batch}: {len(t)/s:.0f} textos/s")
