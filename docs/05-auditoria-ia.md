# Paso 5 — Auditoría y clasificación de fallos de la IA

Se ejecutaron las respuestas del asistente de IA
(`blog/duel/ai_answers.py`) contra el mismo oráculo
determinista que valida las del equipo:

```console
$ .venv\Scripts\python.exe manage.py duel --source ai

Duelo — respuestas de: ai
q1  [OK] correcta            1 consulta(s)   Los artículos que ya están publicados.
q2  [OK] correcta            1 consulta(s)   Los artículos que no tienen categoría asignada.
q3  [X] resultado distinto   1 consulta(s)   Los artículos publicados entre el 1 de marzo y el 31 de mayo
      -> faltan 2 (p. ej. 'Introducción al ORM de Django')
q4  [~] correcta pero cara   16 consulta(s)  Los artículos con más de dos comentarios.
      -> 16 consultas; una buena respuesta necesita 1
q5  [X] resultado distinto   1 consulta(s)   Los tres artículos publicados con más comentarios, y de cada
      -> devolvió [('Introducción al ORM de Django', 18, 18), ('QuerySets perezosos', 12, 12),
         ('Managers propios paso a paso', 8, 8)];
         se esperaba [('Introducción al ORM de Django', 6, 3), ('Managers propios paso a paso', 4, 2),
         ('QuerySets perezosos', 3, 4)]
q6  [X] error                0 consulta(s)   Los artículos escritos por autores de Perú (publicados o no)
      -> FieldError: Unsupported lookup 'country' for ForeignKey or join on the field not permitted.
q7  [OK] correcta            1 consulta(s)   Los comentarios de los artículos de la categoría «Tecnología»
q8  [X] resultado distinto   1 consulta(s)   Los autores que nunca han publicado un artículo.
      -> faltan 1 (p. ej. 'Diego Pinto'); sobran 1 (p. ej. 'Ana Quispe')

3 de 8 correctas y baratas.
```

**Resultado global de la IA: 3 de 8.** La del equipo: **8 de 8**
(`python manage.py duel`), una consulta por pregunta.

## Lado del equipo (referencia correcta)

| Pregunta | Consulta | Costo |
|---|---|---|
| q1 | `Post.objects.filter(published=True)` | 1 |
| q2 | `Post.objects.filter(category__isnull=True)` | 1 |
| q3 | `Post.objects.filter(published_at__range=(date(2026,3,1), date(2026,5,31)))` | 1 |
| q4 | `Post.objects.annotate(n_comments=Count("comments")).filter(n_comments__gt=2)` | 1 |
| q5 | `Post.objects.filter(published=True).annotate(n_comments=Count("comments", distinct=True), n_tags=Count("tags", distinct=True)).order_by("-n_comments")[:3]` | 1 |
| q6 | `Post.objects.filter(author__profile__country="Perú")` | 1 |
| q7 | `Comment.objects.filter(post__category__name="Tecnología")` | 1 |
| q8 | `Author.objects.exclude(posts__published=True)` | 1 |

> **Intentos por pregunta del equipo**: 1 en los ocho casos. La
> primera ejecución de `python manage.py duel` ya reportó
> «8 de 8 correctas y baratas»; ninguna pregunta requirió
> reescritura. (Las respuestas llegaron implementadas en el
> repositorio y se verificaron tal como están; el registro de
> intentos refleja esa verificación.)

## Evidencia SQL y clasificación de cada fallo

### q3 — «resultado distinto por un borde»

La IA escribió comparadores estrictos:

```python
Post.objects.filter(
    published_at__gt=date(2026, 3, 1),
    published_at__lt=date(2026, 5, 31),
)
```

SQL compilado (`print(consulta.query)`):

```sql
SELECT ... FROM "blog_post"
WHERE ("blog_post"."published_at" > '2026-03-01'
   AND "blog_post"."published_at" < '2026-05-31')
```

La pregunta dice «**ambos días incluidos**». El SQL excluye los
extremos y pierde exactamente los dos artículos de borde:
«Introducción al ORM de Django» (`2026-03-01`) y «Reseña:
festival de cine andino» (`2026-05-31`). El operador correcto es
`__range` (equivalente a `BETWEEN`, inclusivo).

**Clasificación: resultado distinto por un borde.**

### q4 — «correcta pero cara»

```python
[post for post in Post.objects.all() if post.comments.count() > 2]
```

El resultado es correcto, pero el filtro ocurre **en Python** y
`post.comments.count()` se ejecuta por artículo: 1 consulta para
traer los 15 artículos + 15 consultas `COUNT(*)` (una por cada
`post_id`) = **16 consultas** frente a 1 esperada. Traza real:

