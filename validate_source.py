import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from update_source import GITHUB_APPS, TARGET_APPS

FILENAME = "apps.json"
EXPECTED_APPS = {app["name"] for app in GITHUB_APPS} | set(TARGET_APPS)
REQUIRED_APP_FIELDS = {
    "name",
    "bundleIdentifier",
    "developerName",
    "subtitle",
    "localizedDescription",
    "iconURL",
    "tintColor",
    "category",
    "screenshots",
    "versions",
}
REQUIRED_VERSION_FIELDS = {
    "version",
    "date",
    "localizedDescription",
    "downloadURL",
    "size",
}


def fail(message):
    print(f"❌ {message}")
    return False


def valid_https_url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.netloc)
    except Exception:
        return False


def validate_source():
    path = Path(FILENAME)
    if not path.exists():
        return fail(f"{FILENAME} does not exist")

    try:
        source = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"Cannot parse {FILENAME}: {exc}")

    if not isinstance(source, dict):
        return fail("Root must be an object")

    for field in ("name", "identifier", "sourceURL", "subtitle", "description", "website", "iconURL", "featuredApps", "apps", "news"):
        if field not in source:
            return fail(f"Missing root field: {field}")

    for field in ("sourceURL", "website", "iconURL"):
        if not valid_https_url(source[field]):
            return fail(f"Invalid root URL: {field}")

    if not isinstance(source["apps"], list):
        return fail("apps must be an array")
    if not isinstance(source["featuredApps"], list):
        return fail("featuredApps must be an array")
    if not isinstance(source["news"], list):
        return fail("news must be an array")

    apps = source["apps"]
    names = [app.get("name") for app in apps if isinstance(app, dict)]
    missing = EXPECTED_APPS - set(names)
    unexpected = set(names) - EXPECTED_APPS
    if missing:
        return fail(f"Missing expected apps: {', '.join(sorted(missing))}")
    if unexpected:
        return fail(f"Unexpected apps: {', '.join(sorted(unexpected))}")
    if len(apps) != len(EXPECTED_APPS):
        return fail(f"Expected {len(EXPECTED_APPS)} apps, found {len(apps)}")

    bundle_ids = set()
    for app in apps:
        if not isinstance(app, dict):
            return fail("Every app entry must be an object")
        missing_fields = REQUIRED_APP_FIELDS - set(app)
        if missing_fields:
            return fail(f"{app.get('name', 'Unknown')}: missing fields: {', '.join(sorted(missing_fields))}")
        if app["bundleIdentifier"] in bundle_ids:
            return fail(f"Duplicate bundleIdentifier: {app['bundleIdentifier']}")
        bundle_ids.add(app["bundleIdentifier"])
        if not valid_https_url(app["iconURL"]):
            return fail(f"{app['name']}: invalid iconURL")
        if not isinstance(app["screenshots"], list):
            return fail(f"{app['name']}: screenshots must be an array")
        if not isinstance(app["versions"], list) or not app["versions"]:
            return fail(f"{app['name']}: versions must be a non-empty array")

        latest = app["versions"][0]
        if not isinstance(latest, dict):
            return fail(f"{app['name']}: latest version must be an object")
        missing_version_fields = REQUIRED_VERSION_FIELDS - set(latest)
        if missing_version_fields:
            return fail(f"{app['name']}: missing version fields: {', '.join(sorted(missing_version_fields))}")
        if not latest["version"]:
            return fail(f"{app['name']}: empty version")
        if not valid_https_url(latest["downloadURL"]):
            return fail(f"{app['name']}: invalid downloadURL")
        if not str(latest["downloadURL"]).lower().split("?", 1)[0].endswith(".ipa"):
            return fail(f"{app['name']}: downloadURL is not an IPA")
        if not isinstance(latest["size"], int) or latest["size"] <= 0:
            return fail(f"{app['name']}: invalid IPA size")

    expected_featured = [app["bundleIdentifier"] for app in apps]
    if source["featuredApps"] != expected_featured:
        return fail("featuredApps does not match apps order")

    print(f"✅ Source validation passed: {len(apps)} apps")
    return True


if __name__ == "__main__":
    sys.exit(0 if validate_source() else 1)
