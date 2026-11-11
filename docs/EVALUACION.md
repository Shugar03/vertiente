# Criterios de evaluación

Fuente: README de https://github.com/qualydata-org/desafio-qualydata y su `evaluacion/puntuar.py`
(el mismo script que usa el jurado). *Puntaje "sujeto a las bases y condiciones del hackathon".*

## Puntaje (100)

| Criterio | Pts | Cómo se mide |
|---|---|---|
| Calidad de narrativas | 30 | Automático sobre el set final |
| Detección de coordinación | 25 | Automático sobre el set final |
| Costo, escala y almacenamiento | 20 | Jurado: `costo.json`, tiempo de proceso, dónde/cómo guardamos y por qué, cómo escala a millones/día |
| Robustez del pipeline | 15 | Jurado: un comando de punta a punta, datos sucios, reproducible |
| Claridad y visualización | 10 | Jurado: demo y pitch. ¿Se entiende en 1 minuto qué circula, desde cuándo y quién lo empuja? |

### Desglose automático (55)

| Componente | Peso | Pts | Métrica |
|---|---|---|---|
| Narrativas · agrupamiento | 50% de 30 | 15 | B-cubed F1, **solo sobre comentarios que sí son narrativa** |
| Narrativas · ruido | 15% de 30 | 4,5 | F1 de la clase "ninguna" |
| Narrativas · postura | 20% de 30 | 6 | macro-F1 apoya/rechaza (las dos pesan igual; en práctica 53/47) |
| Narrativas · origen emergentes | 15% de 30 | 4,5 | 1,0 si error ≤ 3 h; lineal a 0 en 48 h |
| Coordinación · detección | 70% de 25 | **17,5** | F1 de cuentas marcadas (115 de ~16.000 en práctica → **la precisión manda**) |
| Coordinación · operación | 30% de 25 | 7,5 | B-cubed F1 de grupos |

**Prioridad:** detección de coordinación > agrupamiento de narrativas > costo/escala (jurado).

## Cómo puntúa el script (detalles que importan)

- Comentario **ausente** en `comentarios.csv` ⇒ cuenta como **ruido**. Escribir siempre todos los ids.
- Etiquetas `""`, `ninguna`, `none`, `null` ⇒ ruido. Usar `n01`, `n02`…
- En B-cubed, un comentario de narrativa que marcamos como ruido queda como grupo de uno ⇒ baja el recall.
  Partir de más baja el recall; juntar de más baja la precisión. El nombre/número de grupos no importa.
- Origen: para cada narrativa emergente real se toma **nuestro grupo con mayor solapamiento** y su `fecha_origen`.
- `fecha_origen` **con zona horaria** (`-03:00`). Si no, el script compara fecha con y sin zona y **se cae**.
- CSV **UTF-8 sin BOM** (con BOM falla la validación de columnas).
- Postura en minúsculas: `apoya` / `rechaza`; vacía en ruido.

## Formato de `entrega/`

| Archivo | Columnas |
|---|---|
| `comentarios.csv` | `comentario_id, narrativa, postura` |
| `narrativas.csv` | `narrativa, titulo, frases_clave` (separadas por `|`), `fecha_origen` (ISO con zona) |
| `cuentas.csv` | `cuenta_id, grupo` (vacío si es genuina) |
| `costo.json` | `comentarios_procesados, segundos, tokens_ia, usd_ia, usd_por_mil_comentarios, hardware, almacenamiento, notas` |

Reglas de postura del desafío:
- Respuestas cortas que solo acompañan ("Tal cual", "Exacto") heredan narrativa **y** postura del comentario padre.
- Una respuesta que contradice al anterior va a la misma narrativa con postura opuesta.

## Requisitos excluyentes

- [ ] Repo **público** a la hora de cierre, con `entrega/` commiteada (se clona y se anota el commit; lo posterior no cuenta).
- [ ] Video de demo cargado en Hacki + pitch ante el jurado.
- [ ] README: cómo correr, dónde guardamos los datos y por qué esa base, qué código/librerías existían antes.
- [ ] Un comando de punta a punta sobre el set final; **sin etiquetado manual** del set final; el jurado puede re-correrlo.
- [ ] Trabajo original del hackathon (librerías/modelos/servicios públicos permitidos).
- [ ] Solo datos provistos o fuentes públicas; sin datos personales.
- [ ] **Sin claves ni secretos** en el repo.
- [ ] Todo gasto de IA reportado en `costo.json`.

## Set final

- Se publica el **viernes 13 a la mañana** (hora a confirmar). Va en `datos/final/`, que **no se sube**.
- Misma estructura, ~150.000 comentarios en 10 días, **otros temas, narrativas y campañas**.

## Preguntas abiertas para la organización

1. ¿Big Data y Streaming tienen premios separados o es un solo track?
2. Hora exacta de publicación del set final y de cierre.
3. ¿APIs de LLM pagas permitidas? ¿Dan créditos?
4. Si el jurado re-corre: ¿con internet? ¿con nuestras claves?
5. Duración máxima del video.
