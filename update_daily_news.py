import os
import json
import re
import datetime
from google import generativeai as genai
import requests

# 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY")
REPO_PATH = "index.html"

def get_current_date():
    # 한국 시간 기준 (UTC+9)
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    return now.strftime("%Y-%m-%d")

def fetch_insurance_news():
    print("Fetching insurance news...", flush=True)
    url = "https://api.search.brave.com/res/v1/web/search"
    query = f"보험 업계 신규 정책 뉴스 {get_current_date()}"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": BRAVE_API_KEY
    }
    params = {"q": query, "count": 10}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            results = response.json().get("web", {}).get("results", [])
            print(f"Successfully fetched {len(results)} news items.", flush=True)
            return results
        else:
            print(f"Brave Search Error: {response.status_code}", flush=True)
            return []
    except Exception as e:
        print(f"Brave Search Request Failed: {e}", flush=True)
        return []

def generate_news_entry(news_results):
    print("Generating news entry using Gemini...", flush=True)
    genai.configure(api_key=GEMINI_API_KEY)
    
    # 모델 설정 (Gemini 1.5 Flash가 빠르므로 우선 사용 시도)
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
    except:
        model = genai.GenerativeModel("gemini-1.5-pro")

    prompt = f"""
    아래는 오늘 날짜({get_current_date()})의 보험 관련 뉴스 검색 결과이다.
    이 내용들을 바탕으로 '안프로의 보험 핵심 뉴스 브리핑'에 들어갈 5개의 핵심 뉴스 항목을 JSON 배열 형태로 생성해줘.
    
    각 뉴스 항목은 다음 형식을 따라야 해:
    {{
        "category": "영문 카테고리 (예: NEW POLICY, MARKET TREND, AI TECH, REGULATION, NEW PRODUCT)",
        "icon": "Lucide 아이콘 이름 (예: activity, trending-up, bot, shield-alert, brain)",
        "title": "기사의 핵심을 찌르는 임팩트 있는 제목 (한국어)",
        "details": ["내용 요약 1", "내용 요약 2", "내용 요약 3"],
        "insight": "전문가로서의 통찰력이 담긴 한 줄 평 (대표님께 조언하는 스타일)",
        "link": "기사 원문 URL"
    }}

    검색 결과:
    {json.dumps(news_results, ensure_ascii=False)}

    응답은 반드시 순수 JSON 배열이어야 하며, 다른 설명은 포함하지 마.
    """

    try:
        response = model.generate_content(prompt)
        print("Gemini response received.", flush=True)
        # JSON 문자열 추출 (마크다운 코드 블록 제거 등)
        match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if match:
            json_str = match.group()
            return json.loads(json_str)
        else:
            print(f"JSON structure not found in Gemini response: {response.text[:100]}...", flush=True)
            return None
    except Exception as e:
        print(f"Gemini API or Parsing Error: {e}", flush=True)
        return None

def update_index_html(new_entry):
    date_str = get_current_date()
    print(f"Updating index.html with news for {date_str}...", flush=True)
    
    with open(REPO_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 이미 해당 날짜의 데이터가 존재한다면 업데이트 하지 않음 (중복 방지)
    if f'"{date_str}":' in content:
        print(f"News for {date_str} already exists. Skipping update.", flush=True)
        return

    # NEWS_DATABASE 객체를 찾아 새로운 데이터 삽입
    new_data_json = json.dumps(new_entry, ensure_ascii=False, indent=16)
    insertion_text = f'"{date_str}": {new_data_json},\n            '
    
    updated_content = re.sub(r'(const NEWS_DATABASE = \{)', r'\1\n            ' + insertion_text, content)

    with open(REPO_PATH, "w", encoding="utf-8") as f:
        f.write(updated_content)
    print("Update complete!", flush=True)

if __name__ == "__main__":
    if not GEMINI_API_KEY or not BRAVE_API_KEY:
        print("Error: environment variables GEMINI_API_KEY or BRAVE_API_KEY not set.", flush=True)
    else:
        news = fetch_insurance_news()
        if news:
            entry = generate_news_entry(news)
            if entry:
                update_index_html(entry)
            else:
                print("Failed to generate news entry.", flush=True)
        else:
            print("No news found to update.", flush=True)
