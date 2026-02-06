import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster
import math
import os
import requests
import urllib
from pyproj import Transformer
from geopy.geocoders import Nominatim
from dotenv import load_dotenv

from src.db_crud import get_near_parking_data
from src.utils import find_address_and_point
from folium.plugins import MarkerCluster

ITEMS_PER_PAGE = 4

# 1. 환경 설정 및 API 키 로드 (주유소)
load_dotenv()
OPINET_KEY = os.getenv("OPINET")

# 좌표 변환기 설정 (WGS84 <-> KATEC)
KATEC_STR = "+proj=tmerc +lat_0=38 +lon_0=128 +k=0.9999 +x_0=400000 +y_0=600000 +ellps=bessel +units=m +no_defs +towgs84=-115.80,483.35,664.43,0,0,0,0"
WGS84_STR = "epsg:4326"

to_katec = Transformer.from_crs(WGS84_STR, KATEC_STR, always_xy=True)
to_wgs84 = Transformer.from_crs(KATEC_STR, WGS84_STR, always_xy=True)

# 주소 -> 위경도 변환기 (Nominatim 사용)
geolocator = Nominatim(user_agent="gas_station_mate")

BRAND_MAP = {
    'SKE': 'SK에너지', 'GSC': 'GS칼텍스', 'HDO': '현대오일뱅크',
    'SOL': 'S-OIL', 'RTE': '자영알뜰', 'RTX': '고속도로알뜰',
    'NHO': '농협알뜰', 'ETC': '자가상표', 'E1G': 'E1', 'SKG': 'SK가스', 'RTO': '자영알뜰'
}

# 2. 페이지 설정
st.set_page_config(layout="wide", page_title="Parking & Gas Mate")

# 글자 깨짐 등 해결
st.markdown("""
    <style>
    /* 버튼 내부 글자 줄바꿈 방지 */
    div.stButton > button p {
        white-space: nowrap !important;
        font-size: 14px !important;
    }
    /* 버튼 간격 및 최소 너비 최적화 */
    div.stButton > button {
        min-width: 35px !important; 
        width: 100% !important;
        padding: 0px !important;
        margin: 0px 2px !important; 
    }
    /* 컬럼 간격 미세 조정 */
    [data-testid="column"] {
        padding-left: 1px !important;
        padding-right: 1px !important;
    }
    </style>
""", unsafe_allow_html=True)

# 3. 세션 상탸 초기화
if 'parking_results' not in st.session_state:  # 주차장 조회 결과 저장
    st.session_state.parking_results = []

if 'oil_results' not in st.session_state:  # 주유소 조회 결과 저장
    st.session_state.oil_results = []

if 'map_center' not in st.session_state:  # 지도 표시 위치 초기화
    st.session_state.map_center = [37.5665, 126.9780]  # 서울 시청 기준

if "current_page" not in st.session_state:  # 리스트에서 현재 탐색중인 페이지
    st.session_state.current_page = 1

if "destination" not in st.session_state:  # 검색 결과
    st.session_state.destination = None


# 4. 데이터 호출 함수
def get_oil_stations(lat, lon, radius=3000):
    kx, ky = to_katec.transform(lon, lat)
    url = "https://www.opinet.co.kr/api/aroundAll.do"
    params = {
        "code": OPINET_KEY,
        "out": "json",
        "x": kx,
        "y": ky,
        "radius": radius,
        "prodcd": "B027",  # 휘발유 기준
        "sort": 2  # 거리순
    }
    try:
        res = requests.get(url, params=params)
        data = res.json()
        stations = data.get('RESULT', {}).get('OIL', [])

        for s in stations:
            s['lng'], s['lat'] = to_wgs84.transform(s['GIS_X_COOR'], s['GIS_Y_COOR'])
            s['brand_nm'] = BRAND_MAP.get(s['POLL_DIV_CD'], '기타')
        return stations
    except Exception as e:
        st.error(f"오피넷 API 오류: {e}")
        return []

