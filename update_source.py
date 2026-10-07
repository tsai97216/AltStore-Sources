import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from packaging import version as pkg_version
import requests
from providers import GitHubProvider, JsonSourceProvider
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

FILENAME = "apps.json"
README_FILENAME = "README.md"
YOUR_GITHUB_ID = "tsai97216"
DISPLAY_NAME = "Chi Sources"
SOURCE_URL = "https://altstore.chi.qzz.io"
SOURCE_ICON_URL = f"https://raw.githubusercontent.com/{YOUR_GITHUB_ID}/AltStore-Sources/main/source_icon.png"
SOURCE_DESCRIPTION = "iOS IPA Source"


def create_session():
    retry = Retry(total=3, connect=3, read=3, status=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=frozenset({"GET", "HEAD"}), respect_retry_after_header=True)
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "Chi-Sources-Updater/1.0", "Accept": "application/json"})
    return session

SESSION = create_session()
GITHUB_PROVIDER = GitHubProvider(SESSION)
JSON_PROVIDER = JsonSourceProvider(lambda url: fetch_json(url))


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
        if ok:
            if not content_length:
                ok = False
            else:
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


APP_CONFIG_FILENAME = "app_config.json"

def load_app_config():
    path = Path(APP_CONFIG_FILENAME)
    data = json.loads(path.read_text(encoding="utf-8"))
    apps = data.get("apps") if isinstance(data, dict) else None
    if not isinstance(apps, list) or not all(isinstance(app, dict) for app in apps):
        raise ValueError(f"{APP_CONFIG_FILENAME}: apps must be a list of objects")
    return apps

GITHUB_APPS = load_app_config()
SOURCE_DATA_URL = "https://raw.githubusercontent.com/apptesters-org/AppTesters_Repo/main/apps.json"
APPT_ESTERS_REPO_URL = "https://github.com/apptesters-org/AppTesters_Repo"
SIDeloadLABS_SOURCE_URL = "https://raw.githubusercontent.com/SideloadLabs/SideloasLabs-AltSource/main/apps.json"
SIDELOADLABS_REPO_URL = "https://github.com/SideloadLabs/SideloasLabs-AltSource"
TARGET_APPS = ["Facebook", "Threads", "Instagram"]
SIDELOADLABS_APP = "EeveeSpotifyReincarnated(PATCHED)"
SIDELOADLABS_DISPLAY_NAME = "EeveeSpotify Reincarnated"
APP_STYLE = {
    "Facebook": {"color": "78A5E3", "subtitle": "AppTesters"},
    "Threads": {"color": "858585", "subtitle": "AppTesters"},
    "Instagram": {"color": "DC8FA1", "subtitle": "AppTesters"},
    "EeveeSpotify Reincarnated": {"color": "669878", "subtitle": "SideloadLabs"},
}
STATUS_START = "<!-- AUTO-UPDATE-STATUS:START -->"
STATUS_END = "<!-- AUTO-UPDATE-STATUS:END -->"
STATUS_TIMES_START = "<!-- AUTO-UPDATE-STATUS-TIMES:START -->"
STATUS_TIMES_END = "<!-- AUTO-UPDATE-STATUS-TIMES:END -->"


def fetch_remote():
    data = JSON_PROVIDER.fetch(SOURCE_DATA_URL)
    return None if data is None else ensure_list(data, "apps")


def get_version(app):
    if not isinstance(app, dict): return "0.0.0"
    if app.get("version"): return str(app["version"])
    versions = app.get("versions") or []
    return str(versions[0].get("version", "0.0.0")) if versions and isinstance(versions[0], dict) else "0.0.0"


def normalize_version(name, text):
    text = str(text)
    if name == "MaxMusic":
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
    if app.get("name") == "MaxMusic":
        preferred = [a for a in candidates if "no_ymp" not in str(a.get("name", "")).lower() and "no-ymp" not in str(a.get("name", "")).lower()]
        if preferred: candidates = preferred
    if not candidates: return None
    keywords = [str(k).lower() for k in app.get("asset_keywords", [])]
    def score(asset):
        name = str(asset.get("name", "")).lower()
        return (max((len(k) for k in keywords if k in name), default=0), asset.get("created_at") or "", name)
    return max(candidates, key=score)


def choose_highest_ytkace_ipa(releases):
    candidates = []
    for release in releases:
        if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
            continue
        for asset in release.get("assets", []):
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name", ""))
            if not name.lower().endswith(".ipa"):
                continue
            match = re.search(r"(?:youtube|yt)[_\s-]*[vV]?[_\s-]*(\d+\.\d+\.\d+)", name, re.IGNORECASE)
            if not match:
                continue
            candidates.append((pkg_version.parse(match.group(1)), release, asset))
    if not candidates:
        print("⚠️ YTKACE: no IPA with a YouTube version found")
        return None
    candidates.sort(key=lambda x: (x[0], x[1].get("published_at") or x[1].get("created_at") or ""), reverse=True)
    for v, release, asset in candidates:
        print(f"🔎 YTKACE candidate: YouTube {v} -> {asset.get('name')} ({release.get('name') or release.get('tag_name')})")
    v, release, asset = candidates[0]
    print(f"✅ YTKACE selected: YouTube {v} -> {asset.get('name')}")
    return release, asset


