#!/usr/bin/env python3
"""
Importiert ein Rezept von einer Webseite in recipes.json.

Wird automatisch vom GitHub-Workflow (.github/workflows/import-recipe.yml)
gestartet, sobald ein neues Issue mit einem Rezept-Link im Titel angelegt wird.

Zum Ausprobieren auf dem eigenen Computer:
    pip install -r scripts/requirements.txt
    python scripts/import_recipe.py https://www.beispiel.de/mein-rezept

Mehrere Links auf einmal: einen in den Titel, weitere in die Beschreibung
(einen pro Zeile). Höchstens 20 Links pro Issue.

Optional im Issue-Text (jeweils eine Zeile):
    Tags: Pasta, schnell
    Notiz: Mit weniger Salz kochen
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse

import requests

ROOT = Path(__file__).resolve().parent.parent
RECIPES_FILE = ROOT / "recipes.json"
IMAGES_DIR = ROOT / "images"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}
TIMEOUT = 30
MAX_IMAGE_SIDE = 1200

MANUAL_HINT = (
    "**So trägst du das Rezept stattdessen von Hand ein:** Öffne die Rezept-Seite, "
    "markiere den Rezepttext und kopiere ihn. Öffne dann die App, tippe unten auf "
    "**➕ Neu** → **📋 Rezepttext einfügen & automatisch ausfüllen**, füge den Text ein "
    "und tippe auf **Felder ausfüllen**. Prüfe die Felder und speichere."
)


class ImportFehler(Exception):
    """Fehler mit einer verständlichen Meldung für das Issue."""

    def __init__(self, message: str, blocked: bool = False):
        super().__init__(message)
        self.blocked = blocked


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def find_url(*texts: str) -> str | None:
    for text in texts:
        m = re.search(r"https?://[^\s<>\"')\]]+", text or "")
        if m:
            return m.group(0).rstrip(".,;")
    return None


TRACKING = re.compile(r"^(utm_|fbclid$|gclid$|mc_|ref$|source$|igshid$|si$)", re.I)


def normalize_url(url: str) -> str:
    """Macht URLs vergleichbar, damit Duplikate erkannt werden (gleiche Logik wie in der App)."""
    try:
        p = urlparse(url.strip())
        host = (p.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        query = sorted((k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not TRACKING.match(k))
        path = p.path.rstrip("/")
        q = urlencode(query)
        return (host + path + ("?" + q if q else "")).lower()
    except Exception:
        return url.strip().lower()


def slugify(text: str) -> str:
    text = text.lower().replace("ß", "ss")
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:40].strip("-") or "rezept"


def safe(fn, default=None):
    """Ruft eine Scraper-Methode auf und gibt bei Fehlern den Standardwert zurück."""
    try:
        value = fn()
        return default if value in (None, "", [], {}) else value
    except Exception:
        return default


def parse_number(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    m = re.search(r"\d+(?:[.,]\d+)?", str(value))
    return float(m.group(0).replace(",", ".")) if m else None


def parse_servings(value) -> int:
    n = parse_number(value)
    return max(1, int(round(n))) if n else 2


def as_minutes(value) -> int:
    n = parse_number(value)
    return max(0, int(round(n))) if n else 0


def split_tags(*values) -> list[str]:
    tags, seen = [], set()
    for value in values:
        if not value:
            continue
        items = value if isinstance(value, (list, tuple)) else re.split(r"[,;|]", str(value))
        for t in items:
            t = re.sub(r"\s+", " ", str(t)).strip(" #")
            if 1 < len(t) <= 30 and t.lower() not in seen:
                seen.add(t.lower())
                tags.append(t[:1].upper() + t[1:])
    return tags


def load_recipes() -> list[dict]:
    if not RECIPES_FILE.exists():
        return []
    data = json.loads(RECIPES_FILE.read_text(encoding="utf-8") or "[]")
    return data if isinstance(data, list) else data.get("recipes", [])


def save_recipes(recipes: list[dict]) -> None:
    RECIPES_FILE.write_text(json.dumps(recipes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_issue_extras(body: str) -> tuple[list[str], str]:
    tags, notes = [], ""
    for line in (body or "").splitlines():
        m = re.match(r"\s*(tags?|schlagw[öo]rter)\s*:\s*(.*)$", line, re.I)
        if m:
            tags = split_tags(m.group(2))
        m = re.match(r"\s*(notiz|notizen|notes?)\s*:\s*(.*)$", line, re.I)
        if m:
            notes = m.group(2).strip()
    return tags, notes


# ---------------------------------------------------------------------------
# Webseite laden und auslesen
# ---------------------------------------------------------------------------

def fetch_html(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except requests.exceptions.Timeout:
        raise ImportFehler("Die Webseite hat nicht rechtzeitig geantwortet (Zeitüberschreitung).", blocked=True)
    except requests.exceptions.RequestException as e:
        raise ImportFehler(f"Die Webseite konnte nicht erreicht werden ({type(e).__name__}). Ist der Link richtig?")

    text_start = r.text[:5000].lower() if r.text else ""
    challenge = any(s in text_start for s in ("cf-chl", "just a moment", "attention required", "captcha", "access denied"))
    if r.status_code in (401, 403, 406, 429, 451, 503) or (challenge and r.status_code >= 400):
        raise ImportFehler(
            f"Die Webseite blockiert automatische Abrufe (Fehlercode {r.status_code}). "
            "Viele große Rezeptseiten schützen sich so vor Robotern.",
            blocked=True,
        )
    if r.status_code == 404:
        raise ImportFehler("Die Seite wurde nicht gefunden (Fehler 404). Bitte prüfe den Link.")
    if r.status_code >= 400:
        raise ImportFehler(f"Die Webseite hat mit einem Fehler geantwortet (Fehlercode {r.status_code}).", blocked=True)
    if challenge and len(r.text) < 20000:
        raise ImportFehler("Die Webseite zeigt statt des Rezepts eine Roboter-Prüfung an.", blocked=True)
    r.encoding = r.encoding if r.encoding and r.encoding.lower() != "iso-8859-1" else r.apparent_encoding
    return r.text


def make_scraper(html: str, url: str):
    try:
        from recipe_scrapers import scrape_html
    except ImportError:  # sehr alte Versionen
        from recipe_scrapers import scrape_me  # type: ignore
        return scrape_me(url, wild_mode=True)
    try:
        return scrape_html(html, org_url=url, supported_only=False)
    except TypeError:
        # ältere Versionen von recipe-scrapers kannten "supported_only" noch nicht
        return scrape_html(html, org_url=url, wild_mode=True)


def scrape(url: str) -> dict:
    html = fetch_html(url)
    try:
        s = make_scraper(html, url)
    except Exception as e:
        raise ImportFehler(
            "Auf dieser Seite wurde kein Rezept in einem lesbaren Format gefunden "
            f"({type(e).__name__}). Manche Seiten stellen ihre Rezepte nicht maschinenlesbar bereit."
        )

    title = safe(s.title)
    ingredients = [re.sub(r"\s+", " ", str(i)).strip() for i in (safe(s.ingredients, []) or [])]
    ingredients = [i for i in ingredients if i]
    if not title or not ingredients:
        raise ImportFehler(
            "Auf dieser Seite wurde kein vollständiges Rezept gefunden (Titel oder Zutaten fehlen). "
            "Ist das wirklich eine Rezeptseite?"
        )

    steps = safe(s.instructions_list, []) or []
    if not steps:
        raw = safe(s.instructions, "") or ""
        steps = [x for x in raw.split("\n")]
    steps = [re.sub(r"\s+", " ", str(x)).strip() for x in steps]
    steps = [x for x in steps if x]

    prep = as_minutes(safe(s.prep_time))
    cook = as_minutes(safe(s.cook_time))
    total = as_minutes(safe(s.total_time))
    if not cook and total:
        cook = max(0, total - prep)

    nutrients = safe(s.nutrients, {}) or {}

    def nut(*keys):
        for k in keys:
            if k in nutrients:
                return parse_number(nutrients[k])
        return None

    calories = nut("calories")
    if calories is not None and "kj" in str(nutrients.get("calories", "")).lower() and "kcal" not in str(nutrients.get("calories", "")).lower():
        calories = calories / 4.184
    nutrition = {
        "calories": round(calories) if calories is not None else None,
        "protein": nut("proteinContent", "protein"),
        "fat": nut("fatContent", "fat"),
        "carbs": nut("carbohydrateContent", "carbohydrates", "carbs"),
    }

    image_url = safe(s.image)
    if isinstance(image_url, (list, tuple)):
        image_url = image_url[0] if image_url else None
    if image_url:
        image_url = urljoin(url, str(image_url))

    tags = split_tags(safe(s.category), safe(s.cuisine), safe(s.keywords))[:8]

    return {
        "title": re.sub(r"\s+", " ", str(title)).strip(),
        "servings": parse_servings(safe(s.yields)),
        "prep_time": prep,
        "cook_time": cook,
        "ingredients": ingredients,
        "steps": steps,
        "nutrition": nutrition,
        "image_url": image_url,
        "tags": tags,
        "canonical": safe(s.canonical_url),
        "lang": str(safe(lambda: s.language(), "") or "")[:2].lower(),
    }


def download_image(image_url: str, recipe_id: str) -> str:
    """Lädt das Titelbild herunter, verkleinert es und gibt den Pfad zurück ("" bei Fehler)."""
    if not image_url:
        return ""
    try:
        r = requests.get(image_url, headers={**HEADERS, "Accept": "image/*"}, timeout=TIMEOUT)
        if r.status_code != 200 or len(r.content) < 500:
            return ""
        IMAGES_DIR.mkdir(exist_ok=True)
        try:
            from PIL import Image

            im = Image.open(io.BytesIO(r.content))
            im = im.convert("RGB")
            im.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
            path = IMAGES_DIR / f"{recipe_id}.jpg"
            im.save(path, "JPEG", quality=82, optimize=True, progressive=True)
        except Exception:
            ctype = r.headers.get("content-type", "").lower()
            ext = ".png" if "png" in ctype else ".webp" if "webp" in ctype else ".gif" if "gif" in ctype else ".jpg"
            path = IMAGES_DIR / f"{recipe_id}{ext}"
            path.write_bytes(r.content)
        return f"images/{path.name}"
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Hauptablauf
# ---------------------------------------------------------------------------

def app_url() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" not in repo:
        return ""
    owner, name = repo.split("/", 1)
    if name.lower() == f"{owner.lower()}.github.io":
        return f"https://{owner.lower()}.github.io/"
    return f"https://{owner.lower()}.github.io/{name}/"


MAX_LINKS = 20


def find_urls(*texts: str) -> list[str]:
    """Alle Links aus Titel und Text, ohne Doppelte (in der Reihenfolge des Auftretens)."""
    urls, seen = [], set()
    for text in texts:
        for m in re.finditer(r"https?://[^\s<>\"')\]]+", text or ""):
            url = m.group(0).rstrip(".,;")
            key = normalize_url(url)
            if key not in seen:
                seen.add(key)
                urls.append(url)
    return urls


def import_one(url: str, recipes: list[dict], extra_tags: list[str], notes: str) -> tuple[str, str, str, str]:
    """Importiert einen Link in die (noch nicht gespeicherte) Liste.
    Gibt (status, nachricht, rezepttitel, rezept_id) zurück. status: success | duplicate | error"""
    known = {normalize_url(r.get("source_url", "")): r for r in recipes if str(r.get("source_url", "")).startswith("http")}
    dup = known.get(normalize_url(url))
    if dup:
        return ("duplicate", f"ℹ️ **Schon vorhanden:** „{dup.get('title')}“ – nichts geändert.", dup.get("title", ""), "")

    try:
        data = scrape(url)
    except ImportFehler as e:
        msg = f"❌ **Import fehlgeschlagen.** {e}"
        if e.blocked:
            msg += " Das liegt nicht an dir – die Seite lässt den automatischen Import leider nicht zu."
        return ("error", msg, "", "")

    # Duplikat auch über die "offizielle" Adresse der Seite prüfen
    if data.get("canonical"):
        dup = known.get(normalize_url(str(data["canonical"])))
        if dup:
            return ("duplicate", f"ℹ️ **Schon vorhanden:** „{dup.get('title')}“ – nichts geändert.", dup.get("title", ""), "")

    base_id = slugify(data["title"])
    recipe_id = f"{base_id}-{hashlib.sha1(normalize_url(url).encode()).hexdigest()[:5]}"
    existing_ids = {r.get("id") for r in recipes}
    while recipe_id in existing_ids:
        recipe_id += "x"

    image = download_image(data["image_url"], recipe_id)
    recipe = {
        "id": recipe_id,
        "title": data["title"],
        "source_url": url,
        "image": image,
        "servings": data["servings"],
        "prep_time": data["prep_time"],
        "cook_time": data["cook_time"],
        "difficulty": "",
        "rating": 0,
        "tags": split_tags(extra_tags, data["tags"])[:8],
        "ingredients": data["ingredients"],
        "steps": data["steps"],
        "nutrition": data["nutrition"],
        "notes": notes,
        "last_cooked": "",
        "added_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "lang": data["lang"] if data.get("lang") in ("de", "en") else "",
    }
    recipes.append(recipe)

    n = recipe["nutrition"]
    details = (
        f"🥕 {len(recipe['ingredients'])} Zutaten · 📝 {len(recipe['steps'])} Schritte · "
        f"⏱ {recipe['prep_time'] + recipe['cook_time'] or '–'} Min. · "
        f"🔥 Nährwerte: {'ja' if any(v for v in n.values()) else 'nein'} · 🖼 Bild: {'ja' if image else 'nein'}"
    )
    msg = f"✅ **Importiert:** {recipe['title']}\n{details}"
    if not recipe["steps"]:
        msg += "\n⚠️ Keine Zubereitungsschritte gefunden – du kannst sie in der App ergänzen."
    return ("success", msg, recipe["title"], recipe_id)


def run(title: str, body: str) -> tuple[str, str, str]:
    """Gibt (status, nachricht, commit-titel) zurück. status: success (mind. ein Rezept neu) | duplicate | error"""
    urls = find_urls(title, body)
    if not urls:
        return ("error",
                "❌ **Kein Link gefunden.**\n\nBitte schreibe den vollständigen Link zur Rezeptseite "
                "(beginnend mit `https://`) in den **Titel** des Issues. Mehrere Links kannst du in die "
                "Beschreibung schreiben – einen pro Zeile.", "")
    skipped = urls[MAX_LINKS:]
    urls = urls[:MAX_LINKS]

    recipes = load_recipes()
    extra_tags, notes = read_issue_extras(body)
    results = [(url, *import_one(url, recipes, extra_tags, notes)) for url in urls]
    imported = [r for r in results if r[1] == "success"]
    if imported:
        save_recipes(recipes)

    link = app_url()
    if len(urls) == 1:
        url, status, msg, rtitle, rid = results[0]
        if status == "error":
            msg += "\n\n" + MANUAL_HINT
        elif status == "success" and link:
            msg += f"\n\nIn 1–2 Minuten ist es in deiner App: {link}#/r/{rid}"
        return (status, msg, rtitle)

    counts = {s: sum(1 for r in results if r[1] == s) for s in ("success", "duplicate", "error")}
    lines = [
        f"📚 **{len(urls)} Links verarbeitet:** ✅ {counts['success']} importiert · "
        f"ℹ️ {counts['duplicate']} schon vorhanden · ❌ {counts['error']} fehlgeschlagen",
        "",
    ]
    for i, (url, status, msg, rtitle, rid) in enumerate(results, 1):
        lines.append(f"**{i}.** {url}\n{msg}\n")
    if skipped:
        lines.append(f"⚠️ Es werden höchstens {MAX_LINKS} Links pro Issue verarbeitet. "
                     f"Diese {len(skipped)} Links wurden übersprungen – bitte in einem neuen Issue senden:\n"
                     + "\n".join(f"- {u}" for u in skipped))
    if counts["error"]:
        lines.append("\n" + MANUAL_HINT)
    if imported and link:
        lines.append(f"\nIn 1–2 Minuten sind die neuen Rezepte in deiner App: {link}")
    if imported:
        commit_title = imported[0][3] if len(imported) == 1 else f"{len(imported)} Rezepte"
        return ("success", "\n".join(lines), commit_title)
    return ("duplicate" if counts["duplicate"] and not counts["error"] else "error", "\n".join(lines), "")


def main() -> int:
    title = os.environ.get("ISSUE_TITLE", "")
    body = os.environ.get("ISSUE_BODY", "")
    if len(sys.argv) > 1:  # lokaler Test: python scripts/import_recipe.py <URL>
        title = " ".join(sys.argv[1:])

    try:
        status, message, recipe_title = run(title, body)
    except Exception as e:  # unerwarteter Fehler – trotzdem verständlich melden
        status, message, recipe_title = (
            "error",
            f"❌ **Unerwarteter Fehler beim Import** ({type(e).__name__}: {e}).\n\n{MANUAL_HINT}",
            "",
        )

    print(message)
    result_file = os.environ.get("RESULT_FILE")
    if result_file:
        Path(result_file).write_text(message + "\n", encoding="utf-8")
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        clean_title = re.sub(r"[\r\n]+", " ", recipe_title)[:100]
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"status={status}\n")
            f.write(f"title={clean_title}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
