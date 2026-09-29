import sys
import os
from dotenv import load_dotenv


def check_environment():
    print("=" * 40)
    print("旅游AI助手开发环境检查报告")
    print("=" * 40)

    # 1. Python版本检查
    print(f"[Python] 当前版本: {sys.version}")
    assert sys.version_info.major == 3 and sys.version_info.minor == 10, "Python版本必须为3.10"

    # 2. 依赖包版本检查
    try:
        import streamlit, pandas, numpy, dashscope, gradio, plotly, matplotlib, sklearn
        print(f"[Streamlit] 版本: {streamlit.__version__}")
        print(f"[Pandas] 版本: {pandas.__version__}")
        print(f"[NumPy] 版本: {numpy.__version__}")
        print(f"[Dashscope] 版本: {getattr(dashscope, '__version__', '（无版本属性）')}")
        print("[依赖包] 所有核心依赖安装成功")
    except ImportError as e:
        print(f"[错误] 缺少依赖包: {e}")
        return False

    # 3. .env文件检查
    if os.path.exists(".env"):
        print("[.env] 环境变量文件存在")
        load_dotenv()
    else:
        print("[警告] 未找到 .env 文件")
        return False

    # 4. API Key配置检查
    qwen_key = os.getenv("DASHSCOPE_API_KEY")
    amap_key = os.getenv("AMAP_MAP_KEY")

    if qwen_key:
        print("[通义千问API] Key已配置")
    else:
        print("[警告] 未配置 DASHSCOPE_API_KEY")

    if amap_key:
        print("[高德地图API] Key已配置")
    else:
        print("[警告] 未配置 AMAP_MAP_KEY")

    print("=" * 40)
    print("环境检查完成！")
    return True


if __name__ == "__main__":
    check_environment()