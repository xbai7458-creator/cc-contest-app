# -*- coding: utf-8 -*-
"""AI 評分引擎：按主線維度 + 關鍵詞命中真實計算分數"""
import re, json
from config import SCORING_DIMS, LINE_DIMS, DIM_MAX

# 維度權重：LINE_DIMS 各維度加總 = 90，歸一化到百分制
TOTAL_DIM_WEIGHT = sum(DIM_MAX[d] for d in SCORING_DIMS)


def score_transcript(transcript: str, main_line: str = "首通") -> dict:
    """
    根據 main_line 調用對應維度，真實計算 AI 分數（0-100）。
    - 基礎分：關鍵詞命中越多，分數越高（基礎分比例）
    - 加分：命中高分話術關鍵詞 → 維度加 5 分（上限不超過維度原始滿分）
    """
    if not transcript or len(transcript.strip()) < 10:
        return {
            "total": 0,
            "dims": {},
            "summary": "文字稿太短，無法評估",
            "suggestions": []
        }

    text = transcript
    dims_config = LINE_DIMS.get(main_line, LINE_DIMS["首通"])
    raw_total = 0.0  # 原始加總（未歸一化）

    results = {}
    for dim_name in dims_config:
        dim_cfg = SCORING_DIMS[dim_name]
        dim_result = _score_dim(text, dim_cfg, dim_name, main_line=main_line)
        results[dim_name] = dim_result
        raw_total += dim_result["raw_score"]

    # 歸一化到百分制
    total = round(raw_total / TOTAL_DIM_WEIGHT * 100, 1)
    total = min(100.0, max(0.0, total))

    # 收集建議
    suggestions = _generate_suggestions(results, main_line)
    summary = _generate_summary(results, total, main_line)

    return {
        "total": total,
        "dims": results,
        "summary": summary,
        "suggestions": suggestions,
        "main_line": main_line,
    }


# ──────────────────────────────────────────────
#  ⑤抗拒處理：家長先有抗拒 → 老師再化解，才算處理
#  若家長全程未表達任何抗拒，則此維度不應得分（視為「無需處理」）
# ──────────────────────────────────────────────
RESISTANCE_PATTERNS = [
    # 家長說「沒有...」
    "沒有", "沒時間", "沒興趣", "沒需要", "沒考慮",
    "不需要", "不要", "不用了", "不考慮", "不想要",
    "不會", "不行", "不可以", "不允許",
    "太貴", "太忙", "來不及", "過不了",
    # 家長說「我覺得/我想...」
    "我再想想", "我再考慮", "我再看看",
    "之後再說", "過段時間", "最近不方便",
    "改天", "等一下", "先不要",
    # 家長說「已經...」
    "已經報名", "已經在上", "已經學了", "已經有",
    "小孩沒時間", "孩子沒時間",
    # 家長說「身邊沒有」
    "身邊沒有", "身邊朋友", "認識的人",
    "我身邊沒有",
]

SOOTHING_PATTERNS = [
    # 老師說「理解」
    "理解", "了解", "我懂", "我完全理解", "完全了解",
    # 老師說「不強求」
    "不強求", "不為難", "不影響", "不會為難",
    # 老師說「先了解」
    "先了解", "先看看", "先加", "先留", "先試",
    # 老師說「隨時/任何時候」
    "隨時可以", "任何時候", "等您方便", "您決定",
    # 老師說「考慮一下沒關係」
    "考慮一下", "考慮考慮", "沒關係", "不急",
    # 老師說「不影響」
    "不影響", "不冲突", "不衝突",
]


def _has_parent_resistance(text: str) -> bool:
    """檢測家長是否在文字稿中表達了任何抗拒/顧慮"""
    for pat in RESISTANCE_PATTERNS:
        if pat in text:
            return True
    return False


def _count_soothing(text: str) -> int:
    """統計老師說了幾次化解抗拒的話術"""
    return sum(1 for p in SOOTHING_PATTERNS if p in text)


