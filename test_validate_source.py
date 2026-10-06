import copy
import json

import validate_source as validator


def load_source():
    with open("apps.json", encoding="utf-8") as file:
        return json.load(file)


def test_validate_current_source():
    assert validator.validate_source_data(load_source()) is True


def test_rejects_invalid_tint_color():
    source = copy.deepcopy(load_source())
    source["apps"][0]["tintColor"] = "GGGGGG"
    assert validator.validate_source_data(source) is False


def test_rejects_invalid_version_date():
    source = copy.deepcopy(load_source())
    source["apps"][0]["versions"][0]["date"] = "not-a-date"
    assert validator.validate_source_data(source) is False


def test_rejects_non_positive_size():
    source = copy.deepcopy(load_source())
    source["apps"][0]["versions"][0]["size"] = 0
    assert validator.validate_source_data(source) is False


def test_rejects_invalid_screenshot_url():
    source = copy.deepcopy(load_source())
    source["apps"][0]["screenshots"] = ["http://example.com/image.png"]
    assert validator.validate_source_data(source) is False


def test_rejects_duplicate_version():
    source = copy.deepcopy(load_source())
    source["apps"][0]["versions"].append(copy.deepcopy(source["apps"][0]["versions"][0]))
    assert validator.validate_source_data(source) is False
