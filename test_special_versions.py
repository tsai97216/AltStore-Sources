import update_source as updater


def test_choose_highest_ytkace_ipa():
    releases = [
        {
            "name": "YTKACE old",
            "published_at": "2026-08-29T10:00:00Z",
            "assets": [{"name": "YTKACE_21.33.2.ipa"}],
        },
        {
            "name": "YTKACE new",
            "published_at": "2026-08-30T10:00:00Z",
            "assets": [{"name": "YTKACE_21.34.3.ipa"}],
        },
    ]
    release, asset = updater.choose_highest_ytkace_ipa(releases)
    assert release["name"] == "YTKACE new"
    assert asset["name"] == "YTKACE_21.34.3.ipa"


def test_choose_highest_ytkace_ipa_ignores_prerelease_and_non_ipa():
    releases = [
        {
            "name": "YTKACE prerelease",
            "published_at": "2026-08-31T10:00:00Z",
            "prerelease": True,
            "assets": [{"name": "YTKACE_99.99.99.ipa"}],
        },
        {
            "name": "YTKACE stable",
            "published_at": "2026-08-30T10:00:00Z",
            "assets": [
                {"name": "YTKACE_21.34.3.zip"},
                {"name": "YTKACE_21.34.3.ipa"},
            ],
        },
    ]
    release, asset = updater.choose_highest_ytkace_ipa(releases)
    assert release["name"] == "YTKACE stable"
    assert asset["name"] == "YTKACE_21.34.3.ipa"


def test_choose_highest_ytkace_ipa_returns_none_without_matching_version():
    releases = [
        {"name": "YTKACE", "assets": [{"name": "YTKACE-latest.ipa"}]},
    ]
    assert updater.choose_highest_ytkace_ipa(releases) is None


def test_normalize_ytkace_version():
    assert updater.normalize_version("YTKACE", "YTKACE YouTube 21.34.3") == "21.34.3"


def test_normalize_ytmultimate_version():
    assert updater.normalize_version("YTMUltimate+", "YTMUltimate+ and 9.33.3") == "9.33.3"
