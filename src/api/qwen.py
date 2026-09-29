"""通义千问大模型 API 调用模块

``dashscope`` 采用延迟导入：仅在实际调用时导入，避免未安装该依赖时
整个应用在启动阶段就因导入失败而崩溃（Qwen 功能本身保持不变）。
"""

import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


def init_qwen():
    """初始化通义千问客户端（需环境变量 DASHSCOPE_API_KEY）"""
    import dashscope

    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()


def chat(prompt: str, model: str = "qwen-turbo") -> str:
    """调用通义千问对话模型，返回回复文本"""
    from dashscope import Generation

    if not os.getenv("DASHSCOPE_API_KEY"):
        raise ValueError("未配置 DASHSCOPE_API_KEY，请在 .env 中填写")
    init_qwen()
    response = Generation.call(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        result_format="message",
    )
    if response.status_code == 200:
        return response.output.choices[0].message.content
    raise RuntimeError(f"通义千问调用失败: {response.code} - {response.message}")


if __name__ == "__main__":
    print(chat("你好，请用一句话介绍杭州"))
