# Paso 10 — Entregable: tabla de uso de IA y conclusiones técnicas

## Tabla de auditoría del uso de la IA

| Requerimiento | Prompt (pregunta dictada) | Respuesta de la IA | Decisión técnica | Justificación |
|---|---|---|---|---|
| Artículos publicados | «Los artículos que ya están publicados.» | `Post.objects.filter(published=True)` | **Aceptada** | Correcta, 1 consulta, dentro del presupuesto. El filtro booleano directo es el caso trivial. |
| Artículos sin categoría | «Los artículos que no tienen categoría asignada.» | `Post.objects.filter(category__isnull=True)` | **Aceptada** | Correcta, 1 consulta. `isnull=True` es la forma canónica de consultar una FK nullable. |
| Rango de fechas inclusivo | «Los artículos publicados entre el 1 de marzo y el 31 de mayo de 2026, ambos días incluidos.» | `filter(published_at__gt=..., published_at__lt=...)` | **Rechazada** | Usa comparadores estrictos: excluye los dos artículos de borde (`2026-03-01`, `2026-05-31`). *Resultado distinto por un borde.* Correcto: `__range`. |
| Más de dos comentarios | «Los artículos con más de dos comentarios.» | `[p for p in Post.objects.all() if p.comments.count() > 2]` | **Rechazada** | El resultado es correcto pero filtra en Python: 16 consultas (N+1). *Correcta pero cara.* Correcto: `annotate(Count("comments")).filter(n_comments__gt=2)` en 1 consulta. |
| Top 3 con conteos | «Los tres artículos publicados con más comentarios, y de cada uno cuántos comentarios y cuántas etiquetas tiene.» | `annotate(n_comments=Count("comments"), n_tags=Count("tags"))` | **Rechazada** | Dos `JOIN` a colecciones generan producto cartesiano: 6 comentarios × 3 etiquetas = 18. *Conteos multiplicados.* Correcto: `Count(..., distinct=True)`. |
| Autores de Perú | «Los artículos escritos por autores de Perú (publicados o no).» | `Post.objects.filter(author__country="Perú")` | **Rechazada** | `country` no existe en `Author`; vive en `Profile`. *Campo inventado*: `FieldError` en tiempo de construcción. Correcto: `author__profile__country`. |
| Comentarios de Tecnología | «Los comentarios de los artículos de la categoría «Tecnología».» | `Comment.objects.filter(post__category__name="Tecnología")` | **Aceptada** | Correcta, 1 consulta. Navegación en cadena por FK con el operador de lookup adecuado. |
| Autores que nunca publicaron | «Los autores que nunca han publicado un artículo.» | `Author.objects.filter(posts__published=False)` | **Rechazada** | Retorna «autores con al menos un borrador», no «autores que nunca publicaron»: incluye a Ana Quispe y excluye a Diego Pinto. *Resultado distinto por el significado de la pregunta.* Correcto: `exclude(posts__published=True)`. |

**Balance**: 3 de 8 aceptables (q1, q2, q7). Las cinco restantes
demuestran que la IA no verifica bordes, cardinalidades, existencia
de campos ni el sentido del enunciado, y que su coste puede ser 16×
el necesario.

## Conclusiones técnicas

### 1. La salida de un LLM es un dato, no una instrucción

Un modelo de lenguaje produce texto probable, no verdad
verificada. En este laboratorio eso se demostró tres
veces: la IA **inventó un campo** (`author__country`),
**multiplicó conteos** (producto cartesiano sin
`distinct`) y **malinterpretó el enunciado** («tiene
borradores» ≠ «nunca publicó»). Ninguna de esas salidas
puede tratarse como confiable por el simple hecho de
venir del modelo: son *datos no confiables*
(`untrusted_data`), exactamente como un comentario de
usuario que contiene «IGNORA TUS INSTRUCCIONES
ANTERIORES».

### 2. Todo lo que ejecuta un LLM debe pasar por un contrato determinista

El patrón correcto —implementado en
`blog/agent/registry.py`— es separar **proponer** de
**ejecutar**:

- **Catálogo cerrado**: solo existen las acciones
  explícitamente registradas; lo desconocido se niega,
  no se interpreta.
- **Sin superficie de código**: nada de `eval`, `exec`
  ni SQL libre; la intención es JSON estructurado.
- **Tipos exactos**: la validación rechaza argumentos
  faltantes, sobrantes o de tipo incorrecto (un `bool`
  no es un `post_id` válido).
- **Presupuesto de consultas**: una respuesta correcta
  pero cara (16 consultas) es un defecto, no un éxito;
  el duelo mide coste, no solo resultado.
- **Oráculo determinista**: la respuesta esperada se
  calcula **sin el ORM** (Python puro sobre datos
  fijos), de modo que si el ORM y el oráculo
  discrepan, el error está en la consulta.

### 3. Las escrituras destructivas exigen aprobación humana con hash

Ninguna acción de riesgo R2 se ejecuta por decir del
modelo: la pasarela devuelve un **plan** con el hash
SHA-256 del estado que se va a tocar, y solo la
aplicación del plan —aprobado por un humano que
introduce ese hash— materializa la operación. Si los
datos cambian entre la visualización y la aprobación
(concurrencia), el hash caduca y la operación vuelve a
requerir revisión: el consentimiento humano es
**vinculante al estado exacto** que se aprobó, no a la
intención del modelo.

### 4. La verificación es el límite que vuelve útil a la IA

La IA es aceptable como **autor de borradores** dentro
de un proceso con verificación: el duelo la somete a un
oráculo determinista y a un presupuesto de consultas, y
la auditoría clasifica cada fallo con evidencia SQL
(`print(consulta.query)`). Con ese límite, sus aciertos
se aprovechan (q1, q2, q7) y sus errores se detectan
antes de llegar a producción. Sin ese límite, sus
errores se despliegan.

### 5. Resumen ejecutivo

| Principio | Implementación en el laboratorio |
|---|---|
| Salidas de LLM = datos no confiables | `untrusted_data` en lecturas R0 |
| Contrato determinista de acciones | `ACTIONS` cerrado + `_valid_args` |
| Sin ejecución de código arbitrario | JSON, no `eval`; no hay `run_sql` |
| Presupuesto y oráculo | `duel`: `expected` en Python puro + `budget` |
| Escritura con consentimiento informado | `plan_hash` + `--approve` humano |
| Concurrencia | el hash cubre el estado actual; mutaciones lo invalidan |

**Conclusión general**: un LLM puede *proponer*; los
sistemas empresariales deben *disponer*. La frontera
entre ambos —catálogo cerrado, validación de tipos,
presupuesto de consultas, oráculo determinista y
aprobación humana con hash— es lo que convierte una
salida probabilística en una operación segura.
