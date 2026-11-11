"""Origen de una narrativa: primer momento con actividad real, no el primer comentario suelto."""

from __future__ import annotations

import numpy as np
import pandas as pd


def origen_robusto(ts: pd.Series, ventana_h: float, minimo: int) -> pd.Timestamp:
    """Primer instante t tal que en [t, t + ventana] hay >= `minimo` comentarios. Si nunca pasa, el más temprano."""
    t = ts.dropna().sort_values().reset_index(drop=True)
    if t.empty:
        raise ValueError("narrativa sin fechas")
    fin = np.searchsorted(t.values, (t + pd.Timedelta(hours=ventana_h)).values, side="right")
    cuenta = fin - np.arange(len(t))
    ok = np.flatnonzero(cuenta >= minimo)
    return t.iloc[int(ok[0])] if len(ok) else t.iloc[0]
