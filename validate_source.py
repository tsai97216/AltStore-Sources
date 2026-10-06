import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from update_source import GITHUB_APPS, TARGET_APPS

FILENAME = "apps.json"
EXPECTED_APPS = {app["name"] for app in GITHUB_APPS} | set(TARGET_APPS) | {"EeveeSpotify Reincarnated"}

REQUIRED_ROOT_FIELDS = {
    "name", "identifier", "sourceURL", "subtitle", "description",
    "website", "iconURL", "featuredApps", "apps", "news",
}
REQUIRED_APP_FIELDS = {
    "name", "bundleIdentifier", "developerName", "subtitle",
    "localizedDescription", "iconURL", "tintColor", "category",
    "screenshots", "versions",
}
REQUIRED_VERSION_FIELDS = {
    "version", "date", "localizedDescription", "downloadURL", "size",
}
HEX_COLOR_RE = re.compile(r"^(?:#)?[0-9A-Fa-f]{6}$")


def fail(message):
    print(f"❌ {message}")
    return False


def valid_nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def valid_https_url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.netloc)
    except Exception:
        return False


def valid_hex_color(value):
    return isinstance(value, str) and bool(HEX_COLOR_RE.fullmatch(value))


def valid_date(value):
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate_source_data(source):
    if not isinstance(source, dict):
        return fail("Root must be an object")

    missing_root = REQUIRED_ROOT_FIELDS - set(source)
    if missing_root:
        return fail(f"Missing root fields: {', '.join(sorted(missing_root))}")

    for field in ("name", "identifier", "subtitle", "description"):
        if not valid_nonempty_string(source[field]):
            return fail(f"Invalid root field: {field}")

    for field in ("sourceURL", "website", "iconURL"):
        if not valid_https_url(source[field]):
            return fail(f"Invalid root URL: {field}")

    for field in ("apps", "featuredApps", "news"):
        if not isinstance(source[field], list):
            return fail(f"{field} must be an array")

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
            return fail(
                f"{app.get('name', 'Unknown')}: missing fields: "
                f"{', '.join(sorted(missing_fields))}"
            )

        app_name = app["name"]
        for field in (
            "name", "bundleIdentifier", "developerName",
            "subtitle", "localizedDescription", "category",
        ):
            if not valid_nonempty_string(app[field]):
                return fail(f"{app_name}: invalid field: {field}")

        bundle_id = app["bundleIdentifier"]
        if bundle_id in bundle_ids:
            return fail(f"Duplicate bundleIdentifier: {bundle_id}")
        bundle_ids.add(bundle_id)

        if not valid_https_url(app["iconURL"]):
            return fail(f"{app_name}: invalid iconURL")
        if not valid_hex_color(app["tintColor"]):
            return fail(f"{app_name}: invalid tintColor")

        if not isinstance(app["screenshots"], list):
            return fail(f"{app_name}: screenshots must be an array")
        for screenshot in app["screenshots"]:
            if not valid_https_url(screenshot):
                return fail(f"{app_name}: invalid screenshot URL")

        versions = app["versions"]
        if not isinstance(versions, list) or not versions:
            return fail(f"{app_name}: versions must be a non-empty array")

        seen_versions = set()
        for index, version in enumerate(versions):
            if not isinstance(version, dict):
                return fail(f"{app_name}: version {index} must be an object")

            missing_version_fields = REQUIRED_VERSION_FIELDS - set(version)
            if missing_version_fields:
                return fail(
                    f"{app_name}: version {index} missing fields: "
                    f"{', '.join(sorted(missing_version_fields))}"
                )

            version_name = version["version"]
            if not valid_nonempty_string(version_name):
                return fail(f"{app_name}: version {index} has an invalid version")
            if version_name in seen_versions:
                return fail(f"{app_name}: duplicate version: {version_name}")
            seen_versions.add(version_name)

            if not valid_date(version["date"]):
                return fail(f"{app_name}: invalid version date: {version['date']}")
            if not isinstance(version["localizedDescription"], str):
                return fail(f"{app_name}: invalid version description")
            if not valid_https_url(version["downloadURL"]):
                return fail(f"{app_name}: invalid downloadURL")
            if not str(version["downloadURL"]).lower().split("?", 1)[0].endswith(".ipa"):
                return fail(f"{app_name}: downloadURL is not an IPA")
            if type(version["size"]) is not int or version["size"] <= 0:
                return fail(f"{app_name}: invalid IPA size")

    expected_featured = [app["bundleIdentifier"] for app in apps]
    if source["featuredApps"] != expected_featured:
        return fail("featuredApps does not match apps order")

    print(f"✅ Source validation passed: {len(apps)} apps")
    return True


def validate_source():
    path = Path(FILENAME)
    if not path.exists():
        return fail(f"{FILENAME} does not exist")

    try:
        source = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"Cannot parse {FILENAME}: {exc}")

    return validate_source_data(source)


if __name__ == "__main__":
    sys.exit(0 if validate_source() else 1)
