from dotenv import load_dotenv
import mysql.connector
import streamlit as st
import os
import json

from src.model import ParkingLot
from src.model import Destination

from src.utils import get_mbr_polygon

load_dotenv()

DB_CONFIG = json.loads(os.getenv('DB_CONFIG', '{}'))

@st.cache_resource
def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        st.error(f"Error: {err}")
        return None

def get_near_parking_data(dest: Destination):
    try:
        conn = get_connection()
        if not conn:
            return list()
        if not conn.is_connected():
            conn.reconnect(attempts=3, delay=2)
        delta = 0.023
        min_lat, max_lat = dest.lat - delta, dest.lat + delta
        min_lng, max_lng = dest.lng - delta, dest.lng + delta

        sql = '''SELECT id, reg_id, name, lat, lng, sido, sigungu, full_address, space_no, ST_Distance_Sphere(POINT(lng, lat), POINT(%s, %s)) as dist FROM parking_lot WHERE MBRContains(ST_GeomFromText(%s, 4326, 'axis-order=long-lat'), coord) ORDER BY dist LIMIT 100'''
        polygon_str = get_mbr_polygon(min_lng, min_lat, max_lng, max_lat)
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(sql, (dest.lng, dest.lat, polygon_str))
            rows = cursor.fetchall()
            if not rows: return list()
            print(ParkingLot)
            return [ParkingLot(row['id'], row['reg_id'], row['name'], row['lat'], row['lng'], row['sido'], row['sigungu'], row['full_address'], row['space_no'])for row in rows]

    except Exception as e:
        st.error(f"DB 연결 오류: {e}")
        return []

def get_parkinglots_by_region():
    return