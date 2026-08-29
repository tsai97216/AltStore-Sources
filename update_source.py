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
        "desc": "第三方 Bilibili 客戶端，提供增強播放與其他功能。",
        "color": "7DCEA0",
        "category": "entertainment",
        "asset_keywords": ["piliplus"],
    },
    {
        "repo": "itzzace/ytkace",
        "name": "YTKACE",
        "bundleID": "com.google.ios.youtube",
        "icon": "https://raw.githubusercontent.com/tsai97216/AltStore-Sources/main/YT.png",
        "subtitle": "YouTube 修改版",
        "desc": "An open-source YouTube enhancement for iOS.",
        "color": "FF0000",
        "category": "entertainment",
        "asset_keywords": ["ytkace"],
    },
    {
        "repo": "Mark02-2012/YTMUltimatePLUS",
        "name": "YTMUltimate+",
        "bundleID": "com.google.ios.youtubemusic",
        "icon": "https://raw.githubusercontent.com/Mark02-2012/YTMUltimatePLUS/MYmain/Resources/IMG_5914.png",
        "subtitle": "YouTube Music 修改版",
        "desc": "YTMUltimate+ is a fork of YTMusicUltimate with additional tweaks for YouTube Music on iOS.",
        "color": "FF0000",
        "category": "entertainment",
        "asset_keywords": ["ytmultimate", "ytmusicultimate", "youtubemusic"],
    },
]

SOURCE_DATA_URL = "https://raw.githubusercontent.com/apptesters-org/AppTesters_Repo/main/apps.json"
TARGET_APPS = ["Facebook", "Threads", "Instagram", "EeveeSpotify"]
APP_STYLE = {
    "Facebook": {"color": "1877F2", "subtitle": "Facebook修改版", "description": "Facebook 修改版。"},
    "Threads": {"color": "2D2D2D", "subtitle": "Threads修改版", "description": "Threads 修改版。"},
    "Instagram": {"color": "E4405F", "subtitle": "Instagram修改版", "description": "Instagram 修改版。"},
    "EeveeSpotify": {"color": "1DB954", "subtitle": "Spotify修改版", "description": "Spotify 修改版。"},
}

STATUS_START = "<!-- AUTO-UPDATE-STATUS:START -->"
STATUS_END = "<!-- AUTO-UPDATE-STATUS:END -->"


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


def choose_ipa_asset(assets, app):
    candidates = [
        asset for asset in assets
        if isinstance(asset, dict) and str(asset.get("name", "")).lower().endswith(".ipa")
    ]
    if not candidates:
        return None

    keywords = [str(keyword).lower() for keyword in app.get("asset_keywords", [])]

    def score(asset):
        name = str(asset.get("name", "")).lower()
        keyword_score = max((len(keyword) for keyword in keywords if keyword in name), default=0)
        return (keyword_score, asset.get("created_at") or "", name)

    return max(candidates, key=score)


