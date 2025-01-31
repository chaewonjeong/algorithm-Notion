import requests
from config import NOTION_HEADERS, NOTION_DATABASE_ID
from utils import split_text_into_blocks

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
        print(response.json())

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


def add_problem_to_notion(title, description, code, difficulty, site_name, github_link):
    url = "https://api.notion.com/v1/pages"

    # ✅ 기존 옵션 가져오기
    existing_difficulties = get_notion_database_properties()

    # ✅ 새로운 난이도 값이 기존에 없으면 기본값 "Unknown" 설정
    difficulty_value = difficulty if difficulty in existing_difficulties else difficulty

    # ✅ 긴 텍스트 분할
    description_blocks = split_text_into_blocks(description)
    code_blocks = split_text_into_blocks(code)

    payload = {
        "parent": { "database_id": NOTION_DATABASE_ID },
        "properties": {
            "문제 제목": { "title": [{ "text": { "content": title } }] },
            "GitHub 링크": { "url": github_link },
            "난이도": { "select": { "name": difficulty_value } },
            "사이트": {"select": {"name": site_name}},
        },
        "children": [
            { "object": "block", "type": "heading_2", "heading_2": { "rich_text": [{ "text": { "content": "문제 설명" } }] }}
        ]
    }

    # ✅ 문제 설명을 여러 블록으로 추가
    for block in description_blocks:
        payload["children"].append(
            { "object": "block", "type": "paragraph", "paragraph": { "rich_text": [{ "text": { "content": block } }] }}
        )

    # ✅ 소스 코드 추가 (여러 블록으로 나누기)
    payload["children"].append(
        { "object": "block", "type": "heading_2", "heading_2": { "rich_text": [{ "text": { "content": "소스 코드" } }] }}
    )

    for block in code_blocks:
        payload["children"].append(
            { "object": "block", "type": "code", "code": { 
                "rich_text": [{ "text": { "content": block } }], 
                "language": "java"
            }}
        )

    response = requests.post(url, headers=NOTION_HEADERS, json=payload)

    if response.status_code == 200:
        print(f"✅ Notion에 문제 추가 성공: {title}")
    else:
        print(f"❌ Notion API 에러: {response.status_code}, {response.json()}")
