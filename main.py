import os
from fastapi import FastAPI, Request
import google.generativeai as genai
import httpx

app = FastAPI()

# 환경변수에서 핵심 정보 불러오기
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Gemini AI 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

@app.get("/")
def home():
    return {"message": "서버가 정상 작동 중입니다!"}

@app.post("/webhook")
async def tradingview_webhook(request: Request):
    try:
        data = await request.json()
    except Exception:
        return {"error": "JSON 형식이 아닙니다."}
    
    symbol = data.get("symbol", "알수없음")
    signal = data.get("signal", "알수없음")
    price = data.get("price", 0)
    sma200 = data.get("sma200", 0)
    rsi = data.get("rsi", 0)
    interval = data.get("interval", "15")

    # AI 검증 요청
    prompt = f"""
    당신은 코인 선물 트레이딩 리스크 관리자입니다.
    다음 진입 신호에 대해 2차 검증을 해주세요.

    - 종목 및 봉: {symbol} ({interval}분봉)
    - 현재가: {price}
    - 신호: {signal}
    - 장기 이평선(SMA 200): {sma200}
    - RSI(14): {rsi}

    [판단 기준]
    1. SMA 200이 현재가 위에 있고 롱 신호가 뜨면 저항 맞고 떨어질 확률이 높음 (주의/금지)
    2. 박스권 횡보이거나 RSI 모멘텀이 약하면 속임수(Fakeout)일 가능성 높음

    [답변 양식]
    - 최종 결론: [진입 추천 / 주의 요망 / 진입 금지] 중 택1
    - 이유 3가지 (각 1줄 요약)
    """

    try:
        response = model.generate_content(prompt)
        ai_result = response.text
    except Exception as e:
        ai_result = f"AI 분석 실패: {str(e)}"

    # 텔레그램으로 알림 전송
    msg = (
        f"🚨 [{symbol}] {signal} 신호 발생 ({interval}분봉)\n"
        f"현재가: {price} | SMA200: {sma200} | RSI: {rsi}\n\n"
        f"🤖 AI 리스크 검증:\n{ai_result}"
    )

    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(telegram_url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

    return {"status": "ok"}
