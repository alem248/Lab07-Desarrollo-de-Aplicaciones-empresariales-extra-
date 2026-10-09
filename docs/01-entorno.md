# Paso 1 — Inicialización y exploración del entorno

## Entorno de trabajo

| Componente | Versión |
|---|---|
| Sistema operativo | Windows 11 (win32) |
| Intérprete Python | 3.14.8 (`C:\Users\iansh\AppData\Local\Programs\Python\Python314\python.exe`) |
| Django (desde `requirements.txt`: `Django>=5.2,<7`) | 6.1.2 |
| Git | 2.56.0.windows.2 |
| Identidad de commit | Ian1709 <ian.rau.1721@gmail.com> |

## Transcripción de la puesta en marcha

```console
$ python -m venv .venv
$ .venv\Scripts\python.exe -m pip install --upgrade pip
$ .venv\Scripts\python.exe -m pip install -r requirements.txt
$ .venv\Scripts\python.exe -c "import django; print(django.get_version())"
6.1.2

$ .venv\Scripts\python.exe manage.py migrate
Operations to perform:
  Apply all migrations: admin, auth, blog, contenttypes, sessions
Running migrations:
  Applying contenttypes.0001_initial... OK
  ... (migraciones de auth, admin, contenttypes, sessions) ...
  Applying blog.0001_initial... OK
  Applying sessions.0001_initial... OK

$ .venv\Scripts\python.exe manage.py seed_blog
Listo: 4 autores, 15 artículos, 23 comentarios.
```

## Conteo verificado desde la consola interactiva

```console
$ .venv\Scripts\python.exe manage.py shell
>>> from blog.models import Author, Post, Comment, Profile, Tag, Category
>>> Author.objects.count()    # autores
4
>>> Profile.objects.count()    # perfiles (uno por autor, OneToOne)
4
>>> Category.objects.count()   # categorías
4
>>> Tag.objects.count()        # etiquetas
5
>>> Post.objects.count()       # artículos en total
15
>>> Post.objects.filter(published=True).count()   # publicados
11
>>> Post.objects.filter(published=False).count()  # borradores
4
>>> Comment.objects.count()    # comentarios
23
```

## Registro de los datos deterministas

El comando `seed_blog` borra y vuelve a cargar **siempre el mismo
contenido** (`blog/seed_data.py`), lo que convierte la base de datos en un
oráculo determinista: la respuesta correcta de cada pregunta del duelo se
puede calcular de antemano con Python puro, sin el ORM.

| Entidad | Cantidad | Nota |
|---|---|---|
| Autores (`Author`) | 4 | Ana Quispe (Perú), Beto Salas (Perú), Carla Rojas (Chile), Diego Pinto (Chile) |
| Perfiles (`Profile`) | 4 | Uno por autor; guardan el país (campo que usa la pregunta 6) |
| Categorías (`Category`) | 4 | Tecnología, Cultura, Deportes, Opinión |
| Etiquetas (`Tag`) | 5 | django, python, orm, noticias, tutorial |
| Artículos (`Post`) | 15 | 11 publicados + 4 borradores |
| Comentarios (`Comment`) | 23 | Distribuidos: 6, 4, 3, 2, 1, 0, 2, 2, 0, 1, 2 y 0 en los borradores |

### Observaciones de borde que el laboratorio trae a propósito

- Dos artículos caen **exactamente** en los límites del rango de la
  pregunta 3: `2026-03-01` («Introducción al ORM de Django») y
  `2026-05-31` («Reseña: festival de cine andino»). Sirven para detectar
  respuestas que usan comparadores estrictos (`>`, `<`) en vez de un
  rango inclusivo.
- El cuarto comentario del artículo 1 contiene un texto hostil diseñado
  para atacar a un agente (véase el Paso 8).
- Diego Pinto **nunca escribió** ningún artículo; Carla Rojas solo tiene
  borradores. Ambos nunca publicaron (pregunta 8).

> **Nota de corrección aplicada**: el reporte del duelo usaba símbolos
> Unicode (`✔ ⚠ ✘ └`) que la consola Windows (cp1252) no puede codificar,
> lo que crasheaba el comando. Se cambiaron por marcadores ASCII
> (`[OK]`, `[~]`, `[X]`, `[-]`, `->`) en el commit
> `fix(duelo): marcadores ASCII para consolas Windows (cp1252)`.
