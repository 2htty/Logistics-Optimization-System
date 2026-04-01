import streamlit as st
import networkx as nx
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import requests
import altair as alt

# 頁面設定
st.set_page_config(page_title="智慧物流：多站點計算器", layout="wide")
st.title("智慧物流：多站點路徑分析系統")

# 初始化
if 'stop_count' not in st.session_state:
    st.session_state.stop_count = 0

# 地點
locations = {
    "台北轉運站": [25.049, 121.517],
    "內湖科學園區": [25.082, 121.571],
    "板橋車站": [25.013, 121.462],
    "南港展覽館": [25.055, 121.616],
    "新莊副都心": [25.061, 121.443],
    "桃園物流中心": [24.993, 121.301],
    "信義商圈": [25.033, 121.564]
}

# 圖
G = nx.Graph()
edges = [
    ("台北轉運站", "內湖科學園區", 15), ("台北轉運站", "板橋車站", 10),
    ("內湖科學園區", "南港展覽館", 8), ("板橋車站", "新莊副都心", 12),
    ("新莊副都心", "桃園物流中心", 25), ("台北轉運站", "信義商圈", 8),
    ("信義商圈", "南港展覽館", 15), ("信義商圈", "板橋車站", 12)
]
G.add_weighted_edges_from(edges)

# 道路API 
def get_real_route(start_coord, end_coord):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{start_coord[1]},{start_coord[0]};{end_coord[1]},{end_coord[0]}?overview=full&geometries=geojson"
        response = requests.get(url).json()
        if response.get('routes'): 
            return response['routes'][0]['geometry']['coordinates']
    except: 
        return None
    return None

# 側邊欄
st.sidebar.header("配送路徑設定")
all_locs = list(locations.keys())

# 起點站
start_node = st.sidebar.selectbox("起點站", all_locs, key="start")
route_selection = [start_node]

# 停靠站 (排除已選地點)
for i in range(st.session_state.stop_count):
    available_options = [loc for loc in all_locs if loc not in route_selection]
    if available_options:
        stop = st.sidebar.selectbox(f"停靠站 {i+1}", available_options, key=f"stop_{i}")
        route_selection.append(stop)
    else:
        st.sidebar.warning(f"停靠站 {i+1}: 無更多可用地點")

# 最終終點站 (排除已選地點)
available_final_options = [loc for loc in all_locs if loc not in route_selection]
if available_final_options:
    end_node = st.sidebar.selectbox("最終終點站", available_final_options, key="end")
    route_selection.append(end_node)
else:
    st.sidebar.error("已無剩餘地點可作為終點")
    route_selection.append(None)

# 增減
col_btn1, col_btn2 = st.sidebar.columns(2)
with col_btn1:
    if st.button("➕ 新增停靠站"):
        st.session_state.stop_count += 1
        st.rerun()
with col_btn2:
    if st.button("➖ 減少停靠站") and st.session_state.stop_count > 0:
        st.session_state.stop_count -= 1
        st.rerun()

run_optimization = st.sidebar.button("執行路徑計算", type="primary")

# 路段時間分析
full_path_nodes = []
all_road_points = []
leg_labels = [] 
leg_times = []  

if run_optimization and None not in route_selection:
    try:
        for i in range(len(route_selection)-1):
            u, v = route_selection[i], route_selection[i+1]
            path_segment = nx.dijkstra_path(G, u, v, weight='weight')
            
            # 記錄節點
            if i == 0: full_path_nodes.extend(path_segment)
            else: full_path_nodes.extend(path_segment[1:])
            
            # 記錄各路段時間
            for j in range(len(path_segment)-1):
                node_a, node_b = path_segment[j], path_segment[j+1]
                t = G[node_a][node_b]['weight']
                leg_times.append(t)
                leg_labels.append(f"{node_a} ➔ {node_b}")

            # 真實道路API
            route_points = get_real_route(locations[u], locations[v])
            if route_points: 
                all_road_points.extend([[p[1], p[0]] for p in route_points])
                
    except Exception as e:
        st.error(f"路徑計算失敗：某些地點間在圖中無連通。")

# 畫面
col_map, col_chart = st.columns([1, 1])

with col_map:
    st.subheader("配送路徑地圖")
    # 初始化台北地圖
    m = folium.Map(location=[25.045, 121.53], zoom_start=11,
                   tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google Maps')
    
    # 畫出所有地點標籤
    for name, coord in locations.items():
        # 如果是被選中的地點，圖標換成紅色
        icon_color = "red" if name in route_selection else "blue"
        folium.Marker(coord, tooltip=name, icon=folium.Icon(color=icon_color)).add_to(m)
    
    # 畫出紅色的真實路徑線
    if all_road_points:
        folium.PolyLine(all_road_points, color="#FF4B4B", weight=6, opacity=0.8).add_to(m)
    
    st_folium(m, width=700, height=500, returned_objects=[])

with col_chart:
    st.subheader("路段時間分析")
    if run_optimization and leg_times:
        st.success(f"最佳路徑總耗時：{sum(leg_times)} 分鐘")
        
        # 建立圖表資料
        chart_df = pd.DataFrame({
            "路段": leg_labels,
            "耗時(分)": leg_times,
            "order": range(len(leg_labels))
        })
        
        # 使用 Altair 繪製長條圖
        chart = alt.Chart(chart_df).mark_bar(color='#52A1FF').encode(
            x=alt.X('路段:N', 
                  sort=alt.EncodingSortField(field="order", order="ascending"), 
                  axis=alt.Axis(labelAngle=-45, labelOverlap=False, labelFontSize=12, title="配送路段順序")),
            y=alt.Y('耗時(分):Q', title="單段行駛時間 (分鐘)"),
            tooltip=['路段', '耗時(分)']
        ).properties(height=400)

        st.altair_chart(chart, use_container_width=True)
        
        # 數據總結
        st.metric("預計總時程", f"{sum(leg_times)} min", "Dijkstra 演算法結果")
        st.markdown("### 詳細行經節點")
        st.write(" ➔ ".join(full_path_nodes))
    else:
        st.info(" 請在左側設定配送點，並點擊「執行路徑計算」按鈕。")

