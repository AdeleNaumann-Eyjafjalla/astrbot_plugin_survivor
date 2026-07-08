"""
末日生存游戏 - 大模型事件生成器

通过 AstrBot 内置 LLM 按需生成随机探索事件，充实事件池。
采用预生成 + 缓存策略，减少 API 调用频率。
"""

import random
import json
import time
from typing import Dict, List, Optional, Any

from models import GameEvent, EventType


# 事件缓存
_cached_events: List[GameEvent] = []
_cache_lock = False       # 防止并发刷新
_last_generate_time = 0.0
GENERATE_COOLDOWN = 120   # 2 分钟内不重复调用 LLM（避免意外频繁请求）
MAX_CACHE_SIZE = 300      # 缓存上限（每天补充到 300 个）
REFILL_THRESHOLD = 50     # 低于此数量触发后台补充
BATCH_SIZE = 15           # 每次批量生成的个数（不宜过大，避免 LLM 输出截断）


def cache_size() -> int:
    return len(_cached_events)


def pop_event() -> Optional[GameEvent]:
    """从缓存中随机取一个事件"""
    global _cached_events
    if not _cached_events:
        return None
    idx = random.randrange(len(_cached_events))
    return _cached_events.pop(idx)


# ================================================================
# 系统提示词 —— 指导 LLM 生成符合格式的事件
# ================================================================

SYSTEM_PROMPT = """你是一个末日生存游戏的随机事件生成器。你需要为玩家生成有趣、多样的探索事件。

## 游戏背景
末日废土世界，幸存者要搜集资源、对抗丧尸和掠夺者、应对恶劣天气。玩家有：食物(🍖)、水(💧)、木材(🪵)、石料(🪨)、铁(🔩)、药品(💊)、弹药(🔫)、燃料(⛽) 八种资源。

## 输出格式
你只输出一个 JSON 数组，包含若干事件对象。每个事件的格式：

```json
[
  {
    "name": "事件名称（简短，5-8字）",
    "event_type": "resource|danger|opportunity|weather|social",
    "description": "事件描述文本（1-2句话，告诉玩家发生了什么）",
    "choices": [
      {
        "text": "选项按钮文字（带emoji，简短）",
        "result": {
          "resources": {"资源名": [最小值, 最大值], ...},     // 可省略
          "items": {"物品ID": [最小值, 最大值], ...},         // 可省略，物品ID只能用下述列表中的
          "combat": {"enemy_attack": 攻击力, "enemy_health": 生命},  // 可省略
          "rewards": {"exp": [最小值, 最大值], "items": {...}, "resources": {...}},  // 战斗胜利奖励
          "exp": [最小值, 最大值],       // 可省略
          "heal": 数值,                  // 可省略
          "health_damage": [最小值, 最大值],  // 可省略
          "escape_chance": 0.x,          // 可省略，逃跑成功率
          "stealth_chance": 0.x,         // 可省略，潜行成功率
          "lose_resources": {"资源名": 0.x},  // 可省略，损失比例
          "description": "结果描述",
          "description_win": "战斗胜利描述",
          "description_lose": "战斗失败描述",
          "description_escape": "逃脱成功描述",
          "description_fail": "失败描述"
        }
      }
    ]
  }
]
```

## 可用物品 ID 列表（只能使用这些）
武器: rusty_knife, baseball_bat, hunting_rifle, fire_axe, crossbow, flame_sword
防具: leather_jacket, riot_shield, military_vest
消耗品: canned_food, bottled_water, bandage, first_aid_kit, mre, stimpack, antidote
材料: scrap_metal, cloth, rope, nails, glass, electronics, gunpowder, herb, leather, plastic, wood_plank, matchbox, battery, flashlight
特殊: survivor_journal, radio, molotov, night_gear, firestarter, trap_kit

## 资源名只能用: food, water, wood, stone, iron, medicine, ammo, fuel

## 规则
1. 每个事件给出 2-4 个选项，至少有一个选项是安全的或不选的
2. 奖励数值要合理：资源 (1,5)~(10,30)，物品 (0,1)~(2,5)，exp (10,30)~(80,200)
3. combat 的 enemy_attack 建议 5-30，enemy_health 建议 15-80
4. 高收益的选项对应高风险
5. 根据当前天气和危险等级调整事件难度和内容
6. event_type 分布要多样，不要全是同一种类型
7. 事件描述要生动、有末日氛围，偶尔可以幽默
8. 只输出 JSON 数组，不要输出任何解释文字"""


