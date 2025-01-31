from github_api import get_all_commits, get_commit_files, get_file_content
from notion_api import fetch_notion_database, add_problem_to_notion
from utils import extract_difficulty, extract_site_name_from_path, extract_problem_link, extract_submission_date
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

def extract_problem_info(file_contents, existing_titles, difficulty, latest_commit_per_problem):
    """
    `.md` 파일에서 문제 정보를 추출하여 문제별 데이터를 저장하는 함수
    """
    problem_dict = {}

    for filename, content in file_contents.items():
        if filename.endswith(".md"):  # ✅ 문제 설명 파일 (README.md)
            if filename.count("/") < 2:  # ✅ 최상단 README.md 파일 제외
                print(f"⚠️ 최상단의 {filename} 파일은 제외합니다.")
                continue

            # ✅ 문제 링크, 제출 일자 추출
            problem_link = extract_problem_link(content)
            submission_date = extract_submission_date(content)

            # ✅ 문제 이름과 사이트명 추출
            site_name = extract_site_name_from_path(filename)
            problem_name = os.path.basename(os.path.dirname(filename))  # 폴더명 = 문제 제목

            # ✅ 기존 Notion 데이터베이스에 존재하는 경우 최신 커밋인지 확인
            if problem_name in existing_titles:
                print(f"✅ {problem_name} 문제는 이미 Notion에 존재하므로 건너뜀.")
                continue  # 중복 방지

            # ✅ 동일 문제의 기존 코드 블록 유지 (과거 풀이 보존)
            previous_code_blocks = latest_commit_per_problem.get(problem_name, {}).get("code_blocks", [])

            # ✅ 문제 정보 저장 (기존 코드 블록 유지)
            problem_dict[problem_name] = {
                "description": content,  # 최신 설명 유지
                "code_blocks": previous_code_blocks,  # 기존 코드 유지
                "difficulty": difficulty,
                "site_name": site_name,
                "problem_link": problem_link,
                "submission_date": submission_date
            }

    return problem_dict


def match_code_files(file_contents, problem_dict):
    """
    문제별 코드 파일을 찾아 해당 문제에 연결하는 함수 (여러 풀이 유지)
    """
    for filename, content in file_contents.items():
        ext = filename.split(".")[-1]  # 확장자 추출
        problem_name = os.path.basename(os.path.dirname(filename))  # 폴더명 = 문제 제목

        if problem_name in problem_dict and ext in NOTION_LANGUAGE_MAP:
            # ✅ 기존 코드 블록 유지 + 새로운 코드 추가
            problem_dict[problem_name]["code_blocks"].append({
                "language": NOTION_LANGUAGE_MAP[ext],
                "content": content
            })
            print(f"✅ {problem_name}의 {ext.upper()} 코드 추가 완료.")

    return problem_dict


def process_commit(commit, existing_titles, latest_commit_per_problem):
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
        return {}

    # ✅ 모든 파일 내용 가져오기
    file_contents = {filename: get_file_content(filename) for filename, _ in files}

    # ✅ 문제 정보 추출 (기존 코드 유지)
    problem_dict = extract_problem_info(file_contents, existing_titles, difficulty, latest_commit_per_problem)

    # ✅ 코드 파일 매칭 (여러 풀이 유지)
    problem_dict = match_code_files(file_contents, problem_dict)

    return problem_dict


def filter_latest_commits(commits, latest_commit_per_problem):
    """
    기존에 존재하는 문제라면 최신 커밋인지 확인하고 최신 것만 남기는 함수
    """
    filtered_commits = []
    for commit in commits:
        commit_date = commit["commit"]["committer"]["date"]

        problem_dict = process_commit(commit, {}, latest_commit_per_problem)
        for problem_name in problem_dict.keys():
            if problem_name in latest_commit_per_problem:
                prev_commit_date = latest_commit_per_problem[problem_name]["commit"]["committer"]["date"]
                if commit_date <= prev_commit_date:
                    print(f"✅ {problem_name} 문제의 최신 커밋({commit_date})이 이미 존재함. 건너뜀.")
                    continue

            latest_commit_per_problem[problem_name] = commit
            filtered_commits.append(commit)

    return filtered_commits


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
            data["problem_link"],
            data["submission_date"]
        )


def main():
    """Notion에서 기존 문제 목록을 가져와 GitHub의 최신 커밋을 처리"""
    existing_titles = {page["properties"]["문제 제목"]["title"][0]["text"]["content"] for page in fetch_notion_database()}
    print(f"📌 Notion에 저장된 문제 개수: {len(existing_titles)}")

    commits = get_all_commits()
    if not commits:
        print("⚠️ GitHub에서 가져올 커밋이 없습니다.")
        return

    latest_commit_per_problem = {}

    # ✅ 최신 커밋만 필터링
    filtered_commits = filter_latest_commits(commits, latest_commit_per_problem)

    # ✅ 최신 커밋들만 처리하여 Notion에 업로드
    for commit in filtered_commits:
        problem_dict = process_commit(commit, existing_titles, latest_commit_per_problem)
        upload_to_notion(problem_dict)

if __name__ == "__main__":
    main()