def get_latest_special_release(app, releases=None):
    try:
        if releases is None:
            releases = GITHUB_PROVIDER.releases(app["repo"], per_page=30)
        candidates = []
        for release in releases if isinstance(releases, list) else []:
            if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"): continue
            name = str(release.get("name") or "")
            lower = name.lower()
            if app["name"] == "MaxMusic":
                if not any(marker in lower for marker in ("ytmultimate+", "ytmusicultimate+")) or "no-ymp" in lower or "no_ymp" in lower: continue
                if not re.search(r"\band\s+\d+\.\d+\.\d+\b", name, re.IGNORECASE): continue
            elif app["name"] == "YTKACE":
                if "ytkace" not in lower: continue
            candidates.append(release)
        if not candidates: return None
        candidates.sort(key=lambda r: r.get("published_at") or r.get("created_at") or "", reverse=True)
        return candidates[0]
    except (requests.RequestException, ValueError):
        return None


def format_subtitle(author, date):
    return f"{author}（{date}）" if date else author


def format_app_subtitle(author, version_date):
    return format_subtitle(author, version_date)


def build_from_github(app):
    try:
        special = app.get("name") in {"MaxMusic", "YTKACE"}
        releases = GITHUB_PROVIDER.releases(app["repo"], per_page=100) if special else None
        data = get_latest_special_release(app, releases) if special else GITHUB_PROVIDER.latest_release(app["repo"])
        if not data: return None
        if app.get("name") == "YTKACE":
            selected = choose_highest_ytkace_ipa(releases or [])
            if not selected: return None
            data, ipa = selected
            version_match = re.search(r"(?:youtube|yt)[_\s-]*[vV]?[_\s-]*(\d+\.\d+\.\d+)", str(ipa.get("name", "")), re.IGNORECASE)
            version_name = version_match.group(1) if version_match else ""
        else:
            ipa = choose_ipa_asset(data.get("assets", []), app)
            if not ipa: return None
            raw_version = data.get("name") or data.get("tag_name") or ""
            version_name = normalize_version(app["name"], raw_version.lstrip("v"))
        download_url, size = ipa.get("browser_download_url"), ipa.get("size", 0)
        if not version_name or not download_url or not validate_download_url(download_url, size): return None
        version_date = (data.get("published_at") or data.get("created_at") or "")[:10]
        return {"name": app["name"], "bundleIdentifier": app["bundleID"], "developerName": app["author"], "subtitle": format_app_subtitle(app["subtitle"], version_date), "localizedDescription": app["desc"], "iconURL": app["icon"], "tintColor": app["color"], "category": app.get("category", "entertainment"), "screenshots": [], "versions": [{"version": version_name, "date": version_date, "localizedDescription": (data.get("body") or "")[:500], "downloadURL": download_url, "size": size}]}
    except (requests.RequestException, ValueError):
        return None


def build_from_sideloadlabs(apps):
    if not isinstance(apps, list): return None
    match = next((app for app in apps if isinstance(app, dict) and app.get("name") == SIDELOADLABS_APP), None)
    if not isinstance(match, dict): return None
    url, size = match.get("downloadURL"), match.get("size", 0)
    if not match.get("bundleIdentifier") or not url or not validate_download_url(url, size): return None
    return {
        "name": SIDELOADLABS_DISPLAY_NAME,
        "bundleIdentifier": match["bundleIdentifier"],
        "developerName": match.get("developerName", "SideloadLabs"),
        "subtitle": format_app_subtitle("SideloadLabs", match.get("versionDate", "")),
        "localizedDescription": match.get("localizedDescription", ""),
        "iconURL": match.get("iconURL"),
        "tintColor": "669878",
        "category": "entertainment",
        "screenshots": [],
        "versions": [{
            "version": match.get("version", ""),
            "date": match.get("versionDate", ""),
            "localizedDescription": match.get("versionDescription") or match.get("localizedDescription", ""),
            "downloadURL": url,
            "size": size,
        }],
    }


