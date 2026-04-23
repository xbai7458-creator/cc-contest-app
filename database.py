# -*- coding: utf-8 -*-
"""JSON 資料庫（兼容 SQLite 介面）— 用於 Streamlit Cloud"""
import json, os, copy
from datetime import datetime, timedelta

# 修正時區：Streamlit Cloud 伺服器UTC，+8 → 台灣時間
def now_str():
    return (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")

DATA_FILE = "submissions.json"


def _load():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save(rows):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════
#  初始化（保證欄位完整）
# ══════════════════════════════════════════

def init_db():
    pass  # JSON 版不需要初始化建表


# ══════════════════════════════════════════
#  讀寫操作
# ══════════════════════════════════════════

def add_submission(cc_name, main_line, filename, file_path,
                   name_cn="", team=""):
    from config import CC_INFO, CC_TO_TEAM
    if not name_cn:
        name_cn = CC_INFO.get(cc_name, {}).get("name_cn", "")
    if not team:
        team = CC_TO_TEAM.get(cc_name, "")

    rows = _load()
    new_id = (max([r["id"] for r in rows]) + 1) if rows else 1
    row = {
        "id": new_id,
        "cc_name": cc_name,
        "name_cn": name_cn,
        "team": team,
        "main_line": main_line,
        "filename": filename,
        "file_path": file_path,
        "transcript": "",
        "ai_score": 0,
        "ai_detail": "{}",
        "admin_score": None,
        "admin_comment": "",
        "submitted_at": now_str(),
        "status": "pending",
    }
    rows.append(row)
    _save(rows)
    return new_id


def get_submissions(cc_name=None, status=None):
    rows = _load()
    result = []
    for r in rows:
        match = True
        if cc_name and r.get("cc_name", "").lower() != cc_name.lower():
            match = False
        if status and r.get("status") != status:
            match = False
        if match:
            result.append(r)
    return sorted(result, key=lambda x: x.get("submitted_at", ""), reverse=True)


def update_transcript(submission_id, transcript):
    rows = _load()
    for r in rows:
        if r["id"] == submission_id:
            r["transcript"] = transcript
            break
    _save(rows)


def update_ai_score(submission_id, score, detail_json):
    rows = _load()
    for r in rows:
        if r["id"] == submission_id:
            r["ai_score"] = round(score, 1)
            r["ai_detail"] = detail_json
            r["status"] = "scored"
            break
    _save(rows)


def update_admin_score(submission_id, score, comment):
    rows = _load()
    for r in rows:
        if r["id"] == submission_id:
            r["admin_score"] = score
            r["admin_comment"] = comment
            break
    _save(rows)


def get_pending_admin():
    return [r for r in _load()
            if r.get("admin_score") is None]


def get_scored_admin():
    return [r for r in _load()
            if r.get("admin_score") is not None]


def get_composite_score(sub):
    ai_score = sub.get("ai_score") or 0
    admin = sub.get("admin_score")
    ai_contribution = ai_score * 0.6
    if admin is not None:
        return round(ai_contribution + admin * 0.4, 1)
    return round(ai_contribution, 1)


def get_equal3_for_cc(cc_name):
    rows = _load()
    cc_rows = [r for r in rows
               if r.get("cc_name", "").lower() == cc_name.lower()]
    composites = [get_composite_score(r) for r in cc_rows]
    n = len(composites)
    if n == 0:
        return composites, 0.0
    return composites, round(max(composites), 1)


def get_team_rankings():
    from config import CC_INFO
    team_scores = {}
    for cc_name, info in CC_INFO.items():
        team = info["team"]
        if team not in team_scores:
            team_scores[team] = {"total": 0.0, "members": []}
        _, cc_avg = get_equal3_for_cc(cc_name)
        team_scores[team]["members"].append({"cc": cc_name, "avg": cc_avg})
        team_scores[team]["total"] += cc_avg
    for team in team_scores:
        team_scores[team]["total"] = round(team_scores[team]["total"], 1)
    return sorted(team_scores.items(),
                  key=lambda x: x[1]["total"], reverse=True)


def get_cc_leaderboard():
    from config import CC_TO_TEAM, CC_INFO
    rows = _load()
    cc_map = {}
    for r in rows:
        cc = r["cc_name"]
        if cc not in cc_map:
            cc_map[cc] = {
                "cc": cc,
                "name_cn": r.get("name_cn") or CC_INFO.get(cc, {}).get("name_cn", ""),
                "team": r.get("team") or CC_TO_TEAM.get(cc, ""),
                "scores": [],
            }
        cc_map[cc]["scores"].append(get_composite_score(r))

    results = []
    for cc, data in cc_map.items():
        composites = data["scores"]
        results.append({
            "cc": cc,
            "name_cn": data["name_cn"],
            "team": data["team"],
            "eq3_scores": composites,
            "eq3_avg": round(max(composites), 1) if composites else 0.0,
            "submitted_count": len(composites),
        })
    return sorted(results, key=lambda x: x["eq3_avg"], reverse=True)
