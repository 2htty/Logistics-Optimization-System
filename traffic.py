import streamlit as st

st.title("🚛 智慧物流路徑規劃系統")
start_point = st.sidebar.selectbox("起點", ["台北車站", "西門町", "公館"])
end_point = st.sidebar.selectbox("終點", ["內湖科學園區", "南港展覽館"])

if st.button("計算最優路徑"):
    # 這裡放你的 Queue 演算法
    path = my_algorithm(start_point, end_point)
    st.success(f"建議路徑：{path}")
    st.info("演算法核心：使用 Priority Queue 實作 Dijkstra 最佳化")