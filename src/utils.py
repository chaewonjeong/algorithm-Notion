from bs4 import BeautifulSoup
import re
import markdown
from datetime import datetime, timedelta

# 문제 제목이나 커밋 메시지에서 난이도를 추출하는 함수
def extract_difficulty(text):
    match = re.search(r"\[(.*?)\]", text)  # `[]` 안의 내용 추출
    return match.group(1) if match else "Unknown"  # 없으면 "Unknown" 반환
    
# 긴 텍스트를 2000자 이하의 블록으로 분할하는 함수
def split_text_into_blocks(text, max_length=2000):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

# repo 파일에서 사이트명 추출
def extract_site_name_from_path(filename):
    return filename.split("/")[0] if "/" in filename else "Unknown"

# markdown text를 Notion 본문에 입력하기위해 변환하는 함수
def convert_markdown_to_notion_blocks(markdown_text):
    """Markdown과 HTML을 Notion 블록 형식으로 변환"""
    # ✅ Markdown을 HTML로 변환
    html_text = markdown.markdown(markdown_text)

    # ✅ BeautifulSoup으로 HTML 파싱
    soup = BeautifulSoup(html_text, "html.parser")
    notion_blocks = []

    for element in soup.children:  # ✅ 모든 최상위 요소만 순회 (중복 방지)
        if element.name == "h1":  # 제목 (h1)
            notion_blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"text": {"content": element.get_text()}}]
                }
            })
        elif element.name == "h2":  # 제목 (h2)
            notion_blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"text": {"content": element.get_text()}}]
                }
            })
        elif element.name == "h3":  # 제목 (h3)
            notion_blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"text": {"content": element.get_text()}}]
                }
            })
        elif element.name == "p":  # ✅ `<p>` 내부에 `img` 태그가 있는 경우도 포함
            img_tags = element.find_all("img")
            text_content = element.get_text(strip=True)

            if img_tags:  # ✅ `<p>` 안에 `img` 태그가 있을 경우
                if text_content:  # ✅ `<p>` 안에 텍스트가 있는 경우 먼저 텍스트 추가
                    notion_blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"text": {"content": text_content}}]
                        }
                    })
                for img in img_tags:
                    img_src = img.get("src")
                    img_alt = img.get("alt", "이미지")  # 대체 텍스트 기본값 설정

                    if img_src.startswith("http"):  # Notion은 URL 이미지만 지원
                        notion_blocks.append({
                            "object": "block",
                            "type": "image",
                            "image": {
                                "type": "external",
                                "external": {"url": img_src}
                            }
                        })
                        if img_alt:
                            notion_blocks.append({
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [{"text": {"content": img_alt}}]
                                }
                            })
            else:  # ✅ 일반 단락 처리
                if text_content:
                    notion_blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"text": {"content": text_content}}]
                        }
                    })
        elif element.name == "ul":  # 불릿 리스트
            for li in element.find_all("li"):
                notion_blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": li.get_text()}}]
                    }
                })
        elif element.name == "ol":  # 번호 매긴 리스트
            for idx, li in enumerate(element.find_all("li"), start=1):
                notion_blocks.append({
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": [{"text": {"content": f"{idx}. {li.get_text()}"}}]
                    }
                })
        elif element.name == "table":  # 테이블 변환 (Notion API에서 테이블 지원 안 함 → 리스트 형태로 변환)
            rows = element.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                row_text = " | ".join([col.get_text() for col in cols])
                notion_blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": row_text}}]
                    }
                })
        elif element.name == "code":  # 코드 블록
            code_content = element.get_text()
            notion_blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"text": {"content": code_content}}],
                    "language": "java"  # 언어 감지 추가 가능
                }
            })
        elif element.name == "img":  # ✅ 단독 이미지 변환
            img_src = element.get("src")
            img_alt = element.get("alt", "이미지")  # 대체 텍스트 기본값 설정

            if img_src.startswith("http"):  # Notion은 URL 이미지만 지원
                notion_blocks.append({
                    "object": "block",
                    "type": "image",
                    "image": {
                        "type": "external",
                        "external": {"url": img_src}
                    }
                })
                if img_alt:
                    notion_blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"text": {"content": img_alt}}]
                        }
                    })
        elif element.name is None:  # ✅ 일반 텍스트 처리
            text = element.strip()
            if text:
                notion_blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": text}}]
                    }
                })

    return notion_blocks


# content 에서 추출한 markdown text에서 문제 링크 추출하는 함수
def extract_problem_link(markdown_text):
    """
    README.md에서 문제 링크를 추출하는 함수.
    - 문제 링크 패턴을 찾고, 첫 번째 링크를 반환
    - 링크가 없는 경우 None 반환
    """
    match = re.search(r"\[문제 링크\]\((.*?)\)", markdown_text)
    return match.group(1) if match else None

# content 에서 추출한 markdown text에서 제출 일자 추출하는 함수
def extract_submission_date(markdown_text):
    """
    README.md에서 '제출 일자' 정보를 추출하여 ISO 8601 형식(UTC)으로 변환
    - Notion API가 요구하는 `"YYYY-MM-DDTHH:MM:SS.000Z"` 포맷으로 변환
    """
    match = re.search(r"### 제출 일자\s*\n\s*(\d{4})년 (\d{1,2})월 (\d{1,2})일 (\d{2}):(\d{2}):(\d{2})", markdown_text)

    if match:
        # ✅ 문자열 날짜 → datetime 변환
        year, month, day, hour, minute, second = map(int, match.groups())
        submission_datetime = datetime(year, month, day, hour, minute, second)

        # ✅ 한국 시간(UTC+9)을 UTC로 변환
        submission_datetime -= timedelta(hours=9)

        # ✅ Notion API에서 요구하는 ISO 8601 형식 (`YYYY-MM-DDTHH:MM:SS.000Z`)으로 변환
        return submission_datetime.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    return None  # 날짜 정보가 없으면 None 반환