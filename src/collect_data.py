import requests
# mysql-connector
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

# mysql-connection 정보
config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'skn26',
    'password': 'skn26',
    'database':'menudb'
}

class ParkingLot:
    def __init__(self, id: int ,reg_id: str, name: str, lat: str, lng: str, sido: str, sigungu: str, full_addr: str, space_no: int, coord: float = None):
        self.__id = id
        self.__reg_id = reg_id
        self.__name = name
        self.__lat = lat
        self.__lng = lng
        self.__sido = sido
        self.__sigungu = sigungu
        self.__full_addr = full_addr
        self.__space_no = int(space_no)
        self.__coord = coord

    @property
    def id(self):
        return self.__id

    @property
    def reg_id(self):
        return self.__reg_id

    @property
    def name(self):
        return self.__name

    @property
    def lat(self):
        return self.__lat

    @property
    def lng(self):
        return self.__lng

    @property
    def sido(self):
        return self.__sido

    @property
    def sigungu(self):
        return self.__sigungu

    @property
    def full_addr(self):
        return self.__full_addr

    @property
    def space_no(self):
        return self.__space_no

    @property
    def coord(self):
        return self.__coord

    def __repr__(self):
        return f'ParkingLot:{self.__id}, {self.__reg_id}, {self.__name}, {self.__lat}, {self.__lng}, {self.__sido}, {self.__sigungu}, {self.__full_addr}'


API_KEY = os.getenv(("API_KEY"))
BASE_URL = 'https://apis.data.go.kr/B553881/Parking/PrkSttusInfo'

params = {'serviceKey':API_KEY, 'pageNo':1,'numOfRows':2000, 'format':2}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01'
}
response = requests.get(url=BASE_URL, params=params, headers=headers)

parking_lots_list: list[ParkingLot] = []
if response.status_code == 200:
    parking_lots = response.json()["PrkSttusInfo"] #주차장 리스트
    # print(parking_lots)
    # print(len(parking_lots))

    if len(parking_lots) > 0:
        for parking_lot in parking_lots:
            parking_lots_list.append(ParkingLot(None, parking_lot['prk_center_id'], parking_lot['prk_plce_nm'], parking_lot['prk_plce_entrc_la'], parking_lot['prk_plce_entrc_lo'], parking_lot['prk_plce_adres_sido'], parking_lot['prk_plce_adres_sigungu'], parking_lot['prk_plce_adres'], parking_lot['prk_cmprt_co'], None))

else:
    print('PROBLEM', response.status_code, response.text)
print(parking_lots_list)

if len(parking_lots_list) > 0:
    try:
        with mysql.connector.connect(**config) as conn:
            with conn.cursor() as cursor:
                for parking_lot in parking_lots_list:
                    cursor.execute('''
                        insert
                          into parkinglot (id
                                          , reg_id
                                          , name
                                          , lat
                                          , lng
                                          , sido
                                          , sigungu
                                          , full_address
                                          , space_no
                                        )
                        values ( %s
                               , %s
                               , %s
                               , %s
                               , %s
                               , %s
                               , %s
                               , %s
                               , %s
                               )
                    ''', (None ,parking_lot.reg_id, parking_lot.name, parking_lot.lat, parking_lot.lng, parking_lot.sido, parking_lot.sigungu, parking_lot.full_addr, parking_lot.space_no))
                conn.commit()
    except mysql.connector.Error as err:
        print('DB에러: ', err)