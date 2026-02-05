import streamlit as st
from streamlit_folium import st_folium
import folium
import mysql.connector
import pandas as pd
import os
import json
import math
import warnings  # 👈 경고 메시지 제어를 위해 추가
from geopy.geocoders import Nominatim
from dotenv import load_dotenv

# --- 0. 불필요한 경고 및 출력 억제 ---
# Pandas의 SQLAlchemy 관련 UserWarning을 무시합니다.
warnings.filterwarnings('ignore', category=UserWarning)

# 1. 환경 설정 로드 (메시지 출력 제거)
load_dotenv('env')
geolocator = Nominatim(user_agent="parking_mate")

db_config_raw = os.getenv("DB_CONFIG")
if db_config_raw:
    DB_CONFIG = json.loads(db_config_raw)
    # print 문 제거 완료!
else:
    st.error("DB 설정 정보를 불러올 수 없습니다.")

# 세션 상태 초기화
if 'results' not in st.session_state:
    st.session_state['results'] = pd.DataFrame()
if 'page' not in st.session_state:
    st.session_state.page = 1


# 2. DB 조회 함수 (반경 기반)
def get_parking_data_by_coords(lat, lng, radius=3000):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        query = """
                SELECT name, \
                       lat, \
                       lng, \
                       full_address, \
                       space_no,
                       ST_Distance_Sphere(POINT(lng, lat), POINT(%s, %s)) AS distance
                FROM parking_lot
                HAVING distance <= %s
                ORDER BY distance
                """
        df = pd.read_sql(query, conn, params=(lng, lat, radius))
        conn.close()
        return df
    except Exception as e:
        st.error(f"DB 조회 중 오류: {e}")
        return pd.DataFrame()


# --- 레이아웃 설정 ---
st.set_page_config(layout="wide", page_title="Parking Mate")
st.title("🚗 Parking Mate")
st.write("---")

left_col, right_col = st.columns([1, 2])
df = st.session_state['results']

# --- 왼쪽 영역: 검색 결과 리스트 & 페이지네이션 ---
with left_col:
    st.subheader(f"🔍 검색 결과 ({len(df)}건)")
    st.radio("정렬", ["가까운순 ▼", "가격순 ▼", "공영"], horizontal=True)
    st.write("---")

    if not df.empty:
        items_per_page = 5
        total_pages = min(math.ceil(len(df) / items_per_page), 5)

        start_idx = (st.session_state.page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        df_page = df.iloc[start_idx:end_idx]

        for i, row in df_page.iterrows():
            st.markdown(f"""
            <div style="border:1px solid #ddd; padding:15px; border-radius:10px; margin-bottom:10px; background-color:white;">
                <h4 style="margin:0; color:black;">{row['name']}</h4>
                <p style="margin:5px 0; font-size:14px; color:#666;">📍 {row['full_address']}</p>
                <p style="margin:0; color:#007BFF; font-weight:bold;">🅿️ 주차면수: {row['space_no']}면</p>
            </div>
            """, unsafe_allow_html=True)

        st.write("---")
        cols = st.columns([1] * (total_pages + 2))
        for p in range(1, total_pages + 1):
            with cols[p]:
                btn_type = "primary" if st.session_state.page == p else "secondary"
                if st.button(str(p), key=f"p_{p}", type=btn_type, use_container_width=True):
                    st.session_state.page = p
                    st.rerun()
    else:
        st.info("오른쪽 검색창에서 가고 싶은 곳을 검색해 보세요!")

# --- 오른쪽 영역: 검색창 & 지도 ---
with right_col:
    with st.form(key='main_search_form'):
        search_input_col, search_btn_col = st.columns([5, 1])
        with search_input_col:
            target_location = st.text_input(label="검색어", placeholder="예: 강남역, 서초동", label_visibility="collapsed")
        with search_btn_col:
            search_submit = st.form_submit_button(label="검색")

    if search_submit:
        if target_location:
            with st.spinner(f"'{target_location}' 주변을 찾는 중..."):
                location = geolocator.geocode(target_location)
                if location:
                    # 1.5km 자동 반경 조절 로직 적용
                    df_results = get_parking_data_by_coords(location.latitude, location.longitude, 3000)
                    if len(df_results) > 25:
                        df_results = get_parking_data_by_coords(location.latitude, location.longitude, 1500)
                        st.info(f"💡 결과가 많아 가장 가까운 1.5km 이내 정보 위주로 보여드려요!")

                    st.session_state['results'] = df_results
                    st.session_state.page = 1
                    st.rerun()
                else:
                    st.warning("장소를 찾을 수 없습니다.")
        else:
            st.warning("검색어를 입력해 주세요.")

    # 지도 표시
    center_lat, center_lng = (df.iloc[0]['lat'], df.iloc[0]['lng']) if not df.empty else (37.5665, 126.9780)
    m = folium.Map(location=[center_lat, center_lng], zoom_start=14 if not df.empty else 12)

    for i, row in df.iterrows():
        folium.Marker(
            location=[row['lat'], row['lng']],
            popup=f"<b>{row['name']}</b><br>면수: {row['space_no']}면",
            icon=folium.Icon(color='orange', icon='info-sign')
        ).add_to(m)

    st_folium(m, width="100%", height=600, key="main_map")