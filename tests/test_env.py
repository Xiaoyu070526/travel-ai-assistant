"""基础环境测试：验证核心依赖可导入"""


def test_core_imports():
    import numpy  # noqa: F401
    import pandas  # noqa: F401
    import streamlit  # noqa: F401

    assert True


def test_utils_import():
    from src.utils.config import load_config  # noqa: F401

    assert True
