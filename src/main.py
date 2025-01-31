from github_api import get_all_commits, get_commit_files, get_file_content
from notion_api import fetch_notion_database, add_problem_to_notion
from utils import extract_difficulty, extract_site_name_from_path, extract_problem_link
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

def extract_problem_info(file_contents, existing_titles, difficulty):
    """
    `.md` 파일에서 문제 정보를 추출하여 문제별 데이터를 저장하는 함수
    """
    problem_dict = {}

    for filename, content in file_contents.items():
        if filename.endswith(".md"):  # ✅ 문제 설명 파일 (README.md)
            if filename.count("/") < 2:  # ✅ 최상단 README.md 파일 제외
                print(f"⚠️ 최상단의 {filename} 파일은 제외합니다.")
                continue

            # ✅ 문제 링크 추출 (README.md 파일에서)
            problem_link = extract_problem_link(content)

            # ✅ 문제 이름과 사이트명 추출
            site_name = extract_site_name_from_path(filename)
            problem_name = os.path.basename(os.path.dirname(filename))  # 폴더명 = 문제 제목

            if problem_name in existing_titles:
                print(f"✅ {problem_name} 문제는 이미 Notion에 존재하므로 건너뜀.")
                continue  # 중복 방지

            # ✅ 문제 정보 저장
            problem_dict[problem_name] = {
                "description": content,
                "code_blocks": [],
                "difficulty": difficulty,
                "site_name": site_name,
                "problem_link": problem_link
            }

    return problem_dict


def match_code_files(file_contents, problem_dict):
    """
    문제별 코드 파일을 찾아 해당 문제에 연결하는 함수
    """
    for filename, content in file_contents.items():
        ext = filename.split(".")[-1]  # 확장자 추출
        problem_name = os.path.basename(os.path.dirname(filename))  # 폴더명 = 문제 제목

        if problem_name in problem_dict and ext in NOTION_LANGUAGE_MAP:
            problem_dict[problem_name]["code_blocks"].append({
                "language": NOTION_LANGUAGE_MAP[ext],
                "content": content
            })
            print(f"✅ {problem_name}의 {ext.upper()} 코드 추가 완료.")

    return problem_dict

def upload_to_notion(problem_dict):
    """
    추출된 문제 데이터를 Notion에 업로드하는 함수
    """
    for problem_name, data in problem_dict.items():
        print(f"🆕 새로운 문제 발견! {problem_name}을(를) Notion에 업로드합니다.")
        add_problem_to_notion(
            problem_name,
            data["description"],
            data["code_blocks"],
            data["difficulty"],
            data["site_name"],
            data["problem_link"]
        )


def process_commit(commit, existing_titles):
    """GitHub 커밋을 처리하여 Notion에 추가하는 함수"""
    commit_sha = commit["sha"]
    commit_message = commit["commit"]["message"]

    print(f"\n🔍 최근 커밋 SHA: {commit_sha}")
    print(f"📌 커밋 메시지: {commit_message}")

    # ✅ 난이도 추출
    difficulty = extract_difficulty(commit_message)

    # ✅ 커밋 내 변경된 파일 목록 가져오기
    files = get_commit_files(commit_sha)
    if not files:
        print(f"⚠️ 커밋 {commit_sha}에 변경된 파일이 없습니다.")
        return

    # ✅ 모든 파일 내용 가져오기
    file_contents = {filename: get_file_content(filename) for filename, _ in files}

    # ✅ 문제 정보 추출
    problem_dict = extract_problem_info(file_contents, existing_titles, difficulty)

    # ✅ 코드 파일 매칭
    problem_dict = match_code_files(file_contents, problem_dict)

    # ✅ Notion에 업로드
    upload_to_notion(problem_dict)



def main():
    """Notion에서 기존 문제 목록을 가져와 GitHub의 최신 커밋을 처리"""
    existing_titles = {page["properties"]["문제 제목"]["title"][0]["text"]["content"] for page in fetch_notion_database()}
    print(f"📌 Notion에 저장된 문제 개수: {len(existing_titles)}")

    commits = get_all_commits()
    if not commits:
        print("⚠️ GitHub에서 가져올 커밋이 없습니다.")
        return

    # ✅ 가장 최근 커밋부터 처리
    for commit in commits:
        process_commit(commit, existing_titles)

if __name__ == "__main__":
    main()