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
SOURCE_DESCRIPTION = "iOS IPA Source"


def create_session():
    retry = Retry(total=3, connect=3, read=3, status=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=frozenset({"GET", "HEAD"}), respect_retry_after_header=True)
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "Chi-Sources-Updater/1.0", "Accept": "application/json"})
    return session

SESSION = create_session()


def fetch_json(url):
    try:
        response = SESSION.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"⚠️ fetch failed: {url} -> {exc}")
        return None


def validate_download_url(url, expected_size=0):
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    try:
        response = SESSION.head(url, allow_redirects=True, timeout=15)
        if response.status_code in (405, 501):
            response.close()
            response = SESSION.get(url, headers={"Range": "bytes=0-0"}, allow_redirects=True, timeout=15, stream=True)
        ok = response.status_code in (200, 206)
        content_length = response.headers.get("Content-Length")
        if ok and content_length:
            ok = int(content_length) > 0 and (not expected_size or int(content_length) == int(expected_size))
        response.close()
        return ok
    except (requests.RequestException, ValueError):
        return False


def ensure_list(data, key=None):
    if isinstance(data, list): return data
    if isinstance(data, dict):
        value = data.get(key, []) if key else []
        return value if isinstance(value, list) else []
    return []

GITHUB_APPS = [
    {"repo": "bggRGjQaUbCoE/PiliPlus", "name": "PiliPlus", "bundleID": "com.bgg.piliplus", "author": "bggRGjQaUbCoE", "repo_url": "https://github.com/bggRGjQaUbCoE/PiliPlus", "icon": "https://raw.githubusercontent.com/tsai97216/AltStore-Sources/main/piliplus.png", "subtitle": "bggRGjQaUbCoE", "desc": "第三方 Bilibili 客戶端，提供增強播放與其他功能。", "color": "B8D2C1", "category": "entertainment", "asset_keywords": ["piliplus"]},
    {"repo": "itzzace/ytkace", "name": "YTKACE", "bundleID": "com.google.ios.youtube", "author": "itzzace", "repo_url": "https://github.com/itzzace/ytkace", "icon": "https://raw.githubusercontent.com/tsai97216/AltStore-Sources/main/YT.png", "subtitle": "itzzace", "desc": "An open-source YouTube enhancement for iOS.", "color": "E8A8B7", "category": "entertainment", "asset_keywords": ["ytkace"]},
    {"repo": "Mark02-2012/YTMUltimatePLUS", "name": "YTMUltimate+", "bundleID": "com.google.ios.youtubemusic", "author": "Mark02-2012", "repo_url": "https://github.com/Mark02-2012/YTMUltimatePLUS", "icon": "https://raw.githubusercontent.com/Mark02-2012/YTMUltimatePLUS/MYmain/Resources/IMG_5914.png", "subtitle": "Mark02-2012", "desc": "YTMUltimate+ is a fork of YTMusicUltimate with additional tweaks for YouTube Music on iOS.", "color": "E8A8B7", "category": "entertainment", "asset_keywords": ["ytmultimate", "ytmusicultimate", "youtubemusic"]},
]
SOURCE_DATA_URL = "https://raw.githubusercontent.com/apptesters-org/AppTesters_Repo/main/apps.json"
APPT_ESTERS_REPO_URL = "https://github.com/apptesters-org/AppTesters_Repo"
TARGET_APPS = ["Facebook", "Threads", "Instagram", "EeveeSpotify"]
APP_STYLE = {
    "Facebook": {"color": "78A5E3", "subtitle": "AppTesters"},
    "Threads": {"color": "858585", "subtitle": "AppTesters"},
    "Instagram": {"color": "DC8FA1", "subtitle": "AppTesters"},
    "EeveeSpotify": {"color": "669878", "subtitle": "AppTesters"},
}
STATUS_START = "<!-- AUTO-UPDATE-STATUS:START -->"
STATUS_END = "<!-- AUTO-UPDATE-STATUS:END -->"


def fetch_remote():
    data = fetch_json(SOURCE_DATA_URL)
    return None if data is None else ensure_list(data, "apps")


def get_version(app):
    if not isinstance(app, dict): return "0.0.0"
    if app.get("version"): return str(app["version"])
    versions = app.get("versions") or []
    return str(versions[0].get("version", "0.0.0")) if versions and isinstance(versions[0], dict) else "0.0.0"


def normalize_version(name, text):
    text = str(text)
    if name == "YTMUltimate+":
        match = re.search(r"\band\s+(\d+\.\d+\.\d+)(?!\d)", text, re.IGNORECASE)
        return match.group(1) if match else text
    if name == "YTKACE":
        match = re.search(r"(?:youtube|yt)\s*[vV]?\s*(\d+\.\d+\.\d+)(?!\d)", text, re.IGNORECASE)
        return match.group(1) if match else text
    return text


