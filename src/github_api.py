import requests
import base64
from config import GITHUB_HEADERS, GITHUB_OWNER, GITHUB_REPO

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
