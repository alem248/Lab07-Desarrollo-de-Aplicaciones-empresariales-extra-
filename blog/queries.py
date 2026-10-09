"""Queries behind the views. Part 2 of the lab happens in this file."""
from blog.models import Post


def posts_for_front_page():
    # One query fetches the posts together with their author (one-to-one/many-to-
    # one relation, `select_related`); a second one fetches all their tags at
    # once (many-to-many relation, `prefetch_related`). Two queries, regardless
    # of how many posts are published.
    return (
        Post.objects.filter(published=True)
        .select_related("author")
        .prefetch_related("tags")
        .order_by("-published_at")
    )
