"""Profesor LLM (opcional): juzga, por narrativa, cuál de sus dos lados AFIRMA y redacta la afirmación.

Principio del proyecto: el LLM nunca procesa comentario por comentario. Se llama UNA vez por narrativa con ~8
ejemplos por lado (≈13 llamadas por corrida). Es la decisión donde las señales locales son más débiles (E19/E31).

- SDK oficial `anthropic`, salida estructurada (JSON validado por esquema) y fallback del servidor ante rechazos.
- Caché en disco por hash del pedido (cache/llm/, se commitea): el jurado puede re-correr sin clave.
- Sin clave y sin caché, o ante cualquier error: devuelve None y el pipeline usa las reglas locales.
- Cuenta tokens y USD para costo.json.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_ESQUEMA = {
    "type": "object",
    "properties": {
        "afirmacion": {"type": "string"},
        "lado_que_afirma": {"type": "string", "enum": ["A", "B"]},
        "confianza": {"type": "number"},
    },
    "required": ["afirmacion", "lado_que_afirma", "confianza"],
    "additionalProperties": False,
}

_INSTRUCCION = """Analizás una discusión pública en redes. Te doy comentarios de dos bandos que discuten UNA misma
narrativa: un bando la afirma (instala o sostiene una idea, un reclamo o un rumor) y el otro la rechaza (la niega,
la relativiza o la refuta con un contraargumento).

Bando A:
{a}

Bando B:
{b}

Respondé en JSON:
- "afirmacion": la narrativa como una afirmación breve en español neutro (máx. 12 palabras), tal como la sostiene
  el bando que afirma; sin muletillas, sin emojis.
- "lado_que_afirma": "A" o "B".
- "confianza": entre 0 y 1."""


class Profesor:
    def __init__(self, cache_dir: Path, modelo: str, precio_in: float, precio_out: float,
                 cliente: Any = None, reintentos: int = 3):
        self.cache_dir = Path(cache_dir)
        self.modelo = modelo
        self.precio_in, self.precio_out = precio_in, precio_out
        self.cliente = cliente
        self.reintentos = reintentos
        self.uso = {"tokens": 0, "usd": 0.0, "llamadas": 0, "cache": 0}

    @classmethod
    def desde_config(cls, cfg: dict) -> "Profesor":
        modelo = os.environ.get("LLM_MODEL") or cfg["modelo"]
        precios = cfg["precios_usd_por_millon"].get(modelo, {"in": 0.0, "out": 0.0})
        cliente = None
        if os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("LLM_PROVIDER", "anthropic") != "none":
            import anthropic

            cliente = anthropic.Anthropic(timeout=cfg["timeout_s"], max_retries=0)
        return cls(Path(cfg["cache_dir"]), modelo, precios["in"], precios["out"], cliente, reintentos=cfg["reintentos"])

    def juzgar_narrativa(self, lado_a: list[str], lado_b: list[str]) -> dict | None:
        lista = lambda xs: "\n".join(f"- {x}" for x in xs)  # noqa: E731
        return self._json(_INSTRUCCION.format(a=lista(lado_a), b=lista(lado_b)), _validar_juicio)

    # --- infraestructura ---------------------------------------------------------------------------------------

    def _json(self, prompt: str, validar) -> dict | None:
        clave = hashlib.sha256(f"{self.modelo}\n{prompt}".encode()).hexdigest()[:24]
        ruta = self.cache_dir / f"{clave}.json"
        if ruta.exists():
            self.uso["cache"] += 1
            return json.loads(ruta.read_text(encoding="utf-8"))
        if self.cliente is None:
            return None
        for intento in range(self.reintentos):
            try:
                r = self.cliente.beta.messages.create(
                    model=self.modelo, max_tokens=1024,
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                    output_config={"effort": "low", "format": {"type": "json_schema", "schema": _ESQUEMA}},
                    messages=[{"role": "user", "content": prompt}],
                )
                self._contar(r.usage)
                if r.stop_reason == "refusal":
                    return None
                datos = json.loads(next(b.text for b in r.content if b.type == "text"))
                if not validar(datos):
                    log.warning("respuesta LLM inválida: %s", datos)
                    return None
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                ruta.write_text(json.dumps(datos, ensure_ascii=False, sort_keys=True), encoding="utf-8")
                return datos
            except Exception as e:  # noqa: BLE001 - cualquier falla del profesor degrada a reglas locales
                log.warning("LLM intento %d falló: %s", intento + 1, e)
                if intento + 1 < self.reintentos:
                    time.sleep(min(2 ** intento, 8))
        return None

    def _contar(self, usage) -> None:
        tin, tout = int(getattr(usage, "input_tokens", 0)), int(getattr(usage, "output_tokens", 0))
        self.uso["llamadas"] += 1
        self.uso["tokens"] += tin + tout
        self.uso["usd"] += (tin * self.precio_in + tout * self.precio_out) / 1e6


def _validar_juicio(d: dict) -> bool:
    return (isinstance(d, dict) and d.get("lado_que_afirma") in ("A", "B")
            and isinstance(d.get("afirmacion"), str) and isinstance(d.get("confianza"), (int, float)))