def _score_dim(text: str, dim_cfg: dict, dim_name: str,
               main_line: str = "首通") -> dict:
    """
    單維度評分：
    - ⑤抗拒處理：家長先有抗拒 → 老師再化解，才算處理
    - ④行動閉環：根據主線自動切換（首通=價值認同，其他=索取行動）
    - 其他維度：基礎分 + 高分話術加分
    """
    # ── ⑤抗拒處理特殊邏輯 ──────────────────────
    if dim_name == "⑤抗拒處理":
        return _score_resistance_dim(text, dim_cfg)

    # ── ④行動閉環特殊邏輯（首通 vs 其他主線）───────
    if dim_name == "④行動閉環":
        return _score_action闭环_dim(text, dim_cfg, main_line)

    # ── 一般維度評分 ───────────────────────────
    keywords  = dim_cfg.get("keywords", [])
    high_kw   = dim_cfg.get("high_score_keywords", [])
    max_score = dim_cfg["max_score"]

    # 關鍵詞命中
    found_normal = [kw for kw in keywords if kw in text]
    found_high   = [kw for kw in high_kw if kw in text]

    # 基礎分：命中比例
    kw_count = len(keywords)
    if kw_count > 0:
        base_ratio = len(found_normal) / kw_count
    else:
        base_ratio = 0.0
    base_score = max_score * base_ratio

    # 加分：高分關鍵詞 × 5
    bonus = len(found_high) * 5
    raw_score = min(max_score, base_score + bonus)  # 上限不超過維度滿分

    # 未命中
    missing_normal = [kw for kw in keywords if kw not in text]

    # 小結文字
    parts = []
    if found_high:
        parts.append(f"✅ 高分話術：{'、'.join(found_high[:5])}")
    if len(found_normal) < 3 and missing_normal:
        parts.append(f"⚠️ 話術偏少（{len(found_normal)}/{len(keywords)}），建議補充：{'、'.join(missing_normal[:3])}")
    if not parts:
        parts.append("✅ 本維度表現正常")

    return {
        "score": round(raw_score, 1),
        "max": max_score,
        "raw_score": raw_score,
        "base_score": round(base_score, 1),
        "bonus": bonus,
        "desc": dim_cfg["desc"],
        "found_high": found_high,
        "found_normal": found_normal,
        "missing_normal": missing_normal,
        "bonus_summary": " | ".join(parts),
    }


def _score_resistance_dim(text: str, dim_cfg: dict) -> dict:
    """
    ⑤抗拒處理維度評分：
    1. 檢測家長是否表達了任何抗拒
    2. 統計老師的化解話術次數
    3. 家長沒說抗拒 → 本維度 0 分（無需處理）
    4. 老師化解次數越多 → 分數越高（上限維度滿分）
    """
    max_score = dim_cfg["max_score"]

    # Step 1：家長是否有抗拒？
    has_resistance = _has_parent_resistance(text)
    if not has_resistance:
        return {
            "score": 0.0,
            "max": max_score,
            "raw_score": 0.0,
            "base_score": 0.0,
            "bonus": 0,
            "desc": dim_cfg["desc"],
            "found_high": [],
            "found_normal": [],
            "missing_normal": [],
            "bonus_summary": "⚠️ 家長未表達任何抗拒（無需處理）→ 此維度不計分",
        }

    # Step 2：老師化解了幾次
    found_normal = []
    for p in SOOTHING_PATTERNS:
        if p in text:
            found_normal.append(p)

    found_high = [p for p in found_normal if any(
        h in p or p in h for h in ["我完全理解", "完全了解", "不強求", "不影響", "不會為難", "考慮一下", "任何時候"]
    )]

    # Step 3：計分
    # 化解 1 次 → 40%，化解 2 次 → 70%，化解 3 次及以上 → 100%
    soothing_count = len(found_normal)
    if soothing_count == 0:
        base_ratio = 0.0
    elif soothing_count == 1:
        base_ratio = 0.4
    elif soothing_count == 2:
        base_ratio = 0.7
    else:
        base_ratio = 1.0

    base_score = max_score * base_ratio

    # 高分化解話術額外加分
    bonus = min(len(found_high) * 5, max_score - base_score)
    raw_score = min(max_score, base_score + bonus)

    # 小結
    parts = []
    parts.append(f"✅ 檢測到家長抗拒：{soothing_count} 處化解回應")
    if found_high:
        parts.append(f"✅ 高分化解：{'、'.join(found_high[:4])}")
    if not found_normal:
        parts.append("❌ 有抗拒但老師未化解")
    parts.append("📌 家長有抗拒才進入此維度評分")

    return {
        "score": round(raw_score, 1),
        "max": max_score,
        "raw_score": raw_score,
        "base_score": round(base_score, 1),
        "bonus": bonus,
        "desc": dim_cfg["desc"],
        "found_high": found_high,
        "found_normal": found_normal,
        "missing_normal": [],
        "bonus_summary": " | ".join(parts),
    }


# ──────────────────────────────────────────────
#  ④行動閉環：首通=價值認同，其他=索取行動
# ──────────────────────────────────────────────

# 首通：價值認同關鍵詞
FIRST_CALL_VALUE_KW = [
    "您覺得", "您希望", "您認為", "您也是",
    "比起", "更重要", "更關心",
    "英語思維", "敢開口", "敢表達",
    "不是要一百分", "一百分", "考試",
    "說出來", "說過",
    "是的", "沒錯", "認同", "而且", "同時",
    "對不對", "是嗎", "對吧",
]
FIRST_CALL_VALUE_HIGH = [
    "不是要一百分",
    "敢開口", "敢表達",
    "英語思維",
    "不是要一個只會考試的孩子",
    "敢開口敢表達",
    "是的，同時",
    "沒錯，而且",
    "我很認同您",
    "您也是這樣想的對吧",
]

# 其他主線：索取行動關鍵詞
ACTION_TAKE_KW = [
    "電話", "聯絡", "聯繫",
    "發送", "發給", "給您",
    "連結", "鏈接", "海報",
    "我來", "我親自",
    "您就", "您只管",
    "不用管", "什麼都不用",
]
ACTION_TAKE_HIGH = [
    "我親自", "我來處理",
    "把電話給我", "把聯絡方式給我",
    "您什麼都不用管",
    "我安排好", "我來安排",
    "馬上聯繫", "立刻聯絡",
]


