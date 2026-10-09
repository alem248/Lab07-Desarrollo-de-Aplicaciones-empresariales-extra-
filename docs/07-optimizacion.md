# Paso 7 — Optimización de consultas en el ORM

## Refactorización de `blog/queries.py`

```python
"""Queries behind the views. Part 2 of the lab happens in this file."""
from blog.models import Post


def posts_for_front_page():
    # One query fetches the posts together with their author (one-to-one/
    # many-to-one relation, `select_related`); a second one fetches all
    # their tags at once (many-to-many relation, `prefetch_related`). Two
    # queries, regardless of how many posts are published.
    return (
        Post.objects.filter(published=True)
        .select_related("author")
        .prefetch_related("tags")
        .order_by("-published_at")
    )
```

## Regla aplicada

| Relación | Tipo | Herramienta | Por qué |
|---|---|---|---|
| `Post.author` | ForeignKey (muchos a uno) | `select_related` | Se resuelve con un `JOIN` SQL en la **misma** consulta: una fila del autor por cada fila de artículo |
| `Post.tags` | ManyToMany (colección) | `prefetch_related` | No cabe en un `JOIN` sin inflar el resultado; se trae **todas** las etiquetas de **todos** los artículos en **una** consulta extra y se unen en Python |

> `select_related` es para relaciones «uno a uno» (OneToOne, ForeignKey);
> `prefetch_related` es para colecciones (ManyToMany, FK inversa).

## Suite en verde

```console
$ .venv\Scripts\python.exe manage.py test
Found 24 test(s).
System check identified no issues (0 silenced).
.........s.....s........
----------------------------------------------------------------------
Ran 24 tests in 0.268s
OK (skipped=2)
Destroying test database for alias 'default'...
```

Las dos pruebas omitidas (`s`) requieren la carpeta `teacher/` del
docente, ausente en la copia del estudiante; el resto —incluida
`test_front_page_runs_two_queries`— pasa.

## Tabla comparativa (mediciones sobre la misma máquina)

Medición con 200 repeticiones de la carga completa de la portada
(artículos + `post.author.name` + `post.tags.all()` por artículo):

| Versión | Consultas | Tiempo medio | Reducción |
|---|---|---|---|
| Ingenua (N+1, roja) | 23 | 14.422 ms | — |
| Optimizada (`select_related` + `prefetch_related`, verde) | **2** | **2.943 ms** | **23 → 2 consultas (−91 %)**, **≈ 4.9× más rápida** |

| Métrica | Roja | Verde |
|---|---|---|
| Consultas por petición | 23 | 2 |
| Escalabilidad | O(N): +2 consultas por artículo publicado | O(1): 2 consultas fijas |
| Caudal estimado (peticiones/seg) | ~69 | ~340 |

La diferencia de tiempo es modesta con 11 artículos, pero la consulta
verde **no crece** con el número de artículos: con 1 000 publicados, la
roja haría 2 001 consultas y la verde seguiría haciendo 2.

## Nota sobre el historial

El refactor ya estaba en el código al iniciar la sesión (commit
`ee0d36b perf(front-page): select_related+prefetch_related...`); se
verificó su validez ejecutando la traza roja (Paso 6), el benchmark
superior y la suite completa en verde.
