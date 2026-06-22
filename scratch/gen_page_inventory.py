"""
Generate docs/page_inventory.md:
  Part A: curated navigable pages (sidebar + settings) — the HR menu surface.
  Part B: full crawl of the URL resolver, classified into PAGE vs ACTION/FRAGMENT,
          so we capture detail/tab/sub-views that have no sidebar entry.
ponytail: heuristic classifier; refine keyword lists if something lands wrong.
"""
import os, sys, re, glob, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skylinx.settings")
django.setup()
from django.urls import get_resolver, reverse

# ── Part A: sidebar + settings (curated) ────────────────────────────────
def rurl(name):
    try:
        return reverse(name)
    except Exception:
        try:
            return reverse(name, kwargs={"pk": 1})
        except Exception:
            return "(needs id)"

def sidebar_sections():
    out = []
    for f in sorted(glob.glob("*/sidebar.py")):
        s = open(f, encoding="utf-8").read()
        m = re.search(r'MENU\s*=\s*_\("([^"]+)"', s)
        if not m:
            continue
        pairs = re.findall(
            r'"menu":\s*_\("([^"]+)"\),\s*\n\s*"redirect":\s*reverse(?:_lazy)?\(\s*"([^"]+)"',
            s,
        )
        if pairs:
            out.append((m.group(1), [(l, rurl(n)) for l, n in pairs]))
    return out

def settings_sections():
    out = []
    for f in glob.glob("**/*.py", recursive=True):
        if "referance" in f:
            continue
        try:
            s = open(f, encoding="utf-8").read()
        except Exception:
            continue
        if "settings_menu.register" not in s:
            continue
        for blk in re.split(r"@settings_menu.register", s)[1:]:
            t = re.search(r'title\s*=\s*_\("([^"]+)"', blk)
            if not t:
                continue
            pairs = re.findall(
                r'"label":\s*_\("([^"]+)"\),\s*\n\s*"url":\s*reverse(?:_lazy)?\(\s*"([^"]+)"',
                blk,
            )
            if pairs:
                out.append((t.group(1), [(l, rurl(n)) for l, n in pairs]))
    return out

# ── Part B: full resolver crawl + classifier ────────────────────────────
ACTION_KW = (
    "search delete create update add edit remove hx ajax filter export import "
    "duplicate archive unarchive bulk toggle send save validate approve reject "
    "count dropdown redirect pagination upload download api widget chart "
    "autocomplete select unselect activate deactivate enable disable confirm "
    "submit refresh reload status quick assign-modal mass note-add comment "
    "store fetch json data-export"
).split()

SKIP_PREFIX = ("admin/", "api/", "__debug__/")
SKIP_NAME_SUBSTR = ("initialize-database", "load-demo", "load_demo")
KNOWN_APPS = {
    "asset", "attendance", "employee", "ess", "helpdesk", "leave", "configuration",
    "offboarding", "onboarding", "payroll", "pms", "project", "recruitment",
    "settings", "meet", "whatsapp", "backup", "theme", "license", "biometric",
    "manage", "subscriptions",
}

def walk(patterns, prefix=""):
    rows = []
    for p in patterns:
        if hasattr(p, "url_patterns"):
            rows += walk(p.url_patterns, prefix + str(p.pattern))
        else:
            rows.append((prefix + str(p.pattern), p.name, p.callback))
    return rows

def is_page(path, name):
    n = (name or "").lower()
    pth = path.lower()
    if any(k in n for k in ACTION_KW):
        return False
    if any(k in pth for k in ("search", "delete", "ajax", "hx-", "export", "import", "/api/", "create", "update", "/add", "/edit")):
        return False
    if pth.endswith(("/delete/", "/create/", "/update/", "/add/", "/edit/")):
        return False
    # page-ish names
    PAGE_HINT = ("view", "dashboard", "list", "detail", "tab", "individual", "profile",
                 "home", "page", "report", "summary", "pipeline", "calendar", "chart-view")
    if any(h in n for h in PAGE_HINT):
        return True
    # bare top-level paths with no action verb
    if name and "-" in (name or "") and not any(c in pth for c in ("<",)):
        return None  # ambiguous -> separate bucket
    return None