# todo: 주차장 리스트 표시
def parking_spot(page_data_parking):
    for parking_lot in page_data_parking:
        with st.container():
            st.markdown(f"""
            <div style="border:1px solid #ddd; padding:15px; border-radius:10px; margin-bottom:10px; background-color:white;">
                <h4 style="margin:0; color:black;">{parking_lot.name}</h4>
                <p style="margin:5px 0; font-size:14px; color:#666;">📍 {parking_lot.full_addr}</p>
                <p style="margin:0; color:#007BFF; font-weight:bold;">🅿️ 주차면수: {parking_lot.space_no}면</p>
            </div>
            """, unsafe_allow_html=True)

# todo: 주유소 리스트 표시
def oil_spot(oil_data_parking):
    for s in page_data_oil:
        with st.container():
            st.markdown(f"""
                    <div style="border:1px solid #ddd; padding:15px; border-radius:10px; margin-bottom:10px; background-color:white;">
                        <h4 style="margin:0; color:#333;">{s['OS_NM']} <small style="color:#666;">({s['brand_nm']})</small></h4>
                        <p style="margin:5px 0; font-size:16px; color:#ff4b4b; font-weight:bold;">가격: {int(s['PRICE']):,}원</p>
                        <p style="margin:0; font-size:13px; color:#666;">📏 거리: {s['DISTANCE']}m</p>
                    </div>
                    """, unsafe_allow_html=True)


# 4. 상단 로고 (검색바는 아래 right_col로 이동)
st.title("🚗 Parking & Oil Mate ⛽")
st.write("---")
st.subheader(
    f"🔍 검색 결과 주차장: ({len(st.session_state.parking_results) if len(st.session_state.parking_results) > 0 else 0}건) | "
    f"주유소: ({len(st.session_state.oil_results) if len(st.session_state.oil_results) > 0 else 0}건)")

print(len(st.session_state.parking_results))
print(len(st.session_state.oil_results))

# 5. 메인 레이아웃 분할: 왼쪽(리스트) | 오른쪽(검색창 + 지도)
left_col, right_col = st.columns([1, 2])

