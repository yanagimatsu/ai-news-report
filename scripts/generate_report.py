"""
AI Daily News Report Generator
Claude API (web_search tool) でニュース収集 → LINE通知
"""

import os
import json
import datetime
import requests

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_USER_ID = os.environ["LINE_USER_ID"]

JST = datetime.timezone(datetime.timedelta(hours=9))
TODAY = datetime.datetime.now(JST).strftime("%Y年%m月%d日")
WEEKDAY = ["月", "火", "水", "木", "金", "土", "日"][datetime.datetime.now(JST).weekday()]

def generate_report() -> str:
    prompt = f"""
あなたはAI業界専門のリサーチャーです。
今日（{TODAY}・{WEEKDAY}曜日）時点の最新情報を web_search で調査して、
以下の3カテゴリに分けた日本語の朝刊レポートを作成してください。

【調査カテゴリ】
1. Claude / Anthropic 最新情報
2. AI業界全般ニュース（OpenAI / Google / Meta / xAI など）
3. X（Twitter）上のAI活用事例（site:x.com で検索、日本語圏優先）

【出力ルール】
- 合計1500文字以内
- 絵文字不使用。【】や■を使う
- 各カテゴリ2〜3トピック、1トピック2〜3行
- 末尾にURL1件
- 冒頭に日付ヘッダー

■ AI朝刊 {TODAY}（{WEEKDAY}）

【Claude / Anthropic】
【AI業界】
【X活用事例】

参照: https://...
"""
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}],
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Claude API error: {response.status_code} {response.text}")
    data = response.json()
    report_text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
    if not report_text.strip():
        raise RuntimeError("Claude APIからテキストが返ってきませんでした")
    return report_text.strip()

def send_line_message(text: str) -> None:
    if len(text) > 4900:
        text = text[:4900] + "\n\n...(省略)"
    response = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"},
        json={"to": LINE_USER_ID, "messages": [{"type": "text", "text": text}]},
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"LINE API error: {response.status_code} {response.text}")
    print("LINE送信成功")

def send_line_error(error_msg: str) -> None:
    try:
        send_line_message(f"■ AI朝刊レポート 生成エラー\n{TODAY}\n\n{error_msg}")
    except Exception:
        pass

if __name__ == "__main__":
    print(f"レポート生成開始: {TODAY}")
    try:
        report = generate_report()
        print(report)
        send_line_message(report)
        print("完了")
    except Exception as e:
        send_line_error(str(e))
        raise
