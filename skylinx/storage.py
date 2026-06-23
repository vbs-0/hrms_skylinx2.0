"""Static files storage for production.

Manifest storage hashes filenames (style.abc123.css) so WhiteNoise can serve
them with a 1-year immutable cache instead of the 60s default — first load
downloads once, every later visit is a browser cache hit. Compression keeps the
precompressed .gz/.br variants.

The vendored frontend bundle references a few assets that aren't shipped (e.g.
sourcemaps). manifest_strict=False handles that at *runtime*; the hashed_name
override keeps *collectstatic* from crashing on those missing references.
"""

from whitenoise.storage import CompressedManifestStaticFilesStorage


class StaticStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False

    def hashed_name(self, name, content=None, filename=None):
        # A missing referenced file (stray sourcemap, etc.) must not abort the
        # whole collectstatic post-process — keep the plain name for that ref.
        try:
            return super().hashed_name(name, content, filename)
        except ValueError:
            return name
