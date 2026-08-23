import json
import re
import requests
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from packaging import version as pkg_version

# =========================
# 🌙 基本設定
# =========================
FILENAME = "apps.json"
README_FILENAME = "README.md"

YOUR_GITHUB_ID = "tsai97216"
DISPLAY_NAME = "Chi Sources"

SOURCE_URL = f"https://chi.qzz.io/AltStore-Sources/{FILENAME}"
SOURCE_ICON_URL = f"https://raw.githubusercontent.com/{YOUR_GITHUB_ID}/AltStore-Sources/main/source_icon.PNG"

# =========================
# 📡 SAFE FETCH（核心升級）
# =========================
def fetch_json(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }

        r = requests.get(url, headers=headers, timeout=15)

        print(f"📡 {url} -> {r.status_code}")

        if r.status_code != 200:
            print("⚠️ fetch failed:", url)
            return None

        return r.json()

    except Exception as e:
        print("⚠️ fetch error:", url, e)
        return None


# =========================
# 🧱 SAFE NORMALIZER
# =========================
def ensure_list(data, key=None):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get(key, []) if key else []
    return []


# =========================
# 📦 SOURCES
# =========================
LOCAL_APPS = [
    {
        "repo": "bggRGjQaUbCoE/PiliPlus",
        "name": "PiliPlus",
        "bundleID": "com.bgg.piliplus",
        "icon": "...",
        "subtitle": "第三方 Bilibili 客戶端",
        "desc": "...",
        "color": "7DCEA0",
    }
]

SOURCE_DATA_URL = "https://raw.githubusercontent.com/apptesters-org/AppTesters_Repo/main/apps.json"

TARGET_APPS = {"Facebook", "Threads", "Instagram", "EeveeSpotify"}

APP_STYLE = {
    "Facebook": {"color": "1877F2", "subtitle": "Facebook修改版"},
    "Threads": {"color": "2D2D2D", "subtitle": "Threads修改版"},
    "Instagram": {"color": "E4405F", "subtitle": "Instagram修改版"},
    "EeveeSpotify": {"color": "1DB954", "subtitle": "Spotify修改版"},
}

YT_REPO = "https://repo.ballermc.com/repo.json"

YT_STYLE = {
    "YTPlusM": {"color": "FF4D4D", "subtitle": "YouTube 修改版"},
    "YouTube Music Ultimate+": {"color": "FF4D4D", "subtitle": "YouTube Music 修改版"},
}


# =========================
# 📡 FETCH WRAPPERS
# =========================
def fetch_remote():
    data = fetch_json(SOURCE_DATA_URL)
    return ensure_list(data, "apps")


def fetch_yt_repo():
    data = fetch_json(YT_REPO)

    if isinstance(data, dict):
        return data.get("apps", [])

    if isinstance(data, list):
        return data

    return []


# =========================
# 🔥 VERSION
# =========================
def get_version(app):
    if not isinstance(app, dict):
        return "0.0.0"

    v = app.get("version")
    if v:
        return v

    versions = app.get("versions") or []
    if isinstance(versions, list) and versions:
        return versions[0].get("version", "0.0.0")

    return "0.0.0"


def keep_latest_only(apps):
    latest = {}

    for app in apps:
        if not isinstance(app, dict):
            continue

        bid = app.get("bundleIdentifier")
        if not bid:
            continue

        ver = get_version(app)

        if bid not in latest:
            latest[bid] = app
            continue

        try:
            if pkg_version.parse(ver) > pkg_version.parse(get_version(latest[bid])):
                latest[bid] = app
        except:
            latest[bid] = app

    return list(latest.values())


# =========================
# 🐙 GITHUB
# =========================
def build_from_github(app):
    try:
        url = f"https://api.github.com/repos/{app['repo']}/releases/latest"

        r = requests.get(url, timeout=15)
        data = r.json()

        assets = data.get("assets", []) if isinstance(data, dict) else []
        ipa = next((a for a in assets if a.get("name", "").endswith(".ipa")), None)

        return {
            "name": app["name"],
            "bundleIdentifier": app["bundleID"],
            "developerName": app["repo"].split("/")[0],
            "subtitle": app["subtitle"],
            "localizedDescription": app["desc"],
            "iconURL": app["icon"],
            "tintColor": app["color"],
            "category": "entertainment",
            "screenshots": [],
            "versions": [{
                "version": (data.get("tag_name") or "").replace("v", ""),
                "date": (data.get("published_at") or "")[:10],
                "localizedDescription": (data.get("body") or "")[:500],
                "downloadURL": ipa.get("browser_download_url", "") if ipa else "",
                "size": ipa.get("size", 0) if ipa else 0,
            }]
        }

    except Exception as e:
        print("⚠️ GitHub build failed:", e)
        return None


# =========================
# 📱 APPT TESTERS
# =========================
def build_from_apptesters(app):
    if not isinstance(app, dict):
        return None

    name = app.get("name")
    style = APP_STYLE.get(name, {"color": None, "subtitle": "Imported"})

    return {
        "name": name,
        "bundleIdentifier": app.get("bundleIdentifier"),
        "developerName": "AppTesters",
        "subtitle": style["subtitle"],
        "localizedDescription": app.get("localizedDescription", ""),
        "iconURL": app.get("iconURL") or app.get("icon"),
        "tintColor": style["color"],
        "category": "social",
        "screenshots": [],
        "versions": [{
            "version": app.get("version", ""),
            "date": app.get("versionDate", ""),
            "localizedDescription": app.get("localizedDescription", ""),
            "downloadURL": app.get("downloadURL"),
            "size": app.get("size", 0),
        }]
    }


