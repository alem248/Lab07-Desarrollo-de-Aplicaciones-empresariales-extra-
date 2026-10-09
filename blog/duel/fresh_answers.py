"""Step 8 of the lab: the same eight questions asked to an assistant again.

`blog/duel/ai_answers.py` holds the assistant's FIRST cold answers (they were
written without the duel to check them). This module holds the SECOND request:
the same questions, again with only `blog/models.py` as context.

Caveat that belongs in the report: by the time this was written the assistant
had already answered these eight questions in the same session, so this is NOT
an independent sample of "an assistant asked cold". The independent sample is
`ai_answers.py`. This module is kept so the second round is reproducible:

    python manage.py duel --source fresh
"""
from datetime import date

from django.db.models import Count, Q

from blog.models import Author, Comment, Post


def q1():
    return Post.objects.filter(published=True)


def q2():
    return Post.objects.filter(category__isnull=True)


def q3():
    # `__range` is inclusive on both ends, which is what the question asks.
    return Post.objects.filter(published_at__range=(date(2026, 3, 1), date(2026, 5, 31)))


def q4():
    return Post.objects.annotate(n_comments=Count("comments")).filter(n_comments__gt=2)


def q5():
    return (
        Post.objects.filter(published=True)
        .annotate(
            n_comments=Count("comments", distinct=True),
            n_tags=Count("tags", distinct=True),
        )
        .order_by("-n_comments")[:3]
    )


def q6():
    # The country lives in Profile, the one-to-one of Author.
    return Post.objects.filter(author__profile__country="Perú")


def q7():
    return Comment.objects.filter(post__category__name="Tecnología")


def q8():
    # "Never published": annotate how many published posts each author has and
    # keep the ones with zero.
    return Author.objects.annotate(
        n_published=Count("posts", filter=Q(posts__published=True))
    ).filter(n_published=0)
