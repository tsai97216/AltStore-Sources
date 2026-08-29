import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from packaging import version as pkg_version

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

FILENAME = "apps.json"
README_FILENAME = "README.md"
YOUR_GITHUB_ID = "tsai97216"
DISPLAY_NAME = "Chi Sources"
SOURCE_URL = f"https://chi.qzz.io/AltStore-Sources/{FILENAME}"
SOURCE_ICON_URL = f"https://raw.githubusercontent.com/{YOUR_GITHUB_ID}/AltStore-Sources/main/source_icon.PNG"


def create_session():
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "Chi-Sources-Updater/1.0", "Accept": "application/json"})
    return session


SESSION = create_session()


def fetch_json(url):
    try:
        response = SESSION.get(url, timeout=15)
        print(f"📡 {url} -> {response.status_code}")
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as e:
        print(f"⚠️ fetch failed: {url} -> {e}")
        return None


def ensure_list(data, key=None):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        value = data.get(key, []) if key else []
        return value if isinstance(value, list) else []
    return []


GITHUB_APPS = [
    {
        "repo": "bggRGjQaUbCoE/PiliPlus",
        "name": "PiliPlus",
        "bundleID": "com.bgg.piliplus",
        "icon": "https://raw.githubusercontent.com/tsai97216/AltStore-Sources/main/piliplus.png",
        "subtitle": "第三方 Bilibili 客戶端",
        "desc": "...",
        "color": "7DCEA0",
    },
    {
        "repo": "itzzace/ytkace",
        "name": "YTKACE",
        "bundleID": "com.google.ios.youtube",
        "icon": "https://raw.githubusercontent.com/tsai97216/AltStore-Sources/main/YT.png",
        "subtitle": "YouTube 修改版",
        "desc": "An open-source YouTube enhancement for iOS.",
        "color": "FF0000",
    },
    {
        "repo": "Mark02-2012/YTMUltimatePLUS",
        "name": "YTMUltimate+",
        "bundleID": "com.google.ios.youtubemusic",
        "icon": "https://raw.githubusercontent.com/Mark02-2012/YTMUltimatePLUS/MYmain/Resources/IMG_5914.png",
        "subtitle": "YouTube Music 修改版",
        "desc": "YTMUltimate+ is a fork of YTMusicUltimate with additional tweaks for YouTube Music on iOS.",
        "color": "FF0000",
    },
]

SOURCE_DATA_URL = "https://raw.githubusercontent.com/apptesters-org/AppTesters_Repo/main/apps.json"
TARGET_APPS = {"Facebook", "Threads", "Instagram", "EeveeSpotify"}
APP_STYLE = {
    "Facebook": {"color": "1877F2", "subtitle": "Facebook修改版"},
    "Threads": {"color": "2D2D2D", "subtitle": "Threads修改版"},
    "Instagram": {"color": "E4405F", "subtitle": "Instagram修改版"},
    "EeveeSpotify": {"color": "1DB954", "subtitle": "Spotify修改版"},
}


def fetch_remote():
    data = fetch_json(SOURCE_DATA_URL)
    if data is None:
        return None
    return ensure_list(data, "apps")


def get_version(app):
    if not isinstance(app, dict):
        return "0.0.0"
    if app.get("version"):
        return str(app["version"])
    versions = app.get("versions") or []
    if isinstance(versions, list) and versions and isinstance(versions[0], dict):
        return str(versions[0].get("version", "0.0.0"))
    return "0.0.0"


def keep_latest_only(apps):
    latest = {}
    for app in apps:
        if not isinstance(app, dict) or not app.get("bundleIdentifier"):
            continue
        bid, ver = app["bundleIdentifier"], get_version(app)
        if bid not in latest:
            latest[bid] = app
            continue
        try:
            if pkg_version.parse(ver) > pkg_version.parse(get_version(latest[bid])):
                latest[bid] = app
        except Exception:
            latest[bid] = app
    return list(latest.values())


def build_from_github(app):
    try:
        url = f"https://api.github.com/repos/{app['repo']}/releases/latest"
        response = SESSION.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        ipa = next((a for a in data.get("assets", []) if a.get("name", "").lower().endswith(".ipa")), None)
        if not ipa:
            print(f"⚠️ No IPA asset found for {app['name']}")
            return None
        version_name = (data.get("tag_name") or "").lstrip("v")
        if not version_name:
            print(f"⚠️ No release version found for {app['name']}")
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
                "version": version_name,
                "date": (data.get("published_at") or "")[:10],
                "localizedDescription": (data.get("body") or "")[:500],
                "downloadURL": ipa.get("browser_download_url", ""),
                "size": ipa.get("size", 0),
            }],
        }
    except (requests.RequestException, ValueError) as e:
        print(f"⚠️ GitHub build failed for {app['name']}: {e}")
        return None


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
        }],
    }