def build_from_apptesters(app):
    if not isinstance(app, dict): return None
    name = app.get("name"); style = APP_STYLE.get(name, {"color": None, "subtitle": "AppTesters"})
    url, size = app.get("downloadURL"), app.get("size", 0)
    if not app.get("bundleIdentifier") or not url or not validate_download_url(url, size): return None
    return {"name": name, "bundleIdentifier": app["bundleIdentifier"], "developerName": "AppTesters", "subtitle": format_app_subtitle(style["subtitle"], app.get("versionDate", "")), "localizedDescription": app.get("localizedDescription", ""), "iconURL": app.get("iconURL") or app.get("icon"), "tintColor": style["color"], "category": "social" if name in {"Facebook", "Threads", "Instagram"} else "entertainment", "screenshots": [], "versions": [{"version": app.get("version", ""), "date": app.get("versionDate", ""), "localizedDescription": app.get("localizedDescription", ""), "downloadURL": url, "size": size}]}


def find_previous_app(old_apps, bundle_id=None, name=None):
    if not isinstance(old_apps, dict): return None
    for app in old_apps.get("apps", []):
        if isinstance(app, dict) and ((bundle_id and app.get("bundleIdentifier") == bundle_id) or (name and app.get("name") == name)): return app
    return None


def now_taiwan(): return datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S")


def get_previous_content_update(readme):
    match = re.search(r"最近內容更新：\s*\*?\*?\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", readme)
    return match.group(1) if match else "尚未更新"


def get_status_updated_at(readme):
    match = re.search(re.escape(STATUS_TIMES_START) + r"\s*<!--\s*(\{.*?\})\s*-->\s*" + re.escape(STATUS_TIMES_END), readme, flags=re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group(1))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def is_updated_within_day(updated_at, checked_at):
    try:
        updated = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
        checked = datetime.strptime(checked_at, "%Y-%m-%d %H:%M:%S")
        elapsed = (checked - updated).total_seconds()
        return 0 <= elapsed < 86400
    except (TypeError, ValueError):
        return False


def get_app_meta(name):
    for app in GITHUB_APPS:
        if app["name"] == name: return app["author"], app["repo_url"]
    if name == SIDELOADLABS_DISPLAY_NAME: return "SideloadLabs", SIDELOADLABS_REPO_URL
    return ("AppTesters", APPT_ESTERS_REPO_URL) if name in TARGET_APPS else ("Unknown", "")


def format_app_update_time(app, status_times, checked_at):
    name = app.get("name", "Unknown")
    exact_time = status_times.get(name)
    if exact_time and is_updated_within_day(exact_time, checked_at):
        return f"🟢 **{exact_time}**"
    date = ((app.get("versions") or [{}])[0]).get("date", "N/A")
    return date or "N/A"


