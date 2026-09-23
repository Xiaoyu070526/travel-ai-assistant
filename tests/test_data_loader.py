"""``src.utils.data_loader`` 的基础测试（Day 3）。

运行方式（在项目根目录执行）::

    python -m unittest discover -s tests -v

本测试使用标准库 ``unittest`` 编写，无需额外安装依赖；
若已安装 pytest，也可以用 ``pytest tests -v`` 运行。

测试使用的是 ``data/processed/`` 下的**示例数据**，
因此断言只针对数据结构与关联关系，不针对任何真实旅游信息。
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

# 允许从任意目录运行测试：把项目根目录加入 sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils import data_loader  # noqa: E402
from src.utils.data_loader import (  # noqa: E402
    DataFileNotFoundError,
    DataLoadError,
    get_app,
    get_apps_by_ids,
    get_attraction,
    get_attractions_by_city,
    get_attractions_by_ids,
    get_city,
    load_apps,
    load_attractions,
    load_cities,
)

# 各实体必须包含的字段（与 Day 3 的数据结构设计一致）
CITY_FIELDS = (
    "city_id",
    "city_name",
    "description",
    "transport",
    "tips",
    "app_ids",
    "attraction_ids",
)

ATTRACTION_FIELDS = (
    "attraction_id",
    "city_id",
    "name",
    "description",
    "reservation_required",
    "passport_booking_status",
    "entry_method",
    "alternative_attraction_ids",
    "source_url",
    "updated_at",
)

APP_FIELDS = (
    "app_id",
    "name",
    "category",
    "description",
    "download_links",
)


class DataDirMixin:
    """提供临时数据目录，用于构造文件缺失 / 内容损坏等异常场景。"""

    def make_temp_dir(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)


class TestLoadCities(unittest.TestCase):
    def test_returns_non_empty_list(self):
        cities = load_cities()
        self.assertIsInstance(cities, list)
        self.assertGreater(len(cities), 0)

    def test_every_city_has_required_fields(self):
        for city in load_cities():
            for field in CITY_FIELDS:
                self.assertIn(field, city, f"城市 {city.get('city_id')} 缺少字段 {field}")

    def test_chinese_text_is_decoded_correctly(self):
        """验证 UTF-8 读取：示例数据中的中文城市名能够正确解析。"""
        beijing = get_city("beijing")
        self.assertIsNotNone(beijing)
        self.assertEqual(beijing["city_name"], "北京")

    def test_id_lists_are_lists(self):
        for city in load_cities():
            self.assertIsInstance(city["app_ids"], list)
            self.assertIsInstance(city["attraction_ids"], list)
            self.assertIsInstance(city["tips"], list)


class TestGetCity(unittest.TestCase):
    def test_found(self):
        city = get_city("beijing")
        self.assertIsInstance(city, dict)
        self.assertEqual(city["city_id"], "beijing")

    def test_not_found_returns_none(self):
        self.assertIsNone(get_city("city-that-does-not-exist"))

    def test_none_id_returns_none(self):
        self.assertIsNone(get_city(None))

    def test_every_declared_city_is_retrievable(self):
        for city in load_cities():
            self.assertIsNotNone(get_city(city["city_id"]))


class TestLoadAttractions(unittest.TestCase):
    def test_returns_non_empty_list(self):
        attractions = load_attractions()
        self.assertIsInstance(attractions, list)
        self.assertGreater(len(attractions), 0)

    def test_every_attraction_has_required_fields(self):
        for attraction in load_attractions():
            for field in ATTRACTION_FIELDS:
                self.assertIn(
                    field,
                    attraction,
                    f"景点 {attraction.get('attraction_id')} 缺少字段 {field}",
                )

    def test_booking_fields_are_not_fabricated(self):
        """示例数据不得包含编造的真实预订信息。"""
        for attraction in load_attractions():
            self.assertIsNone(attraction["reservation_required"])
            self.assertIsNone(attraction["entry_method"])
            self.assertIsNone(attraction["source_url"])
            self.assertEqual(attraction["passport_booking_status"], "unknown")


class TestGetAttractionsByCity(unittest.TestCase):
    def test_returns_only_that_city(self):
        attractions = get_attractions_by_city("beijing")
        self.assertGreater(len(attractions), 0)
        for attraction in attractions:
            self.assertEqual(attraction["city_id"], "beijing")

    def test_unknown_city_returns_empty_list(self):
        self.assertEqual(get_attractions_by_city("city-that-does-not-exist"), [])

    def test_none_city_returns_empty_list(self):
        self.assertEqual(get_attractions_by_city(None), [])

    def test_result_matches_city_attraction_ids(self):
        """get_attractions_by_city 与 city["attraction_ids"] 应保持一致。"""
        for city in load_cities():
            by_city = {a["attraction_id"] for a in get_attractions_by_city(city["city_id"])}
            self.assertEqual(by_city, set(city["attraction_ids"]))


class TestGetAttraction(unittest.TestCase):
    def test_found(self):
        attraction = get_attraction("beijing-forbidden-city")
        self.assertIsInstance(attraction, dict)
        self.assertEqual(attraction["attraction_id"], "beijing-forbidden-city")
        self.assertEqual(attraction["city_id"], "beijing")

    def test_not_found_returns_none(self):
        self.assertIsNone(get_attraction("attraction-that-does-not-exist"))

    def test_none_id_returns_none(self):
        self.assertIsNone(get_attraction(None))


class TestGetAttractionsByIds(unittest.TestCase):
    def test_preserves_requested_order(self):
        ids = ["beijing-badaling-great-wall", "beijing-forbidden-city"]
        result = get_attractions_by_ids(ids)
        self.assertEqual([a["attraction_id"] for a in result], ids)

    def test_skips_unknown_ids(self):
        result = get_attractions_by_ids(["beijing-forbidden-city", "nope"])
        self.assertEqual(len(result), 1)

    def test_empty_input(self):
        self.assertEqual(get_attractions_by_ids([]), [])
        self.assertEqual(get_attractions_by_ids(None), [])


class TestLoadApps(unittest.TestCase):
    def test_returns_non_empty_list(self):
        apps = load_apps()
        self.assertIsInstance(apps, list)
        self.assertGreater(len(apps), 0)

    def test_every_app_has_required_fields(self):
        for app in load_apps():
            for field in APP_FIELDS:
                self.assertIn(field, app, f"App {app.get('app_id')} 缺少字段 {field}")

    def test_download_links_structure(self):
        for app in load_apps():
            links = app["download_links"]
            self.assertIsInstance(links, dict)
            for key in ("ios", "android", "official_website"):
                self.assertIn(key, links)
                # 示例数据中的链接一律为空，不做编造
                self.assertIsNone(links[key])


class TestGetApp(unittest.TestCase):
    def test_found(self):
        app = get_app("alipay")
        self.assertIsInstance(app, dict)
        self.assertEqual(app["app_id"], "alipay")

    def test_not_found_returns_none(self):
        self.assertIsNone(get_app("app-that-does-not-exist"))

    def test_none_id_returns_none(self):
        self.assertIsNone(get_app(None))


class TestGetAppsByIds(unittest.TestCase):
    def test_preserves_requested_order(self):
        ids = ["didi", "alipay"]
        result = get_apps_by_ids(ids)
        self.assertEqual([a["app_id"] for a in result], ids)

    def test_skips_unknown_ids(self):
        result = get_apps_by_ids(["alipay", "nope"])
        self.assertEqual(len(result), 1)

    def test_empty_input(self):
        self.assertEqual(get_apps_by_ids([]), [])
        self.assertEqual(get_apps_by_ids(None), [])


class TestErrorHandling(DataDirMixin, unittest.TestCase):
    def test_missing_file_raises_data_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(DataFileNotFoundError) as ctx:
                load_cities(data_dir=tmp)
            # 错误信息中应包含出错的路径，便于排查
            self.assertIn("cities.json", str(ctx.exception))

    def test_missing_file_is_also_file_not_found(self):
        """DataFileNotFoundError 应同时是标准库的 FileNotFoundError。"""
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                load_attractions(data_dir=tmp)

    def test_missing_file_is_also_data_load_error(self):
        """便于调用方统一按 DataLoadError 捕获。"""
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(DataLoadError):
                load_apps(data_dir=tmp)

    def test_all_three_loaders_raise_on_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            for loader in (load_cities, load_attractions, load_apps):
                with self.subTest(loader=loader.__name__):
                    with self.assertRaises(DataFileNotFoundError):
                        loader(data_dir=tmp)

    def test_invalid_json_raises_data_load_error(self):
        tmp_dir = self.make_temp_dir()
        (tmp_dir / "cities.json").write_text("{ this is not json", encoding="utf-8")
        with self.assertRaises(DataLoadError) as ctx:
            load_cities(data_dir=tmp_dir)
        self.assertIn("JSON", str(ctx.exception))

    def test_missing_top_level_key_raises_data_load_error(self):
        tmp_dir = self.make_temp_dir()
        (tmp_dir / "cities.json").write_text(
            json.dumps({"unexpected": []}, ensure_ascii=False), encoding="utf-8"
        )
        with self.assertRaises(DataLoadError) as ctx:
            load_cities(data_dir=tmp_dir)
        self.assertIn("cities", str(ctx.exception))

    def test_wrong_type_for_records_raises_data_load_error(self):
        tmp_dir = self.make_temp_dir()
        (tmp_dir / "apps.json").write_text(
            json.dumps({"apps": "not-a-list"}, ensure_ascii=False), encoding="utf-8"
        )
        with self.assertRaises(DataLoadError):
            load_apps(data_dir=tmp_dir)

    def test_top_level_list_is_accepted(self):
        """兼容顶层直接是列表的写法。"""
        tmp_dir = self.make_temp_dir()
        (tmp_dir / "cities.json").write_text(
            json.dumps([{"city_id": "test-city", "city_name": "测试城市"}], ensure_ascii=False),
            encoding="utf-8",
        )
        cities = load_cities(data_dir=tmp_dir)
        self.assertEqual(len(cities), 1)
        self.assertEqual(get_city("test-city", data_dir=tmp_dir)["city_name"], "测试城市")


class TestDataIntegrity(unittest.TestCase):
    """跨文件的引用完整性检查，防止数据文件之间出现悬空 ID。"""

    def test_city_attraction_ids_exist(self):
        for city in load_cities():
            for attraction_id in city["attraction_ids"]:
                with self.subTest(city=city["city_id"], attraction_id=attraction_id):
                    self.assertIsNotNone(get_attraction(attraction_id))

    def test_city_app_ids_exist(self):
        for city in load_cities():
            for app_id in city["app_ids"]:
                with self.subTest(city=city["city_id"], app_id=app_id):
                    self.assertIsNotNone(get_app(app_id))

    def test_attraction_city_ids_exist(self):
        for attraction in load_attractions():
            with self.subTest(attraction=attraction["attraction_id"]):
                self.assertIsNotNone(get_city(attraction["city_id"]))

    def test_alternative_attraction_ids_exist(self):
        for attraction in load_attractions():
            for alt_id in attraction["alternative_attraction_ids"]:
                with self.subTest(attraction=attraction["attraction_id"], alt=alt_id):
                    self.assertIsNotNone(get_attraction(alt_id))

    def test_ids_are_unique(self):
        city_ids = [c["city_id"] for c in load_cities()]
        attraction_ids = [a["attraction_id"] for a in load_attractions()]
        app_ids = [a["app_id"] for a in load_apps()]

        self.assertEqual(len(city_ids), len(set(city_ids)), "city_id 出现重复")
        self.assertEqual(len(attraction_ids), len(set(attraction_ids)), "attraction_id 出现重复")
        self.assertEqual(len(app_ids), len(set(app_ids)), "app_id 出现重复")

    def test_sample_data_is_marked_as_sample(self):
        """每个数据文件的 _meta 都应标明这是示例数据。"""
        for filename in ("cities.json", "attractions.json", "apps.json"):
            with self.subTest(filename=filename):
                payload = json.loads((data_loader.DATA_DIR / filename).read_text(encoding="utf-8"))
                self.assertEqual(payload["_meta"]["data_type"], "sample")


if __name__ == "__main__":
    unittest.main(verbosity=2)
