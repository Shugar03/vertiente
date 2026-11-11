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

## Resultados (`uv run python -m radar.eval.sinteticos`)

| Set | Narrativas | Coordinación | Total |
|---|---|---|---|
| práctica (control) | 29,70 | 23,92 | 53,62 |
| **temas nuevos** (2 temas y 8 narrativas que el sistema nunca vio) | **29,72** | 15,75 | 45,47 |
| **campañas nuevas** (3 campañas de estilos nuevos + trampas) | 28,91 | 15,85 | 44,76 |

**Narrativas: agnósticas de verdad.** Sobre temas nuevos: B-cubed 0,997, ruido 0,977, postura 0,996 (el lado
"apoya" correcto en las 8 narrativas nuevas, incluidas las 2 que cambian de redacción), origen 0,977.

**Coordinación, por campaña:**

| Campaña | Estilo | Detectadas |
|---|---|---|
| Q1 | 25 cuentas nuevas, rumor nocturno, plantilla + hashtag | **25/25** |
| K2 | 8 cuentas nuevas, plantilla sin hashtag que nadie discute | **8/8** (0/8 antes de E33) |
| K3 | 20 cuentas de baja actividad (3–5 comentarios) | 12/20 |
| K1 | 35 cuentas antiguas, empujan *rechaza*, **subgrupos rotativos** | 15/35 |
| Q2 | 30 cuentas antiguas, empujan *rechaza*, **subgrupos rotativos** | 0/30 |
| trampas (pico viral, frase copiada) | genuinas | 0–5 falsos positivos |

**Límite conocido:** campañas de cuentas antiguas que rotan subgrupos (cada par coincide < 2 veces). Se probaron
cuatro ideas y ninguna mejora el promedio sin dañar práctica: expansión por lazos débiles (E33), ponderar por
tamaño del evento (E35), vía por foco narrativo (E36) y alineación del ruido por microgrupo (E33). Se documenta
como límite en vez de sobreajustar.

**Correcciones que sí entraron** (mejoran promedio y peor caso sobre práctica, variantes y sintéticos):
- E33–E34: el ruido es una clase de alineación (K2 pasó de 0/8 a 8/8).
- E37: el mínimo para fijar el origen es relativo al volumen de la narrativa (origen en temas nuevos 0,5 → 0,977;
  `solo_litio` 25,1 → 29,6 en narrativas).