# --- 왼쪽 영역: 검색 결과 리스트 ---
with left_col:
    option = st.radio("", ["전체", "주차장", "주유소"], horizontal=True)
    if st.session_state.parking_results or st.session_state.oil_results:
        total_items = len(st.session_state.parking_results) + len(st.session_state.oil_results)
        total_pages = math.ceil(total_items / ITEMS_PER_PAGE)

        current_group = (st.session_state.current_page - 1) // 5
        start_page = current_group * 5 + 1
        end_page = min(start_page + 4, total_pages)

        start_idx = (st.session_state.current_page - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE

        page_data_parking = sorted(st.session_state.parking_results, key=lambda x: x.name)[start_idx:end_idx]
        page_data_oil = st.session_state.oil_results[start_idx:end_idx]

        if option == "전체":
            parking_spot(page_data_parking)
            oil_spot(page_data_oil)
        if option == "주차장":
            parking_spot(page_data_parking)
        if option == "주유소":
            oil_spot(page_data_oil)

        st.write("---")

        # [3] 화살표 + 숫자 5개 버튼 UI (겹침 방지 비율 적용)
        page_cols = st.columns([1.1, 1, 1, 1, 1, 1, 1.5])

        with page_cols[0]:
            if current_group > 0:
                if st.button("◀", key="prev_group"):
                    st.session_state.current_page = start_page - 1
                    st.rerun()

        for i, p in enumerate(range(start_page, end_page + 1)):
            with page_cols[i + 1]:
                btn_type = "primary" if st.session_state.current_page == p else "secondary"
                if st.button(str(p), key=f"p_{p}", type=btn_type, use_container_width=True):
                    st.session_state.current_page = p
                    st.rerun()

        with page_cols[6]:
            if end_page < total_pages:
                if st.button("▶", key="next_group"):
                    st.session_state.current_page = end_page + 1
                    st.rerun()
    else:
        st.info("오른쪽 검색창에서 가고 싶은 곳을 검색해 보세요!")

# --- 오른쪽 영역: 검색창(상단) + 지도(하단) ---
with right_col:
    # 지도 너비에 맞춘 단일 검색 폼
    with st.form(key='main_search_form'):
        search_input_col, search_btn_col = st.columns([5, 1])
        with search_input_col:
            target_location = st.text_input(
                label="검색어 입력",
                placeholder="어디로 가시나요? (예: 강남역)",
                label_visibility="collapsed"
            )
        with search_btn_col:
            search_submit = st.form_submit_button(label="검색")

    # 검색 로직 실행
    if search_submit:
        if target_location:
            with st.spinner('데이터를 불러오는 중...'):
                dest = find_address_and_point(target_location)
                st.session_state.destination = dest
                parking_lots = get_near_parking_data(dest)
                st.session_state.parking_results = parking_lots
                found_stations = get_oil_stations(dest.lat, dest.lng)
                st.session_state.oil_results = found_stations
                st.rerun()  # 데이터를 세션에 넣은 후 화면 즉시 갱신
        else:
            st.warning("검색어를 입력해 주세요.")

    # 지도 표시 로직
    # todo: 전체를 선택했을 때 map 표시 (parking(하늘색 마커) + oil(초록색 마커))
    if option == "전체":
        if st.session_state.parking_results or st.session_state.oil_results:
            # 데이터가 있을 때 첫 번째 검색 결과 위치로 이동
            center_lat = st.session_state.parking_results[0].lat
            center_lng = st.session_state.parking_results[0].lng
            zoom_level = 14
        else:
            center_lat, center_lng = 37.5665, 126.9780  # 서울 기본 위치
            zoom_level = 12

        m = folium.Map(location=[center_lat, center_lng], zoom_start=zoom_level)
        cluster = MarkerCluster().add_to(m)
        # 목적지 마커 추가
        if st.session_state.destination:
            dest = st.session_state.destination
            folium.Marker(
                location=[dest.lat, dest.lng],
                icon=folium.Icon(color="red", icon="star")
            ).add_to(m)

        # 주차장 마커 추가
        for parking_lot in st.session_state.parking_results:
            # 1. 길찾기를 위한 출발지 정보 (검색창에 입력한 위치)
            if st.session_state.destination:
                # 주소 전체보다는 사용자가 검색한 명칭이 가독성이 좋습니다.
                raw_start_name = st.session_state.destination.name if st.session_state.destination.name else "내 목적지"
                start_lat = st.session_state.destination.lat
                start_lon = st.session_state.destination.lng
            else:
                raw_start_name = "내 목적지"
                start_lat, start_lon = center_lat, center_lng

            # 2. 안전한 URL 생성을 위한 인코딩 처리
            s_name = urllib.parse.quote(raw_start_name)
            e_name = urllib.parse.quote(parking_lot.name)

            # 카카오맵 길찾기 'dir' 파라미터 구성
            # sp: 출발지 좌표 및 이름, ep: 목적지 좌표 및 이름
            kakao_dir_url = (
                f"https://map.kakao.com/link/from/{s_name},{start_lat},{start_lon}"
                f"/to/{e_name},{parking_lot.lat},{parking_lot.lng}"
            )

            popup_html = f"""
                <div style="width:220px; font-family: 'Nanum Gothic', sans-serif; line-height:1.5;">
                    <h4 style="margin:0 0 5px 0; color:#333;">{parking_lot.name}</h4>
                    <div style="font-size:13px; color:#666; margin-bottom:10px;">
                        <b>📍 주소:</b> {parking_lot.full_addr}<br>
                        <b>🅿️ 주차면수:</b> <span style="color:#007BFF; font-weight:bold;">{parking_lot.space_no}면</span>
                    </div>
                    <a href="{kakao_dir_url}" target="_blank" 
                       style="display:block; text-align:center; padding:8px; background-color:#FAE100; color:#3C1E1E; text-decoration:none; border-radius:5px; font-size:13px; font-weight:bold;">
                       🚕 자동으로 길찾기 시작
                    </a>
                </div>
                """

            folium.Marker(
                location=[parking_lot.lat, parking_lot.lng],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(cluster)

        # 주유소 마커 추가
        for oil_lot in st.session_state.oil_results:
            # 출발지 정보: 사용자가 검색한 주소와 좌표
            # 목적지 정보: 주유소 이름과 좌표
            start_name = target_location if target_location else "내 검색 위치"
            start_lat, start_lon = st.session_state['map_center']

            # 카카오맵 길찾기 'dir' 파라미터 구성
            # sp: 출발지 좌표 및 이름, ep: 목적지 좌표 및 이름
            kakao_dir_url = (
                f"https://map.kakao.com/link/from/{start_name},{start_lat},{start_lon}"
                f"/to/{oil_lot['OS_NM']},{oil_lot['lat']},{oil_lot['lng']}"
            )

            popup_html = f"""
                        <div style="width:220px; font-family: 'Nanum Gothic', sans-serif; line-height:1.5;">
                            <h4 style="margin:0 0 5px 0; color:#333;">{oil_lot['OS_NM']}</h4>
                            <div style="font-size:13px; color:#666; margin-bottom:10px;">
                                <b>💰 가격:</b> <span style="color:#ff4b4b; font-weight:bold;">{int(oil_lot['PRICE']):,}원</span><br>
                                <b>™️ 브랜드:</b> {oil_lot['brand_nm']}<br>
                                <b>📏 거리:</b> {oil_lot['DISTANCE']}m
                            </div>
                            <a href="{kakao_dir_url}" target="_blank" 
                               style="display:block; text-align:center; padding:8px; background-color:#FAE100; color:#3C1E1E; text-decoration:none; border-radius:5px; font-size:13px; font-weight:bold;">
                               🚕 자동으로 길찾기 시작
                            </a>
                        </div>
                        """

            folium.Marker(
                location=[oil_lot['lat'], oil_lot['lng']],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color='green', icon='tint', prefix='fa')
            ).add_to(cluster)

    # todo: '주차장' 선택했을 때 map 표시 (parking, 파란색 마커)
    if option == '주차장':
        if st.session_state.parking_results and len(st.session_state.parking_results) > 0:
            # 데이터가 있을 때 첫 번째 검색 결과 위치로 이동
            center_lat = st.session_state.parking_results[0].lat
            center_lng = st.session_state.parking_results[0].lng
            zoom_level = 14
        else:
            center_lat, center_lng = 37.5665, 126.9780  # 서울 기본 위치
            zoom_level = 12

        m = folium.Map(location=[center_lat, center_lng], zoom_start=zoom_level)
        cluster = MarkerCluster().add_to(m)
        # 목적지 마커 추가
        if st.session_state.destination:
            dest = st.session_state.destination
            folium.Marker(
                location=[dest.lat, dest.lng],
                icon=folium.Icon(color="red", icon="star")
            ).add_to(m)

        # 주차장 마커 추가
        for parking_lot in st.session_state.parking_results:
            # 1. 길찾기를 위한 출발지 정보 (검색창에 입력한 위치)
            if st.session_state.destination:
                # 주소 전체보다는 사용자가 검색한 명칭이 가독성이 좋습니다.
                raw_start_name = st.session_state.destination.name if st.session_state.destination.name else "내 목적지"
                start_lat = st.session_state.destination.lat
                start_lon = st.session_state.destination.lng
            else:
                raw_start_name = "내 목적지"
                start_lat, start_lon = center_lat, center_lng

            # 2. 안전한 URL 생성을 위한 인코딩 처리
            s_name = urllib.parse.quote(raw_start_name)
            e_name = urllib.parse.quote(parking_lot.name)

            # 카카오맵 길찾기 'dir' 파라미터 구성
            # sp: 출발지 좌표 및 이름, ep: 목적지 좌표 및 이름
            kakao_dir_url = (
                f"https://map.kakao.com/link/from/{s_name},{start_lat},{start_lon}"
                f"/to/{e_name},{parking_lot.lat},{parking_lot.lng}"
            )

            popup_html = f"""
                <div style="width:220px; font-family: 'Nanum Gothic', sans-serif; line-height:1.5;">
                    <h4 style="margin:0 0 5px 0; color:#333;">{parking_lot.name}</h4>
                    <div style="font-size:13px; color:#666; margin-bottom:10px;">
                        <b>📍 주소:</b> {parking_lot.full_addr}<br>
                        <b>🅿️ 주차면수:</b> <span style="color:#007BFF; font-weight:bold;">{parking_lot.space_no}면</span>
                    </div>
                    <a href="{kakao_dir_url}" target="_blank" 
                       style="display:block; text-align:center; padding:8px; background-color:#FAE100; color:#3C1E1E; text-decoration:none; border-radius:5px; font-size:13px; font-weight:bold;">
                       🚕 자동으로 길찾기 시작
                    </a>
                </div>
                """

            folium.Marker(
                location=[parking_lot.lat, parking_lot.lng],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(cluster)

    # todo: '주유소' 선택했을 때 map 표시 (oil, 초록색 마커)
    if option == '주유소':
        if st.session_state.parking_results or st.session_state.oil_results:
            # 데이터가 있을 때 첫 번째 검색 결과 위치로 이동
            center_lat = st.session_state.parking_results[0].lat
            center_lng = st.session_state.parking_results[0].lng
            zoom_level = 14
        else:
            center_lat, center_lng = 37.5665, 126.9780  # 서울 기본 위치
            zoom_level = 12

        m = folium.Map(location=[center_lat, center_lng], zoom_start=zoom_level)
        cluster = MarkerCluster().add_to(m)
        # 목적지 마커 추가
        if st.session_state.destination:
            dest = st.session_state.destination
            folium.Marker(
                location=[dest.lat, dest.lng],
                icon=folium.Icon(color="red", icon="star")
            ).add_to(m)

        # 주유소 마커 추가
        for oil_lot in st.session_state.oil_results:
            # 출발지 정보: 사용자가 검색한 주소와 좌표
            # 목적지 정보: 주유소 이름과 좌표
            start_name = target_location if target_location else "내 검색 위치"
            start_lat, start_lon = st.session_state['map_center']

            # 카카오맵 길찾기 'dir' 파라미터 구성
            # sp: 출발지 좌표 및 이름, ep: 목적지 좌표 및 이름
            kakao_dir_url = (
                f"https://map.kakao.com/link/from/{start_name},{start_lat},{start_lon}"
                f"/to/{oil_lot['OS_NM']},{oil_lot['lat']},{oil_lot['lng']}"
            )

            popup_html = f"""
                        <div style="width:220px; font-family: 'Nanum Gothic', sans-serif; line-height:1.5;">
                            <h4 style="margin:0 0 5px 0; color:#333;">{oil_lot['OS_NM']}</h4>
                            <div style="font-size:13px; color:#666; margin-bottom:10px;">
                                <b>💰 가격:</b> <span style="color:#ff4b4b; font-weight:bold;">{int(oil_lot['PRICE']):,}원</span><br>
                                <b>™️ 브랜드:</b> {oil_lot['brand_nm']}<br>
                                <b>📏 거리:</b> {oil_lot['DISTANCE']}m
                            </div>
                            <a href="{kakao_dir_url}" target="_blank" 
                               style="display:block; text-align:center; padding:8px; background-color:#FAE100; color:#3C1E1E; text-decoration:none; border-radius:5px; font-size:13px; font-weight:bold;">
                               🚕 자동으로 길찾기 시작
                            </a>
                        </div>
                        """

            folium.Marker(
                location=[oil_lot['lat'], oil_lot['lng']],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color='green', icon='tint', prefix='fa')
            ).add_to(cluster)

    st_folium(m, width="100%", height=600, key="main_map", returned_objects=[])




