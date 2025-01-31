import re

# 문제 제목이나 커밋 메시지에서 난이도를 추출하는 함수
def extract_difficulty(text):
    match = re.search(r"\[(.*?)\]", text)  # `[]` 안의 내용 추출
    return match.group(1) if match else "Unknown"  # 없으면 "Unknown" 반환
    
# 긴 텍스트를 2000자 이하의 블록으로 분할하는 함수
def split_text_into_blocks(text, max_length=2000):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

# 데이터 베이스에 업로드 될 커밋메세지에서의 제목