"""YOUR answers. One function per question, no arguments.

Write the ORM query that answers each question and return it (a QuerySet or a
list). Do not write SQL and do not filter in Python what the database can
filter. Check yourself with:

    python manage.py duel                 # all of them
    python manage.py duel --question q4   # just one

Question 5 asks for two numbers per post: annotate them as `n_comments` and
`n_tags`.
"""
from datetime import date

from django.db.models import Count, Q

from blog.models import Author, Category, Comment, Post, Profile, Tag


def q1():
    """Los artículos que ya están publicados."""
    return Post.objects.filter(published=True)


def q2():
    """Los artículos que no tienen categoría asignada."""
    # `category__isnull=True` looks for the missing category, not for a null
    # name on an existing one.
    return Post.objects.filter(category__isnull=True)


def q3():
    """Los artículos publicados entre el 1 de marzo y el 31 de mayo de 2026, ambos días incluidos."""
    start, end = date(2026, 3, 1), date(2026, 5, 31)
    # `__gte`/`__lte`, never `__gt`/`__lt`: the question includes both dates,
    # so the posts sitting exactly on them must show up.
    # On this dataset `published=True` changes nothing (drafts carry no date),
    # but the question asks for published articles, so the filter says so.
    return Post.objects.filter(
        published=True, published_at__gte=start, published_at__lte=end
    )


def q4():
    """Los artículos con más de dos comentarios."""
    # The counting and the filtering happen in the database: annotating the
    # count and filtering on it is one query. Counting with `.count()` per
    # post (what the AI answer does) is the N+1 problem.
    return Post.objects.annotate(n_comments=Count("comments")).filter(n_comments__gt=2)


def q5():
    """Los tres artículos publicados con más comentarios; de cada uno, cuántos comentarios
    (`n_comments`) y cuántas etiquetas (`n_tags`)."""
    return (
        Post.objects.filter(published=True)
        # `distinct=True` on BOTH counts: without it the join between
        # comments and tags multiplies the rows (a post with 6 comments and 3
        # tags counts 18 of each), and the answer comes out inflated.
        .annotate(
            n_comments=Count("comments", distinct=True),
            n_tags=Count("tags", distinct=True),
        )
        .order_by("-n_comments", "title")[:3]
    )


def q6():
    """Los artículos escritos por autores de Perú (publicados o no)."""
    # The country is not a field of Author: it lives in Profile, the one-to-one
    # hanging off it, so the lookup walks `author__profile__country`.
    return Post.objects.filter(author__profile__country="Perú")


def q7():
    """Los comentarios de los artículos de la categoría «Tecnología»."""
    # From Comment towards the post and its category. Nothing says published,
    # so drafts in that category are in the answer as well.
    return Comment.objects.filter(post__category__name="Tecnología")


def q8():
    """Los autores que nunca han publicado un artículo."""
    # "Never published" is the absence of any published post. Excluding the
    # authors that have one keeps both the drafts-only author and the author
    # that wrote nothing at all; `posts__published=False` is not the same
    # thing, because an author with drafts and published posts would match it.
    return Author.objects.exclude(posts__published=True)


# F401: the imports above are the ones the questions need; keeping them named
# here documents what each answer is built with (Count for q4/q5, Q, the
# models, `date` for q3).
