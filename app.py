# -*- coding: utf-8 -*-
"""
CC 轉介紹話術大賽系統
入口文件
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import database as db

st.set_page_config(
    page_title="CC轉介紹話術大賽",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()

# ── 密碼工具 ────────────────────────────────────────────
def check_admin():
    if "admin_mode" not in st.session_state:
        st.session_state["admin_mode"] = False
    if st.session_state["admin_mode"]:
        return True
    with st.sidebar:
        st.header("🔐 管理員登入")
        pw = st.text_input("請輸入管理員密碼", type="password")
        if pw:
            if pw == st.secrets.get("ADMIN_PWD", "cccontest2026"):
                st.session_state["admin_mode"] = True
                st.rerun()
            else:
                st.error("密碼錯誤")
    return False

def check_library_access():
    """錄音庫密碼保護"""
    if "library_access" not in st.session_state:
        st.session_state["library_access"] = False
    if st.session_state["library_access"]:
        return True
    with st.sidebar:
        st.header("🔒 錄音庫密碼")
        pw = st.text_input("請輸入錄音庫密碼", type="password", key="lib_pw")
        if pw:
            if pw == st.secrets.get("LIBRARY_PWD", "cclib2026"):
                st.session_state["library_access"] = True
                st.rerun()
            else:
                st.error("密碼錯誤")
    return False

# ── 側邊欄導航 ─────────────────────────────────────────
st.sidebar.title("🏆 CC轉介紹話術大賽")
st.sidebar.caption("Q2 2026 · 轉介紹錄音評分系統")

NAV_PAGES = [
    "🏠 首頁/說明",
    "📤 提交錄音",
    "📊 即時排名",
    "📚 錄音庫",
    "📋 評分標準",
    "👑 管理員評分",
]
page = st.sidebar.radio("功能導航", NAV_PAGES, index=0)

# ════════════════════════════════════════════════════════
# ① 首頁
# ════════════════════════════════════════════════════════
if page == "🏠 首頁/說明":
    st.title("🏆 CC轉介紹話術大賽")
    st.markdown("""
    ## 📋 比賽說明

    ### 參賽資格
    - 全體 CC 老師均可參加
    - 每位 CC 可提交**任意數量**錄音參賽

    ### 錄音主線要求
    參賽錄音必須覆蓋以下 **3 條主線**（至少各有 1 通）：

    | 主線 | 說明 | 評分維度 |
    |------|------|---------|
    | 🔔 **首通** | 老師稱讚孩子 → 引導家長說出教育觀 → 了解孩子個性（活潑/害羞）| ①服務墊高 ②需求引導 ④行動閉環 ⑤抗拒處理 |
    | 💳 **付款當下** | 祝賀肯定 → 零阻力索取電話 → 消除顧慮 | ②需求引導 ③雙向利益 ④行動閉環 ⑤抗拒處理 |
    | 🎁 **權益兌換** | 肯定陪伴成果 → 三件事一起說 → 優雅邀請 | ①服務墊高 ②需求引導 ③雙向利益 ④行動閉環 ⑤抗拒處理 |

    ### 評分維度（AI真實計算）

    | 維度 | 說明 | 首通 | 付款當下 | 權益兌換 |
    |------|------|:----:|:--------:|:--------:|
    | ① 服務墊高 | 展示學員進步，肯定陪伴成果 | ✅ | — | ✅ |
    | ② 需求引導 | 自然引出朋友需求，不生硬推銷 | ✅ | ✅ | ✅ |
    | ③ 雙向利益 | 對朋友的好處 + 對自己的好處 | — | ✅ | ✅ |
    | ④ 行動閉環 | 索取聯絡/發連結/設定跟進 | ✅ | ✅ | ✅ |
    | ⑤ 抗拒處理 | 面對4種抗拒能優雅化解 | ✅ | ✅ | ✅ |

    ### 計分規則
    - **AI評分** × 60% + **管理員評分** × 40% = 綜合分數
    - AI評分根據各主線維度真實計算（基礎分 + 高分話術加分，滿分100）
    - 每位 CC 取所有錄音中**綜合分最高的 1 通**為個人總分
    - 各小組全部 CC 總分加總 = 團隊總分
    - **團隊總分 TOP 1 → 下午茶獎勵** ☕

    ### ⚠️ 注意事項
    - 錄音請上傳 **音頻檔案**（MP3 / WAV / M4A）
    - 系統將自動轉寫文字稿後進行 AI 評分
    - 管理員可覆寫評分，最終以綜合分數為準
    - 提交前請確認 CC 姓名填寫正確
    """)
    st.divider()
    st.caption("📅 比賽時間：Q2 2026 | 主辦：51Talk 教學團隊")

# ════════════════════════════════════════════════════════
# ② 提交錄音
# ════════════════════════════════════════════════════════
elif page == "📤 提交錄音":
    import time, whisper, json, re
    from config import TEAMS, CC_TO_TEAM, CC_INFO, ALL_CC_NAMES, ALL_TEAMS, MAIN_LINES, UPLOAD_DIR
    from scoring import score_transcript

    st.title("📤 提交錄音")

    # ── Step 1：輸入 CC 姓名 ──────────────────────────────
    st.subheader("👤 參賽者身份")

    raw_cc_input = st.text_input(
        "📝 請輸入您的 CC 姓名",
        placeholder="51caoyunxiu",
        help="在51Talk系統中的 CC 登入帳號，例如：51caoyunxiu、51wangyadong04"
    ).strip()

    cc_name = raw_cc_input  # 直接使用用戶輸入

    # 查詢是否匹配到名單
    matched = CC_INFO.get(cc_name)
    name_cn = matched.get("name_cn", "") if matched else ""
    team = matched.get("team", "") if matched else ""

    if cc_name:
        if matched:
            st.success(f"✅ 匹配成功！**{name_cn}** — 隸屬於 **{team}**，可提交任意數量錄音。")
        else:
            st.warning(f"⚠️ 「{cc_name}」不在現有名單中，請填寫以下資訊以便管理員審核：")
            with st.container():
                st.markdown("#### 🔧 補充您的資訊")
                col_a, col_b = st.columns(2)
                with col_a:
                    name_cn_input = st.text_input(
                        "✏️ 中文姓名",
                        placeholder="例如：曹云秀",
                        key="manual_name_cn"
                    )
                with col_b:
                    team_input = st.selectbox(
                        "📌 所屬小組",
                        ALL_TEAMS,
                        key="manual_team"
                    )
                name_cn = name_cn_input
                team = team_input
                if not name_cn_input:
                    st.info("請填寫中文姓名後再上傳錄音")

        # 已提交記錄
        existing = db.get_submissions(cc_name=cc_name)
        st.markdown(f"**已提交：{len(existing)} 通**")
        for sub in existing:
            status_emoji = "✅" if sub["status"] == "scored" else "⏳"
            comp = db.get_composite_score(sub)
            admin_str = f" | 管: {sub['admin_score']:.1f}" if sub["admin_score"] is not None else " | 管: 待評"
            label = f"  {status_emoji} [{sub['main_line']}] AI:{sub['ai_score']:.0f} {admin_str} | **綜合:{comp:.1f}**"
            with st.expander(label):
                # 顯示逐維度診斷報告
                if sub.get("ai_detail") and sub.get("ai_detail") != "{}":
                    try:
                        detail = json.loads(sub["ai_detail"])
                        for dim, data in detail.get("dims", {}).items():
                            st.markdown(f"**{dim}** `{data['score']}/{data['max']}` — {data['desc']}")
                            high = data.get("found_high", [])
                            normal = data.get("found_normal", [])
                            missing = data.get("missing_normal", [])
                            if high:  st.success(f"✅ 加分：{' / '.join(high[:6])}")
                            if normal: st.write(f"✅ 已提及：{' / '.join(normal[:8])}")
                            if missing: st.error(f"❌ 缺失：{' / '.join(missing[:5])}")
                            if not high and not normal and not missing: st.write("（無話術記錄）")
                            st.caption(f"💬 {data.get('bonus_summary', '—')}")
                            st.divider()
                        if detail.get("suggestions"):
                            st.markdown("**📝 改進建議**")
                            for s in detail["suggestions"]: st.write(f"- {s}")
                    except Exception:
                        st.info("評分細節載入失敗，請稍後再試")
                else:
                    st.info("AI 評分尚未完成，請稍候...")
                if sub.get("transcript"):
                    with st.expander("📄 文字稿"):
                        st.text_area("", sub["transcript"], height=150, disabled=True, label_visibility="collapsed")

        # ── Step 2：上傳錄音 ──────────────────────────────
        st.divider()
        st.subheader("📤 上傳新錄音")

        col1, col2 = st.columns([1, 2])
        with col1:
            main_line = st.selectbox(
                "📌 主線類型",
                list(MAIN_LINES.keys()),
                index=0,
                format_func=lambda x: f"{x}：{MAIN_LINES[x]}"
            )
        with col2:
            uploaded_file = st.file_uploader(
                "🎧 上傳音頻檔（MP3 / WAV / M4A）",
                type=["mp3", "wav", "m4a", "ogg", "flac"],
            )

        # 阻擋條件：未填中文姓名
        if not matched and not name_cn:
            st.stop()

        if uploaded_file and st.button("🚀 提交錄音", type="primary"):
            safe_name = re.sub(r'\W+', '_', cc_name)
            safe_line  = re.sub(r'\W+', '_', main_line)
            ts = int(time.time())
            ext = os.path.splitext(uploaded_file.name)[1]
            # 命名規則：CC姓名_主線_時間戳.擴展名
            stored_name = f"{safe_name}_{safe_line}_{ts}{ext}"
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            file_path = os.path.join(UPLOAD_DIR, stored_name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.read())

            sid = db.add_submission(cc_name, main_line, uploaded_file.name, stored_name,
                                    name_cn=name_cn, team=team)
            st.success(f"✅ 檔案已上傳，提交成功！")

            with st.spinner("🤖 AI 正在轉寫錄音（Whisper）..."):
                try:
                    model = whisper.load_model("tiny", download_root=os.path.expanduser("~/.cache/whisper"))
                    result = model.transcribe(file_path, language="zh")
                    transcript = result["text"]
                    db.update_transcript(sid, transcript)
                except Exception as e:
                    transcript = f"[轉寫失敗：{e}]（請管理員手動上傳文字稿）"
                    db.update_transcript(sid, transcript)

            with st.spinner("📊 AI 評分中..."):
                import database as _db
                score_result = score_transcript(transcript, main_line)
                _db.update_ai_score(sid, score_result["total"], json.dumps(score_result, ensure_ascii=False))

            st.balloons()
            st.success(f"🎉 評分完成！**AI 評分：{score_result['total']} 分**")
            st.markdown(f"**評語：**{score_result['summary']}")
            if score_result["suggestions"]:
                with st.expander("📝 查看改進建議"):
                    for s in score_result["suggestions"]:
                        st.write(f"- {s}")
            with st.expander("📄 查看 AI 轉寫文字稿"):
                st.text_area("文字稿", transcript, height=200, disabled=True, label_visibility="collapsed")
            with st.expander("🔍 查看逐維度 AI 診斷報告（加分 / 減分分析）"):
                st.info(f"💡 AI評分：真實計算（維度加權合計），請管理員參考診斷報告給出最終評分")
                for dim, data in score_result["dims"].items():
                    with st.container():
                        st.markdown(f"#### {dim} `{data['score']}/{data['max']}`")
                        st.caption(f"📌 {data['desc']}")

                        # ✅ 加分項
                        found_high = data.get("found_high", [])
                        if found_high:
                            st.success(f"✅ **高分表達（加分）：** {' / '.join(found_high[:6])}")
                        else:
                            st.warning("⚠️ **高分表達（加分）：** 未找到，建議提升")

                        # ✅ 已提及
                        found_normal = data.get("found_normal", [])
                        if found_normal:
                            st.write(f"✅ **已提及：** {' / '.join(found_normal[:8])}")
                        else:
                            st.write("⚠️ **已提及：** 未找到任何基礎話術")

                        # ❌ 缺失
                        missing = data.get("missing_normal", [])
                        if missing:
                            st.error(f"❌ **缺失話術（減分）：** {' / '.join(missing[:5])}")
                        else:
                            st.write("✅ **缺失話術：** 無，維度完整")

                        # 💬 維度小結
                        st.markdown(f"> 💬 {data.get('bonus_summary', '—')}")
                        st.divider()
                if score_result["suggestions"]:
                    st.markdown("### 📝 AI 改進建議")
                    for s in score_result["suggestions"]:
                        st.write(f"- {s}")
            st.rerun()

# ════════════════════════════════════════════════════════
# ③ 即時排名
# ════════════════════════════════════════════════════════
elif page == "📊 即時排名":
    st.title("📊 即時排名")
    from config import TEAMS

    tab1, tab2 = st.tabs(["🏅 團隊排名", "👤 個人排名"])

    with tab1:
        st.subheader("團隊總分排行（截至目前）")
        rankings = db.get_team_rankings()
        medal = ["🥇", "🥈", "🥉"]
        for rank, (team, data) in enumerate(rankings, 1):
            m = medal[rank - 1] if rank <= 3 else f"#{rank}"
            is_top = (rank == 1)
            row_cols = st.columns([1, 3, 2, 2])
            with row_cols[0]: st.write(f"**{m}**")
            with row_cols[1]:
                st.write(f"**{team}**")
                st.caption(" | ".join([
                    f"{mm['cc'].replace('51','')}: {mm['avg']:.1f}"
                    for mm in data["members"] if mm["avg"] > 0
                ]))
            with row_cols[2]: st.metric("總分", f"{data['total']:.1f}")
            with row_cols[3]:
                if is_top: st.success("☕ TOP 1!")
                else: st.write(f"差 {rankings[0][1]['total'] - data['total']:.1f} 分")
        if not rankings:
            st.info("尚未有人提交錄音，成為第一個吧！")

    with tab2:
        st.subheader("CC 個人排行榜（取最佳單條）")
        lb = db.get_cc_leaderboard()
        if lb:
            cols = st.columns([1, 2, 2, 2, 3, 2])
            for h, c in zip(["排名","中文姓名","CC姓名","小組","各錄音綜合分","最佳"], cols):
                h and c.write(f"**{h}**")
            for rank, item in enumerate(lb, 1):
                medal = ["🥇","🥈","🥉"]
                m = medal[rank-1] if rank <= 3 else ""
                rc = st.columns([1, 2, 2, 2, 3, 2])
                rc[0].write(f"{m} #{rank}")
                rc[1].write(f"**{item.get('name_cn') or '—'}**")
                rc[2].write(f"`{item['cc']}`")
                rc[3].write(item['team'])
                scores_str = " / ".join([f"{s:.1f}" for s in item['eq3_scores']]) if item['eq3_scores'] else "—"
                rc[4].write(scores_str)
                rc[5].write(f"**{item['eq3_avg']:.1f}**")
        else:
            st.info("尚無評分記錄，請 CC 老師踴躍參賽！")

    st.divider()
    st.caption("⏱ 即時更新 | 單通：AI×60% + 管理員×40% | 個人：所有錄音中最佳綜合分 | 團隊：小組最佳分總和")

# ════════════════════════════════════════════════════════
# ④ 錄音庫（密碼保護）
# ════════════════════════════════════════════════════════
elif page == "📚 錄音庫":
    if not check_library_access():
        st.warning("🔒 此頁面需要密碼，請在左側輸入密碼後訪問")
        st.info("💡 密碼請向管理員索取")
        st.stop()
        st.rerun()

    st.success("✅ 已解鎖錄音庫")
    st.title("📚 錄音庫")

    from config import CC_TO_TEAM, MAIN_LINES, UPLOAD_DIR

    # 讀取所有提交記錄
    all_subs = db.get_submissions()
    if not all_subs:
        st.info("目前尚無任何錄音記錄")
        st.stop()

    # 篩選器
    filter_cc = st.selectbox(
        "👤 依 CC 姓名篩選",
        ["全部"] + sorted(set(s["cc_name"] for s in all_subs))
    )
    filter_line = st.selectbox(
        "📌 依主線篩選",
        ["全部"] + list(MAIN_LINES.keys())
    )

    filtered = [
        s for s in all_subs
        if (filter_cc == "全部" or s["cc_name"] == filter_cc)
        and (filter_line == "全部" or s["main_line"] == filter_line)
    ]

    st.markdown(f"**共 {len(filtered)} 筆錄音記錄**")

    # 按 CC 姓名分組顯示
    grouped = {}
    for s in filtered:
        key = s["cc_name"]
        grouped.setdefault(key, []).append(s)

    for cc_name, subs in sorted(grouped.items(), key=lambda x: x[0]):
        team = CC_TO_TEAM.get(cc_name, "")
        with st.expander(f"**{cc_name.replace('51','')}**（{team}）— {len(subs)} 通錄音"):
            for sub in sorted(subs, key=lambda x: x["submitted_at"], reverse=True):
                composite = db.get_composite_score(sub)
                score_badge = "✅" if sub["status"] == "scored" else "⏳"
                st.markdown(f"""
                <div style="border-left:4px solid #4CAF50;padding:8px 12px;margin:6px 0;background:#f9f9f9;border-radius:4px">
                <b>{score_badge} {sub['main_line']}</b> &nbsp;|&nbsp;
                AI <b>{sub['ai_score']:.1f}</b> 分
                &nbsp;|&nbsp; 綜合 <b>{composite:.1f}</b> 分
                &nbsp;|&nbsp; <code>{sub['submitted_at'][:16].replace('T',' ')}</code>
                &nbsp;|&nbsp; 原始檔名：<code>{sub['filename']}</code>
                </div>
                """, unsafe_allow_html=True)

                # 音頻播放
                audio_path = os.path.join(UPLOAD_DIR, sub["file_path"])
                if os.path.exists(audio_path):
                    st.audio(open(audio_path, "rb").read(), format="audio/mp3")
                else:
                    st.caption(f"⚠️ 音頻檔案未找到：{sub['file_path']}")

                # 文字稿
                if sub.get("transcript"):
                    with st.expander("📝 文字稿"):
                        st.text(sub["transcript"])

                # AI評分維度
                if sub.get("ai_detail") and sub["status"] == "scored":
                    try:
                        ai_detail = json.loads(sub["ai_detail"])
                        if ai_detail.get("dims"):
                            with st.expander("🔍 AI評分詳情"):
                                for dim, data in ai_detail["dims"].items():
                                    pct = data["score"] / data["max"] * 100
                                    bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                                    st.write(f"{dim} `{data['score']}/{data['max']}` [{bar}] {pct:.0f}%")
                    except Exception:
                        pass

                st.markdown("---")

    # 批量下載提示
    st.divider()
    st.markdown(f"""
    **💡 提示**
    - 錄音命名規則：`CC姓名_主線_上傳時間戳.擴展名`
    - 如需批量導出，請聯繫管理員使用後台工具
    """)

# ════════════════════════════════════════════════════════
# ⑤ 評分標準
# ════════════════════════════════════════════════════════
elif page == "📋 評分標準":
    st.title("📋 評分標準")
    st.markdown("""
    以下為本次比賽的 **評分維度說明**。不同主線適用不同維度組合，
    AI評分根據維度真實計算（基礎分 + 高分話術加分），滿分 **100 分**。
    """)
    st.divider()

    # 五維度詳細說明
    DIM_DETAILS = [
        {
            "name": "① 服務墊高",
            "emoji": "🌟",
            "max": 20,
            "desc": "稱讚孩子 / 展示老師對孩子的關注，讓家長感受到「老師真的很懂我的孩子」（首通核心維度）",
            "look_for": [
                "「老師特別稱讚了孩子」：直接引用老師原話，是最強的破冰武器",
                "「不是要一百分，而是要敢開口、敢表達」：引導家長認同課程核心價值",
                "「英語思維」：自然帶出專業詞彙，讓家長感受老師的專業視角",
                "「我特別想要跟您聊一下」：表達老師主動關懷，不是流水線客服",
                "先認同家長，再補充專業價值：先說「媽媽我懂您」再給專業建議",
            ],
            "high_keywords": ["老師特別稱讚了孩子","不是要一百分","敢開口","敢表達","英語思維","我特別想要跟您聊一下","系統裡看到","我想要跟您分享一下"],
            "low_keywords": [],
            "high_script": {
                "speaker": "老師",
                "text": "那我想請問一下，孩子之前有接觸過英文嗎？他是屬於那種比較活潑、願意多說的孩子，還是說一開始會比較需要時間觀察的那種？我了解之後，之後跟老師溝通時可以特別注意這些部分。"
            },
            "low_script": {
                "speaker": "老師",
                "text": "您好，這邊有一個轉介紹的活動，推薦成功可以獲得獎勵，請問您有朋友想學英文嗎？"
            },
        },
        {
            "name": "② 需求引導",
            "emoji": "🤝",
            "max": 30,
            "desc": "自然引出家長需求；首通時問孩子個性（活潑/害羞）並引導家長說出教育期待",
            "look_for": [
                "問孩子個性：「活潑」或「害羞」的回答，直接影響後續輔導方向",
                "引導家長說出教育觀：「不是要一百分，而是要敢開口」，讓家長自己認同課程價值",
                "自然帶出「英語思維」：不要硬背，而是讓家長覺得這個概念很專業",
                "TOP老師慣性：先認同家長，再補充專業價值",
                "「我了解之後」：表達會針對孩子情況做差異化服務",
            ],
            "high_keywords": ["孩子之前有接觸過英文嗎","活潑","害羞","需要時間觀察","我了解之後","之後跟老師溝通","敢開口","英語思維","不是要一百分"],
            "low_keywords": [],
            "high_script": {
                "speaker": "老師",
                "text": "媽媽我懂您的想法，您不是要一個只會考試的孩子，而是希望他敢開口、敢表達對吧？其實這也是我們課程最核心的價值——不是分數，是讓孩子有英語思維，看到英文就知道怎麼回應，這個是很大的進步。"
            },
            "low_script": {
                "speaker": "老師",
                "text": "您好，我們有一個推薦活動，推薦成功報名可以獲得獎勵，請問您有沒有朋友想報名？"
            },
        },
        {
            "name": "③ 雙向利益",
            "emoji": "🎁",
            "max": 20,
            "desc": "清楚說明：對朋友的好處 + 對自己的好處，消除「推薦是佔朋友便宜」的顧慮",
            "look_for": [
                "對朋友的好處：「他可以拿到和您一模一樣的優惠」、「免費試聽」",
                "對自己的好處：「推薦一位獲得2堂課，推薦三位獲得5堂課」",
                "具體數字而非模糊表述：「2堂/5堂」比「豐厚獎勵」更有說服力",
                "信任背書：「推薦朋友不是在佔便宜，而是在分享好的東西」",
            ],
            "high_keywords": ["朋友可以拿到","朋友的好處","朋友報名","一模一樣的優惠","同等級的服務","推薦一位成功","推薦三位","五堂課","兩堂課獎勵"],
            "low_keywords": [],
            "high_script": {
                "speaker": "老師",
                "text": "他可以拿到和您一模一樣的優惠，推薦一位成功報名您可以獲得兩堂課的獎勵，推薦三位就是五堂課，這個月活動名額有限。"
            },
            "low_script": {
                "speaker": "老師",
                "text": "推薦成功可以獲得獎勵，具體福利請看海报。"
            },
        },
        {
            "name": "④ 行動閉環",
            "emoji": "🎯",
            "max": 25,
            "desc": "【付款當下/權益兌換】索取聯絡方式 / 主動發送連結 / 老師親自出擊\n【首通】引導家長自己說出教育觀，建立價值認同",
            "look_for": [
                "─── 付款當下/權益兌換：索取行動 ───",
                "索取電話：「您把他的電話給我，我親自打給他」",
                "拿走操作負擔：「做完截圖給我，我來確認」",
                "設定跟進：「優惠這個月內有效，我記錄一下，到時候再找您」",
                "降低行動成本：「您什麼都不用管，我來服務」",
                "─── 首通：價值認同 ───",
                "引導家長說出教育觀：「您覺得孩子敢開口，和考一百分，哪個更重要？」",
                "讓家長自己認同：「您也是這樣想的對吧？英語思維比考試更重要」",
                "先認同再補充：「是的，同時...」「沒錯，而且...」",
                "自然帶出「英語思維」：讓家長感受專業，不硬背",
            ],
            "high_keywords": ["我親自打給他","我親自服務","我來處理","把電話給我","把聯絡方式給我","您什麼都不用管","我安排好","我來安排","馬上聯繫","立刻聯絡","不是要一百分","敢開口敢表達","英語思維","是的，同時","沒錯，而且","您也是這樣想的對吧"],
            "low_keywords": [],
            "high_script": {
                "speaker": "老師（付款當下）",
                "text": "您把他的電話給我，我親自打給他，他試聽完我親自服務，您什麼都不用管。"
            },
            "low_script": {
                "speaker": "老師",
                "text": "優惠連結我發給您，您自己分享給朋友就好。"
            },
        },
        {
            "name": "⑤ 抗拒處理",
            "emoji": "🛡",
            "max": 15,
            "desc": "⚠️ 前置條件：家長需先表達抗拒（沒時間/不需要/太貴等），老師再化解才算處理",
            "look_for": [
                "⚠️ 重要邏輯：家長未表達任何抗拒 → 此維度 0 分（無需處理）",
                "「沒有朋友要學」→「我把連結發給您，半年內都有效，有需要再分享」",
                "「不好意思推薦」→「這個不是推銷，是給朋友一個免費試聽的機會」",
                "「不知道怎麼說」→「您就把連結分享過去，什麼都不用管」",
                "「我再想想」→「不急，先記錄下來，有需要找我」",
                "化解 1 次 → 40%分，化解 2 次 → 70%，化解 3+ 次 → 100%",
            ],
            "high_keywords": ["我完全理解","完全了解","沒有關係","先了解看看","不影響","不強求","不會為難","隨時可以","決定權在您","考慮一下沒關係","先加微信","先留個聯絡"],
            "low_keywords": [],
            "high_script": {
                "speaker": "老師",
                "text": "我完全理解您的想法。這個優惠半年內都有效，我先記錄一下，有需要再找我。千萬不要等到月底，因為活動名額是限量的。"
            },
            "low_script": {
                "speaker": "老師",
                "text": "那您再想想吧，謝謝。"
            },
        },
    ]

    for dim in DIM_DETAILS:
        with st.expander(f"{dim['emoji']} **{dim['name']}** — 滿分 {dim['max']} 分", expanded=True):
            st.markdown(f"**核心定義：**{dim['desc']}")

            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown("**✅ 評分重點（找到這些話術特徵加分）**")
                for item in dim["look_for"]:
                    st.write(f"- {item}")

            with col2:
                st.markdown("**🔑 高分關鍵詞**")
                st.write("、".join([f"`{kw}`" for kw in dim["high_keywords"]]))

            st.divider()

            # 高分 vs 低分範例對比
            st.markdown("**📊 高分話術 vs 低分話術 示範**")
            ex1, ex2 = st.columns([1, 1])
            with ex1:
                st.success(f"🌟 高分範例（{dim['high_script']['speaker']}）")
                st.markdown(f"> 「{dim['high_script']['text']}」")
            with ex2:
                st.error(f"⚠️ 低分範例（{dim['low_script']['speaker']}）")
                st.markdown(f"> 「{dim['low_script']['text']}」")

            st.markdown("---")

    # 維度滿分說明
    st.subheader("📐 各主線維度滿分配置")
    st.markdown("""
    AI評分維度加總均為 **90分**，歸一化到百分制（×100/90）。

    | 維度 | 原始滿分 | 首通 | 付款當下 | 權益兌換 |
    |------|:-------:|:----:|:--------:|:--------:|
    | ① 服務墊高 | 20 | ✅ | — | ✅ |
    | ② 需求引導 | 30 | ✅ | ✅ | ✅ |
    | ③ 雙向利益 | 20 | — | ✅ | ✅ |
    | ④ 行動閉環 | 25 | ✅ | ✅ | ✅ |
    | ⑤ 抗拒處理 | 15 | ✅ | ✅ | ✅ |
    | **合計** | **90** | **90** | **90** | **90** |

    #### 加分機制
    每命中一個 **高分話術關鍵詞**，該維度額外 **+5 分**（上限為維度原始滿分）。
    """)

    # 四種抗拒處理話術
    st.subheader("🛡 四種常見抗拒 — 標準應對話術")
    RESISTANCES = [
        {
            "situation": "😕 家長說「沒有朋友要學」",
            "script": "「我了解，媽媽。現在身邊朋友的需求不一定一樣，這個不急。我先把這個連結路徑發給您，如果有朋友剛好聊到這個話題，您就可以馬上分享給他——這個優惠半年內都有效的。」",
            "背後邏輯": "不施壓，但保留行動路徑",
        },
        {
            "situation": "😣 家長說「不好意思推薦」",
            "script": "「我懂媽媽的想法。您是覺得推薦朋友就好像在推銷對吧？但其實您想想，您是真的覺得這個課程對孩子有幫助才會介紹的對嗎？朋友拿到的是一樣的優惠，不是您在佔他便宜，這個是給他一個免費試聽的機會。」",
            "背後邏輯": "重新框架：推薦=幫朋友，不是推銷",
        },
        {
            "situation": "🤷 家長說「我不知道怎麼介紹」",
            "script": "「不需要您特別介紹啦，您就把孩子的試聽連結直接分享到LINE群或私訊，朋友點進去就可以試聽了，他試聽完我親自服務，您什麼都不用管。」",
            "背後邏輯": "降低行動成本，什麼都不用家長做",
        },
        {
            "situation": "⏳ 家長說「我再想想」",
            "script": "「好的，媽媽這個不急。優惠的話這個月內都有效，我這邊先幫您記錄一下，到時候您有想法了隨時找我就好。不過我特別想要提醒您的是——如果您身邊真的有朋友想試，千萬不要等到月底，因為活動名額是限量的。」",
            "背後邏輯": "不施壓 + 輕微時間壓力（有事實依據）",
        },
    ]

    for r in RESISTANCES:
        with st.expander(f"{r['situation']}"):
            st.markdown(f"**✅ 標準話術：**")
            st.info(f"「{r['script']}」")
            st.markdown(f"**🧠 背後邏輯：** {r['背後邏輯']}")

    st.divider()
    st.caption("📋 評分標準版本：v1.0 | 比賽時間：Q2 2026 | 如有疑問請聯繫管理員")

# ════════════════════════════════════════════════════════
# ⑥ 管理員評分
# ════════════════════════════════════════════════════════
elif page == "👑 管理員評分":
    if not check_admin():
        st.warning("請在左側輸入管理員密碼以訪問評分介面")
        st.stop()
    else:
        st.success("✅ 管理員模式已啟用")
        st.title("👑 管理員評分面板")
        st.info(
            "📐 **評分說明：** 單通綜合分 = AI評分×60% + 管理員評分×40% "
            "｜個人：所有錄音中取最佳 ｜團隊總分 = 小組最佳分總和"
        )

        pending = db.get_pending_admin()
        scored = db.get_scored_admin()

        tab1, tab2 = st.tabs([f"⏳ 待評分 ({len(pending)})", f"✅ 已評分 ({len(scored)})"])

        with tab1:
            if not pending:
                st.info("目前無待評分錄音")
            for sub in pending:
                composite = db.get_composite_score(sub)
                with st.expander(
                    f"`{sub['cc_name']}` — [{sub['main_line']}] "
                    f"| AI:100 | 當前綜合: **{composite:.1f}** | {sub['filename']}"
                ):
                    # 顯示文字稿
                    if sub.get("transcript"):
                        with st.expander("📝 AI 轉寫文字稿", expanded=False):
                            st.text_area("文字稿", sub["transcript"], height=150, disabled=True, label_visibility="collapsed")

                    # 顯示 AI 診斷（如果有）
                    ai_detail_raw = sub.get("ai_detail", "{}")
                    try:
                        ai_detail = json.loads(ai_detail_raw) if ai_detail_raw else {}
                    except Exception:
                        ai_detail = {}
                    if ai_detail and ai_detail.get("dims"):
                        with st.expander("🔍 AI 逐維度診斷報告（請參考）", expanded=True):
                            for dim, data in ai_detail["dims"].items():
                                found_high = data.get("found_high", [])
                                found_normal = data.get("found_normal", [])
                                missing = data.get("missing_normal", [])
                                st.markdown(f"**{dim}** `{data['score']}/{data['max']}`")
                                if found_high:
                                    st.success(f"✅ 高分表達：`{'/'.join(found_high[:5])}`")
                                if found_normal:
                                    st.write(f"✅ 已提及：`{'/'.join(found_normal[:6])}`")
                                if missing:
                                    st.error(f"❌ 缺失：`{'/'.join(missing[:4])}`")
                                st.caption(f"💬 {data.get('bonus_summary','')}")
                                st.divider()

                    st.markdown("---")
                    st.markdown(f"📐 **評分說明：** 綜合分 = AI評分×60% + 管理員評分×40%")
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        admin_score = st.number_input(
                            "👑 管理員評分（0-100）",
                            min_value=0.0, max_value=100.0, step=0.5,
                            value=50.0,
                            key=f"admin_score_{sub['id']}"
                        )
                    with col2:
                        comment = st.text_input("📝 評語（可選）", key=f"comment_{sub['id']}")
                    col_preview, _ = st.columns([1, 1])
                    with col_preview:
                        st.metric("💡 儲存後單通綜合分", f"{60 + admin_score * 0.4:.1f}")
                    if st.button("💾 儲存評分", key=f"save_{sub['id']}"):
                        db.update_admin_score(sub["id"], admin_score, comment)
                        st.success("✅ 已儲存！")
                        st.rerun()

        with tab2:
            for sub in scored:
                composite = db.get_composite_score(sub)
                with st.expander(
                    f"`{sub['cc_name']}` — [{sub['main_line']}] "
                    f"| AI:100 | 管:{sub['admin_score']:.1f} "
                    f"| **綜合 {composite:.1f}**"
                ):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        new_score = st.number_input(
                            "覆寫管理員評分",
                            min_value=0.0, max_value=100.0, step=0.5,
                            value=float(sub["admin_score"]) if sub["admin_score"] is not None else 50.0,
                            key=f"override_{sub['id']}"
                        )
                        new_comment = st.text_input(
                            "評語",
                            value=sub.get("admin_comment", ""),
                            key=f"comment_override_{sub['id']}"
                        )
                    with col2:
                        ai_detail = {}
                        try:
                            ai_detail = json.loads(sub.get("ai_detail", "{}"))
                        except Exception:
                            pass
                        if ai_detail.get("dims"):
                            for dim, data in ai_detail["dims"].items():
                                st.write(f"{dim}: {data['score']}/{data['max']}")
                    if st.button("🔄 更新評分", key=f"update_{sub['id']}"):
                        db.update_admin_score(sub["id"], new_score, new_comment)
                        st.success("已更新！")
                        st.rerun()

        st.divider()
        if st.button("📥 導出所有評分結果（CSV）"):
            import csv
            all_subs = db.get_submissions()
            path = "contest_results.csv"
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "id","cc_name","team","main_line","filename",
                    "ai_score","admin_score","composite","submitted_at"
                ])
                w.writeheader()
                for s in all_subs:
                    s["team"] = CC_TO_TEAM.get(s["cc_name"], "")
                    s["composite"] = db.get_composite_score(s)
                    w.writerow(s)
            st.success(f"已導出：{path}")
            st.download_button("下載 CSV", open(path, "rb"), path, "text/csv")
