import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re
import pytz

st.title("연합뉴스 RSS 뉴스 검색")

# 카테고리 선택
categories = {
    "전체": "https://www.yna.co.kr/rss/news.xml",
    "정치": "https://www.yna.co.kr/rss/politics.xml",
    "경제": "https://www.yna.co.kr/rss/economy.xml",
    "사회": "https://www.yna.co.kr/rss/society.xml",
    "국제": "https://www.yna.co.kr/rss/international.xml",
    "스포츠": "https://www.yna.co.kr/rss/sports.xml",
    "IT/과학": "https://www.yna.co.kr/rss/technology.xml"
}

# 기간 선택 옵션
period_options = {
    "전체": None,
    "최근 1시간": 1,
    "최근 3시간": 3,
    "최근 6시간": 6,
    "최근 12시간": 12,
    "최근 24시간": 24,
    "최근 3일": 72,
    "최근 7일": 168
}

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    keyword = st.text_input("검색어를 입력하세요")
with col2:
    category = st.selectbox("카테고리", list(categories.keys()))
with col3:
    period = st.selectbox("기간", list(period_options.keys()), index=5)  # 기본값: 최근 24시간

def parse_rss_date(date_str):
    """RSS 날짜 문자열을 datetime 객체로 변환"""
    try:
        # RSS 표준 날짜 형식: "Mon, 29 Jul 2025 14:30:00 +0900"
        return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
    except ValueError:
        try:
            # 다른 형식 시도
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

def is_within_period(pub_date_str, hours_limit):
    """기사가 지정된 기간 내에 있는지 확인"""
    if hours_limit is None:
        return True
        
    article_date = parse_rss_date(pub_date_str)
    if article_date is None:
        return True  # 날짜 파싱 실패 시 포함
    
    # 현재 시간 (한국 시간)
    kst = pytz.timezone('Asia/Seoul')
    current_time = datetime.now(kst)
    
    # 기준 시간 계산
    cutoff_time = current_time - timedelta(hours=hours_limit)
    
    # 기사 날짜가 timezone aware가 아니면 KST로 설정
    if article_date.tzinfo is None:
        article_date = kst.localize(article_date)
    
    return article_date >= cutoff_time

