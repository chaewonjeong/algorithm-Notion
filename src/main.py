from github_api import get_all_commits, get_commit_files, get_file_content
from notion_api import fetch_notion_database, add_problem_to_notion
from utils import extract_difficulty, extract_site_name_from_path
from config import GITHUB_OWNER, GITHUB_REPO
import os

# ✅ Notion API에서 지원하는 언어 매핑
NOTION_LANGUAGE_MAP = {
    "py": "python",
    "java": "java",
    "cpp": "c++",
    "c": "c",
    "js": "javascript",
    "ts": "typescript",
    "go": "go",
    "swift": "swift",
    "rb": "ruby",
    "kt": "kotlin",
    "php": "php",
    "rs": "rust"
}

def process_commit(commit, existing_titles):
    """GitHub 커밋을 처리하여 Notion에 추가하는 함수"""
    commit_sha = commit["sha"]
    commit_message = commit["commit"]["message"]  # 커밋 메시지 추출
    commit_url = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/commit/{commit_sha}"

    print(f"\n🔍 최근 커밋 SHA: {commit_sha}")
    print(f"📌 커밋 메시지: {commit_message}")

    # ✅ 난이도 추출
    difficulty = extract_difficulty(commit_message)

    # ✅ 해당 커밋에서 변경된 파일 목록 가져오기
    files = get_commit_files(commit_sha)
    if not files:
        print(f"⚠️ 커밋 {commit_sha}에 변경된 파일이 없습니다.")
        return

    file_contents = {filename: get_file_content(filename) for filename, _ in files}

    # ✅ 문제별로 `.md`와 코드 파일을 매칭
    problem_dict = {}

    for filename, content in file_contents.items():
        if filename.endswith(".md"):  # ✅ 문제 설명 파일 (README.md)
            # ✅ 최상단의 README.md 파일인지 확인
            if filename.count("/") < 2:  # 상위 디렉토리가 없는 경우 (최상단 README.md)
                print(f"⚠️ 최상단의 {filename} 파일은 제외합니다.")
                continue  # 최상단 README.md 파일은 제외

            # ✅ 문제 이름을 폴더 구조에서 가져오기 (마지막 폴더명)
            site_name = extract_site_name_from_path(filename)  # ✅ 파일 경로에서 사이트명 추출
            problem_name = os.path.basename(os.path.dirname(filename))  # 상위 폴더명을 문제 제목으로 사용

            if problem_name in existing_titles:
                print(f"✅ {problem_name} 문제는 이미 Notion에 존재하므로 건너뜀.")
                continue  # 이미 존재하는 경우 스킵

            # ✅ 문제 설명 저장
            problem_dict[problem_name] = {
                "description": content,
                "code_blocks": [],  # ✅ 여러 언어의 코드 블록 저장
                "difficulty": difficulty,
                "site_name": site_name,
                "commit_url": commit_url
            }

    # ✅ `.java`, `.py`, `.cpp` 등 다양한 언어 파일을 해당 문제에 연결
    for filename, content in file_contents.items():
        ext = filename.split(".")[-1]  # 파일 확장자 추출
        problem_name = os.path.basename(os.path.dirname(filename))  # 같은 폴더 내 문제 이름 찾기

        if problem_name in problem_dict and ext in NOTION_LANGUAGE_MAP:
            problem_dict[problem_name]["code_blocks"].append({
                "language": NOTION_LANGUAGE_MAP[ext],  # ✅ Notion API에서 지원하는 언어로 변환
                "content": content
            })
            print(f"✅ {problem_name}의 {ext.upper()} 코드 추가 완료.")

    # ✅ Notion에 업로드
    for problem_name, data in problem_dict.items():
        print(f"🆕 새로운 문제 발견! {problem_name}을(를) Notion에 업로드합니다.")
        add_problem_to_notion(
            problem_name, data["description"], data["code_blocks"], data["difficulty"], data["site_name"], data["commit_url"]
        )

def main():
    """Notion에서 기존 문제 목록을 가져와 GitHub의 최신 커밋을 처리"""
    existing_titles = {page["properties"]["문제 제목"]["title"][0]["text"]["content"] for page in fetch_notion_database()}
    print(f"📌 Notion에 저장된 문제 개수: {len(existing_titles)}")

    commits = get_all_commits()
    if not commits:
        print("⚠️ GitHub에서 가져올 커밋이 없습니다.")
        return

    # ✅ 가장 최근 커밋부터 처리
    for commit in commits:  # 최신 5개 커밋만 처리
        process_commit(commit, existing_titles)

if __name__ == "__main__":
    main()