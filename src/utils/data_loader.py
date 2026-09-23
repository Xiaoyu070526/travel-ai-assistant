"""数据读取模块（Day 3）。

从 ``data/processed/`` 目录读取城市、景点、App 三类 JSON 数据，
并提供按 ID 查询的辅助函数。

JSON 文件结构
-------------
三个数据文件都采用「元信息 + 数据列表」的结构::

    {
      "_meta": { ... },
      "cities": [ {...}, {...} ]
    }

``_meta`` 存放数据集的元信息（版本、数据来源说明、字段约定），
本模块的读取函数只返回数据列表部分，不返回 ``_meta``。
为了兼容后续可能出现的简单格式，若文件顶层直接是列表，也会被接受。

数据说明
--------
``data/processed/`` 下的数据目前均为 **示例数据（sample data）**，
仅用于打通开发与测试流程，**不包含任何真实的预订 / 预约信息**。
凡涉及真实世界事实的字段，一律留空而不做编造：

- ``reservation_required`` / ``entry_method`` / ``source_url`` 为 ``None``
- ``passport_booking_status`` 为 ``"unknown"``

错误处理
--------
- 数据文件不存在 -> :class:`DataFileNotFoundError`（``FileNotFoundError`` 的子类）
- JSON 格式非法、或顶层结构不符合约定 -> :class:`DataLoadError`
- 按 ID 查询时 ID 不存在 -> 返回 ``None``（或空列表），不抛异常
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = [
    "DATA_DIR",
    "DataLoadError",
    "DataFileNotFoundError",
    "load_cities",
    "get_city",
    "load_attractions",
    "get_attractions_by_city",
    "get_attraction",
    "load_apps",
    "get_app",
    "get_attractions_by_ids",
    "get_apps_by_ids",
]


# --------------------------------------------------------------------------- #
# 路径与常量
# --------------------------------------------------------------------------- #

#: 项目根目录下的 data/processed 目录（本文件位于 <root>/src/utils/data_loader.py）
DATA_DIR: Path = Path(__file__).resolve().parents[2] / "data" / "processed"

CITIES_FILE = "cities.json"
ATTRACTIONS_FILE = "attractions.json"
APPS_FILE = "apps.json"

# JSON 文件顶层的数据列表所对应的键名
_CITIES_KEY = "cities"
_ATTRACTIONS_KEY = "attractions"
_APPS_KEY = "apps"


# --------------------------------------------------------------------------- #
# 异常
# --------------------------------------------------------------------------- #


class DataLoadError(Exception):
    """数据加载失败：JSON 格式非法，或文件结构不符合约定。"""


class DataFileNotFoundError(DataLoadError, FileNotFoundError):
    """数据文件不存在。

    同时继承 :class:`FileNotFoundError`，调用方既可以按本模块的
    :class:`DataLoadError` 统一捕获，也可以按 Python 标准异常处理。
    """


# --------------------------------------------------------------------------- #
# 内部工具
# --------------------------------------------------------------------------- #


def _resolve_path(filename: str, data_dir: str | Path | None = None) -> Path:
    """把文件名解析为绝对路径，``data_dir`` 为空时使用默认的 :data:`DATA_DIR`。"""
    base = Path(data_dir) if data_dir is not None else DATA_DIR
    return base / filename


def _load_json_records(
    filename: str,
    data_key: str,
    data_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """读取一个数据文件并返回其中的记录列表。

    :param filename: 文件名，例如 ``"cities.json"``
    :param data_key: 该文件中记录列表对应的顶层键名，例如 ``"cities"``
    :param data_dir: 可选，自定义数据目录（便于测试）。默认使用 :data:`DATA_DIR`
    :raises DataFileNotFoundError: 文件不存在
    :raises DataLoadError: JSON 非法，或结构不符合约定
    """
    path = _resolve_path(filename, data_dir)

    if not path.is_file():
        raise DataFileNotFoundError(
            f"数据文件不存在：{path}\n"
            f"请确认数据文件已生成，或通过 data_dir 参数指定正确的目录。"
        )

    try:
        with path.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"数据文件不是合法的 JSON：{path}（{exc}）") from exc
    except OSError as exc:
        raise DataLoadError(f"读取数据文件失败：{path}（{exc}）") from exc

    # 兼容两种顶层写法：{"cities": [...]} 或直接 [...]
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        if data_key not in payload:
            raise DataLoadError(
                f"数据文件缺少顶层字段 {data_key!r}：{path}"
            )
        records = payload[data_key]
    else:
        raise DataLoadError(
            f"数据文件顶层应为对象或列表，实际为 {type(payload).__name__}：{path}"
        )

    if not isinstance(records, list):
        raise DataLoadError(
            f"顶层字段 {data_key!r} 应为列表，实际为 {type(records).__name__}：{path}"
        )

    return records


def _find_by_id(
    records: list[dict[str, Any]],
    id_field: str,
    id_value: Any,
) -> dict[str, Any] | None:
    """在记录列表中按指定 ID 字段查找，找到返回该记录，否则返回 ``None``。"""
    if id_value is None:
        return None

    for record in records:
        if isinstance(record, dict) and record.get(id_field) == id_value:
            return record
    return None


def _filter_by_id(
    records: list[dict[str, Any]],
    id_field: str,
    id_value: Any,
) -> list[dict[str, Any]]:
    """在记录列表中按指定 ID 字段筛选，返回所有匹配的记录。"""
    if id_value is None:
        return []

    return [
        record
        for record in records
        if isinstance(record, dict) and record.get(id_field) == id_value
    ]


# --------------------------------------------------------------------------- #
# 城市
# --------------------------------------------------------------------------- #


def load_cities(data_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """读取全部城市记录。

    :return: 城市字典组成的列表
    :raises DataFileNotFoundError: ``cities.json`` 不存在
    :raises DataLoadError: 文件内容非法
    """
    return _load_json_records(CITIES_FILE, _CITIES_KEY, data_dir)


def get_city(
    city_id: str,
    data_dir: str | Path | None = None,
) -> dict[str, Any] | None:
    """按 ``city_id`` 查询单个城市。

    :return: 城市字典；找不到该 ID 时返回 ``None``
    """
    return _find_by_id(load_cities(data_dir), "city_id", city_id)


# --------------------------------------------------------------------------- #
# 景点
# --------------------------------------------------------------------------- #


def load_attractions(data_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """读取全部景点记录。

    :return: 景点字典组成的列表
    :raises DataFileNotFoundError: ``attractions.json`` 不存在
    :raises DataLoadError: 文件内容非法
    """
    return _load_json_records(ATTRACTIONS_FILE, _ATTRACTIONS_KEY, data_dir)


def get_attractions_by_city(
    city_id: str,
    data_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """查询某个城市下的全部景点。

    :return: 景点字典列表；该城市没有景点或 ID 不存在时返回空列表
    """
    return _filter_by_id(load_attractions(data_dir), "city_id", city_id)


def get_attraction(
    attraction_id: str,
    data_dir: str | Path | None = None,
) -> dict[str, Any] | None:
    """按 ``attraction_id`` 查询单个景点。

    :return: 景点字典；找不到该 ID 时返回 ``None``
    """
    return _find_by_id(load_attractions(data_dir), "attraction_id", attraction_id)


def get_attractions_by_ids(
    attraction_ids: list[str] | None,
    data_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """按 ID 列表批量查询景点，用于展开 ``city["attraction_ids"]``。

    返回顺序与传入的 ID 顺序一致；不存在的 ID 会被跳过。
    """
    if not attraction_ids:
        return []

    index = {
        record.get("attraction_id"): record
        for record in load_attractions(data_dir)
        if isinstance(record, dict)
    }
    return [index[aid] for aid in attraction_ids if aid in index]


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #


def load_apps(data_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """读取全部 App 记录。

    :return: App 字典组成的列表
    :raises DataFileNotFoundError: ``apps.json`` 不存在
    :raises DataLoadError: 文件内容非法
    """
    return _load_json_records(APPS_FILE, _APPS_KEY, data_dir)


def get_app(
    app_id: str,
    data_dir: str | Path | None = None,
) -> dict[str, Any] | None:
    """按 ``app_id`` 查询单个 App。

    :return: App 字典；找不到该 ID 时返回 ``None``
    """
    return _find_by_id(load_apps(data_dir), "app_id", app_id)


def get_apps_by_ids(
    app_ids: list[str] | None,
    data_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """按 ID 列表批量查询 App，用于展开 ``city["app_ids"]``。

    返回顺序与传入的 ID 顺序一致；不存在的 ID 会被跳过。
    """
    if not app_ids:
        return []

    index = {
        record.get("app_id"): record
        for record in load_apps(data_dir)
        if isinstance(record, dict)
    }
    return [index[aid] for aid in app_ids if aid in index]
