# Video demo — storyboard de producción (≈ 80 s)

Para grabarlo el equipo. 16:9, 1920×1080. Locución en rioplatense + subtítulos (`subtitulos.srt`, ya sincronizados
con este guion) + música suave de fondo. Se entiende aunque se proyecte sin sonido.

**Mensaje único:** *Vertiente muestra en un minuto qué se dice, desde cuándo y quién lo empuja — con un comando, en
segundos y sin gastar en IA.*

## Escenas

| # | Tiempo | Qué se ve | Locución (leer tal cual) |
|---|---|---|---|
| 1 | 0:00–0:08 | **Gancho.** Terminal con comentarios crudos pasando rápido (comando A). Texto en pantalla: **"200.000 comentarios"**. | "Doscientos mil comentarios sobre temas públicos. ¿Qué se está diciendo? ¿Y qué parte está armada?" |
| 2 | 0:08–0:20 | **La idea.** README en GitHub, sección *Cómo funciona* (el diagrama). Zoom lento. | "Nuestra idea: la conversación misma es la etiqueta. Cuando alguien responde con un argumento, discute la misma narrativa desde el otro lado. Y una operación no se ve en un comentario: se ve en la repetición." |
| 3 | 0:20–0:32 | **Un comando.** Terminal: `make run` (comando B), acelerado ×2 hasta `listo en … s`; corte a `make check` → **OK: formato válido**. | "Todo corre con un solo comando, en una notebook común: quince segundos para doscientos mil comentarios, sin GPU y sin gastar un peso en IA." |
| 4 | 0:32–0:40 | **Qué circula.** Dashboard arriba de todo (`01_inicio.png`): las tarjetas y las primeras narrativas. Pasar el mouse sobre un gráfico (aparece el tooltip). | "Encuentra solas las trece narrativas: arriba los que apoyan, abajo los que rechazan." |
| 5 | 0:40–0:55 | **En vivo.** Click en **▶ Reproducir en vivo**. Dejar correr hasta el **día 6** (`02_dia6.png`): aparecen juntas la alerta de *narrativa emergente* y la de *operación op03*. Pausar ahí (click en ■). | "Reproducimos los catorce días. El día seis, a la una de la mañana, aparece un rumor nuevo… y en el mismo minuto, veinticuatro cuentas creadas el día anterior empiezan a empujarlo de madrugada." |
| 6 | 0:55–1:05 | **Quién lo empuja.** Scroll al panel *Quién lo empuja* (`03_final.png`, columna derecha): op01, op02, op03 con cuentas, antigüedad y actividad nocturna. | "Tres operaciones, con su perfil: cuentas nuevas, cuentas antiguas que se responden entre sí, actividad nocturna. Qué empujan y desde cuándo." |
| 7 | 1:05–1:15 | **Probado.** `docs/SINTETICOS.md` en GitHub (tabla de resultados) o placa con: **53,6 / 55 en práctica · narrativas 29,7/30 en temas que nunca vio · robusto a datos sucios**. | "Lo medimos con el puntaje oficial: cincuenta y tres coma seis sobre cincuenta y cinco. Y lo probamos con temas que nunca vio, datos sucios y menos volumen." |
| 8 | 1:15–1:22 | **Cierre.** Placa final: **Vertiente** · *Qué circula, desde cuándo y quién lo empuja* · link al repo · Sebastián Paz, Francisco Fernández y Antonio Chocobar. | "Vertiente: narrativas y coordinación a escala. Explicable, rápido y barato." |

Duración total ≈ 1:22. Si sobra tiempo, la escena 5 es la que más luce: dejala respirar.

## Cómo grabar

**Preparación (una vez):**
1. `make run && make demo` → abre `salida/practica/dashboard.html` en Chrome.
2. Chrome en ventana de **1920×1080**, zoom 100%, **tema claro** (botón ◐ si hace falta: proyecta mejor), sin barra de
   favoritos, modo invitado (sin extensiones ni datos personales a la vista).
3. Terminal con fuente grande (≥ 18 pt), fondo oscuro, ventana a pantalla completa, prompt corto
   (`PS1='$ '` en zsh: `export PS1='$ '`).
4. Notificaciones del sistema desactivadas (modo No molestar).

**Comandos para las tomas:**
- **A (escena 1):** `gzcat datos/practica/comentarios.csv.gz | head -400` (líneas crudas del CSV pasando rápido)
- **B (escena 3):** `make run` y después `make check` (para que corra en ~15 s, correlo una vez antes: deja la caché
  caliente).
- Atajo para saltar a un día del dashboard sin esperar la reproducción: agregar `#t=21` al final de la URL (día 6).

**Captura:** macOS `Cmd+Shift+5` → *Grabar pantalla completa* (o QuickTime). Una toma por escena; 2–3 segundos de
margen antes y después de cada una para cortar cómodo.

**Locución:** un integrante, con el celular a un palmo y en un lugar sin eco (un placard con ropa funciona). Leer el
guion escena por escena, una toma por escena, con una pausa breve entre frases. Tono: claro, sin apuro. Si no hay
lugar tranquilo en el evento, la alternativa es una voz sintética leyendo la misma tabla.

**Edición (CapCut, iMovie o DaVinci Resolve, gratis):**
1. Pistas: video de pantalla · locución · música (volumen ~15%, bajarla más cuando hay voz).
2. Cortar cada toma al tiempo de la tabla; la escena 3 acelerada ×2.
3. Importar `subtitulos.srt` (está sincronizado con la tabla; si la locución queda más larga, correr los bloques).
4. Placas de texto (escenas 1, 7 y 8): fondo `#f9f9f7`, texto `#0b0b0b`, tipografía del sistema, grande.
5. Exportar **1080p, H.264, MP4**, ≤ 3 min (límite a confirmar con la organización, ver `docs/CONSULTAS.md`).

**Música:** algo instrumental y tranquilo, libre de derechos (la biblioteca de audio de YouTube o la de CapCut
alcanzan). Nada con letra.

## Checklist antes de subir a Hacki

- [ ] Se lee sin sonido (subtítulos visibles en toda la duración).
- [ ] No aparecen claves, mails personales ni pestañas privadas en ninguna toma.
- [ ] Los números en pantalla coinciden con los del README al momento de grabar (si corren el set final, actualizar
      la placa de la escena 7).
- [ ] Duración ≤ 3:00 y archivo MP4 1080p.
