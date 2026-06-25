"""Static files storage for production.

Manifest storage hashes filenames (style.abc123.css) so WhiteNoise can serve
them with a 1-year immutable cache instead of the 60s default — first load
downloads once, every later visit is a browser cache hit. Compression keeps the
precompressed .gz/.br variants.

The vendored frontend bundle references a few assets that aren't shipped (e.g.
sourcemaps). manifest_strict=False handles that at *runtime*; the hashed_name
override keeps *collectstatic* from crashing on those missing references.
"""

from django.core.exceptions import SuspiciousOperation
from whitenoise.storage import CompressedManifestStaticFilesStorage


class StaticStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False

    def hashed_name(self, name, content=None, filename=None):
        # A bad static reference must never 500/400 a page. Two cases seen:
        #   ValueError          -> missing referenced file (stray sourcemap)
        #   SuspiciousOperation -> template uses a leading-slash path like
        #                          {% static '/jquery/jquery.min.js' %}, which
        #                          safe_join() rejects as outside STATIC_ROOT.
        # Either way, fall back to the plain name and let the page render.
        try:
            return super().hashed_name(name, content, filename)
        except (ValueError, SuspiciousOperation):
            return name