def keep_latest_only(apps):
    latest = {}
    for app in apps:
        if not isinstance(app, dict) or not app.get("bundleIdentifier"): continue
        bid, ver = app["bundleIdentifier"], get_version(app)
        if bid not in latest:
            latest[bid] = app
        else:
            try:
                if pkg_version.parse(ver) > pkg_version.parse(get_version(latest[bid])): latest[bid] = app
            except Exception: latest[bid] = app
    return list(latest.values())


def choose_ipa_asset(assets, app):
    candidates = [a for a in assets if isinstance(a, dict) and str(a.get("name", "")).lower().endswith(".ipa")]
    if app.get("name") == "YTMUltimate+":
        preferred = [a for a in candidates if "no_ymp" not in str(a.get("name", "")).lower() and "no-ymp" not in str(a.get("name", "")).lower()]
        if preferred: candidates = preferred
    if not candidates: return None
    keywords = [str(k).lower() for k in app.get("asset_keywords", [])]
    def score(asset):
        name = str(asset.get("name", "")).lower()
        return (max((len(k) for k in keywords if k in name), default=0), asset.get("created_at") or "", name)
    return max(candidates, key=score)


def get_latest_special_release(app):
    try:
        response = SESSION.get(f"https://api.github.com/repos/{app['repo']}/releases?per_page=30", timeout=15)
        response.raise_for_status()
        releases = response.json()
        candidates = []
        for release in releases if isinstance(releases, list) else []:
            if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"): continue
            name = str(release.get("name") or "")
            lower = name.lower()
            if app["name"] == "YTMUltimate+":
                if "ytmultimate+" not in lower or "no-ymp" in lower or "no_ymp" in lower: continue
                if not re.search(r"\band\s+\d+\.\d+\.\d+\b", name, re.IGNORECASE): continue
            elif app["name"] == "YTKACE":
                if "ytkace" not in lower: continue
                if not re.search(r"(?:youtube|yt)\s*[vV]?\s*\d+\.\d+\.\d+\b", name, re.IGNORECASE): continue
            candidates.append(release)
        if not candidates: return None
        candidates.sort(key=lambda r: r.get("published_at") or r.get("created_at") or "", reverse=True)
        return candidates[0]
    except (requests.RequestException, ValueError):
        return None


def build_from_github(app):
    try:
        data = get_latest_special_release(app) if app.get("name") in {"YTMUltimate+", "YTKACE"} else None
        if data is None and app.get("name") not in {"YTMUltimate+", "YTKACE"}:
            response = SESSION.get(f"https://api.github.com/repos/{app['repo']}/releases/latest", timeout=15)
            response.raise_for_status(); data = response.json()
        if not data: return None
        ipa = choose_ipa_asset(data.get("assets", []), app)
        if not ipa: return None
        raw_version = data.get("name") or data.get("tag_name") or ""
        version_name = normalize_version(app["name"], raw_version.lstrip("v"))
        download_url, size = ipa.get("browser_download_url"), ipa.get("size", 0)
        if not version_name or not download_url or not validate_download_url(download_url, size): return None
        return {"name": app["name"], "bundleIdentifier": app["bundleID"], "developerName": app["author"], "subtitle": app["subtitle"], "localizedDescription": app["desc"], "iconURL": app["icon"], "tintColor": app["color"], "category": app.get("category", "entertainment"), "screenshots": [], "versions": [{"version": version_name, "date": (data.get("published_at") or "")[:10], "localizedDescription": (data.get("body") or "")[:500], "downloadURL": download_url, "size": size}]}
    except (requests.RequestException, ValueError):
        return None


def build_from_apptesters(app):
    if not isinstance(app, dict): return None
    name = app.get("name"); style = APP_STYLE.get(name, {"color": None, "subtitle": "AppTesters"})
    url, size = app.get("downloadURL"), app.get("size", 0)
    if not app.get("bundleIdentifier") or not url or not validate_download_url(url, size): return None
    return {"name": name, "bundleIdentifier": app["bundleIdentifier"], "developerName": "AppTesters", "subtitle": style["subtitle"], "localizedDescription": app.get("localizedDescription", ""), "iconURL": app.get("iconURL") or app.get("icon"), "tintColor": style["color"], "category": "social" if name in {"Facebook", "Threads", "Instagram"} else "entertainment", "screenshots": [], "versions": [{"version": app.get("version", ""), "date": app.get("versionDate", ""), "localizedDescription": app.get("localizedDescription", ""), "downloadURL": url, "size": size}]}


def find_previous_app(old_apps, bundle_id=None, name=None):
    if not isinstance(old_apps, dict): return None
    for app in old_apps.get("apps", []):
        if isinstance(app, dict) and ((bundle_id and app.get("bundleIdentifier") == bundle_id) or (name and app.get("name") == name)): return app
    return None


def now_taiwan(): return datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S")


def get_previous_content_update(readme):
    match = re.search(r"最近內容更新：\s*\*?\*?\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", readme)
    return match.group(1) if match else "尚未更新"


