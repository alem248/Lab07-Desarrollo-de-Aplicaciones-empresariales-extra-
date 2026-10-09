# Paso 2 — Análisis del modelo de datos (`blog/models.py`)

## Entidades y campos

| Modelo | Campos | Observaciones |
|---|---|---|
| `Author` | `name` (CharField, 100) | Autor del blog; raíz del grafo de relaciones |
| `Profile` | `author` (OneToOneField), `country` (CharField, 60), `bio` (TextField, blank) | Perfil **uno a uno** del autor; aquí vive el país que usa la pregunta 6 |
| `Category` | `name` (CharField, 60, unique) | Categoría de artículos; `verbose_name_plural = "categories"` |
| `Tag` | `name` (CharField, 40, unique) | Etiqueta reutilizable entre artículos |
| `Post` | `title`, `body`, `author` (FK), `category` (FK nullable), `tags` (M2M), `published` (BooleanField), `published_at` (DateField nullable) | Artículo; `published=False` con `published_at=None` marca un borrador |
| `Comment` | `post` (FK), `author_name` (CharField), `text`, `created_at` (DateTimeField, `auto_now_add`) | Comentario; el autor es texto libre, **no** un `Author` |

## Relaciones desglosadas

### 1. `Profile` ↔ `Author`: OneToOneField

```python
author = models.OneToOneField(Author, on_delete=models.CASCADE, related_name="profile")
```

- **Cardinalidad 1:1**: cada autor tiene como máximo un perfil y cada
  perfil pertenece a exactamente un autor.
- La FK vive en `Profile` (la tabla «hija» guarda `author_id`).
- `on_delete=CASCADE`: borrar el autor elimina su perfil.
- Accesos: `author.profile` (directo) y `profile.author` (inverso,
  nombre del modelo en minúsculas por defecto).
- **Implicación para las consultas**: es una relación de «muchos a uno
  hacia atrás», por lo que el ORM la resuelve con `select_related`
  (un `JOIN`), no con `prefetch_related`.

### 2. `Post` → `Author`: ForeignKey (muchos a uno)

```python
author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="posts")
```

- Un autor escribe **muchos** artículos; cada artículo tiene **un** autor.
- `related_name="posts"`: acceso inverso `author.posts.all()`.
- `on_delete=CASCADE`: borrar el autor borra sus artículos.

### 3. `Post` → `Category`: ForeignKey **opcional**

```python
category = models.ForeignKey(
    Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="posts"
)
```

- **Opcional**: `null=True, blank=True` permite artículos sin categoría
  (base de la pregunta 2: `category__isnull=True`).
- `on_delete=SET_NULL`: si se borra la categoría, el artículo queda
  «sin categoría» en vez de desaparecer.
- `related_name="posts"`: acceso inverso `category.posts.all()`.

### 4. `Post` ↔ `Tag`: ManyToManyField

```python
tags = models.ManyToManyField(Tag, blank=True, related_name="posts")
```

- **Cardinalidad N:M**: un artículo tiene muchas etiquetas y una
  etiqueta aparece en muchos artículos.
- Django crea la tabla intermedia `blog_post_tags` (`post_id`, `tag_id`).
- `blank=True`: un artículo puede no tener etiquetas.
- Accesos: `post.tags.all()` y `tag.posts.all()`.
- **Implicación para las consultas**: es una **colección**, por lo que se
  resuelve con `prefetch_related` (una consulta extra para todos los
  artículos), nunca con `select_related`.

### 5. `Comment` → `Post`: ForeignKey

```python
post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
```

- Un artículo acumula **muchos** comentarios; cada comentario pertenece a
  **un** artículo.
- `related_name="comments"`: acceso inverso `post.comments.all()` y
  agregación `Count("comments")`.
- `on_delete=CASCADE`: borrar el artículo borra sus comentarios.
- El autor del comentario es `author_name` (cadena libre), **no** una FK
  hacia `Author`: los lectores no son autores del blog.

## Diagrama conceptual

```mermaid
erDiagram
    Author ||--|| Profile : tiene
    Author ||--o{ Post : escribe
    Category ||--o{ Post : clasifica
    Post ||--o{ Comment : recibe
    Post }o--o{ Tag : etiquetan

    Author {
        int id PK
        string name
    }
    Profile {
        int id PK
        int author_id UK "OneToOne"
        string country
        text bio
    }
    Category {
        int id PK
        string name UNIQUE
    }
    Tag {
        int id PK
        string name UNIQUE
    }
    Post {
        int id PK
        string title
        text body
        int author_id FK
        int category_id FK "nullable, SET_NULL"
        bool published
        date published_at "nullable"
    }
    PostTag {
        int post_id FK "tabla intermedia"
        int tag_id FK
    }
    Comment {
        int id PK
        int post_id FK
        string author_name
        text text
        datetime created_at
    }
```

En texto plano:

```
┌──────────┐ 1      1 ┌─────────┐
│  Author  │◄─────────│ Profile │   OneToOne (profile.author_id)
└────┬─────┘          └─────────┘
     │ 1
     │                ┌──────────┐
     ├───────────────►│   Post   │◄──────┐  ┌──────────┐
     │  *             └┬───┬──┬──┘       │  │ Category │ (nullable, SET_NULL)
     │                 │   │  │          │  └──────────┘
     │                 │   │  └─ M2M ────┼──►┌────────┐
     │                 │   │    (blog_   │   │  Tag   │
     │                 │   │   post_tags)│   └────────┘
     │                 │   │             │
     │                 │   └── FK ───────┼──►┌─────────┐
     │                 │                 │   │ Comment │ *
     │                 └─ FK (author_id) │   └─────────┘
     │                                   │
     └─── (author_name es texto libre, NO es Author)
```

## Accesores generados por Django

| Desde | Acceso | Tipo | Sentido de la consulta |
|---|---|---|---|
| `Author` | `author.profile` | OneToOne | directo (JOIN) |
| `Author` | `author.posts` | Reverse FK | colección (`prefetch_related`) |
| `Post` | `post.author` | FK | directo (JOIN, `select_related`) |
| `Post` | `post.category` | FK nullable | directo (JOIN, `select_related`) |
| `Post` | `post.tags` | M2M | colección (`prefetch_related`) |
| `Post` | `post.comments` | Reverse FK | colección (`prefetch_related`) |
| `Comment` | `comment.post` | FK | directo (JOIN, `select_related`) |
| `Tag` | `tag.posts` | Reverse M2M | colección (`prefetch_related`) |
| `Category` | `category.posts` | Reverse FK | colección (`prefetch_related`) |

## Trazas de las preguntas del duelo sobre este esquema

| Pregunta | Relación que ejercita | Consulta clave |
|---|---|---|
| q1 — publicados | campo `Post.published` | `filter(published=True)` |
| q2 — sin categoría | FK nullable `Post.category` | `filter(category__isnull=True)` |
| q3 — rango de fechas | campo `Post.published_at` | `filter(published_at__range=(...))` |
| q4 — más de dos comentarios | Reverse FK `Post.comments` | `annotate(Count("comments"))` |
| q5 — top 3 con conteos | Reverse FK + M2M | `Count(..., distinct=True)` contra el producto cartesiano |
| q6 — autores de Perú | OneToOne `Author.profile` | `filter(author__profile__country="Perú")` |
| q7 — comentarios de Tecnología | FK en cadena `Comment→Post→Category` | `filter(post__category__name="Tecnología")` |
| q8 — nunca publicaron | Reverse FK con negación | `exclude(posts__published=True)` |
