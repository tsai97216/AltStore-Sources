import os
import json
import requests
import hashlib

# =========================
# 🌙 ChiSource 設定
# =========================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
FILENAME = "apps.json"

YOUR_GITHUB_ID = "tsai97216"
DISPLAY_NAME = "Chi Source"

SOURCE_URL = f"https://{YOUR_GITHUB_ID}.github.io/My-AltStore-Source/{FILENAME}"

SOURCE_ICON_URL = f"https://raw.githubusercontent.com/{YOUR_GITHUB_ID}/My-AltStore-Source/main/source_icon.PNG"

COLOR_MAIN = "7DCEA0"


# =========================
# 📦 Apps 清單
# =========================
APPS = [
    {
        "repo": "bggRGjQaUbCoE/PiliPlus",
        "name": "PiliPlus",
        "bundleID": "com.bgg.piliplus",
        "icon": "https://raw.githubusercontent.com/bggRGjQaUbCoE/PiliPlus/main/assets/images/logo/desktop/logo_large.png",
        "subtitle": "第三方 Bilibili 客戶端",
        "desc": "提供自動全螢幕、音量均衡、彈幕過濾等功能。"
    },
    {
        "repo": "Mark02-2012/YTPlusM",
        "name": "YTPlusM",
        "bundleID": "com.mark.ytplusm",
        "icon": "https://raw.githubusercontent.com/Mark02-2012/YTPlusM/main/Resources/IMG_5913.png",
        "subtitle": "YouTube 修改版",
        "desc": "提供去廣告、播放優化與額外功能。"
    }
]


# =========================
# 🔐 SHA1 計算
# =========================
def get_sha1(url):
    print(f"🔍 計算 SHA1: {url}")
    r = requests.get(url, stream=True)
    r.raise_for_status()

    sha1 = hashlib.sha1()
    for chunk in r.iter_content(chunk_size=8192):
        if chunk:
            sha1.update(chunk)

    return sha1.hexdigest()


# =========================
# 📡 取得 App 最新版本
# =========================
def get_app_data(app):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    api_url = f"https://api.github.com/repos/{app['repo']}/releases/latest"

    res = requests.get(api_url, headers=headers)

    if res.status_code != 200:
        print(f"❌ {app['name']} 無法取得 release")
        return None

    data = res.json()
    assets = data.get("assets", [])

    ipa_asset = next(
        (a for a in assets if a["name"].lower().endswith(".ipa")),
        None
    )

    if not ipa_asset:
        print(f"⚠️ {app['name']} 沒有 IPA，跳過")
        return None

    print(f"✅ {app['name']} 更新版本: {data.get('tag_name')}")

    return {
        "name": app["name"],
        "bundleIdentifier": app["bundleID"],
        "developerName": app["repo"].split("/")[0],
        "subtitle": app["subtitle"],
        "localizedDescription": app["desc"],
        "iconURL": app["icon"],
        "tintColor": COLOR_MAIN,
        "category": "entertainment",
        "screenshots": [],
        "versions": [
            {
                "version": data.get("tag_name", "").replace("v", ""),
                "date": (data.get("published_at") or "")[:10],
                "localizedDescription": (data.get("body") or "自動同步 GitHub 最新版本")[:1000],
                "downloadURL": ipa_asset["browser_download_url"],
                "size": ipa_asset["size"],
                "sha1hash": get_sha1(ipa_asset["browser_download_url"])
            }
        ]
    }


# =========================
# 🚀 主流程
# =========================
def update_source():
    print(f"🚀 正在更新 {DISPLAY_NAME}...")

    apps_list = []

    for app in APPS:
        data = get_app_data(app)
        if data:
            apps_list.append(data)

    source_data = {
        "name": f"{DISPLAY_NAME}",
        "identifier": f"com.{DISPLAY_NAME.lower()}.custom.source",
        "sourceURL": SOURCE_URL,
        "subtitle": "iOS 修改版 Ipa",
        "description": f"{DISPLAY_NAME} 自動維護的 IPA Source",
        "website": f"https://github.com/{YOUR_GITHUB_ID}/My-AltStore-Source",
        "iconURL": SOURCE_ICON_URL,
        "featuredApps": [app["bundleIdentifier"] for app in apps_list],
        "apps": apps_list,
        "news": []
    }

    with open(FILENAME, "w", encoding="utf-8") as f:
        json.dump(source_data, f, indent=2, ensure_ascii=False)

    print("🎉 Chi Source 更新完成")


if __name__ == "__main__":
    update_source()
