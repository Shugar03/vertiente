# Prueba con sets sintéticos (agnosticismo)

## Por qué

Toda la validación previa usa variantes del set de práctica: mismos temas, mismas plantillas y las mismas 3
campañas. El set final trae otros temas, otras narrativas y "campañas de distintos estilos". Estos sets buscan
**fallas catastróficas** (una campaña no detectada, posturas invertidas en masa, narrativas fusionadas), no décimas.

## Sets

| Set | Construcción | Qué prueba |
|---|---|---|
| **B · campañas nuevas** | Práctica sin C1/C2/C3 (y sin sus cadenas de respuestas) + 3 campañas inyectadas de estilos nuevos + 2 trampas genuinas | Que la coordinación no esté hecha a medida de C1–C3 |
| **A · temas nuevos** | Generador desde cero: 2 temas y 8 narrativas nuevas (1 rumor emergente por tema, 1 con cambio de redacción), ruido, respuestas, 2 campañas | Agrupamiento y, sobre todo, elección del lado "apoya" fuera de las 13 narrativas conocidas |

Campañas nuevas del set B:
- **K1**: ~35 cuentas antiguas, de día, textos variados, empuja el lado **rechaza** de una narrativa existente, sincronizada en ~15 publicaciones y respondiéndose entre sí.
- **K2**: **8** cuentas nuevas, textos casi idénticos sin hashtag, ráfagas a cualquier hora en ~6 publicaciones.
- **K3**: ~20 cuentas de antigüedad mixta y **baja actividad** (3–5 comentarios cada una), de tarde/noche.
- Trampas: un pico viral genuino (~150 cuentas, una sola publicación, una vez) y una frase copiada por ~80 cuentas genuinas a lo largo de días.

## Reglas de la prueba

1. Los generadores los escriben subagentes que **no leen el código del pipeline** (`radar/`, `config.yaml`,
   `experimentos/`, `docs/VALIDACION.md`): solo el README del desafío y los datos de práctica.
2. Cada set trae su verdad en el formato oficial y se puntúa con la réplica del puntaje oficial.
3. **No se ajusta ningún parámetro mirando estos sets.** Si algo falla, solo entra una corrección con sentido general
   que además mantenga práctica y sus variantes (promedio y peor caso).

## Resultados

_(se completan al correr `uv run python -m radar.eval.sinteticos`)_