def find_previous_app(old_apps, bundle_id):
    if not isinstance(old_apps, dict) or not bundle_id:
        return None
    for app in old_apps.get("apps", []):
        if isinstance(app, dict) and app.get("bundleIdentifier") == bundle_id:
            return app
    return None


STATUS_START = "<!-- AUTO-UPDATE-STATUS:START -->"
STATUS_END = "<!-- AUTO-UPDATE-STATUS:END -->"


def now_taiwan():
    return datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S")


def get_previous_content_update(readme):
    for pattern in [r"最近內容更新：\s*\*?\*?\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", r"Last content update:\s*\*?\*?\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"]:
        match = re.search(pattern, readme)
        if match:
            return match.group(1)
    return "尚未更新"


def update_readme(apps, checked_at, content_updated_at):
    path = Path(README_FILENAME)
    readme = path.read_text(encoding="utf-8") if path.exists() else "# Chi Sources\n"
    rows = ["| App | 最新版本 | 版本日期 |", "| --- | --- | --- |"]
    for app in apps:
        if not isinstance(app, dict):
            continue
        versions = app.get("versions") or []
        latest = versions[0] if versions else {}
        rows.append(f"| {app.get('name', 'Unknown')} | {latest.get('version', 'N/A')} | {latest.get('date', 'N/A')} |")
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
    pattern = re.compile(re.escape(STATUS_START) + r".*?" + re.escape(STATUS_END), re.DOTALL)
    readme = pattern.sub(status, readme) if pattern.search(readme) else readme.rstrip() + "\n\n" + status + "\n"
    path.write_text(readme, encoding="utf-8")


def update_source():
    print(f"🚀 Updating {DISPLAY_NAME}...")
    apps = []
    old_apps = None
    try:
        old_apps = json.loads(Path(FILENAME).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    for app in GITHUB_APPS:
        result = build_from_github(app)
        if result:
            apps.append(result)
        else:
            previous = find_previous_app(old_apps, app["bundleID"])
            if previous:
                print(f"↩️ Keeping previous version for {app['name']}")
                apps.append(previous)

    remote = fetch_remote()
    if remote is None:
        print("⚠️ AppTesters source unavailable; keeping previous AppTesters apps")
        for name in TARGET_APPS:
            previous = next((a for a in (old_apps or {}).get("apps", []) if isinstance(a, dict) and a.get("name") == name), None)
            if previous:
                apps.append(previous)
    else:
        remote = keep_latest_only([a for a in remote if isinstance(a, dict) and a.get("name") in TARGET_APPS])
        for app in remote:
            result = build_from_apptesters(app)
            if result:
                apps.append(result)
            else:
                previous = find_previous_app(old_apps, app.get("bundleIdentifier"))
                if previous:
                    print(f"↩️ Keeping previous version for {app.get('name', 'Unknown')}")
                    apps.append(previous)

    source = {
        "name": DISPLAY_NAME,
        "identifier": f"com.{DISPLAY_NAME.lower().replace(' ', '')}.source",
        "sourceURL": SOURCE_URL,
        "subtitle": "iOS IPA Source",
        "description": f"{DISPLAY_NAME} auto curated source",
        "website": f"https://github.com/{YOUR_GITHUB_ID}/AltStore-Sources",
        "iconURL": SOURCE_ICON_URL,
        "featuredApps": [a["bundleIdentifier"] for a in apps if isinstance(a, dict) and a.get("bundleIdentifier")],
        "apps": apps,
        "news": [],
    }

    new_content = json.dumps(source, indent=2, ensure_ascii=False) + "\n"
    old_content = json.dumps(old_apps, indent=2, ensure_ascii=False) + "\n" if old_apps is not None else None
    content_changed = old_content != new_content
    Path(FILENAME).write_text(new_content, encoding="utf-8")

    checked_at = now_taiwan()
    readme = Path(README_FILENAME).read_text(encoding="utf-8") if Path(README_FILENAME).exists() else ""
    previous_content_update = get_previous_content_update(readme)
    content_updated_at = checked_at if content_changed else previous_content_update
    update_readme(apps, checked_at, content_updated_at)

    print("🎉 DONE:", len(apps), "apps")
    print("🔎 Automatic check:", checked_at)
    print("📝 Content changed:", content_changed)


if __name__ == "__main__":
    update_source()
