from github_api import get_all_commits, get_commit_files, get_file_content
from notion_api import fetch_notion_database, add_problem_to_notion
from utils import extract_difficulty
from config import GITHUB_OWNER, GITHUB_REPO

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

    for filename, content in file_contents.items():
        if filename.endswith(".md"):  # ✅ 문제 제목은 .md 파일명에서 추출
            title = filename.replace(".md", "")

            if title in existing_titles:
                print(f"✅ {title} 문제는 이미 Notion에 존재하므로 건너뜀.")
                continue  # 이미 존재하는 경우 스킵
            
            description = content  # 📝 문제 설명 (README.md 내용)
            code = file_contents.get(filename.replace(".md", ".java"), "")  # 💻 소스 코드 (.java 내용)

            print(f"🆕 새로운 문제 발견! {title}을(를) Notion에 업로드합니다.")
            add_problem_to_notion(title, description, code, difficulty, commit_url)


def main():
    """Notion에서 기존 문제 목록을 가져와 GitHub의 최신 커밋을 처리"""
    existing_titles = {page["properties"]["문제 제목"]["title"][0]["text"]["content"] for page in fetch_notion_database()}
    print(f"📌 Notion에 저장된 문제 개수: {len(existing_titles)}")

    commits = get_all_commits()
    if not commits:
        print("⚠️ GitHub에서 가져올 커밋이 없습니다.")
        return

    # ✅ 가장 최근 커밋부터 처리
    for commit in commits[:5]:  # 최신 5개 커밋만 처리
        process_commit(commit, existing_titles)

if __name__ == "__main__":
    main()