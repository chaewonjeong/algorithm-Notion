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

# ✅ 1️⃣ Notion에서 기존 문제 목록 가져오기
def get_existing_notion_titles():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    response = requests.post(url, headers=NOTION_HEADERS)
    
    existing_titles = set()
    if response.status_code == 200:
        results = response.json().get("results", [])
        for page in results:
            title_property = page["properties"].get("문제 제목", {}).get("title", [])
            if title_property:
                existing_titles.add(title_property[0]["text"]["content"])
    return existing_titles

# ✅ 2️⃣ GitHub에서 모든 커밋 가져오기
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

# ✅ 3️⃣ 특정 커밋에서 변경된 파일 가져오기
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
    
# ✅ 4️⃣ 특정 파일의 원본 내용 가져오기
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

        # ✅ 파일 내용을 출력 (또는 Notion에 저장)
        for filename, content in file_contents.items():
            print(f"\n📄 {filename} 내용 (최대 500자 표시):\n{content[:500]}")

if __name__ == "__main__":
    main()
