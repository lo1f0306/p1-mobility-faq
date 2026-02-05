from geopy.geocoders import Nominatim

from src.model import Destination

import requests
import time

# 목적지를 검색하고 해당 목적지의 주소와 위도/경도 반환
# 연속 요청 시 1초 이상의 간격으로
def find_address_and_point(destination_name):
    geolocator = Nominatim(user_agent="chagokchagok")
    try:
        result_data = geolocator.geocode(destination_name, exactly_one=True)
        if result_data:
            return Destination(destination_name, result_data.address, result_data.latitude, result_data.longitude)
        else:
            return None
    except Exception as e:
        raise e

def get_mbr_polygon(min_lng, min_lat, max_lng, max_lat):
    return f"POLYGON(({min_lng} {min_lat}, {max_lng} {min_lat}, {max_lng} {max_lat}, {min_lng} {max_lat}, {min_lng} {min_lat}))"

def fetch_from_api(url:str, params: dict, retries: int=3):
    """
    공통 API 호출 함수
        url(필수): API 호출 url
        params(필수): 호출 시 필요한 파라미터
        -- headers(추가): 기본 header정보 외에 추가적으로 header가 필요한 경우
        retries(추가):
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
        'Accept': 'application/json'
    }

    for i in range(retries):
        try:
            # 타임아웃을 30초 정도로 넉넉하게 잡습니다.
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f" {i + 1}번째 재시도 중... (사유: {e})")
            time.sleep(2 * (i + 1))  # 실패 시 대기 시간을 조금씩 늘림
        except Exception as e:
            print(f"API 요청 중 오류 발생: {e}")
            break
    return None

def valid_check_with_logging(target_list, required_keys, number_keys=None):
    """
    데이터를 체크해서 error msg를 추가
    target_list: 데이터 체크할 리스트
    required_keys: 필요한 key값
    number_keys: number type이 필요한 key값
    """
    for item in target_list:
        errors = []

        # 1. 필수 값 체크
        for r_key in required_keys:
            val = item.get(r_key)

            if val is None or str(val).strip() == "":
                errors.append(f"Missing required key: {r_key}")

        # 2. 숫자 형식 체크
        if number_keys:
            for n_key in number_keys:
                val = item.get(n_key)

                try:
                    if val is not None:
                        float(val) # 변환 가능 여부만 체크
                    else:
                        errors.append(f"Number key is null: {n_key}")

                except (ValueError, TypeError):
                    errors.append(f"Invalid number format: {n_key}({val})")

        # 3. 결과 기록
        if not errors:
            item['error_yn'] = 'N'
            item['error_msg'] = ''
        else:
            item['error_yn'] = 'Y'
            item['error_msg'] = " | ".join(errors)  # 여러 에러를 하나로 합침

    return target_list