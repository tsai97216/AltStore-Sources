import os
import json
import requests

# =========================
# 🌙 Chi Source 設定
# =========================
FILENAME = "apps.json"

YOUR_GITHUB_ID = "tsai97216"
DISPLAY_NAME = "Chi Source"

SOURCE_URL = f"https://{YOUR_GITHUB_ID}.github.io/My-AltStore-Source/{FILENAME}"
SOURCE_ICON_URL = f"https://raw.githubusercontent.com/{YOUR_GITHUB_ID}/My-AltStore-Source/main/source_icon.PNG"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# =========================
# 📦 GitHub Apps
# =========================
LOCAL_APPS = [
    {
        "repo": "bggRGjQaUbCoE/PiliPlus",
        "name": "PiliPlus",
        "bundleID": "com.bgg.piliplus",
        "icon": "https://raw.githubusercontent.com/bggRGjQaUbCoE/PiliPlus/main/assets/images/logo/desktop/logo_large.png",
        "subtitle": "第三方 Bilibili 客戶端",
        "desc": "提供自動全螢幕、音量均衡、彈幕過濾等功能。",
        "color": "7DCEA0"
    },
    {
        "repo": "Mark02-2012/YTPlusM",
        "name": "YTPlusM",
        "bundleID": "com.mark.ytplusm",
        "icon": "https://raw.githubusercontent.com/Mark02-2012/YTPlusM/main/Resources/IMG_5913.png",
        "subtitle": "YouTube 修改版",
        "desc": "提供去廣告、播放優化與額外功能。",
        "color": "FF4D4D"
    }
]

# =========================
# 🌐 AppTesters
# =========================
SOURCE_DATA_URL = "https://raw.githubusercontent.com/apptesters-org/AppTesters_Repo/main/apps.json"
TARGET_APPS = {"Facebook", "Threads"}

# =========================
# 📡 fetch remote
# =========================
def fetch_remote():
    r = requests.get(SOURCE_DATA_URL)
    r.raise_for_status()
    return r.json().get("apps", [])

# =========================
# 🔍 filter target apps（放寬）
# =========================
def filter_remote(apps):
    return [
        a for a in apps
        if any(t in a.get("name", "") for t in TARGET_APPS)
    ]

# =========================
# 🧠 version parser（核心修復）
# =========================
def parse_version(v):
    try:
        return tuple(int(x) for x in v.split("."))
    except:
        return (0, 0, 0)

def safe_version(app):
    try:
        return app.get("versions", [{}])[0].get("version", "0.0.0")
    except:
        return "0.0.0"

# =========================
# 🧠 merge latest（真正正確版本）
# =========================
def merge_latest(apps):
    merged = {}

    for app in apps:
        key = app.get("bundleIdentifier")
        if not key:
            continue

        v = parse_version(safe_version(app))

        if key not in merged:
            merged[key] = app
        else:
            old_v = parse_version(safe_version(merged[key]))

            if v > old_v:
                merged[key] = app

    return list(merged.values())

# =========================
# 🔥 validate（防壞資料）
# =========================
def is_valid_app(app):
    v = app.get("versions", [{}])[0]
    return (
        v.get("version") not in [None, "", " "]
        and v.get("downloadURL") not in [None, "", " "]
    )

# =========================
# 🐙 GitHub builder
# =========================
def build_from_github(app):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    url = f"https://api.github.com/repos/{app['repo']}/releases/latest"

    r = requests.get(url, headers=headers)
    data = r.json()

    assets = data.get("assets", [])
    ipa = next((a for a in assets if a["name"].endswith(".ipa")), None)

    return {
        "name": app["name"],
        "bundleIdentifier": app["bundleID"],
        "developerName": app["repo"].split("/")[0],
        "subtitle": app["subtitle"],
        "localizedDescription": app["desc"],
        "iconURL": app["icon"],
        "tintColor": app.get("color"),
        "category": "entertainment",
        "screenshots": [],
        "versions": [
            {
                "version": (data.get("tag_name") or "").replace("v", ""),
                "date": (data.get("published_at") or "")[:10],
                "localizedDescription": (data.get("body") or "")[:1000],
                "downloadURL": ipa["browser_download_url"] if ipa else "",
                "size": ipa["size"] if ipa else 0,
            }
        ]
    }

# =========================
# 🌐 AppTesters builder
# =========================
def build_from_apptesters(app):
    v = app.get("versions", [{}])[0]

    return {
        "name": app.get("name"),
        "bundleIdentifier": app.get("bundleIdentifier"),
        "developerName": "AppTesters",
        "subtitle": "Imported from AppTesters",
        "localizedDescription": app.get("localizedDescription", ""),
        "iconURL": app.get("iconURL") or app.get("icon"),
        "tintColor": None,
        "category": "social",
        "screenshots": [],
        "versions": [
            {
                "version": v.get("version", "0.0.0"),
                "date": v.get("date", ""),
                "localizedDescription": app.get("localizedDescription", ""),
                "downloadURL": v.get("downloadURL"),
                "size": v.get("size", 0),
            }
        ]
    }

# =========================
# 🚀 main
# =========================
def update_source():
    print(f"🚀 正在更新 {DISPLAY_NAME}...")

    apps_list = []

    # ---------------------
    # GitHub apps
    # ---------------------
    for app in LOCAL_APPS:
        apps_list.append(build_from_github(app))

    # ---------------------
    # AppTesters apps
    # ---------------------
    remote = fetch_remote()
    remote = filter_remote(remote)

    remote = [a for a in remote if is_valid_app(a)]
    remote = merge_latest(remote)

    for app in remote:
        apps_list.append(build_from_apptesters(app))

    # ---------------------
    # output
    # ---------------------
    source_data = {
        "name": DISPLAY_NAME,
        "identifier": f"com.{DISPLAY_NAME.lower().replace(' ', '')}.source",
        "sourceURL": SOURCE_URL,
        "subtitle": "iOS IPA Source",
        "description": f"{DISPLAY_NAME} auto curated source",
        "website": f"https://github.com/{YOUR_GITHUB_ID}/My-AltStore-Source",
        "iconURL": SOURCE_ICON_URL,
        "featuredApps": [a["bundleIdentifier"] for a in apps_list],
        "apps": apps_list,
        "news": []
    }

    with open(FILENAME, "w", encoding="utf-8") as f:
        json.dump(source_data, f, indent=2, ensure_ascii=False)

    print("🎉 Chi Source 更新完成")

if __name__ == "__main__":
    update_source()