def _build_user_prompt(season: str, weather: str, danger_level: int, day: int, count: int) -> str:
    """构建用户提示词"""
    season_cn = {"spring": "春季🌸", "summer": "夏季☀️", "autumn": "秋季🍂", "winter": "冬季❄️"}
    weather_cn = {
        "clear": "晴朗", "cloudy": "多云", "rain": "下雨", "storm": "暴风雨",
        "fog": "大雾", "heatwave": "热浪", "cold_snap": "寒潮", "sandstorm": "沙尘暴"
    }
    return (
        f"请生成 {count} 个末日生存随机事件。"
        f"当前群组状态：第 {day} 天，{season_cn.get(season, season)}，天气 {weather_cn.get(weather, weather)}，危险等级 {'⭐' * danger_level}。"
        f"请根据当前季节和天气生成贴合情境的事件，类型要多样化。"
        f"只输出 JSON 数组，不要附加任何说明。"
    )


async def generate_batch(context, season: str, weather: str,
                        danger_level: int, day: int,
                        force: bool = False) -> int:
    """
    批量生成事件并加入缓存。
    返回新生成的事件数量。

    参数 force=True 时跳过冷却检查（用于背景批量补充）。
    """
    global _cached_events, _cache_lock, _last_generate_time

    if _cache_lock:
        return 0
    if not force and time.time() - _last_generate_time < GENERATE_COOLDOWN:
        return 0
    if len(_cached_events) >= MAX_CACHE_SIZE:
        return 0

    _cache_lock = True

    try:
        prompt = _build_user_prompt(season, weather, danger_level, day, BATCH_SIZE)

        # 直接让 AstrBot 自己决定用哪个 LLM，不需要手动检测 provider
        resp = await context.llm_generate(
            system_prompt=SYSTEM_PROMPT,
            prompt=prompt,
        )

        # 兼容不同 LLM 后端的响应格式
        text = _extract_completion_text(resp)
        if not text:
            print("[LLMEventGen] LLM 返回了空文本，响应对象: %s" % type(resp).__name__)
            return 0

        events = _parse_events(text)
        _cached_events.extend(events)

        # 更新时间戳用于冷却（非 force 模式）
        _last_generate_time = time.time()
        return len(events)

    except Exception:
        import traceback
        print(f"[LLMEventGen] 生成事件失败:")
        traceback.print_exc()
        return 0
    finally:
        _cache_lock = False


def _extract_completion_text(resp) -> str:
    """兼容不同 LLM 后端的响应对象，提取文本"""
    for attr in ("completion_text", "text", "content", "result", "message"):
        val = getattr(resp, attr, None)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    # 兼容部分对象有 .choices[0].message.content 结构
    try:
        return resp.choices[0].message.content
    except Exception:
        pass
    # 最后尝试直接 str()
    try:
        s = str(resp)
        if s and s.strip():
            return s.strip()
    except Exception:
        pass
    return ""


def _parse_events(text: str) -> List[GameEvent]:
    """从 LLM 输出中解析事件列表"""
    # 尝试提取 JSON 部分
    text = text.strip()

    # 移除可能的 markdown 代码块标记
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        raw_list = json.loads(text)
    except json.JSONDecodeError:
        # 尝试找到 JSON 数组
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            try:
                raw_list = json.loads(text[start:end+1])
            except json.JSONDecodeError:
                return []
        else:
            return []

    if not isinstance(raw_list, list):
        return []

    events = []
    for i, raw in enumerate(raw_list):
        try:
            event = _raw_to_event(raw, i)
            if event:
                events.append(event)
        except Exception as e:
            print(f"[LLMEventGen] 解析事件 #{i} 失败: {e}")
            continue

    return events


