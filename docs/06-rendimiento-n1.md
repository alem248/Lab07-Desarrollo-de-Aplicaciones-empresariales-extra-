# Paso 6 — Diagnóstico del problema N+1

## Prueba en rojo

```console
$ .venv\Scripts\python.exe manage.py test blog.tests.test_front_page
...
FAIL: test_front_page_runs_two_queries (blog.tests.test_front_page.FrontPageTests.test_front_page_runs_two_queries)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "...\blog\tests\test_front_page.py", line 29, in test_front_page_runs_two_queries
    with self.assertNumQueries(2):
         ~~~~~~~~~~~~~~~~~~~~~~^^
AssertionError: 23 != 2 : 23 queries executed, 2 expected
...
Ran 3 tests in 0.097s
FAILED (failures=1, skipped=1)
```

La traza completa con las 23 consultas capturadas se conserva en
[`docs/evidencia/traza-n1-rojo.txt`](evidencia/traza-n1-rojo.txt).

## Origen de las 23 consultas

La portada (`blog/views.py`) evalúa `posts_for_front_page()` y la
plantilla `front_page.html` recorre cada artículo publicando, por cada
uno: `{{ post.author.name }}` (una ForeignKey) y `{% for tag in
post.tags.all %}` (un ManyToMany). Con la consulta ingenua
`Post.objects.filter(published=True).order_by("-published_at")` el ORM
no carga ni el autor ni las etiquetas: cada acceso en la plantilla
dispara su propia consulta.

| Bloque de consultas | Cantidad | Patrón en la traza |
|---|---|---|
| Artículos de la portada | **1** | consulta n.º 1: `SELECT ... FROM "blog_post" WHERE "blog_post"."published" = 1` |
| Autores (`post.author`) | **11** | consultas n.º 2, 4, 6, 8, 10, 12, 14, 16, 18, 20 y 22: `SELECT ... FROM "blog_author" WHERE "blog_author"."id" = ? LIMIT 21` |
| Etiquetas (`post.tags.all`) | **11** | consultas n.º 3, 5, 7, 9, 11, 13, 15, 17, 19, 21 y 23: `SELECT ... FROM "blog_tag" INNER JOIN "blog_post_tags" ... WHERE "blog_post_tags"."post_id" = ?` |
| **Total** | **23** | 1 + 11 + 11 |

Hay 11 artículos publicados (15 en total menos 4 borradores), de modo
que el desglose es exactamente **1 + 11 + 11 = 23**.

## Por qué crece en O(N)

El coste es **Q(N) = 1 + 2·N**, donde N es el número de artículos
publicados:

- Cada artículo nuevo obliga al ORM a resolver **dos** relaciones que no
  estaban cargadas: una consulta para su autor y otra para su conjunto
  de etiquetas.
- El gasto **no** depende del volumen de datos traídos por la consulta
  principal, sino del **número de filas iteradas en Python**: cada fila
  repite el mismo par de consultas idénticas en forma (solo cambia el
  `id`).
- Es la definición textual del antipatrón **N+1**: 1 consulta inicial
  «+ N» consultas repetidas por cada objeto. Con 11 artículos son 23;
  con 100 serían 201; con 1 000, 2 001. El rendimiento degrada
  linealmente con el tráfico de la página.

## La corrección (adelanto del Paso 7)

En `blog/queries.py`:

```python
return (
    Post.objects.filter(published=True)
    .select_related("author")     # ForeignKey/OneToOne: un JOIN
    .prefetch_related("tags")     # ManyToMany: una consulta extra para todos
    .order_by("-published_at")
)
```

- `select_related("author")` resuelve la FK del autor con un `JOIN`
  SQL en la misma consulta (relación «uno a uno» hacia atrás).
- `prefetch_related("tags")` trae **todas** las etiquetas de **todos**
  los artículos en una sola consulta adicional y hace el «join» en
  Python (colección ManyToMany).

Resultado: **2 consultas** cualquiera sea el número de artículos
publicados — la prueba `test_front_page_runs_two_queries` pasa a
verde (véase el Paso 7).
