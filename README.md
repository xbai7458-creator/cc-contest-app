# CC 轉介紹話術大賽系統

## 🚀 啟動方式

```bash
cd /Users/xiaobai/Documents/51talk/CC教練-錄音
python3 -m streamlit run contest_app/app.py --server.port 8501
```

## 🔑 访问地址

- 本地：http://localhost:8501
- 局域网：http://26.26.26.1:8501

## 🔐 管理員密碼

```
cccontest2026
```

## 📋 功能一覽

| 頁面 | 說明 |
|------|------|
| 📤 提交錄音 | CC 老師上傳音頻（MP3/WAV/M4A），自動 Whisper 轉寫 + AI 評分 |
| 📊 即時排名 | 團隊總分排行 + CC 個人排行榜，實時更新 |
| 👑 管理員評分 | 密碼登入後可覆寫 AI 評分、查看逐維度分析、導出 CSV |

## ⚙️ 評分邏輯

- AI 評分（Whisper 轉寫 + 關鍵詞分析）× 60%
- 管理員評分 × 40%
- 綜合分數 = 每位 CC 所有錄音中取最佳 1 通
- 團隊總分 = 小組全部 CC 加總

## 📂 數據存放

- 評分記錄：`contest_app/submissions.db`
- 音頻檔案：`contest_app/uploads/`
- 導出 CSV：執行導出後本地生成

## 🛠 常見問題

**Q: 轉寫失敗怎麼辦？**
A: 管理員可在「管理員評分」頁面直接填入文字稿，系統會重新評分。

**Q: 想重置密碼？**
A: 修改 `contest_app/.streamlit/secrets.toml` 中的 `ADMIN_PWD`。

**Q: 想換端口？**
A: 改 `--server.port` 參數即可。
