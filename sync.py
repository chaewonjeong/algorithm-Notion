import os
import requests
from dotenv import load_dotenv
import base64

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

def print_notion_database():
    pages = fetch_notion_database()
    if not pages:
        print("⚠️ Notion 데이터베이스에 저장된 항목이 없습니다.")
        return
    
    print(f"\n📌 Notion 데이터베이스에서 가져온 {len(pages)}개의 문제 목록:")

    for page in pages:
        title_property = page["properties"].get("문제 제목", {}).get("title", [])
        created_time = page.get("created_time", "Unknown")
        
        title = title_property[0]["text"]["content"] if title_property else "제목 없음"
        
        print(f"📝 {title} | 생성 날짜: {created_time}")

def main():

    # ✅ GitHub에서 최근 커밋 목록 가져오기
    commits = get_all_commits()
    if not commits:
        print("⚠️ GitHub에서 가져올 커밋이 없습니다.")
        return
    
    # ✅ 가장 최근 커밋부터 처리
    for commit in commits[:5]:  # 최신 5개 커밋만 처리 (더 많은 경우 반복)
        commit_sha = commit["sha"]
        print(f"\n🔍 최근 커밋 SHA: {commit_sha}")

        # ✅ 해당 커밋에서 변경된 파일 목록 가져오기
        files = get_commit_files(commit_sha)
        if not files:
            print(f"⚠️ 커밋 {commit_sha}에 변경된 파일이 없습니다.")
            continue

        print("\n📂 변경된 파일 목록:")
        file_contents = {}

        # ✅ 모든 파일의 내용을 가져오기
        for filename, status in files:
            print(f"  - {filename} ({status})")

            # ✅ 파일 내용 가져오기
            content = get_file_content(filename)
            if content:
                file_contents[filename] = content
            else:
                print(f"❌ {filename} 파일 내용을 가져오지 못했습니다.")

        # ✅ 파일 내용을 출력 
        for filename, content in file_contents.items():
            print(f"\n📄 {filename} 내용 (최대 500자 표시):\n{content[:500]}")

if __name__ == "__main__":
    main()