def build_from_github(app):
    try:
        url = f"https://api.github.com/repos/{app['repo']}/releases/latest"
        response = SESSION.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        ipa = choose_ipa_asset(data.get("assets", []), app)
        if not ipa:
            print(f"⚠️ No IPA asset found for {app['name']}")
            return None

        version_name = (data.get("tag_name") or "").lstrip("v")
        if not version_name:
            print(f"⚠️ No release version found for {app['name']}")
            return None

        download_url = ipa.get("browser_download_url")
        if not download_url:
            print(f"⚠️ IPA has no download URL for {app['name']}")
            return None

        print(f"📦 {app['name']}: {version_name} -> {ipa.get('name', 'unknown IPA')}")
        return {
            "name": app["name"],
            "bundleIdentifier": app["bundleID"],
            "developerName": app["repo"].split("/")[0],
            "subtitle": app["subtitle"],
            "localizedDescription": app["desc"],
            "iconURL": app["icon"],
            "tintColor": app["color"],
            "category": app.get("category", "entertainment"),
            "screenshots": [],
            "versions": [{
                "version": version_name,
                "date": (data.get("published_at") or "")[:10],
                "localizedDescription": (data.get("body") or "")[:500],
                "downloadURL": download_url,
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
    style = APP_STYLE.get(name, {"color": None, "subtitle": "Imported", "description": ""})
    if not app.get("bundleIdentifier") or not app.get("downloadURL"):
        print(f"⚠️ AppTesters entry incomplete: {name or 'Unknown'}")
        return None
    return {
        "name": name,
        "bundleIdentifier": app.get("bundleIdentifier"),
        "developerName": "AppTesters",
        "subtitle": style["subtitle"],
        "localizedDescription": app.get("localizedDescription", ""),
        "iconURL": app.get("iconURL") or app.get("icon"),
        "tintColor": style["color"],
        "category": "social" if name in {"Facebook", "Threads", "Instagram"} else "entertainment",
        "screenshots": [],
        "versions": [{
            "version": app.get("version", ""),
            "date": app.get("versionDate", ""),
            "localizedDescription": app.get("localizedDescription", ""),
            "downloadURL": app.get("downloadURL"),
            "size": app.get("size", 0),
        }],
    }


def find_previous_app(old_apps, bundle_id=None, name=None):
    if not isinstance(old_apps, dict):
        return None
    for app in old_apps.get("apps", []):
        if not isinstance(app, dict):
            continue
        if bundle_id and app.get("bundleIdentifier") == bundle_id:
            return app
        if name and app.get("name") == name:
            return app
    return None


def now_taiwan():
    return datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S")


def get_previous_content_update(readme):
    for pattern in [
        r"最近內容更新：\s*\*?\*?\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
        r"Last content update:\s*\*?\*?\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
    ]:
        match = re.search(pattern, readme)
        if match:
            return match.group(1)
    return "尚未更新"


def get_readme_description(app):
    name = app.get("name", "Unknown")
    for github_app in GITHUB_APPS:
        if github_app["name"] == name:
            return github_app["desc"]
    if name in APP_STYLE:
        return APP_STYLE[name]["description"]
    return app.get("subtitle", "")


def update_readme(apps, checked_at, content_updated_at, statuses):
    path = Path(README_FILENAME)
    readme = path.read_text(encoding="utf-8") if path.exists() else "# Chi Sources\n"

    app_rows = ["| App | 說明 |", "| --- | --- |"]
    for app in apps:
        if not isinstance(app, dict):
            continue
        app_rows.append(f"| **{app.get('name', 'Unknown')}** | {get_readme_description(app)} |")

    status_rows = ["| App | 狀態 | 最新版本 | 版本日期 |", "| --- | --- | --- | --- |"]
    for app in apps:
        if not isinstance(app, dict):
            continue
        versions = app.get("versions") or []
        latest = versions[0] if versions and isinstance(versions[0], dict) else {}
        status_rows.append(
            f"| {app.get('name', 'Unknown')} | {statuses.get(app.get('name'), '⚪ Unchanged')} | "
            f"{latest.get('version', 'N/A')} | {latest.get('date', 'N/A')} |"
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
        *status_rows,
        "",
        STATUS_END,
    ])

    pattern = re.compile(re.escape(STATUS_START) + r".*?" + re.escape(STATUS_END), re.DOTALL)
    readme = pattern.sub(status, readme) if pattern.search(readme) else readme.rstrip() + "\n\n" + status + "\n"

    app_section = "\n".join(["## App", "", *app_rows])
    app_pattern = re.compile(r"## App\n.*?(?=\n## 更新狀態|\n<!-- AUTO-UPDATE-STATUS:START -->)", re.DOTALL)
    if app_pattern.search(readme):
        readme = app_pattern.sub(app_section, readme)
    else:
        readme = readme.rstrip() + "\n\n" + app_section + "\n"

    path.write_text(readme, encoding="utf-8")


def order_apps(apps):
    preferred = [app["name"] for app in GITHUB_APPS] + TARGET_APPS
    rank = {name: index for index, name in enumerate(preferred)}
    return sorted(apps, key=lambda app: rank.get(app.get("name"), len(rank)))


def update_source():
    print(f"🚀 Updating {DISPLAY_NAME}...")
    apps = []
    statuses = {}
    old_apps = None
    try:
        old_apps = json.loads(Path(FILENAME).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    for app in GITHUB_APPS:
        result = build_from_github(app)
        previous = find_previous_app(old_apps, bundle_id=app["bundleID"])
        if result:
            apps.append(result)
            statuses[app["name"]] = "🟢 Updated" if not previous or get_version(result) != get_version(previous) else "⚪ Unchanged"
        elif previous:
            print(f"↩️ Keeping previous version for {app['name']}")
            apps.append(previous)
            statuses[app["name"]] = "🔴 Failed / Kept previous"

    remote = fetch_remote()
    if remote is None:
        print("⚠️ AppTesters source unavailable; keeping previous AppTesters apps")
        for name in TARGET_APPS:
            previous = find_previous_app(old_apps, name=name)
            if previous:
                apps.append(previous)
                statuses[name] = "🔴 Failed / Kept previous"
    else:
        remote = keep_latest_only([
            app for app in remote
            if isinstance(app, dict) and app.get("name") in TARGET_APPS
        ])
        remote_by_name = {app.get("name"): app for app in remote}
        for name in TARGET_APPS:
            app = remote_by_name.get(name)
            result = build_from_apptesters(app) if app else None
            previous = find_previous_app(old_apps, name=name)
            if result:
                apps.append(result)
                statuses[name] = "🟢 Updated" if not previous or get_version(result) != get_version(previous) else "⚪ Unchanged"
            elif previous:
                print(f"↩️ Keeping previous version for {name}")
                apps.append(previous)
                statuses[name] = "🔴 Failed / Kept previous"

    apps = order_apps(apps)
    source = {
        "name": DISPLAY_NAME,
        "identifier": f"com.{DISPLAY_NAME.lower().replace(' ', '')}.source",
        "sourceURL": SOURCE_URL,
        "subtitle": "iOS IPA Source",
        "description": f"{DISPLAY_NAME} auto curated source",
        "website": f"https://github.com/{YOUR_GITHUB_ID}/AltStore-Sources",
        "iconURL": SOURCE_ICON_URL,
        "featuredApps": [
            app["bundleIdentifier"]
            for app in apps
            if isinstance(app, dict) and app.get("bundleIdentifier")
        ],
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
    update_readme(apps, checked_at, content_updated_at, statuses)

    print("🎉 DONE:", len(apps), "apps")
    print("🔎 Automatic check:", checked_at)
    print("📝 Content changed:", content_changed)


if __name__ == "__main__":
    update_source()
