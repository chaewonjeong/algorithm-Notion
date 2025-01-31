from github_api import get_all_commits, get_commit_files, get_file_content
from notion_api import fetch_notion_database, add_problem_to_notion
from utils import extract_difficulty, extract_site_name_from_path, extract_problem_link, extract_submission_date
from config import GITHUB_OWNER, GITHUB_REPO
import os

# ✅ Notion API에서 지원하는 언어 매핑
NOTION_LANGUAGE_MAP = {
    "py": "python", "java": "java", "cpp": "c++", "c": "c",
    "js": "javascript", "ts": "typescript", "go": "go",
    "swift": "swift", "rb": "ruby", "kt": "kotlin",
    "php": "php", "rs": "rust"
}

def extract_problem_info(file_contents):
    """
    `.md` 파일에서 문제 정보를 추출하여 문제별 데이터를 저장하는 함수
    """
    problem_dict = {}

    for filename, content in file_contents.items():
        if filename.endswith(".md"):
            if filename.count("/") < 2:  # ✅ 최상단 README.md 파일 제외
                continue

            # ✅ 문제 링크, 제출 일자 추출
            problem_link = extract_problem_link(content)
            submission_date = extract_submission_date(content)

            # ✅ 문제 이름과 사이트명 추출
            site_name = extract_site_name_from_path(filename)
            problem_name = os.path.basename(os.path.dirname(filename))

            # ✅ 문제 정보 저장
            problem_dict[problem_name] = {
                "description": content,
                "code_blocks": [],
                "site_name": site_name,
                "problem_link": problem_link,
                "submission_date": submission_date
            }

    return problem_dict


def match_code_files(file_contents, problem_dict):
    """
    문제별 코드 파일을 찾아 해당 문제에 연결하는 함수
    """
    for filename, content in file_contents.items():
        ext = filename.split(".")[-1]
        problem_name = os.path.basename(os.path.dirname(filename))

        if problem_name in problem_dict and ext in NOTION_LANGUAGE_MAP:
            problem_dict[problem_name]["code_blocks"].append({
                "language": NOTION_LANGUAGE_MAP[ext],
                "content": content
            })

    return problem_dict


def process_commit(commit):
    """GitHub 커밋을 처리하여 문제 데이터 반환"""
    commit_sha = commit["sha"]
    commit_message = commit["commit"]["message"]
    difficulty = extract_difficulty(commit_message)

    # ✅ 변경된 파일 목록 가져오기
    files = get_commit_files(commit_sha)
    if not files:
        return None  # 변경된 파일이 없는 경우

    # ✅ 모든 파일 내용 가져오기
    file_contents = {filename: get_file_content(filename) for filename, _ in files}

    # ✅ 문제 정보 추출
    problem_dict = extract_problem_info(file_contents)

    # ✅ 코드 파일 매칭
    problem_dict = match_code_files(file_contents, problem_dict)

    # ✅ 문제별 난이도, 커밋 정보 추가
    for problem in problem_dict.values():
        problem["difficulty"] = difficulty
        problem["commit_sha"] = commit_sha

    return problem_dict  # ✅ 문제 데이터 반환


def filter_latest_commits(problems, latest_commit_per_problem):
    """
    최신 커밋만 유지하도록 필터링
    """
    filtered_problems = {}

    for problem_name, data in problems.items():
        curr_commit_date = data["submission_date"]

        if problem_name in latest_commit_per_problem:
            prev_commit_date = latest_commit_per_problem[problem_name]["submission_date"]

            if curr_commit_date <= prev_commit_date:
                continue  # ✅ 최신 커밋이 아니면 제외

        latest_commit_per_problem[problem_name] = data
        filtered_problems[problem_name] = data

    return filtered_problems


def main():
    """Notion에서 기존 문제 목록을 가져와 GitHub의 최신 커밋을 처리"""
    existing_titles = {
        page["properties"]["문제 제목"]["title"][0]["text"]["content"]
        for page in fetch_notion_database()
    }

    commits = get_all_commits()
    if not commits:
        print("⚠️ GitHub에서 가져올 커밋이 없습니다.")
        return

    latest_commit_per_problem = {}  # ✅ 최신 커밋 저장

    all_problems = {}

    # ✅ 커밋 순회하며 문제 정보 수집
    for commit in commits:
        problem_dict = process_commit(commit)
        if problem_dict:
            all_problems.update(problem_dict)

    # ✅ 최신 커밋 필터링
    filtered_problems = filter_latest_commits(all_problems, latest_commit_per_problem)

    # ✅ Notion 업로드
    for problem_name, data in filtered_problems.items():
        if problem_name not in existing_titles:
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

if __name__ == "__main__":
    main()
