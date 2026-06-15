from skylinx.settings import TEMPLATES

TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "skylinx_crumbs.context_processors.breadcrumbs",
)
