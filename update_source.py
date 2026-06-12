import os
import json
import requests
from packaging import version as pkg_version

# =========================
# 🌙 Chi Source 基本設定
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
        "color": "7DCEA0",
    },
    {
        "repo": "Mark02-2012/YTPlusM",
        "name": "YTPlusM",
        "bundleID": "com.mark.ytplusm",
        "icon": "https://raw.githubusercontent.com/Mark02-2012/YTPlusM/main/Resources/IMG_5913.png",
        "subtitle": "YouTube 修改版",
        "desc": "提供去廣告、播放優化與額外功能。",
        "color": "FF4D4D",
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
    return r.json()["apps"]

# =========================
# 🔥 version helper
# =========================
def get_version(app):
    v = app.get("version")
    if v:
        return v

    versions = app.get("versions") or []
    if versions:
        return versions[0].get("version", "0.0.0")

    return "0.0.0"


def keep_latest_only(apps):
    latest = {}

    for app in apps:
        bid = app.get("bundleIdentifier")
        if not bid:
            continue

        ver = get_version(app)

        if bid not in latest:
            latest[bid] = app
            continue

        old_ver = get_version(latest[bid])

        try:
            if pkg_version.parse(ver) > pkg_version.parse(old_ver):
                latest[bid] = app
        except:
            latest[bid] = app

    return list(latest.values())

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
# 🌐 AppTesters builder（已改色 + subtitle）
# =========================
def build_from_apptesters(app):
    name = app["name"]

    if name == "Facebook":
        tint = "4A90E2"
        subtitle = "Facebook修改版"
    elif name == "Threads":
        tint = "2E2E2E"
        subtitle = "Threads修改版"
    else:
        tint = None
        subtitle = "Imported from AppTesters"

    return {
        "name": name,
        "bundleIdentifier": app.get("bundleIdentifier"),
        "developerName": "AppTesters",
        "subtitle": subtitle,
        "localizedDescription": app.get("localizedDescription", ""),
        "iconURL": app.get("iconURL") or app.get("icon"),
        "tintColor": tint,
        "category": "social",
        "screenshots": [],
        "versions": [
            {
                "version": app.get("version", ""),
                "date": app.get("versionDate", ""),
                "localizedDescription": app.get("localizedDescription", ""),
                "downloadURL": app.get("downloadURL") or app.get("down"),
                "size": app.get("size", 0),
            }
        ]
    }

# =========================
# 🚀 main
# =========================
def update_source():
    print(f"🚀 正在更新 {DISPLAY_NAME}...")

    apps_list = []

    # GitHub apps
    for app in LOCAL_APPS:
        apps_list.append(build_from_github(app))

    # AppTesters apps
    remote = fetch_remote()
    remote = [a for a in remote if a.get("name") in TARGET_APPS]
    remote = keep_latest_only(remote)

    for app in remote:
        apps_list.append(build_from_apptesters(app))

    # source
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
