import json
from pathlib import Path

import update_source as updater


def test_choose_ipa_asset_prefers_keyword():
    assets = [
        {"name": "Other.ipa", "created_at": "2026-08-29T10:00:00Z"},
        {"name": "YTKACE.ipa", "created_at": "2026-08-28T10:00:00Z"},
    ]
    app = {"asset_keywords": ["ytkace"]}
    assert updater.choose_ipa_asset(assets, app)["name"] == "YTKACE.ipa"


def test_choose_ipa_asset_ignores_non_ipa():
    assets = [
        {"name": "YTKACE.zip", "created_at": "2026-08-29T10:00:00Z"},
        {"name": "README.md", "created_at": "2026-08-29T11:00:00Z"},
    ]
    assert updater.choose_ipa_asset(assets, {"asset_keywords": ["ytkace"]}) is None


def test_keep_latest_only():
    apps = [
        {"name": "Example", "bundleIdentifier": "com.example.app", "version": "1.0.0"},
        {"name": "Example", "bundleIdentifier": "com.example.app", "version": "1.2.0"},
        {"name": "Other", "bundleIdentifier": "com.other.app", "version": "2.0.0"},
    ]
    result = updater.keep_latest_only(apps)
    by_bundle = {app["bundleIdentifier"]: app for app in result}
    assert by_bundle["com.example.app"]["version"] == "1.2.0"
    assert len(result) == 2


def test_find_previous_app():
    old = {
        "apps": [
            {"name": "PiliPlus", "bundleIdentifier": "com.bgg.piliplus", "versions": [{"version": "1.0.0"}]}
        ]
    }
    assert updater.find_previous_app(old, bundle_id="com.bgg.piliplus")["name"] == "PiliPlus"
    assert updater.find_previous_app(old, name="PiliPlus")["bundleIdentifier"] == "com.bgg.piliplus"
    assert updater.find_previous_app(old, name="Missing") is None


def test_validate_download_url_rejects_non_https():
    assert updater.validate_download_url("http://example.com/app.ipa") is False
    assert updater.validate_download_url("not-a-url") is False


def test_validate_download_url_success(monkeypatch):
    class Response:
        status_code = 200
        headers = {"Content-Length": "1234"}

        def close(self):
            pass

    monkeypatch.setattr(updater.SESSION, "head", lambda *args, **kwargs: Response())
    assert updater.validate_download_url("https://example.com/app.ipa", 1234) is True


def test_validate_download_url_size_mismatch(monkeypatch):
    class Response:
        status_code = 200
        headers = {"Content-Length": "999"}

        def close(self):
            pass

    monkeypatch.setattr(updater.SESSION, "head", lambda *args, **kwargs: Response())
    assert updater.validate_download_url("https://example.com/app.ipa", 1234) is False
