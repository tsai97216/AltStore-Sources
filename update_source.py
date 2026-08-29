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
        value = data.get(key, []) if key else []
        return value if isinstance(value, list) else []
    return []


# =========================
# 📦 SOURCES
# =========================
LOCAL_APPS = [
    {
        "repo": "bggRGjQaUbCoE/PiliPlus",
        "name": "PiliPlus",
        "bundleID": "com.bgg.piliplus",
        "icon": "https://raw.githubusercontent.com/tsai97216/AltStore-Sources/main/piliplus.png",
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

YT_NAME_ALIASES = {
    "ytplusm",
    "yt plus m",
    "youtube music ultimate+",
    "youtube music ultimate",
}


# =========================
# 📡 FETCH WRAPPERS
# =========================
def fetch_remote():
    data = fetch_json(SOURCE_DATA_URL)
    return ensure_list(data, "apps")


def _collect_dicts(data):
    """
    遞迴尋找來源 JSON 中的 App 物件。
    兼容 apps / applications / repositories 等不同包裝結構。
    """
    results = []

    if isinstance(data, list):
        for item in data:
            results.extend(_collect_dicts(item))
        return results

    if not isinstance(data, dict):
        return results

    # 自己本身看起來像 App
    if any(key in data for key in (
        "bundleIdentifier",
        "bundleID",
        "downloadURL",
        "versions",
        "version"
    )):
        results.append(data)

    for value in data.values():
        if isinstance(value, (dict, list)):
            results.extend(_collect_dicts(value))

    return results


def fetch_yt_repo():
    data = fetch_json(YT_REPO)

    if data is None:
        print("❌ YT source unavailable")
        return None

    apps = _collect_dicts(data)

    # 去除同一物件因巢狀結構造成的重複
    unique = []
    seen = set()

    for app in apps:
        marker = (
            app.get("bundleIdentifier")
            or app.get("bundleID")
            or app.get("name")
            or id(app)
        )

        if marker in seen:
            continue

        seen.add(marker)
        unique.append(app)

    print(f"📦 YT source candidates: {len(unique)}")
    return unique


# =========================
# 🔥 VERSION
# =========================
def get_version(app):
    if not isinstance(app, dict):
        return "0.0.0"

    v = app.get("version")
    if v:
        return str(v)

    versions = app.get("versions") or []
    if isinstance(versions, list) and versions:
        first = versions[0]
        if isinstance(first, dict):
            return str(first.get("version", "0.0.0"))

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
        except Exception:
            latest[bid] = app

    return list(latest.values())


# =========================
# 🐙 GITHUB
# =========================
def build_from_github(app):
    try:
        url = f"https://api.github.com/repos/{app['repo']}/releases/latest"

        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()

        assets = data.get("assets", []) if isinstance(data, dict) else []
        ipa = next((a for a in assets if a.get("name", "").lower().endswith(".ipa")), None)

        if not ipa:
            print(f"⚠️ No IPA asset found for {app['name']}")
            return None

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
                "version": (data.get("tag_name") or "").lstrip("v"),
                "date": (data.get("published_at") or "")[:10],
                "localizedDescription": (data.get("body") or "")[:500],
                "downloadURL": ipa.get("browser_download_url", ""),
                "size": ipa.get("size", 0),
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
def _yt_identity(app):
    if not isinstance(app, dict):
        return ""

    parts = [
        app.get("name", ""),
        app.get("bundleIdentifier", ""),
        app.get("bundleID", ""),
        app.get("developerName", ""),
        app.get("developer", ""),
    ]

    return " ".join(str(x) for x in parts if x).lower()


def match_yt(app):
    identity = _yt_identity(app)

    matched = any(alias in identity for alias in YT_NAME_ALIASES)

    if matched:
        print(
            "✅ YT matched:",
            app.get("name", "Unknown"),
            app.get("bundleIdentifier") or app.get("bundleID", "")
        )

    return matched


def _get_yt_version_entry(app):
    versions = app.get("versions")

    if isinstance(versions, list) and versions:
        return versions[0] if isinstance(versions[0], dict) else {}

    # 有些來源直接把版本資訊放在 App 根節點
    if any(key in app for key in ("downloadURL", "version", "date", "size")):
        return app

    return {}


def build_from_yt(app):
    if not isinstance(app, dict):
        return None

    name = app.get("name", "")
    identity = _yt_identity(app)

    if "ytplusm" in identity or "yt plus m" in identity:
        style = YT_STYLE["YTPlusM"]
    else:
        style = YT_STYLE["YouTube Music Ultimate+"]

    v = _get_yt_version_entry(app)

    download_url = (
        v.get("downloadURL")
        or v.get("downloadUrl")
        or v.get("download")
        or ""
    )

    if not download_url:
        print(f"⚠️ YT matched but no download URL: {name}")
        return None

    return {
        "name": name,
        "bundleIdentifier": app.get("bundleIdentifier") or app.get("bundleID"),
        "developerName": app.get("developerName") or app.get("developer") or "Ballermc",
        "subtitle": style["subtitle"],
        "localizedDescription": app.get("localizedDescription", ""),
        "iconURL": app.get("iconURL") or app.get("icon"),
        "tintColor": style["color"],
        "category": "entertainment",
        "screenshots": [],
        "versions": [{
            "version": str(v.get("version", "")),
            "date": (v.get("date") or v.get("versionDate") or "")[:10],
            "localizedDescription": v.get("localizedDescription", ""),
            "downloadURL": download_url,
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
    patterns = [
        r"最近內容更新：\s*\*?\*?\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
        r"Last content update:\s*\*?\*?\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, readme)
        if match:
            return match.group(1)
    return "尚未更新"


def update_readme(apps, checked_at, content_updated_at):
    path = Path(README_FILENAME)
    readme = path.read_text(encoding="utf-8") if path.exists() else "# Chi Sources\n"

    rows = [
        "| App | 最新版本 | 版本日期 |",
        "| --- | --- | --- |",
    ]

    for app in apps:
        if not isinstance(app, dict):
            continue

        versions = app.get("versions") or []
        latest = versions[0] if versions else {}

        rows.append(
            f"| {app.get('name', 'Unknown')} | "
            f"{latest.get('version', 'N/A')} | "
            f"{latest.get('date', 'N/A')} |"
        )

    status = "\n".join([
        STATUS_START,
        "## 更新狀態",
        "",
        f"- **最近自動檢查：** {checked_at}（台灣時間）",
        f"- **最近內容更新：** {content_updated_at}（台灣時間）",
        "",
        "### App 版本",
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
    remote = [
        a for a in remote
        if isinstance(a, dict) and a.get("name") in TARGET_APPS
    ]
    remote = keep_latest_only(remote)

    for a in remote:
        r = build_from_apptesters(a)
        if r:
            apps.append(r)

    # YT
    yt_raw = fetch_yt_repo()

    if yt_raw is None:
        print("⚠️ YT update skipped: source unavailable")
    else:
        yt_apps = [a for a in yt_raw if match_yt(a)]

        print(f"🎬 YT matched apps: {len(yt_apps)}")

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
    old_content = (
        json.dumps(old_apps, indent=2, ensure_ascii=False) + "\n"
        if old_apps is not None else None
    )

    content_changed = old_content != new_content

    with open(FILENAME, "w", encoding="utf-8") as f:
        f.write(new_content)

    checked_at = now_taiwan()
    readme = (
        Path(README_FILENAME).read_text(encoding="utf-8")
        if Path(README_FILENAME).exists()
        else ""
    )

    previous_content_update = get_previous_content_update(readme)
    content_updated_at = checked_at if content_changed else previous_content_update

    update_readme(apps, checked_at, content_updated_at)

    print("🎉 DONE:", len(apps), "apps")
    print("🔎 Automatic check:", checked_at)
    print("📝 Content changed:", content_changed)
    print("📦 Last content update:", content_updated_at)


if __name__ == "__main__":
    update_source()