# =========================
# 🎬 YT
# =========================
def match_yt(name):
    name = (name or "").lower()
    return any(k.lower() in name for k in YT_STYLE)


def build_from_yt(app):
    if not isinstance(app, dict):
        return None

    name = app.get("name", "")
    style = next(
        (v for k, v in YT_STYLE.items() if k.lower() in name.lower()),
        {"color": None, "subtitle": "YouTube Mod"}
    )

    versions = app.get("versions") or []
    v = versions[0] if versions else {}

    return {
        "name": name,
        "bundleIdentifier": app.get("bundleIdentifier"),
        "developerName": "Ballermc",
        "subtitle": style["subtitle"],
        "localizedDescription": app.get("localizedDescription", ""),
        "iconURL": app.get("iconURL"),
        "tintColor": style["color"],
        "category": "entertainment",
        "screenshots": [],
        "versions": [{
            "version": v.get("version", ""),
            "date": (v.get("date") or "")[:10],
            "localizedDescription": v.get("localizedDescription", ""),
            "downloadURL": v.get("downloadURL", ""),
            "size": v.get("size", 0),
        }]
    }


# =========================
# 📝 README STATUS
# =========================
STATUS_START = "<!-- AUTO-UPDATE-STATUS:START -->"
STATUS_END = "<!-- AUTO-UPDATE-STATUS:END -->"


def now_taiwan():
    return datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S")


def get_previous_content_update(readme):
    match = re.search(r"Last content update:\s*([^\n]+)", readme)
    return match.group(1).strip() if match else "尚未更新"


def update_readme(apps, checked_at, content_updated_at):
    path = Path(README_FILENAME)
    readme = path.read_text(encoding="utf-8") if path.exists() else "# Chi Sources\n"

    rows = [
        "| App | Latest version | Version date |",
        "| --- | --- | --- |",
    ]

    for app in apps:
        if not isinstance(app, dict):
            continue
        versions = app.get("versions") or []
        latest = versions[0] if versions else {}
        rows.append(
            f"| {app.get('name', 'Unknown')} | {latest.get('version', 'N/A')} | {latest.get('date', 'N/A')} |"
        )

    status = "\n".join([
        STATUS_START,
        "## Update Status",
        "",
        f"- **Last automatic check:** {checked_at} (Asia/Taipei)",
        f"- **Last content update:** {content_updated_at} (Asia/Taipei)",
        "",
        "### App Versions",
        "",
        *rows,
        "",
        STATUS_END,
    ])

    pattern = re.compile(
        re.escape(STATUS_START) + r".*?" + re.escape(STATUS_END),
        re.DOTALL,
    )

    if pattern.search(readme):
        readme = pattern.sub(status, readme)
    else:
        readme = readme.rstrip() + "\n\n" + status + "\n"

    path.write_text(readme, encoding="utf-8")


# =========================
# 🚀 MAIN
# =========================
def update_source():
    print(f"🚀 Updating {DISPLAY_NAME}...")

    apps = []

    # Read previous apps.json before rebuilding it.
    old_apps = None
    try:
        with open(FILENAME, "r", encoding="utf-8") as f:
            old_apps = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # GitHub
    for a in LOCAL_APPS:
        r = build_from_github(a)
        if r:
            apps.append(r)

    # AppTesters
    remote = fetch_remote()
    remote = [a for a in remote if isinstance(a, dict) and a.get("name") in TARGET_APPS]
    remote = keep_latest_only(remote)

    for a in remote:
        r = build_from_apptesters(a)
        if r:
            apps.append(r)

    # YT
    yt_raw = fetch_yt_repo()
    yt_apps = [a for a in yt_raw if isinstance(a, dict) and match_yt(a.get("name"))]

    for a in yt_apps:
        r = build_from_yt(a)
        if r:
            apps.append(r)

    # OUTPUT
    source = {
        "name": DISPLAY_NAME,
        "identifier": f"com.{DISPLAY_NAME.lower().replace(' ', '')}.source",
        "sourceURL": SOURCE_URL,
        "subtitle": "iOS IPA Source",
        "description": f"{DISPLAY_NAME} auto curated source",
        "website": f"https://github.com/{YOUR_GITHUB_ID}/AltStore-Sources",
        "iconURL": SOURCE_ICON_URL,
        "featuredApps": [a["bundleIdentifier"] for a in apps if isinstance(a, dict)],
        "apps": apps,
        "news": []
    }

    new_content = json.dumps(source, indent=2, ensure_ascii=False) + "\n"
    old_content = json.dumps(old_apps, indent=2, ensure_ascii=False) + "\n" if old_apps is not None else None
    content_changed = old_content != new_content

    with open(FILENAME, "w", encoding="utf-8") as f:
        f.write(new_content)

    checked_at = now_taiwan()
    readme = Path(README_FILENAME).read_text(encoding="utf-8") if Path(README_FILENAME).exists() else ""
    previous_content_update = get_previous_content_update(readme)
    content_updated_at = checked_at if content_changed else previous_content_update

    update_readme(apps, checked_at, content_updated_at)

    print("🎉 DONE:", len(apps), "apps")
    print("🔎 Automatic check:", checked_at)
    print("📝 Content changed:", content_changed)
    print("📦 Last content update:", content_updated_at)


if __name__ == "__main__":
    update_source()