def get_app_meta(name):
    for app in GITHUB_APPS:
        if app["name"] == name: return app["author"], app["repo_url"]
    return ("AppTesters", APPT_ESTERS_REPO_URL) if name in TARGET_APPS else ("Unknown", "")


def update_readme(apps, checked_at, content_updated_at, statuses):
    path = Path(README_FILENAME); readme = path.read_text(encoding="utf-8") if path.exists() else "# Chi Sources\n"
    rows = ["| App | 原作者 |", "| --- | --- |"]
    for app in apps:
        author, url = get_app_meta(app.get("name", "Unknown")); rows.append(f"| **{app.get('name', 'Unknown')}** | [{author}]({url}) |" if url else f"| **{app.get('name', 'Unknown')}** | {author} |")
    status_rows = ["| App | 狀態 | 最新版本 | 版本日期 |", "| --- | --- | --- | --- |"]
    for app in apps:
        latest = (app.get("versions") or [{}])[0]; status_rows.append(f"| {app.get('name', 'Unknown')} | {statuses.get(app.get('name'), '⚪ Unchanged')} | {latest.get('version', 'N/A')} | {latest.get('date', 'N/A')} |")
    status = "\n".join([STATUS_START, "## 更新狀態", "", f"- **最近自動檢查：** {checked_at}（台灣時間）", f"- **最近內容更新：** {content_updated_at}（台灣時間）", "", "### App 版本", "", *status_rows, "", STATUS_END])
    pattern = re.compile(re.escape(STATUS_START) + r".*?" + re.escape(STATUS_END), re.DOTALL)
    readme = pattern.sub(status, readme) if pattern.search(readme) else readme.rstrip() + "\n\n" + status + "\n"
    app_section = "\n".join(["## App", "", *rows]); app_pattern = re.compile(r"## App\n.*?(?=\n## 更新狀態|\n<!-- AUTO-UPDATE-STATUS:START -->)", re.DOTALL)
    readme = app_pattern.sub(app_section, readme) if app_pattern.search(readme) else readme.rstrip() + "\n\n" + app_section + "\n"
    path.write_text(readme, encoding="utf-8")


def order_apps(apps):
    rank = {name: i for i, name in enumerate([a["name"] for a in GITHUB_APPS] + TARGET_APPS)}
    return sorted(apps, key=lambda app: rank.get(app.get("name"), len(rank)))


def update_source():
    print(f"🚀 Updating {DISPLAY_NAME}..."); apps, statuses, old_apps = [], {}, None
    try: old_apps = json.loads(Path(FILENAME).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): pass
    for app in GITHUB_APPS:
        result = build_from_github(app); previous = find_previous_app(old_apps, bundle_id=app["bundleID"])
        if result:
            apps.append(result); statuses[app["name"]] = "🟢 Updated" if not previous or get_version(result) != get_version(previous) else "⚪ Unchanged"
        elif previous:
            apps.append(previous); statuses[app["name"]] = "🔴 Failed / Kept previous"
        else: statuses[app["name"]] = "🔴 Failed / No previous version"
    remote = fetch_remote()
    for name in TARGET_APPS:
        previous = find_previous_app(old_apps, name=name); remote_app = next((a for a in keep_latest_only([x for x in (remote or []) if isinstance(x, dict) and x.get("name") == name])), None) if remote is not None else None
        result = build_from_apptesters(remote_app) if remote_app else None
        if result:
            apps.append(result); statuses[name] = "🟢 Updated" if not previous or get_version(result) != get_version(previous) else "⚪ Unchanged"
        elif previous:
            apps.append(previous); statuses[name] = "🔴 Failed / Kept previous"
        else: statuses[name] = "🔴 Failed / No previous version"
    apps = order_apps(apps)
    source = {"name": DISPLAY_NAME, "identifier": "com.chisources.source", "sourceURL": SOURCE_URL, "subtitle": "iOS IPA Source", "description": SOURCE_DESCRIPTION, "website": f"https://github.com/{YOUR_GITHUB_ID}/AltStore-Sources", "iconURL": SOURCE_ICON_URL, "featuredApps": [a["bundleIdentifier"] for a in apps if a.get("bundleIdentifier")], "apps": apps, "news": []}
    new_content = json.dumps(source, indent=2, ensure_ascii=False) + "\n"; old_content = json.dumps(old_apps, indent=2, ensure_ascii=False) + "\n" if old_apps is not None else None
    content_changed = old_content != new_content; Path(FILENAME).write_text(new_content, encoding="utf-8")
    checked_at = now_taiwan(); readme = Path(README_FILENAME).read_text(encoding="utf-8") if Path(README_FILENAME).exists() else ""; previous_update = get_previous_content_update(readme)
    update_readme(apps, checked_at, checked_at if content_changed else previous_update, statuses)
    print("🎉 DONE:", len(apps), "apps")

if __name__ == "__main__": update_source()
