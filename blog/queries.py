"""Queries behind the views. Part 2 of the lab happens in this file."""
from blog.models import Post


def posts_for_front_page():
    # The template walks `post.author.name` and `post.tags.all` once per post,
    # so this QuerySet has to bring all that with it:
    #
    # - `select_related("author")`: the author is a FK, so the JOIN rides
    #   along the same SELECT and costs nothing extra.
    # - `prefetch_related("tags")`: tags are MANY TO MANY. No JOIN can do it
    #   (it would repeat the posts), so Django runs ONE second query for all
    #   of them and hands out the sets from there.
    #
    # Both together: 2 queries for any number of posts, instead of
    # 1 + N authors + N tag sets.
    return (
        Post.objects.filter(published=True)
        .select_related("author")
        .prefetch_related("tags")
        .order_by("-published_at")
    )
