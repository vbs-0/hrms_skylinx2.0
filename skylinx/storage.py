"""Static files storage for production.

Manifest storage hashes filenames (style.abc123.css) so WhiteNoise can serve
them with a 1-year immutable cache instead of the 60s default — first load
downloads once, every later visit is a browser cache hit. Compression keeps the
precompressed .gz/.br variants. manifest_strict=False means a stray static
reference that wasn't collected falls back to the plain name instead of 500ing.
"""

from whitenoise.storage import CompressedManifestStaticFilesStorage


class StaticStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False
