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
def test_is_updated_within_day():
    checked = "2026-10-06 12:00:00"
    assert updater.is_updated_within_day("2026-10-06 00:00:00", checked) is True
    assert updater.is_updated_within_day("2026-10-05 11:59:59", checked) is False
    assert updater.is_updated_within_day("2026-10-06 12:00:01", checked) is False
    assert updater.is_updated_within_day("not-a-date", checked) is False


def test_get_status_updated_at():
    readme = """
<!-- AUTO-UPDATE-STATUS-TIMES:START -->
<!-- {"PiliPlus": "2026-10-06 01:00:00", "YTKACE": "2026-10-05 02:00:00"} -->
<!-- AUTO-UPDATE-STATUS-TIMES:END -->
"""
    assert updater.get_status_updated_at(readme) == {
        "PiliPlus": "2026-10-06 01:00:00",
        "YTKACE": "2026-10-05 02:00:00",
    }


def test_get_status_updated_at_invalid_block():
    readme = """
<!-- AUTO-UPDATE-STATUS-TIMES:START -->
<!-- not-json -->
<!-- AUTO-UPDATE-STATUS-TIMES:END -->
"""
    assert updater.get_status_updated_at(readme) == {}


def test_app_config_contains_expected_github_apps():
    assert [app["name"] for app in updater.GITHUB_APPS] == ["PiliPlus", "YTKACE", "MaxMusic"]
    for app in updater.GITHUB_APPS:
        assert app["repo"]
        assert app["bundleID"]
        assert app["author"]


def test_github_provider_builds_release_url():
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"tag_name": "v1.2.3"}

    class FakeSession:
        def get(self, url, timeout):
            assert url.endswith("/repos/example/app/releases/latest")
            assert timeout == 15
            return FakeResponse()

    provider = updater.GITHUB_PROVIDER.__class__(FakeSession())
    assert provider.latest_release("example/app")["tag_name"] == "v1.2.3"


def test_update_source_apps_single_preserves_other_apps(monkeypatch):
    old_apps = [
        {
            "name": "PiliPlus",
            "bundleIdentifier": "com.bgg.piliplus",
            "versions": [{"version": "2.1.6"}],
        },
        {
            "name": "YTKACE",
            "bundleIdentifier": "com.google.ios.youtube",
            "versions": [{"version": "21.40.5"}],
        },
    ]
    updated = {
        "name": "PiliPlus",
        "bundleIdentifier": "com.bgg.piliplus",
        "versions": [{"version": "2.1.7"}],
    }
    monkeypatch.setattr(updater, "build_single_app", lambda name, apps: updated)
    result = updater.update_source_apps({}, old_apps, "PiliPlus")
    by_name = {app["name"]: app for app in result}
    assert by_name["PiliPlus"]["versions"][0]["version"] == "2.1.7"
    assert by_name["YTKACE"]["versions"][0]["version"] == "21.40.5"
    assert len(result) == 2


def test_update_source_apps_single_unknown_app():
    old_apps = [
        {
            "name": "PiliPlus",
            "bundleIdentifier": "com.bgg.piliplus",
            "versions": [{"version": "2.1.6"}],
        }
    ]
    try:
        updater.update_source_apps({}, old_apps, "Missing")
    except ValueError as exc:
        assert "Unknown app or update failed" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_github_failure_falls_back_to_previous(monkeypatch):
    old_apps = [
        {
            "name": "PiliPlus",
            "bundleIdentifier": "com.bgg.piliplus",
            "versions": [{"version": "2.1.6"}],
        }
    ]
    monkeypatch.setattr(updater, "build_from_github", lambda config: None)
    result = updater.update_source_apps({}, old_apps, "PiliPlus")
    assert result == old_apps


def test_apptesters_failure_falls_back_to_previous(monkeypatch):
    old_apps = [
        {
            "name": "Facebook",
            "bundleIdentifier": "com.facebook.Facebook",
            "versions": [{"version": "570.0.0"}],
        }
    ]
    monkeypatch.setattr(updater, "fetch_remote", lambda: None)
    result = updater.update_source_apps({}, old_apps, "Facebook")
    assert result == old_apps


def test_sideloadlabs_failure_falls_back_to_previous(monkeypatch):
    old_apps = [
        {
            "name": "EeveeSpotify Reincarnated",
            "bundleIdentifier": "com.spotify.client.patched",
            "versions": [{"version": "9.1.88"}],
        }
    ]
    monkeypatch.setattr(updater.JSON_PROVIDER, "fetch", lambda url: None)
    result = updater.update_source_apps({}, old_apps, "EeveeSpotify Reincarnated")
    assert result == old_apps


def test_all_update_keeps_previous_app_when_one_source_fails(monkeypatch):
    old_apps = [
        {
            "name": "PiliPlus",
            "bundleIdentifier": "com.bgg.piliplus",
            "versions": [{"version": "2.1.6"}],
        }
    ]
    monkeypatch.setattr(updater, "build_from_github", lambda config: None)
    monkeypatch.setattr(updater, "fetch_remote", lambda: None)
    monkeypatch.setattr(updater.JSON_PROVIDER, "fetch", lambda url: None)
    result = updater.update_source_apps({}, old_apps)
    assert result[0] == old_apps[0]

def test_choose_ipa_asset_accepts_uppercase_extension():
    assets = [
        {"name": "YTKACE.IPA", "created_at": "2026-08-29T10:00:00Z"},
    ]
    assert updater.choose_ipa_asset(assets, {"asset_keywords": ["ytkace"]})["name"] == "YTKACE.IPA"


def test_normalize_version_for_maxmusic():
    assert updater.normalize_version("MaxMusic", "YTMusicUltimate+ and 9.34.4") == "9.34.4"


def test_normalize_version_for_ytkace():
    assert updater.normalize_version("YTKACE", "YouTube v21.40.5") == "21.40.5"


def test_keep_latest_only_handles_v_prefix_versions():
    apps = [
        {"name": "Example", "bundleIdentifier": "com.example.app", "version": "v1.9.0"},
        {"name": "Example", "bundleIdentifier": "com.example.app", "version": "v1.10.0"},
    ]
    result = updater.keep_latest_only(apps)
    assert result[0]["version"] == "v1.10.0"


def test_validate_download_url_rejects_missing_content_length(monkeypatch):
    class Response:
        status_code = 200
        headers = {}

        def close(self):
            pass

    monkeypatch.setattr(updater.SESSION, "head", lambda *args, **kwargs: Response())
    assert updater.validate_download_url("https://example.com/app.ipa") is False


def test_validate_download_url_range_fallback(monkeypatch):
    class Response:
        def __init__(self, status_code, headers):
            self.status_code = status_code
            self.headers = headers

        def close(self):
            pass

    calls = []

    def fake_head(*args, **kwargs):
        calls.append("head")
        return Response(405, {})

    def fake_get(*args, **kwargs):
        calls.append("get")
        assert kwargs["headers"] == {"Range": "bytes=0-0"}
        assert kwargs["stream"] is True
        return Response(206, {"Content-Length": "1"})

    monkeypatch.setattr(updater.SESSION, "head", fake_head)
    monkeypatch.setattr(updater.SESSION, "get", fake_get)
    assert updater.validate_download_url("https://example.com/app.ipa") is True
    assert calls == ["head", "get"]

