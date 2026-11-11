"""Embeddings locales con caché por hash de texto.

Solo se embeben textos únicos (normalizados); el resultado se guarda en `<cache_dir>/<modelo>.parquet`
(texto_hash -> vector), así re-correr cuesta casi cero y el set final reaprovecha textos repetidos.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# Prompt de tarea por modelo (cada familia espera el suyo).
PROMPTS = {
    "intfloat/multilingual-e5-small": "query: ",
    "intfloat/multilingual-e5-base": "query: ",
    "google/embeddinggemma-2": "task: clustering | query: ",
    "google/embeddinggemma-300m": "task: clustering | query: ",
}
_SOLO_TEXTO = {"google/embeddinggemma-2": {"vision_config": None, "audio_config": None}}


def dispositivo(pedido: str = "auto") -> str:
    if pedido != "auto":
        return pedido
    import torch

    if torch.backends.mps.is_available():
        return "mps"
    return "cuda" if torch.cuda.is_available() else "cpu"


@dataclass
class Embedder:
    modelo: str
    cache_dir: Path
    batch: int = 256
    dispositivo: str = "auto"
    dims: int | None = None  # truncado Matryoshka (solo modelos que lo soportan)

    def _cache_path(self) -> Path:
        return self.cache_dir / f"{self.modelo.replace('/', '__')}.parquet"

    def _cargar_cache(self) -> dict[str, np.ndarray]:
        p = self._cache_path()
        if not p.exists():
            return {}
        df = pd.read_parquet(p)
        return dict(zip(df["texto_hash"], df["vector"].map(np.asarray)))

    def _modelo(self):
        from sentence_transformers import SentenceTransformer

        kwargs = {}
        if self.modelo in _SOLO_TEXTO:
            kwargs["config_kwargs"] = _SOLO_TEXTO[self.modelo]
        return SentenceTransformer(self.modelo, device=dispositivo(self.dispositivo), **kwargs)

    def embeber(self, hashes: list[str], textos: list[str]) -> tuple[np.ndarray, dict]:
        """Devuelve la matriz (len(hashes) x d) normalizada L2, en el orden recibido."""
        cache = self._cargar_cache()
        faltan = [(h, t) for h, t in dict(zip(hashes, textos)).items() if h not in cache]
        t0 = time.perf_counter()
        if faltan:
            m = self._modelo()
            prefijo = PROMPTS.get(self.modelo, "")
            orden = sorted(range(len(faltan)), key=lambda i: len(faltan[i][1]))  # lotes de largo parecido
            vecs = m.encode([prefijo + (faltan[i][1] or ".") for i in orden], batch_size=self.batch,
                            normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
            for j, i in enumerate(orden):
                cache[faltan[i][0]] = vecs[j].astype(np.float32)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            pd.DataFrame({"texto_hash": list(cache), "vector": [v.tolist() for v in cache.values()]}) \
                .to_parquet(self._cache_path())
        seg = time.perf_counter() - t0
        X = np.stack([cache[h] for h in hashes]).astype(np.float32)
        if self.dims:
            X = X[:, : self.dims]
            X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-12
        info = {"modelo": self.modelo, "nuevos": len(faltan), "en_cache": len(hashes) - len(faltan),
                "segundos": round(seg, 1), "dims": X.shape[1]}
        log.info("embeddings: %s", info)
        return X, info
