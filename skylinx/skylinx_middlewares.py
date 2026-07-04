"""
skylinx_middlewares.py

This module is used to register skylinx's middlewares without affecting the skylinx/settings.py
"""

import threading
from contextvars import ContextVar

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseNotAllowed
from django.shortcuts import render
from django.utils.datastructures import MultiValueDictKeyError

from skylinx.config import logger

_request_var = ContextVar("request", default=None)
current_company_id = ContextVar("current_company_id", default=None)
_thread_local_state = ContextVar("thread_local_state", default={})


class _ThreadLocalProxy:
    def __getattr__(self, name):
        if name == "request":
            return _request_var.get()
        state = _thread_local_state.get()
        if name in state:
            return state[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name == "request":
            _request_var.set(value)
        else:
            state = dict(_thread_local_state.get())
            state[name] = value
            _thread_local_state.set(state)


_thread_locals = _ThreadLocalProxy()


class ThreadLocalMiddleware:
    """
    ThreadLocalMiddleWare
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        response = self.get_response(request)
        return response
        _thread_locals.request = None


class MethodNotAllowedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if isinstance(response, HttpResponseNotAllowed):
            return render(request, "405.html", status=405)
        return response
        _thread_locals.request = None


class HtmlNoCacheMiddleware:
    """Never let browsers cache app HTML.

    HTMX fetches many URLs both as full pages and as fragments; without
    explicit cache headers a browser may replay a stale/partial response on
    refresh or back-nav, which renders pages with the top bar missing.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_type = response.get("Content-Type", "")
        if content_type.startswith("text/html") and not response.has_header(
            "Cache-Control"
        ):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response["Pragma"] = "no-cache"
        return response


class HtmxRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        is_htmx = (
            request.headers.get("HX-Request") == "true"
            or request.META.get("HTTP_HX_REQUEST") == "true"
        )
        if is_htmx and 300 <= getattr(response, "status_code", 0) < 400:
            redirect_to = response.headers.get("Location") or response.get("Location")
            if redirect_to:
                response.status_code = 200
                try:
                    del response["Location"]
                except Exception:
                    pass
                response["HX-Redirect"] = redirect_to
        return response
        _thread_locals.request = None


class SVGSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Apply security headers to SVG files
        if request.path.endswith(".svg") and response.status_code == 200:
            response["Content-Security-Policy"] = (
                "default-src 'none'; style-src 'unsafe-inline';"
            )
            response["X-Content-Type-Options"] = "nosniff"

        return response
        _thread_locals.request = None


class MissingParameterMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, KeyError):
            missing_key = str(exception).strip("'")
            message = f"Required parameter '{missing_key}' is missing from the request."

            logger.error(message)

            if not settings.DEBUG:
                messages.error(request, message)
                return render(request, "went_wrong.html", status=400)

        return None


def set_selected_company(company_id):
    current_company_id.set(company_id)


def get_selected_company():
    return current_company_id.get()
