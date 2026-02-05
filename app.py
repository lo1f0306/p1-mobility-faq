#streamlit main page
import streamlit as st

# 페이지 정의
entry_p = st.Page("pages/01_entry_page.py", title="홈", icon="🏠", default=True)
nearby_parking_p = st.Page("pages/02_nearby_parkinglots.py", title="Parking Mate", icon="🅿️")
parking_by_region_p = st.Page("pages/03_prototype_category_app.py", title="Parking Lot by region", icon="🅿️")
search_gas_station_p =  st.Page("pages/04_search_gas_station.py", title="Gas Station Mate", icon="⛽")

# 내비게이션 실행
pg = st.navigation({'home':[entry_p], 'parking':[nearby_parking_p, parking_by_region_p], 'Gas Station':[search_gas_station_p]})
pg.run()