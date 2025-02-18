import os
import requests
from dotenv import load_dotenv
import base64
import re




    



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