def _raw_to_event(raw: dict, index: int) -> Optional[GameEvent]:
    """将 LLM 输出的原始 dict 转为 GameEvent"""
    name = str(raw.get("name", "")).strip()
    if not name:
        return None

    event_type_str = str(raw.get("event_type", "resource")).strip().lower()
    event_type_map = {
        "resource": EventType.RESOURCE,
        "danger": EventType.DANGER,
        "opportunity": EventType.OPPORTUNITY,
        "weather": EventType.WEATHER,
        "social": EventType.SOCIAL,
    }
    event_type = event_type_map.get(event_type_str, EventType.RESOURCE)

    description = str(raw.get("description", ""))

    # 解析选项
    choices = _parse_choices(raw.get("choices", []))
    auto_result = _parse_auto_result(raw.get("auto_result"))

    if not choices and not auto_result:
        return None

    # 唯一 ID: llm_ + 时间戳 + 序号
    event_id = f"llm_{int(time.time())}_{index}"

    return GameEvent(
        id=event_id,
        name=name,
        event_type=event_type,
        description=description,
        weight=1.0,
        choices=choices,
        auto_result=auto_result,
    )


def _parse_choices(raw_choices: list) -> List[Dict[str, Any]]:
    """解析事件选项"""
    choices = []
    for choice in raw_choices:
        if not isinstance(choice, dict):
            continue
        text = str(choice.get("text", ""))
        result = _normalize_result(choice.get("result", {}))
        if not text:
            continue
        choices.append({"text": text, "result": result})
    return choices


def _parse_auto_result(raw: Optional[dict]) -> Optional[Dict[str, Any]]:
    """解析自动结算"""
    if not raw or not isinstance(raw, dict):
        return None
    return _normalize_result(raw)


def _normalize_result(raw: dict) -> Dict[str, Any]:
    """规范化 result 中的数值，确保 ranges 是 tuple"""
    result = {}

    # 资源
    if "resources" in raw:
        res = {}
        for k, v in raw["resources"].items():
            if isinstance(v, (list, tuple)) and len(v) == 2:
                res[k] = (int(v[0]), int(v[1]))
            elif isinstance(v, (int, float)):
                res[k] = (int(v), int(v))
        if res:
            result["resources"] = res

    # 物品
    if "items" in raw:
        items = {}
        for k, v in raw["items"].items():
            if isinstance(v, (list, tuple)) and len(v) == 2:
                items[k] = (int(v[0]), int(v[1]))
            elif isinstance(v, (int, float)):
                items[k] = (int(v), int(v))
        if items:
            result["items"] = items

    # 战斗
    if "combat" in raw:
        c = raw["combat"]
        if isinstance(c, dict) and "enemy_attack" in c and "enemy_health" in c:
            result["combat"] = {
                "enemy_attack": int(c["enemy_attack"]),
                "enemy_health": int(c["enemy_health"]),
            }

    # 战斗奖励
    if "rewards" in raw:
        rewards = {}
        r = raw["rewards"]
        if "exp" in r:
            v = r["exp"]
            rewards["exp"] = (int(v[0]), int(v[1])) if isinstance(v, (list, tuple)) else (int(v), int(v))
        if "items" in r:
            items = {}
            for k, v in r["items"].items():
                items[k] = (int(v[0]), int(v[1])) if isinstance(v, (list, tuple)) else (int(v), int(v))
            if items:
                rewards["items"] = items
        if "resources" in r:
            res = {}
            for k, v in r["resources"].items():
                res[k] = (int(v[0]), int(v[1])) if isinstance(v, (list, tuple)) else (int(v), int(v))
            if res:
                rewards["resources"] = res
        if rewards:
            result["rewards"] = rewards

    # 简单数值
    for key in ["exp", "health_damage"]:
        if key in raw:
            v = raw[key]
            result[key] = (int(v[0]), int(v[1])) if isinstance(v, (list, tuple)) else (int(v), int(v))

    for key in ["heal"]:
        if key in raw:
            result[key] = int(raw[key])

    for key in ["escape_chance", "stealth_chance"]:
        if key in raw:
            result[key] = float(raw[key])

    # 资源损失
    if "lose_resources" in raw:
        lr = {}
        for k, v in raw["lose_resources"].items():
            if isinstance(v, (int, float)):
                lr[k] = float(v)
        if lr:
            result["lose_resources"] = lr

    # 文本描述
    for key in ["description", "description_win", "description_lose",
                "description_escape", "description_fail", "description_stealth"]:
        if key in raw:
            result[key] = str(raw[key])

    return result
