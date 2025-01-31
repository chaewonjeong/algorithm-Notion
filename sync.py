import os
import requests
from dotenv import load_dotenv
import base64
import re

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")



# GitHub API 헤더 설정
GITHUB_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

# Notion API 헤더 설정
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# GitHub에서 모든 커밋 가져오기
def get_all_commits():
    commits = []
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/commits"
    
    while url:
        response = requests.get(url, headers=GITHUB_HEADERS)
        if response.status_code == 200:
            commits.extend(response.json())
            # Pagination 지원 (다음 페이지가 있는 경우)
            url = response.links.get("next", {}).get("url")
        else:
            print(f"❌ GitHub API 에러: {response.status_code}")
            break
    
    return commits  # 모든 커밋 리스트 반환s

# 특정 커밋에서 변경된 파일 가져오기
def get_commit_files(commit_sha):
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/commits/{commit_sha}"
    response = requests.get(url, headers=GITHUB_HEADERS)
    
    if response.status_code == 200:
        commit_data = response.json()
        files = commit_data.get("files",[])
        return [(file["filename"], file["status"]) for file in files]
    else:
        print(f"❌ GitHub API 에러: {response.status_code}")
        return []
    
# 문제 제목이나 커밋 메시지에서 난이도를 추출하는 함수
def extract_difficulty(text):
    match = re.search(r"\[(.*?)\]", text)  # `[]` 안의 내용 추출
    return match.group(1) if match else "Unknown"  # 없으면 "Unknown" 반환
    
# 특정 파일의 원본 내용 가져오기
def get_file_content(file_path, branch="main"):
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{file_path}?ref={branch}"
    response = requests.get(url, headers=GITHUB_HEADERS)
    
    if response.status_code == 200:
        file_data = response.json()
        content = base64.b64decode(file_data["content"]).decode("utf-8")
        return content
    else:
        print("Error:", response.json())
        return None

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

# 커밋 처리하기
def process_commit(commit, existing_titles):
    commit_sha = commit["sha"]
    commit_message = commit["commit"]["message"] # 커밋 메세지 추출
    commit_url = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/commit/{commit_sha}"

    print(f"\n🔍 최근 커밋 SHA: {commit_sha}")
    print(f"📌 커밋 메시지: {commit_message}")

    # ✅ 커밋 메시지에서 난이도 추출
    difficulty = extract_difficulty(commit_message)

    files = get_commit_files(commit_sha)
    if not files:
        print(f"⚠️ 커밋 {commit_sha}에 변경된 파일이 없습니다.")
        return

    file_contents = {}

    for filename, status in files:
        print(f"  - {filename} ({status})")

        content = get_file_content(filename)
        if content:
            file_contents[filename] = content

    for filename in file_contents.keys():
        if filename.endswith(".md"):  # ✅ 문제 제목은 .md 파일명에서 추출
            title = filename.split("/")[-1].replace(".md", "")

            if title in existing_titles:
                print(f"✅ {title} 문제는 이미 Notion에 존재하므로 건너뜀.")
                continue  # 이미 존재하는 경우 스킵
            
            description = file_contents[filename]  # 📝 문제 설명 (README.md 내용)
            code = file_contents.get(filename.replace(".md", ".java"), "")  # 💻 소스 코드 (.java 내용)

            
            print(f"🆕 새로운 문제 발견! {title}을(를) Notion에 업로드합니다.")

            add_problem_to_notion(title, description, code, difficulty, commit_url)

def split_text_into_blocks(text, max_length=2000):
    """긴 텍스트를 2000자 이하의 블록으로 분할하는 함수"""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def add_problem_to_notion(title, description, code, difficulty, github_link):
    url = "https://api.notion.com/v1/pages"

    # ✅ 기존 옵션 가져오기
    existing_difficulties = get_notion_database_properties()

    # ✅ 새로운 난이도 값이 기존에 없으면 기본값 "Unknown" 설정
    difficulty_value = difficulty if difficulty in existing_difficulties else "Unknown"

    # ✅ 긴 텍스트 분할
    description_blocks = split_text_into_blocks(description)
    code_blocks = split_text_into_blocks(code)

    payload = {
        "parent": { "database_id": NOTION_DATABASE_ID },
        "properties": {
            "문제 제목": { "title": [{ "text": { "content": title } }] },
            "GitHub 링크": { "url": github_link },
            "난이도": { "select": { "name": difficulty_value } },
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




def main():
    # ✅ Notion에서 기존 문제 목록 가져오기 (중복 방지)
    existing_titles = set()
    notion_pages = fetch_notion_database()
    for page in notion_pages:
        title_property = page["properties"].get("문제 제목", {}).get("title", [])
        if title_property:
            existing_titles.add(title_property[0]["text"]["content"])
    
    print(f"📌 Notion에 저장된 문제 개수: {len(existing_titles)}")


    # ✅ GitHub에서 최근 커밋 목록 가져오기
    commits = get_all_commits()
    if not commits:
        print("⚠️ GitHub에서 가져올 커밋이 없습니다.")
        return
    
    # ✅ 가장 최근 커밋부터 처리
    for commit in commits[:5]:  # 최신 5개 커밋만 처리 (더 많은 경우 반복)
        process_commit(commit, existing_titles)

if __name__ == "__main__":
    main()
