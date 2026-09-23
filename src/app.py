import streamlit as st

st.set_page_config(
    page_title="AI入境旅游搭子",
    page_icon="✈️",
    layout="centered",
)

st.title("✈️ AI入境旅游搭子")
st.write("你好！我是你的 AI 入境旅游搭子。")

st.divider()

city = st.text_input(
    "你想去哪个城市？",
    placeholder="例如：北京",
)

if st.button("开始探索", type="primary"):
    if city.strip():
        st.session_state["city"] = city.strip()
    else:
        st.warning("请先输入城市。")

if "city" in st.session_state:
    selected_city = st.session_state["city"]

    st.subheader(f"📍 {selected_city}")

    st.success(f"正在为你准备「{selected_city}」的旅行信息！")

    st.markdown("### 🗺️ {0}怎么玩".format(selected_city))
    st.write("这里将显示 AI 生成的城市玩法、景点推荐和行程建议。")

    st.markdown("### 📱 App 清单")
    st.write("这里将显示入境旅行需要使用的 App。")

    st.info("目前是 Day 2 UI 测试版本，AI 接口将在后续接入。")