```sql
[1]  SELECT ... FROM "blog_post"
[2]  SELECT COUNT(*) AS "__count" FROM "blog_comment" WHERE "blog_comment"."post_id" = 46
[3]  SELECT COUNT(*) AS "__count" FROM "blog_comment" WHERE "blog_comment"."post_id" = 47
... (una por artículo, hasta 16 en total)
```

Es el patrón **N+1** aplicado a un agregado que el propio
motor puede calcular con `annotate(Count(...))`.

**Clasificación: correcta pero cara.**

### q5 — «conteos multiplicados»

```python
Post.objects.filter(published=True).annotate(
    n_comments=Count("comments"),
    n_tags=Count("tags"),
).order_by("-n_comments")[:3]
```

SQL compilado:

```sql
SELECT ..., COUNT("blog_comment"."id") AS "n_comments",
       COUNT("blog_post_tags"."tag_id") AS "n_tags"
FROM "blog_post"
LEFT OUTER JOIN "blog_comment" ON ("blog_post"."id" = "blog_comment"."post_id")
LEFT OUTER JOIN "blog_post_tags" ON ("blog_post"."id" = "blog_post_tags"."post_id")
WHERE "blog_post"."published" = True
GROUP BY "blog_post"."id", ...
ORDER BY 8 DESC LIMIT 3
```

Al juntar **dos colecciones a la vez**, el `JOIN` produce un
**producto cartesiano**: cada comentario de un artículo se
combina con cada etiqueta del mismo. «Introducción al ORM de
Django» tiene 6 comentarios y 3 etiquetas, y el ORM cuenta
`6 × 3 = 18` filas para *ambos* conteos. Por eso la IA
devolvió `(18, 18)`, `(12, 12)`, `(8, 8)` en lugar de
`(6, 3)`, `(4, 2)`, `(3, 4)`.

La solución es `Count(..., distinct=True)`: cuenta identificadores
distintos, deshaciendo el producto cartesiano.

**Clasificación: conteos multiplicados.**

### q6 — «campo inventado»

```python
Post.objects.filter(author__country="Perú")
```

```text
FieldError: Unsupported lookup 'country' for ForeignKey
or join on the field not permitted.
```

`country` **no existe** en `Author`; vive en `Profile`, que se
relaciona con `Author` por un `OneToOneField`. El ORM ni siquiera
puede compilar la consulta: error en tiempo de construcción,
0 consultas ejecutadas. La ruta correcta es
`author__profile__country="Perú"`.

**Clasificación: campo inventado.**

### q8 — «resultado distinto por el significado de la pregunta»

```python
Author.objects.filter(posts__published=False)
```

SQL compilado:

```sql
SELECT "blog_author"."id", "blog_author"."name"
FROM "blog_author"
INNER JOIN "blog_post" ON ("blog_author"."id" = "blog_post"."author_id")
WHERE "blog_post"."published" = False
```

La pregunta pide «autores que **nunca** han publicado». La IA
buscó «autores que **tienen al menos un borrador**»: el
`INNER JOIN` exige que el autor tenga algún artículo, y el
filtro `published = False` solo retiene los borradores.
Resultado: Ana Quispe (que publicó 6 artículos pero tiene 1
borrador) **aparece** y Diego Pinto (que nunca escribió nada)
**desaparece**. La forma correcta es una negación sobre la
existencia de publicados: `exclude(posts__published=True)`, que
incluye tanto a Carla Rojas (solo borradores) como a Diego
Pinto (sin artículos).

**Clasificación: resultado distinto por el significado de la pregunta.**

## Tabla comparativa final

| Pregunta | Equipo | IA | Falla de la IA | Categoría |
|---|---|---|---|---|
| q1 | ✔ 1 consulta | ✔ 1 consulta | — | — |
| q2 | ✔ 1 consulta | ✔ 1 consulta | — | — |
| q3 | ✔ 1 consulta | ✘ 1 consulta | excluye `2026-03-01` y `2026-05-31` | resultado distinto por un borde |
| q4 | ✔ 1 consulta | ⚠ 16 consultas | filtra en Python, N+1 sobre `COUNT` | correcta pero cara |
| q5 | ✔ 1 consulta | ✘ 1 consulta | `6×3=18` en vez de `(6, 3)` | conteos multiplicados |
| q6 | ✔ 1 consulta | ✘ error | `author__country` no existe | campo inventado |
| q7 | ✔ 1 consulta | ✔ 1 consulta | — | — |
| q8 | ✔ 1 consulta | ✘ 1 consulta | confunde «tiene borradores» con «nunca publicó» | resultado distinto por el significado de la pregunta |

**Conclusión de la auditoría**: la IA acierta las consultas
triviales (q1, q2, q7), pero falla en los cinco casos que
exigen semanticidad (bordes inclusivos, agregados sobre dos
colecciones, navegación por OneToOne, negación existencial) o
eficiencia. Ninguna de sus respuestas debe aceptarse sin el
oráculo determinista del duelo.
