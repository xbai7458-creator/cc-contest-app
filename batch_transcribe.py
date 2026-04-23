# -*- coding: utf-8 -*-
"""
本地 Whisper 轉寫 + 評分腳本
用法：python3 batch_transcribe.py

流程：
  1. 讀取 submissions.json，找出「有音頻檔、尚無文字稿」的記錄
  2. 用 Whisper CLI 轉寫音頻 → 更新文字稿
  3. 自動跑 AI 評分 → 更新分數
  4. 重啟 Streamlit App 後即可看到結果
"""
import os, sys, json, time, re

# ── 設定 ──────────────────────────────────────────────
APP_DIR   = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(APP_DIR, "uploads")
DB_PATH   = os.path.join(APP_DIR, "submissions.json")
TRANSCRIPT_DIR = os.path.join(APP_DIR, "transcripts")

# Whisper CLI 參數（tiny 模型最快，適合中文）
WHISPER_MODEL   = "tiny"
WHISPER_LANG    = "Chinese"
WHISPER_TIMEOUT = 300  # 秒


def load_db():
    if not os.path.exists(DB_PATH):
        return []
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(data):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_pending():
    """找出有音頻檔但無文字稿的記錄"""
    db = load_db()
    pending = []
    for sub in db:
        has_audio = bool(sub.get("file_path"))
        has_text  = bool(sub.get("transcript", "").strip())
        is_scored = sub.get("status") == "scored"
        if has_audio and not has_text and not is_scored:
            raw_path = sub["file_path"]
            # 統一為相對路徑：相對於 APP_DIR
            if os.path.isabs(raw_path):
                audio_path = raw_path
            else:
                audio_path = os.path.join(APP_DIR, raw_path)
            if os.path.exists(audio_path):
                pending.append(sub)
    return pending


def transcribe_whisper(audio_path):
    """用 Python whisper 套件轉寫音頻"""
    print(f"  🔄 載入 Whisper 模型（tiny）...")
    try:
        import whisper
        model = whisper.load_model(
            WHISPER_MODEL,
            download_root=os.path.expanduser("~/.cache/whisper")
        )
        print(f"  🎤 轉寫中（預計 1-2 分鐘）...")
        result = model.transcribe(audio_path, language=WHISPER_LANG)
        text = result["text"].strip()
        return text, None
    except Exception as e:
        return None, f"❌ {e}"


def score_submission(transcript, main_line):
    """呼叫 scoring.py 評分"""
    sys.path.insert(0, APP_DIR)
    from scoring import score_transcript
    return score_transcript(transcript, main_line)


def main():
    print("=" * 55)
    print("🎙️  CC轉介紹話術大賽 — 批量轉寫 + 評分")
    print("=" * 55)

    pending = find_pending()

    if not pending:
        print("\n✅ 目前沒有待處理的錄音（全部已評分或無新上傳）")
        return

    print(f"\n📋 發現 {len(pending)} 個待處理項目：\n")
    for i, sub in enumerate(pending, 1):
        print(f"  {i}. [{sub['main_line']}] {sub['cc_name']} — {sub['filename']}")

    print(f"\n{'─' * 55}")
    confirm = input(f"是否開始轉寫 + 評分？ (y/n): ").strip().lower()
    if confirm != "y":
        print("已取消。")
        return

    print()
    db = load_db()
    sub_map = {f"{s['id']}": s for s in db}

    for sub in pending:
        sid        = sub["id"]
        cc_name    = sub["cc_name"]
        main_line  = sub["main_line"]
        raw_path = sub["file_path"]
        audio_path = raw_path if os.path.isabs(raw_path) else os.path.join(APP_DIR, raw_path)

        print(f"\n{'─' * 55}")
        print(f"▶ 處理：{cc_name} | [{main_line}]")
        print(f"  📁 音頻：{sub['file_path']}")

        # Step 1：Whisper 轉寫
        print(f"  ⏳ Step 1/2：Whisper CLI 轉寫中...")
        transcript, err = transcribe_whisper(audio_path)

        if err or not transcript:
            print(f"  ❌ 轉寫失敗：{err}")
            continue

        print(f"  ✅ 轉寫完成（{len(transcript)} 字）")
        print(f"  📄 預覽：{transcript[:80]}...")

        # Step 2：評分
        print(f"  ⏳ Step 2/2：AI 評分中...")
        try:
            result = score_submission(transcript, main_line)
        except Exception as e:
            print(f"  ⚠️ 評分失敗：{e}")
            result = None

        # 更新資料庫
        record = sub_map.get(sid)
        if record:
            record["transcript"]  = transcript
            record["status"]      = "scored"
            if result:
                record["ai_score"]    = result["total"]
                record["ai_detail"]    = json.dumps(result, ensure_ascii=False)
                print(f"  🏆 AI 評分：{result['total']} 分")
                print(f"  💬 {result['summary'][:60]}...")
            else:
                record["ai_score"]  = 0
                record["ai_detail"] = "{}"
                print(f"  ⚠️ 無評分結果")

            save_db(db)
            print(f"  💾 已寫入 submissions.json")

    print(f"\n{'=' * 55}")
    print("✅ 全部處理完成！請重啟 Streamlit App 查看結果。")
    print("=" * 55)


if __name__ == "__main__":
    main()