def _score_action闭环_dim(text: str, dim_cfg: dict, main_line: str) -> dict:
    """
    ④行動閉環評分：
    - 首通：價值認同導向（引導家長說出教育觀，敢開口比一百分重要）
    - 付款當下/權益兌換：索取行動導向（電話、連結、老師主動出擊）
    """
    max_score = dim_cfg["max_score"]

    if main_line == "首通":
        # ── 首通：價值認同 ─────────────────────────
        kw   = FIRST_CALL_VALUE_KW
        high = FIRST_CALL_VALUE_HIGH
        desc_tag = "【首通】價值認同"
    else:
        # ── 其他主線：索取行動 ─────────────────────
        kw   = ACTION_TAKE_KW
        high = ACTION_TAKE_HIGH
        desc_tag = "【索取行動】"

    found_normal = [k for k in kw   if k in text]
    found_high   = [k for k in high if k in text]

    base_ratio = len(found_normal) / len(kw) if kw else 0
    base_score = max_score * base_ratio
    bonus      = len(found_high) * 5
    raw_score  = min(max_score, base_score + bonus)

    missing = [k for k in kw if k not in text]

    parts = []
    if found_high:
        parts.append(f"✅ 高分話術：{'、'.join(found_high[:5])}")
    if found_normal:
        parts.append(f"✅ 已提及：{'、'.join(found_normal[:6])}")
    if not found_normal:
        parts.append(f"❌ {desc_tag}話術未出現")
    if missing:
        parts.append(f"📌 建議補充：{'、'.join(missing[:3])}")

    return {
        "score": round(raw_score, 1),
        "max": max_score,
        "raw_score": raw_score,
        "base_score": round(base_score, 1),
        "bonus": bonus,
        "desc": dim_cfg["desc"],
        "found_high": found_high,
        "found_normal": found_normal,
        "missing_normal": missing,
        "bonus_summary": " | ".join(parts) if parts else f"✅ {desc_tag}表現正常",
    }


def _generate_suggestions(results: dict, main_line: str) -> list:
    suggestions = []
    for dim_name, data in results.items():
        found_high   = data.get("found_high", [])
        found_normal = data.get("found_normal", [])
        missing      = data.get("missing_normal", [])
        score        = data.get("score", 0)
        max_s        = data.get("max", 20)
        ratio        = score / max_s if max_s > 0 else 0

        if ratio < 0.4:
            top = missing[:3]
            suggestions.append(
                f"【{dim_name}】{data['desc']} — "
                f"話術不足（{score:.0f}/{max_s}），建議：{'、'.join(top) if top else '加強本維度話術'}"
            )
        elif ratio < 0.7 and not found_high:
            suggestions.append(
                f"【{dim_name}】基本到位，建議提升高分表達（如：「我特別去看了一下孩子最近...」）"
            )
    return suggestions


def _generate_summary(results: dict, total: float, main_line: str) -> str:
    found_high_total = sum(len(d["found_high"]) for d in results.values())
    complete_dims    = sum(1 for d in results.values() if d["score"] / d["max"] >= 0.6)
    total_dims       = len(results)

    if total >= 85:
        return f"🌟 標杆話術：{main_line}五維均表現優異，高分話術命中 {found_high_total} 處，建議作為團隊標竿分享"
    elif complete_dims >= total_dims * 0.75:
        return f"👍 優秀話術：{main_line}大部分維度到位，{complete_dims}/{total_dims} 維度合格，建議補足抗拒處理並提升高分表達頻率"
    elif complete_dims >= total_dims * 0.5:
        return f"💪 基礎話術：{main_line}框架基本成立，{complete_dims}/{total_dims} 維度合格，請對照評分標準逐項加強"
    else:
        return f"⚠️ 待提升話術：{main_line}多個維度話術不足，建議熟讀SOP逐字稿後重新練習提交"


def format_score_report(score_result: dict) -> str:
    """格式化為可讀文本"""
    lines = [f"## 🎯 AI 評分報告（總分 {score_result['total']} / 100）"]
    lines.append("")
    lines.append(score_result["summary"])
    lines.append("")
    for dim_name, data in score_result["dims"].items():
        lines.append(f"### {dim_name}  {data['score']}/{data['max']} 分")
        lines.append(f"📌 {data['desc']}")
        if data["found_high"]:
            lines.append(f"  ✅ **高分話術（加分）**：`{'、'.join(data['found_high'][:6])}`")
        if data["found_normal"]:
            lines.append(f"  ✅ **已提及**：`{'、'.join(data['found_normal'][:8])}`")
        if data["missing_normal"]:
            lines.append(f"  ❌ **缺失**：`{'、'.join(data['missing_normal'][:5])}`")
        lines.append(f"  💬 {data['bonus_summary']}")
        lines.append("")
    if score_result["suggestions"]:
        lines.append("### 📝 改進建議")
        for s in score_result["suggestions"]:
            lines.append(f"- {s}")
    return "\n".join(lines)