def app_of(path):
    seg = [s for s in path.split("/") if s and "<" not in s]
    a = seg[0] if seg else "(top-level)"
    return a if a in KNOWN_APPS else "(top-level)"

def is_partial(name):
    n = (name or "").lower()
    # list/tab endpoints that render a fragment inside a page, not a standalone page
    return n.endswith(("-list", "-tab", "-tab-list")) or n.startswith(("list-", "dashboard-"))

def main():
    side = sidebar_sections()
    sett = settings_sections()
    rows = walk(get_resolver().url_patterns)

    pages, partials, ambiguous, actions, skipped = {}, {}, {}, 0, 0
    seen = set()
    for path, name, cb in rows:
        if not name:
            continue
        key = (path, name)
        if key in seen:
            continue
        seen.add(key)
        if path.startswith(SKIP_PREFIX) or any(x in (name or "") for x in SKIP_NAME_SUBSTR):
            skipped += 1
            continue
        verdict = is_page(path, name)
        app = app_of(path)
        if verdict is True and is_partial(name):
            partials.setdefault(app, []).append((name, "/" + path))
        elif verdict is True:
            pages.setdefault(app, []).append((name, "/" + path))
        elif verdict is None:
            ambiguous.setdefault(app, []).append((name, "/" + path))
        else:
            actions += 1

    L = []
    w = L.append
    w("# Skylinx HRMS — Page Inventory\n")
    w("_Auto-generated by scratch/gen_page_inventory.py. Re-run after route changes._\n")
    w(f"- Total URL patterns: **{len(rows)}**")
    npages = sum(len(v) for v in pages.values())
    npart = sum(len(v) for v in partials.values())
    namb = sum(len(v) for v in ambiguous.values())
    w(f"- Classified: **{npages}** standalone pages, **{npart}** tab/list partials, "
      f"**{namb}** likely-pages (review), **{actions}** actions/fragments, "
      f"**{skipped}** skipped (admin/db-init)\n")

    w("\n---\n## PART A — Navigable menu (what HR clicks)\n")
    w("### Modules\n")
    for title, items in side:
        w(f"\n**{title}**\n")
        for label, url in items:
            w(f"- `{url}` — {label}")
    w("\n### Settings\n")
    for title, items in sett:
        w(f"\n**{title}**\n")
        for label, url in items:
            w(f"- `{url}` — {label}")
    w("\n**Owner/Vendor:** `/manage/` Console · `/manage/analytics/` Analytics\n")

    w("\n---\n## PART B — All page-views found in code (incl. detail/tab/sub-views)\n")
    for app in sorted(pages):
        w(f"\n### {app}  ({len(pages[app])})\n")
        for name, url in sorted(pages[app]):
            w(f"- `{url}`  ·  `{name}`")

    w("\n---\n## PART C — Tab / list partials (render inside a parent page)\n")
    for app in sorted(partials):
        w(f"\n### {app}  ({len(partials[app])})\n")
        for name, url in sorted(partials[app]):
            w(f"- `{url}`  ·  `{name}`")

    w("\n---\n## PART D — Likely pages needing manual review (ambiguous)\n")
    for app in sorted(ambiguous):
        w(f"\n### {app}  ({len(ambiguous[app])})\n")
        for name, url in sorted(ambiguous[app]):
            w(f"- `{url}`  ·  `{name}`")

    os.makedirs("docs", exist_ok=True)
    open("docs/page_inventory.md", "w", encoding="utf-8").write("\n".join(L))
    print("WROTE docs/page_inventory.md")
    print("pages:", npages, "partials:", npart, "ambiguous:", namb,
          "actions:", actions, "skipped:", skipped, "total:", len(rows))

main()
