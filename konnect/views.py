"""KONNECT API + web page. One DRF surface serves the web feed (session auth)
and the Flutter app (JWT) — same pattern as the retired Buzz chat."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from employee.models import Employee
from konnect.models import CATEGORY_CHOICES, KonnectComment, KonnectLike, KonnectPost
from skylinx_api.auth import CompanyScopedJWTAuthentication

PAGE_SIZE = 20


def _me(request):
    try:
        return request.user.employee_get
    except Exception:
        return None


def _is_hr_or_ceo(employee):
    from base.rbac import org_rank, HR_MANAGER_RANK

    user = employee.employee_user_id
    return bool(user and org_rank(user) <= HR_MANAGER_RANK)


class KonnectAPIView(APIView):
    authentication_classes = (CompanyScopedJWTAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)


def _post_payload(p, me, request):
    author_name = p.author.get_full_name() if p.author else p.company.company
    author_avatar = p.author.get_avatar() if p.author else None
    return {
        "id": p.id,
        "author": author_name,
        "author_id": p.author_id,
        "author_avatar": author_avatar,
        "is_system": p.author_id is None,
        "body": p.body,
        "image": request.build_absolute_uri(p.image.url) if p.image else None,
        "category": p.category,
        "category_label": dict(CATEGORY_CHOICES).get(p.category, p.category),
        "pinned": p.pinned,
        "mentions": [
            {"id": m.id, "name": m.get_full_name()} for m in p.mentions.all()
        ],
        "likes": p.likes.count(),
        "liked": p.likes.filter(employee_id=me.id).exists(),
        "comments": p.comments.filter(is_deleted=False).count(),
        "deletable": p.author_id == me.id or _is_hr_or_ceo(me),
        "at": p.created_at.isoformat(),
    }


class FeedAPIView(KonnectAPIView):
    """GET ?page=N: company feed, pinned first. POST: create a post."""

    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request):
        me = _me(request)
        if me is None:
            return Response({"error": "Not an employee."}, status=400)
        company = me.get_company()
        if not company:
            return Response({"results": [], "has_more": False})
        qs = (
            KonnectPost.objects.filter(company=company, is_deleted=False)
            .select_related("author", "company")
            .prefetch_related("mentions", "likes", "comments")
        )
        try:
            page = max(1, int(request.GET.get("page", 1)))
        except ValueError:
            page = 1
        start, end = (page - 1) * PAGE_SIZE, page * PAGE_SIZE
        posts = list(qs[start : end + 1])
        has_more = len(posts) > PAGE_SIZE
        data = [_post_payload(p, me, request) for p in posts[:PAGE_SIZE]]
        return Response({
            "results": data,
            "has_more": has_more,
            "can_post": True,
            "can_announce": _is_hr_or_ceo(me),
        })

    def post(self, request):
        me = _me(request)
        if me is None:
            return Response({"error": "Not an employee."}, status=400)
        company = me.get_company()
        if not company:
            return Response({"error": "No company."}, status=400)
        body = str(request.data.get("body", "")).strip()[:4000]
        if not body:
            return Response({"error": "Empty post."}, status=400)
        category = request.data.get("category", "general")
        if category not in dict(CATEGORY_CHOICES):
            category = "general"
        pinned = str(request.data.get("pinned", "")).lower() in ("1", "true")
        # Announcements + pinning are an HR/CEO privilege
        if (category == "announcement" or pinned) and not _is_hr_or_ceo(me):
            return Response({"error": "Only HR/Admin can post announcements."}, status=403)
        post = KonnectPost.objects.create(
            company=company,
            author=me,
            body=body,
            category=category,
            pinned=pinned,
            image=request.FILES.get("image"),
        )
        return Response({"id": post.id}, status=201)


class PostDetailAPIView(KonnectAPIView):
    """DELETE: soft-delete (own post, or HR/CEO on any company post)."""

    def _get(self, request, post_id):
        me = _me(request)
        if me is None:
            return None, None
        post = KonnectPost.objects.filter(
            id=post_id, company=me.get_company(), is_deleted=False
        ).first()
        return me, post

    def delete(self, request, post_id):
        me, post = self._get(request, post_id)
        if post is None:
            return Response({"error": "Not found."}, status=404)
        if post.author_id != me.id and not _is_hr_or_ceo(me):
            return Response({"error": "Not allowed."}, status=403)
        post.is_deleted = True
        post.save(update_fields=["is_deleted"])
        return Response({"ok": True})


class LikeAPIView(KonnectAPIView):
    """POST: toggle like."""

    def post(self, request, post_id):
        me = _me(request)
        if me is None:
            return Response({"error": "Not an employee."}, status=400)
        post = KonnectPost.objects.filter(
            id=post_id, company=me.get_company(), is_deleted=False
        ).first()
        if post is None:
            return Response({"error": "Not found."}, status=404)
        like, created = KonnectLike.objects.get_or_create(post=post, employee=me)
        if not created:
            like.delete()
        return Response({"liked": created, "likes": post.likes.count()})


class CommentsAPIView(KonnectAPIView):
    """GET: comments on a post. POST: add a comment."""

    def _post(self, request, post_id):
        me = _me(request)
        if me is None:
            return None, None
        post = KonnectPost.objects.filter(
            id=post_id, company=me.get_company(), is_deleted=False
        ).first()
        return me, post

    def get(self, request, post_id):
        me, post = self._post(request, post_id)
        if post is None:
            return Response({"error": "Not found."}, status=404)
        data = [
            {
                "id": c.id,
                "author": c.employee.get_full_name(),
                "avatar": c.employee.get_avatar(),
                "body": c.body,
                "at": c.created_at.isoformat(),
                "deletable": c.employee_id == me.id or _is_hr_or_ceo(me),
            }
            for c in post.comments.filter(is_deleted=False).select_related("employee")
        ]
        return Response({"results": data})

    def post(self, request, post_id):
        me, post = self._post(request, post_id)
        if post is None:
            return Response({"error": "Not found."}, status=404)
        body = str(request.data.get("body", "")).strip()[:2000]
        if not body:
            return Response({"error": "Empty comment."}, status=400)
        c = KonnectComment.objects.create(post=post, employee=me, body=body)
        return Response({"id": c.id}, status=201)


class CommentDetailAPIView(KonnectAPIView):
    """DELETE a comment (own, or HR/CEO)."""

    def delete(self, request, comment_id):
        me = _me(request)
        if me is None:
            return Response({"error": "Not an employee."}, status=400)
        c = KonnectComment.objects.filter(
            id=comment_id, post__company=me.get_company(), is_deleted=False
        ).first()
        if c is None:
            return Response({"error": "Not found."}, status=404)
        if c.employee_id != me.id and not _is_hr_or_ceo(me):
            return Response({"error": "Not allowed."}, status=403)
        c.is_deleted = True
        c.save(update_fields=["is_deleted"])
        return Response({"ok": True})


@login_required
def konnect_page(request):
    return render(request, "konnect/konnect.html")
