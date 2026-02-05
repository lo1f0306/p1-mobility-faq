class ParkingLot:
    def __init__(self, id: int ,reg_id: str, name: str, lat: str, lng: str, sido: str, sigungu: str, full_addr: str, space_no: int):
        self.__id = id
        self.__reg_id = reg_id
        self.__name = name
        self.__lat = lat
        self.__lng = lng
        self.__sido = sido
        self.__sigungu = sigungu
        self.__full_addr = full_addr
        self.__space_no = int(space_no)

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

    def __repr__(self):
        return f'ParkingLot:{self.__id}, {self.__reg_id}, {self.__name}, {self.__lat}, {self.__lng}, {self.__sido}, {self.__sigungu}, {self.__full_addr}'

class Destination:
    def __init__(self, address: str, lat: float, lng: float):
        self.__address = address
        self.__lat = lat
        self.__lng = lng

    @property
    def address(self):
        return self.__address
    @property
    def lat(self):
        return self.__lat
    @property
    def lng(self):
        return self.__lng

    def __repr__(self):
        return f'Destination(address = "{self.__address}", lat = {self.__lat}, lng = {self.__lng})'