def update_readme(apps, checked_at, content_updated_at, statuses, status_times):
    path = Path(README_FILENAME); readme = path.read_text(encoding="utf-8") if path.exists() else "# Chi Sources\n"
    rows = ["| App | 原倉庫 | 上次更新 |", "| --- | --- | --- |"]
    for app in apps:
        name = app.get("name", "Unknown")
        author, url = get_app_meta(name)
        app_link = f"[{name}]({url})" if url else name
        rows.append(f"| **{app_link}** | {author} | {format_app_update_time(app, status_times, checked_at)} |")
    status_rows = ["| App | 狀態 | 最新版本 | 版本日期 |", "| --- | --- | --- | --- |"]
    for app in apps:
        latest = (app.get("versions") or [{}])[0]
        status_rows.append(f"| {app.get('name', 'Unknown')} | {statuses.get(app.get('name'), '⚪ Unchanged')} | {latest.get('version', 'N/A')} | {latest.get('date', 'N/A')} |")
    status = "\n".join([STATUS_START, "## 更新狀態", f"- **最近自動檢查：** {checked_at}（台灣時間）", f"- **最近內容更新：** {content_updated_at}（台灣時間）", "", *status_rows, "", STATUS_END])
    status_times_block = "\n".join([
        STATUS_TIMES_START,
        f"<!-- {json.dumps(status_times, ensure_ascii=False, sort_keys=True)} -->",
        STATUS_TIMES_END,
    ])
    if STATUS_START in readme and STATUS_END in readme:
        readme = re.sub(re.escape(STATUS_START) + r".*?" + re.escape(STATUS_END), status, readme, flags=re.DOTALL)
    else:
        readme = readme.rstrip() + "\n\n" + status + "\n"
    if STATUS_TIMES_START in readme and STATUS_TIMES_END in readme:
        readme = re.sub(re.escape(STATUS_TIMES_START) + r".*?" + re.escape(STATUS_TIMES_END), status_times_block, readme, flags=re.DOTALL)
    else:
        readme = readme.rstrip() + "\n" + status_times_block + "\n"
    path.write_text(readme, encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Update Chi Sources")
    parser.add_argument("--app", help="Only update the specified app. Omit to update all apps.")
    return parser.parse_args()


def build_single_app(target_name, old_apps):
    config = next((app for app in GITHUB_APPS if app.get("name") == target_name), None)
    if config:
        built = build_from_github(config)
        if built: return built
        return find_previous_app({"apps": old_apps}, bundle_id=config["bundleID"])

    if target_name in TARGET_APPS:
        remote_apps = fetch_remote()
        match = next((app for app in remote_apps or [] if isinstance(app, dict) and app.get("name") == target_name), None)
        built = build_from_apptesters(match) if match else None
        return built or find_previous_app({"apps": old_apps}, name=target_name)

    if target_name == SIDELOADLABS_DISPLAY_NAME:
        sideload_apps = JSON_PROVIDER.fetch(SIDeloadLABS_SOURCE_URL)
        built = build_from_sideloadlabs(ensure_list(sideload_apps, "apps"))
        return built or find_previous_app({"apps": old_apps}, name=target_name)

    return None


def update_source_apps(old_source, old_apps, target_name=None):
    if not target_name:
        apps = []
        for config in GITHUB_APPS:
            built = build_from_github(config)
            if built: apps.append(built)
            else:
                previous = find_previous_app({"apps": old_apps}, bundle_id=config["bundleID"])
                if previous: apps.append(previous)
                else: print(f"❌ {config['name']}: update failed and no previous version available")

        remote_apps = fetch_remote()
        for target in TARGET_APPS:
            match = next((app for app in remote_apps or [] if isinstance(app, dict) and app.get("name") == target), None)
            built = build_from_apptesters(match) if match else None
            if built: apps.append(built)
            else:
                previous = find_previous_app({"apps": old_apps}, name=target)
                if previous: apps.append(previous)
                else: print(f"❌ {target}: update failed and no previous version available")

        sideload_apps = JSON_PROVIDER.fetch(SIDeloadLABS_SOURCE_URL)
        built = build_from_sideloadlabs(ensure_list(sideload_apps, "apps"))
        if built: apps.append(built)
        else:
            previous = find_previous_app({"apps": old_apps}, name=SIDELOADLABS_DISPLAY_NAME)
            if previous: apps.append(previous)
            else: print(f"❌ {SIDELOADLABS_DISPLAY_NAME}: update failed and no previous version available")
        return keep_latest_only(apps)

    if target_name == "all":
        return update_source_apps(old_source, old_apps)

    updated = build_single_app(target_name, old_apps)
    if not updated: raise ValueError(f"Unknown app or update failed: {target_name}")

    target_bundle = updated.get("bundleIdentifier")
    target_index = next((i for i, app in enumerate(old_apps) if isinstance(app, dict) and ((target_bundle and app.get("bundleIdentifier") == target_bundle) or app.get("name") == target_name)), None)
    apps = list(old_apps)
    if target_index is None: apps.append(updated)
    else: apps[target_index] = updated
    return keep_latest_only(apps)


def main():
    args = parse_args()
    old_source = json.loads(Path(FILENAME).read_text(encoding="utf-8")) if Path(FILENAME).exists() else {}
    old_apps = old_source.get("apps", []) if isinstance(old_source, dict) else []
    apps = update_source_apps(old_source, old_apps, args.app)
    checked_at = now_taiwan()
    current_readme = Path(README_FILENAME).read_text(encoding="utf-8") if Path(README_FILENAME).exists() else ""
    previous_content_update = get_previous_content_update(current_readme) if current_readme else "尚未更新"
    previous_status_times = get_status_updated_at(current_readme)
    content_changed = json.dumps(apps, ensure_ascii=False, sort_keys=True) != json.dumps(old_apps, ensure_ascii=False, sort_keys=True)
    content_updated_at = checked_at if content_changed else previous_content_update
    source = dict(old_source) if isinstance(old_source, dict) else {}
    source.update({"name": DISPLAY_NAME, "identifier": "chi-source", "sourceURL": SOURCE_URL, "subtitle": "Chi's IPA Source", "description": SOURCE_DESCRIPTION, "website": "https://altstore.chi.qzz.io", "iconURL": SOURCE_ICON_URL, "featuredApps": [app["bundleIdentifier"] for app in apps], "apps": apps, "news": source.get("news", [])})
    Path(FILENAME).write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    statuses = {}
    status_times = {}
    old_by_name = {app.get("name"): app for app in old_apps if isinstance(app, dict)}
    for app in apps:
        name = app.get("name")
        old = old_by_name.get(name)
        new_ver = get_version(app)
        old_ver = get_version(old) if old else None
        if old_ver != new_ver:
            statuses[name] = "🟢 Updated"
            status_times[name] = checked_at
        elif previous_status_times.get(name) and is_updated_within_day(previous_status_times[name], checked_at):
            statuses[name] = "🟢 Updated"
            status_times[name] = previous_status_times[name]
        else:
            statuses[name] = "⚪ Unchanged"
    update_readme(apps, checked_at, content_updated_at, statuses, status_times)


if __name__ == "__main__":
    main()
