#!/usr/bin/env python3
"""
世界杯实时比分爬虫
==================
数据源：ESPN 公开 Scoreboard API（无需 API Key）
每小时抓取一次 FIFA World Cup 比赛结果，输出为前端可直接读取的 data.json。

规则：
- 常规时间（90 分钟 + 伤停补时）比分决定庄/闲/和
- 点球大战只决定晋级，不计入赛果，按常规时间平局处理
- 仅保留已完成（FINISHED）的比赛

环境变量：
  ESPN_API_URL   默认 https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.worldcup/scoreboard
  OUTPUT_PATH    默认 data.json
  USE_MOCK       设置为 1 时输出模拟数据（测试用）
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# -------------------- 配置 --------------------
ESPN_API_URL = os.environ.get(
    "ESPN_API_URL",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard",
)
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "data.json"))
USE_MOCK = os.environ.get("USE_MOCK", "0") == "1"

# 请求头：模拟浏览器，降低被封概率
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


# -------------------- 工具函数 --------------------
def log(message: str) -> None:
    """带时间戳的标准输出。"""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{now}] {message}", flush=True)


def fetch_json(url: str, timeout: int = 30) -> dict:
    """使用标准库 GET JSON 数据。"""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw.decode("utf-8"))


def get_regular_time_score(competitor: dict) -> int:
    """
    获取常规时间比分。
    ESPN 的 linescores[0].value 通常为常规时间（90分钟+补时）进球数；
    淘汰赛若进入加时/点球，总比分会放在 score 字段，因此优先取第一节。
    """
    linescores = competitor.get("linescores") or []
    if linescores:
        return int(linescores[0].get("value", 0))
    return int(competitor.get("score", 0) or 0)


def parse_event(event: dict) -> dict | None:
    """把 ESPN event 解析为前端需要的统一格式。"""
    competitions = event.get("competitions", [])
    if not competitions:
        return None

    competition = competitions[0]
    competitors = competition.get("competitors", [])
    if len(competitors) < 2:
        return None

    home = next((c for c in competitors if c.get("homeAway") == "home"), None)
    away = next((c for c in competitors if c.get("homeAway") == "away"), None)
    if not home or not away:
        return None

    status_type = event.get("status", {}).get("type", {})
    completed = status_type.get("completed", False)
    if not completed:
        return None

    home_reg = get_regular_time_score(home)
    away_reg = get_regular_time_score(away)

    # 阶段名称：优先用 ESPN 提供的赛事类型缩写，否则用通用名称
    stage = competition.get("type", {}).get("abbreviation") or "世界杯"

    return {
        "id": str(event.get("id", "")),
        "stage": stage,
        "home_team": home.get("team", {}).get("displayName", "主队"),
        "away_team": away.get("team", {}).get("displayName", "客队"),
        # 总比分（含加时），保留但不参与庄闲判定
        "home_score": int(home.get("score", 0) or 0),
        "away_score": int(away.get("score", 0) or 0),
        # 常规时间比分，前端用它判定庄/闲/和
        "regular_time_home_score": home_reg,
        "regular_time_away_score": away_reg,
        "date": (event.get("date") or "")[:10],
        "status": "FINISHED",
    }


def generate_mock_data() -> dict:
    """当真实接口不可用时，生成若干模拟比赛（仅用于首次测试）。"""
    log("USE_MOCK=1，生成模拟数据")
    return {
        "matches": [
            {
                "id": "mock-001",
                "stage": "小组赛A组",
                "home_team": "卡塔尔",
                "away_team": "厄瓜多尔",
                "home_score": 0,
                "away_score": 2,
                "regular_time_home_score": 0,
                "regular_time_away_score": 2,
                "date": "2026-06-12",
                "status": "FINISHED",
            },
            {
                "id": "mock-002",
                "stage": "小组赛B组",
                "home_team": "英格兰",
                "away_team": "伊朗",
                "home_score": 6,
                "away_score": 2,
                "regular_time_home_score": 6,
                "regular_time_away_score": 2,
                "date": "2026-06-13",
                "status": "FINISHED",
            },
            {
                "id": "mock-003",
                "stage": "小组赛A组",
                "home_team": "塞内加尔",
                "away_team": "荷兰",
                "home_score": 0,
                "away_score": 2,
                "regular_time_home_score": 0,
                "regular_time_away_score": 2,
                "date": "2026-06-13",
                "status": "FINISHED",
            },
            {
                "id": "mock-004",
                "stage": "小组赛B组",
                "home_team": "美国",
                "away_team": "威尔士",
                "home_score": 1,
                "away_score": 1,
                "regular_time_home_score": 1,
                "regular_time_away_score": 1,
                "date": "2026-06-13",
                "status": "FINISHED",
            },
        ]
    }


def load_existing_data(path: Path) -> dict:
    """读取已有的 data.json，用于合并而非覆盖。"""
    if not path.exists():
        return {"matches": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {"matches": data}
            return data
    except (json.JSONDecodeError, OSError) as e:
        log(f"读取已有数据失败：{e}，将重新生成")
        return {"matches": []}


def merge_matches(existing: list, new: list) -> list:
    """以 id 为唯一键合并，保留旧数据中的已完成比赛。"""
    by_id = {m["id"]: m for m in existing if "id" in m}
    for m in new:
        if "id" in m:
            by_id[m["id"]] = m
    return list(by_id.values())


# -------------------- 主流程 --------------------
def main() -> int:
    log(f"开始抓取：{ESPN_API_URL}")
    log(f"输出文件：{OUTPUT_PATH.resolve()}")

    if USE_MOCK:
        payload = generate_mock_data()
    else:
        try:
            api_data = fetch_json(ESPN_API_URL)
            events = api_data.get("events", [])
            log(f"ESPN 返回 {len(events)} 场比赛")

            matches = []
            for ev in events:
                parsed = parse_event(ev)
                if parsed:
                    matches.append(parsed)
            log(f"解析出 {len(matches)} 场已完成比赛")
            payload = {"matches": matches}
        except urllib.error.HTTPError as e:
            log(f"ESPN API HTTP 错误：{e.code} {e.reason}")
            log("保留现有 data.json 不变")
            return 1
        except urllib.error.URLError as e:
            log(f"网络错误：{e.reason}")
            log("保留现有 data.json 不变")
            return 1
        except Exception as e:
            log(f"抓取异常：{e}")
            log("保留现有 data.json 不变")
            return 1

    # 合并旧数据
    existing = load_existing_data(OUTPUT_PATH)
    merged = merge_matches(existing.get("matches", []), payload.get("matches", []))
    output = {"matches": merged}

    # 写入
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    log(f"写入完成，共 {len(merged)} 场比赛")
    return 0


if __name__ == "__main__":
    sys.exit(main())