if st.button("검색"):
    if not keyword.strip():
        st.warning("검색어를 입력해주세요.")
    else:
        try:
            rss_url = categories[category]
            period_hours = period_options[period]
            
            with st.spinner("RSS 피드를 가져오는 중..."):
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(rss_url, headers=headers, timeout=10)
                response.raise_for_status()
                
            # XML 파싱
            root = ET.fromstring(response.content)
            
            # 전체 기사 수집 및 필터링
            all_articles = []
            matching_articles = []
            
            for item in root.findall('.//item'):
                title = item.find('title').text if item.find('title') is not None else ""
                description = item.find('description').text if item.find('description') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                
                # HTML 태그 제거
                clean_description = re.sub('<.*?>', '', description)
                
                article = {
                    'title': title,
                    'description': clean_description,
                    'link': link,
                    'pub_date': pub_date
                }
                
                all_articles.append(article)
                
                # 기간 필터 적용
                if is_within_period(pub_date, period_hours):
                    # 검색어가 제목이나 설명에 포함되어 있는지 확인
                    if keyword.lower() in title.lower() or keyword.lower() in description.lower():
                        matching_articles.append(article)
            
            # 수집 기간 정보 표시
            if all_articles:
                dates = []
                for article in all_articles:
                    parsed_date = parse_rss_date(article['pub_date'])
                    if parsed_date:
                        dates.append(parsed_date)
                
                if dates:
                    oldest_date = min(dates)
                    newest_date = max(dates)
                    
                    # 한국 시간으로 변환하여 표시
                    kst = pytz.timezone('Asia/Seoul')
                    if oldest_date.tzinfo is None:
                        oldest_date = kst.localize(oldest_date)
                    if newest_date.tzinfo is None:
                        newest_date = kst.localize(newest_date)
                    
                    oldest_kst = oldest_date.astimezone(kst)
                    newest_kst = newest_date.astimezone(kst)
                    
                    st.info(f"📊 **수집 기간**: {oldest_kst.strftime('%Y년 %m월 %d일 %H:%M')} ~ {newest_kst.strftime('%Y년 %m월 %d일 %H:%M')} (총 {len(all_articles)}개 기사)")
            
            # 검색 결과 표시
            if not matching_articles:
                if period_hours:
                    st.warning(f"'{keyword}' 관련 기사가 최근 {period}에 없습니다.")
                else:
                    st.warning(f"'{keyword}' 검색 결과가 없습니다.")
            else:
                period_text = f" (최근 {period})" if period_hours else ""
                st.success(f"'{keyword}' 관련 기사 {len(matching_articles)}개를 찾았습니다{period_text}")
                
                # 날짜순으로 정렬 (최신순)
                matching_articles.sort(key=lambda x: parse_rss_date(x['pub_date']) or datetime.min.replace(tzinfo=pytz.UTC), reverse=True)
                
                for i, article in enumerate(matching_articles, 1):
                    # 날짜 포맷팅
                    formatted_date = article['pub_date']
                    parsed_date = parse_rss_date(article['pub_date'])
                    if parsed_date:
                        kst = pytz.timezone('Asia/Seoul')
                        if parsed_date.tzinfo is None:
                            parsed_date = kst.localize(parsed_date)
                        parsed_date_kst = parsed_date.astimezone(kst)
                        formatted_date = parsed_date_kst.strftime('%Y년 %m월 %d일 %H:%M')
                        
                        # 상대적 시간 계산
                        now = datetime.now(kst)
                        time_diff = now - parsed_date_kst
                        
                        if time_diff.days > 0:
                            relative_time = f"{time_diff.days}일 전"
                        elif time_diff.seconds > 3600:
                            hours = time_diff.seconds // 3600
                            relative_time = f"{hours}시간 전"
                        elif time_diff.seconds > 60:
                            minutes = time_diff.seconds // 60
                            relative_time = f"{minutes}분 전"
                        else:
                            relative_time = "방금 전"
                        
                        formatted_date += f" ({relative_time})"
                    
                    st.markdown(f"### {i}. [{article['title']}]({article['link']})")
                    st.write(f"📅 {formatted_date}")
                    st.write(article['description'][:200] + "..." if len(article['description']) > 200 else article['description'])
                    st.markdown("---")
                    
        except requests.exceptions.RequestException as e:
            st.error(f"RSS 피드를 가져오는 중 오류가 발생했습니다: {e}")
        except ET.ParseError as e:
            st.error(f"RSS 피드 파싱 중 오류가 발생했습니다: {e}")
        except Exception as e:
            st.error(f"예상치 못한 오류가 발생했습니다: {e}")

# 사이드바에 정보 표시
with st.sidebar:
    st.markdown("### 📋 사용 방법")
    st.markdown("""
    1. 검색어를 입력하세요
    2. 원하는 카테고리를 선택하세요
    3. 수집 기간을 선택하세요
    4. 검색 버튼을 클릭하세요
    
    **주의사항:**
    - RSS 피드에서 최신 기사만 검색됩니다
    - 검색어는 제목과 요약에서 찾습니다
    - 기간 설정으로 최신 뉴스만 필터링할 수 있습니다
    """)
    
    st.markdown("### 📰 RSS 피드 정보")
    st.markdown("연합뉴스 공식 RSS 피드를 사용합니다")
    
    # 현재 시간 표시
    kst = pytz.timezone('Asia/Seoul')
    current_time = datetime.now(kst)
    st.markdown(f"**현재 시간**: {current_time.strftime('%Y년 %m월 %d일 %H:%M')}")