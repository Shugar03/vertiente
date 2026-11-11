"""E32 — ¿Qué pasa si el set no trae respuestas (respuesta_a vacío)? Caso borde de supervivencia."""
import copy, yaml
from pathlib import Path
from radar.cli import run
from radar.eval.validar import armar_variante, puntuar
cfg = yaml.safe_load(open("config.yaml")); base = Path("salida/validacion")
def sin_resp(c):
    c = c.copy(); c["respuesta_a"] = ""; return c
d = armar_variante(Path("datos/practica"), base / "datos" / "sin_respuestas", sin_resp)
c2 = copy.deepcopy(cfg); c2["interim_dir"] = str(base / "interim")
run(d, base / "salida" / "sin_respuestas", c2)
print(puntuar(d, base / "salida" / "sin_respuestas"))
