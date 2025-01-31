import requests
from config import NOTION_HEADERS, NOTION_DATABASE_ID
from utils import split_text_into_blocks, convert_markdown_to_notion_blocks

# 노션 데이터베이스의 목록 가져오기 
def fetch_notion_database():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    has_more = True
    next_cursor = None
    all_pages = []

    while has_more:
        payload = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor  # 페이지네이션 처리

        response = requests.post(url, headers=NOTION_HEADERS, json=payload)

        # 디버깅
        # print(response.json())

        if response.status_code == 200:
            data = response.json()
            all_pages.extend(data.get("results", []))
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor", None)
        else:
            print(f"❌ Notion API 에러: {response.status_code}, {response.json()}")
            return []

    return all_pages


def get_notion_database_properties():
    """ Notion 데이터베이스 속성(난이도, 태그 등) 가져오기 """
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}"
    response = requests.get(url, headers=NOTION_HEADERS)

    if response.status_code == 200:
        data = response.json()
        properties = data.get("properties", {})

        # ✅ "난이도" 선택 옵션 가져오기
        difficulty_options = [option["name"] for option in properties.get("난이도", {}).get("select", {}).get("options", [])]

        return difficulty_options
    else:
        print(f"❌ Notion API 에러: {response.status_code}, {response.json()}")
        return [], []


def chunk_list(lst, chunk_size):
    """리스트를 chunk_size 크기만큼 나누는 함수"""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def add_problem_to_notion(title, description, code_blocks, difficulty, site_name, problem_link, submission_date):
    """Notion에 문제 추가 (다양한 언어 지원 + 100개 제한 해결 + 상세 예외 처리)"""
    url = "https://api.notion.com/v1/pages"

    # ✅ 기존 옵션 가져오기 (난이도 select 옵션 확인)
    existing_difficulties = get_notion_database_properties()

    # ✅ 새로운 난이도 값이 기존에 없으면 기본값 "Unknown" 설정
    difficulty_value = difficulty if difficulty in existing_difficulties else "Unknown"

    # ✅ Markdown을 Notion 블록으로 변환 (문제 설명)
    description_blocks = convert_markdown_to_notion_blocks(description)

    # ✅ 코드 블록 생성 (다양한 언어 지원)
    notion_code_blocks = []
    for code_block in code_blocks:
        language = code_block["language"]  # ✅ 해당 코드의 언어 추출
        code_content = code_block["content"]

        # ✅ 긴 코드 자동 분할 (2000자 제한 해결)
        for chunk in split_text_into_blocks(code_content):
            notion_code_blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"text": {"content": chunk}}],
                    "language": language
                }
            })

    # ✅ Notion Page 생성 (기본 정보)
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "문제 제목": {"title": [{"text": {"content": title}}]},
            "문제 링크": {"url": problem_link},
            "난이도": {"select": {"name": difficulty_value}},
            "사이트": {"select": {"name": site_name}},
            "제출 일자": {"date": {"start": submission_date}}
        },
    }

    # ✅ 페이지 생성 요청
    response = requests.post(url, headers=NOTION_HEADERS, json=payload)
    if response.status_code == 200:
        notion_page_id = response.json()["id"]
        print(f"✅ Notion에 문제 추가 성공: {title}")
    else:
        print(f"❌ Notion API 에러: {response.status_code}, {response.json()}")
        return

    # ✅ 생성된 페이지에 `children` 블록을 100개씩 나누어 추가
    all_blocks = []
    all_blocks.extend(description_blocks)  # ✅ description_blocks 추가
    all_blocks.append({"object": "block", "type": "divider", "divider": {}})
    all_blocks.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "나의 풀이"}}]}})
    all_blocks.extend(notion_code_blocks)  # ✅ notion_code_blocks 추가
    all_blocks.append({"object": "block", "type": "divider", "divider": {}})
    all_blocks.append({"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"text": {"content": "📌 학습 인사이트"}}]}})
    all_blocks.append({"object": "block", "type": "quote", "quote": {"rich_text": [{"text": {"content": "이 문제에서 배운 점을 기록하세요..."}}]}})
    all_blocks.append({"object": "block", "type": "divider", "divider": {}})
    all_blocks.append({"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"text": {"content": "참고 코드"}}]}})
    all_blocks.append({
        "object": "block",
        "type": "code",
        "code": {
            "rich_text": [{"text": {"content": ""}}],
            "language": language
        }
    })

    # ✅ 블록 개수 제한 해결 (100개씩 나누어 전송)
    for block_chunk in chunk_list(all_blocks, 100):
        update_url = f"https://api.notion.com/v1/blocks/{notion_page_id}/children"
        update_payload = {"children": block_chunk}
        response = requests.patch(update_url, headers=NOTION_HEADERS, json=update_payload)

        if response.status_code != 200:
            print(f"❌ Notion API 추가 블록 전송 실패: {response.status_code}, {response.json()}")
            return

    print(f"✅ Notion에 문제의 설명 및 코드 추가 완료: {title}")