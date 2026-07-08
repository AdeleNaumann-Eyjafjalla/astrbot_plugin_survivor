"""
末日生存游戏 - 数据模型定义

采用数据驱动设计，所有游戏内容（物品、事件、技能、建筑等）
均通过 JSON/YAML 配置定义，便于后续扩展新内容。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import random
import time


# ============================================================
# 枚举定义
# ============================================================

class ResourceType(Enum):
    """资源类型"""
    FOOD = "food"           # 食物
    WATER = "water"         # 水
    WOOD = "wood"           # 木材
    STONE = "stone"         # 石料
    IRON = "iron"           # 铁
    MEDICINE = "medicine"   # 药品
    AMMO = "ammo"           # 弹药
    FUEL = "fuel"           # 燃料


class ItemCategory(Enum):
    """物品分类"""
    TOOL = "tool"           # 工具
    WEAPON = "weapon"       # 武器
    ARMOR = "armor"         # 防具
    CONSUMABLE = "consumable"  # 消耗品
    MATERIAL = "material"   # 材料
    RESOURCE = "resource"   # 基础资源（产出写入 resources 而非 inventory）
    SPECIAL = "special"     # 特殊物品


class PlayerStatus(Enum):
    """玩家状态"""
    ALIVE = "alive"         # 存活
    INJURED = "injured"     # 受伤
    SICK = "sick"           # 生病
    DEAD = "dead"           # 死亡


class PlayerClass(Enum):
    """职业/天赋"""
    SCAVENGER = "scavenger"     # 拾荒者 - 搜索收益+30%
    SOLDIER = "soldier"         # 士兵 - 战斗+20%, 初始攻击+3
    DOCTOR = "doctor"           # 医生 - 治疗效果+50%, 免疫疾病
    ENGINEER = "engineer"       # 工程师 - 建造消耗-20%, 合成材料-15%
    SURVIVALIST = "survivalist" # 生存专家 - 饱食/口渴消耗-30%, 理智恢复+20%
    MERCHANT = "merchant"       # 商人 - 交易收益+40%, 初始物资+50%


class WeatherType(Enum):
    """天气类型"""
    CLEAR = "clear"             # 晴朗
    CLOUDY = "cloudy"           # 多云
    RAIN = "rain"               # 下雨
    STORM = "storm"             # 暴风雨
    FOG = "fog"                 # 大雾
    HEATWAVE = "heatwave"       # 热浪
    COLD_SNAP = "cold_snap"     # 寒潮
    SANDSTORM = "sandstorm"     # 沙尘暴


class BuildingType(Enum):
    """建筑类型"""
    SHELTER = "shelter"         # 避难所
    FARM = "farm"               # 农场
    WELL = "well"               # 水井
    WORKSHOP = "workshop"       # 工坊
    WATCHTOWER = "watchtower"   # 瞭望塔
    STORAGE = "storage"         # 仓库
    HOSPITAL = "hospital"       # 医疗站
    ARMORY = "armory"           # 军械库
    TRAP = "trap"               # 陷阱装置


class EventType(Enum):
    """事件类型"""
    RESOURCE = "resource"       # 资源事件
    DANGER = "danger"           # 危险事件
    OPPORTUNITY = "opportunity" # 机遇事件
    WEATHER = "weather"         # 天气事件
    SOCIAL = "social"           # 社交事件
    CHAIN = "chain"             # 事件链（多步剧情）


# ============================================================
# 数据类定义
# ============================================================

@dataclass
class Item:
    """物品定义"""
    id: str                     # 物品ID
    name: str                   # 名称
    category: ItemCategory      # 分类
    description: str = ""       # 描述
    # 属性加成
    attack_bonus: int = 0       # 攻击加成
    defense_bonus: int = 0      # 防御加成
    health_bonus: int = 0       # 生命加成
    # 消耗品效果
    heal_amount: int = 0        # 恢复生命值
    hunger_restore: int = 0     # 恢复饱食度
    thirst_restore: int = 0     # 恢复口渴度
    # 远程武器标记
    is_ranged: bool = False     # 是否为远程武器（弹药消耗）
    # 其他
    durability: int = 100       # 耐久度
    max_durability: int = 100   # 最大耐久度
    rarity: str = "common"      # 稀有度: common, uncommon, rare, epic, legendary


@dataclass
class Building:
    """建筑定义"""
    id: str
    name: str
    building_type: BuildingType
    description: str = ""
    level: int = 1
    max_level: int = 5
    # 建造消耗
    build_cost: Dict[str, int] = field(default_factory=dict)
    # 升级消耗倍率
    upgrade_cost_multiplier: float = 1.5
    # 每级效果
    effect_per_level: Dict[str, float] = field(default_factory=dict)

    def get_upgrade_cost(self) -> Dict[str, int]:
        """计算升级到下一级的消耗"""
        if self.level >= self.max_level:
            return {}
        multiplier = self.upgrade_cost_multiplier ** (self.level - 1)
        return {k: int(v * multiplier) for k, v in self.build_cost.items()}


@dataclass
class Skill:
    """技能定义"""
    id: str
    name: str
    description: str = ""
    max_level: int = 10
    # 每级效果
    effect_per_level: Dict[str, float] = field(default_factory=dict)


@dataclass
class Achievement:
    """成就定义"""
    id: str
    name: str
    description: str = ""
    category: str = "general"   # general, combat, survival, building, social
    condition: str = ""         # 条件表达式（如 "level >= 10"）
    reward_description: str = ""  # 奖励描述
    reward_items: Dict[str, int] = field(default_factory=dict)     # 奖励物品
    reward_resources: Dict[str, int] = field(default_factory=dict)  # 奖励资源
    reward_exp: int = 0         # 奖励经验
    reward_title: str = ""      # 解锁称号


@dataclass
class GameEvent:
    """游戏事件定义"""
    id: str
    name: str
    event_type: EventType
    description: str = ""
    # 触发概率权重
    weight: float = 1.0
    # 触发条件（lambda 或 dict 表达式，运行时解析）
    condition: Optional[str] = None
    # 事件选项
    choices: List[Dict[str, Any]] = field(default_factory=list)
    # 自动结算（无选项时）
    auto_result: Optional[Dict[str, Any]] = None
    # 事件链相关
    chain_id: Optional[str] = None       # 所属事件链 ID
    chain_order: int = 0                 # 在链中的顺序
    chain_next: Optional[str] = None     # 完成后触发的下一个事件 ID
    weather_only: Optional[List[str]] = None  # 仅在特定天气下触发

@dataclass
class PlayerState:
    """玩家状态数据"""
    user_id: str                # QQ号
    group_id: str               # 群号
    nickname: str = ""          # 昵称

    # 职业
    player_class: Optional[str] = None  # 职业ID

    # 生存属性
    health: int = 100           # 生命值
    max_health: int = 100       # 最大生命值
    hunger: int = 100           # 饱食度 (0-100)
    thirst: int = 100           # 口渴度 (0-100)
    temperature: float = 20.0   # 体温
    sanity: int = 100           # 理智值 (0-100)

    # 战斗属性
    attack: int = 5             # 攻击力
    defense: int = 3            # 防御力
    level: int = 1              # 等级
    exp: int = 0                # 经验值
    skill_points: int = 0       # 可分配技能点

    # 资源
    resources: Dict[str, int] = field(default_factory=lambda: {
        "food": 10, "water": 10, "wood": 5,
        "stone": 3, "iron": 0, "medicine": 2,
        "ammo": 0, "fuel": 0
    })

    # 状态
    status: str = "alive"       # alive, injured, sick, dead
    status_turns: int = 0       # 状态持续回合数
    status_effects: Dict[str, int] = field(default_factory=dict)

    # 装备
    equipped_weapon: Optional[str] = None   # 装备的武器ID
    equipped_armor: Optional[str] = None    # 装备的防具ID

    # 背包
    inventory: Dict[str, int] = field(default_factory=dict)  # {item_id: count}

    # 建筑
    buildings: Dict[str, int] = field(default_factory=dict)  # {building_id: level}

    # 建筑增益（每日结算时更新）
    building_defense_bonus: int = 0     # 避难所防御加成
    building_max_health_bonus: int = 0  # 避难所血量加成

    # 技能
    skills: Dict[str, int] = field(default_factory=dict)     # {skill_id: level}

    # 成就与称号
    unlocked_achievements: List[str] = field(default_factory=list)   # 已解锁成就ID列表
    active_title: Optional[str] = None   # 当前佩戴的称号
    unlocked_titles: List[str] = field(default_factory=list)         # 已解锁称号列表

    # 建造计数（实际建造次数，非等级之和）
    total_builds: int = 0

    # 离线期间未读的升级次数（每日自动搜集中升级）
    unread_level_ups: int = 0

    # PvP 相关
    pvp_shield_until: float = 0.0          # PvP 保护截止时间戳
    pvp_cooldown_until: float = 0.0        # 偷袭冷却截止时间戳
    last_attacked_by: Optional[str] = None  # 上次被谁攻击
    pvp_wins: int = 0                       # PvP 胜利次数
    pvp_losses: int = 0                     # PvP 失败次数

    # 事件链进度
    chain_progress: Dict[str, int] = field(default_factory=dict)  # {chain_id: current_step}

    # 时间戳
    last_action_time: float = 0.0    # 上次行动时间
    created_at: float = 0.0          # 创建时间
    total_actions: int = 0           # 总行动次数
    days_survived: int = 0           # 存活天数

    # 统计
    stats: Dict[str, int] = field(default_factory=lambda: {
        "zombies_killed": 0,
        "items_crafted": 0,
        "events_triggered": 0,
        "deaths": 0,
    })

    # === 全自动搜集 ===
    idle_mode: bool = True   # 始终开启，每游戏天自动入账

    def is_alive(self) -> bool:
        return self.status != "dead"

    def get_resource(self, resource_type: str) -> int:
        return self.resources.get(resource_type, 0)

    def add_resource(self, resource_type: str, amount: int) -> int:
        """添加资源，返回实际添加量"""
        current = self.resources.get(resource_type, 0)
        self.resources[resource_type] = max(0, current + amount)
        return self.resources[resource_type] - current

    def consume_resource(self, resource_type: str, amount: int) -> bool:
        """消耗资源，返回是否成功"""
        current = self.resources.get(resource_type, 0)
        if current >= amount:
            self.resources[resource_type] = current - amount
            return True
        return False

    def add_item(self, item_id: str, count: int = 1):
        """添加物品到背包"""
        self.inventory[item_id] = self.inventory.get(item_id, 0) + count

    def remove_item(self, item_id: str, count: int = 1) -> bool:
        """移除物品，返回是否成功"""
        current = self.inventory.get(item_id, 0)
        if current >= count:
            self.inventory[item_id] = current - count
            if self.inventory[item_id] <= 0:
                del self.inventory[item_id]
            return True
        return False

    def has_item(self, item_id: str, count: int = 1) -> bool:
        return self.inventory.get(item_id, 0) >= count

    def apply_daily_decay(self):
        """应用每日自然消耗"""
        # 生存专家职业加成
        decay_mult = 0.7 if self.player_class == "survivalist" else 1.0

        # 饱食度和口渴度自然下降
        self.hunger = max(0, self.hunger - int(15 * decay_mult))
        self.thirst = max(0, self.thirst - int(20 * decay_mult))

        # 饥饿惩罚
        if self.hunger <= 0:
            self.health = max(0, self.health - 20)
        elif self.hunger <= 30:
            self.health = max(0, self.health - 5)

        # 口渴惩罚
        if self.thirst <= 0:
            self.health = max(0, self.health - 25)
        elif self.thirst <= 30:
            self.health = max(0, self.health - 8)

        # 理智值自然恢复（生存专家加成）
        sanity_regen = 2
        if self.player_class == "survivalist":
            sanity_regen = int(2 * 1.2)
        self.sanity = min(100, self.sanity + sanity_regen)

        # 检查死亡
        if self.health <= 0:
            self.status = "dead"
            self.stats["deaths"] += 1

    def get_title_display(self) -> str:
        """获取称号显示"""
        if self.active_title:
            return f"[{self.active_title}]"
        return ""

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "user_id": self.user_id,
            "group_id": self.group_id,
            "nickname": self.nickname,
            "player_class": self.player_class,
            "health": self.health,
            "max_health": self.max_health,
            "hunger": self.hunger,
            "thirst": self.thirst,
            "temperature": self.temperature,
            "sanity": self.sanity,
            "attack": self.attack,
            "defense": self.defense,
            "level": self.level,
            "exp": self.exp,
            "skill_points": self.skill_points,
            "resources": self.resources,
            "status": self.status,
            "status_turns": self.status_turns,
            "status_effects": self.status_effects,
            "equipped_weapon": self.equipped_weapon,
            "equipped_armor": self.equipped_armor,
            "inventory": self.inventory,
            "buildings": self.buildings,
            "skills": self.skills,
            "unlocked_achievements": self.unlocked_achievements,
            "active_title": self.active_title,
            "unlocked_titles": self.unlocked_titles,
            "total_builds": self.total_builds,
            "unread_level_ups": self.unread_level_ups,
            "pvp_shield_until": self.pvp_shield_until,
            "pvp_cooldown_until": self.pvp_cooldown_until,
            "last_attacked_by": self.last_attacked_by,
            "pvp_wins": self.pvp_wins,
            "pvp_losses": self.pvp_losses,
            "chain_progress": self.chain_progress,
            "last_action_time": self.last_action_time,
            "created_at": self.created_at,
            "total_actions": self.total_actions,
            "days_survived": self.days_survived,
            "stats": self.stats,
            "idle_mode": self.idle_mode,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlayerState":
        """从字典反序列化（兼容旧版存档）"""
        # 过滤出合法的 dataclass 字段
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)


# ============================================================
# 群组游戏状态
# ============================================================

@dataclass
class GroupGameState:
    """群组级别的游戏状态"""
    group_id: str
    current_day: int = 1
    current_season: str = "spring"  # spring, summer, autumn, winter
    season_day: int = 1
    weather: str = "clear"          # 当前天气 (WeatherType)
    weather_day: int = 0            # 当前天气已持续天数
    next_weather: str = "clear"     # 预告下一天天气
    active_events: List[str] = field(default_factory=list)  # 活跃的全局事件ID
    event_history: List[str] = field(default_factory=list)  # 事件历史

    # 全局危险等级 (影响事件难度)
    danger_level: int = 1           # 1-10

    # 群组公告板
    announcements: List[str] = field(default_factory=list)

    def advance_day(self):
        """推进一天"""
        self.current_day += 1
        self.season_day += 1
        self.weather_day += 1

        # 天气更新（每1-3天变化一次）
        if self.weather_day >= random.randint(1, 3):
            self.weather_day = 0
            self._roll_weather()

        # 季节切换 (每30天)
        if self.season_day > 30:
            self.season_day = 1
            seasons = ["spring", "summer", "autumn", "winter"]
            idx = seasons.index(self.current_season)
            self.current_season = seasons[(idx + 1) % 4]
            # 季节切换时强制刷新天气
            self.weather_day = 0
            self._roll_weather()

        # 危险等级递增 (每10天+1)
        self.danger_level = min(10, 1 + self.current_day // 10)

    def _roll_weather(self):
        """根据季节随机天气"""
        season_weathers = {
            "spring": {"clear": 0.4, "cloudy": 0.2, "rain": 0.25, "fog": 0.1, "storm": 0.05},
            "summer": {"clear": 0.35, "cloudy": 0.15, "heatwave": 0.25, "rain": 0.15, "storm": 0.1},
            "autumn": {"clear": 0.3, "cloudy": 0.25, "rain": 0.2, "fog": 0.15, "storm": 0.1},
            "winter": {"clear": 0.3, "cloudy": 0.2, "cold_snap": 0.3, "snow": 0.15, "fog": 0.05},
        }
        weights = season_weathers.get(self.current_season, {"clear": 1.0})
        # 处理 snow 没有在 WeatherType 中的问题：映射到 storm
        if "snow" in weights:
            weights["storm"] = weights.get("storm", 0) + weights.pop("snow", 0)
        total = sum(weights.values())
        r = random.random() * total
        cum = 0
        for w, weight in weights.items():
            cum += weight
            if r <= cum:
                self.weather = w
                break

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "current_day": self.current_day,
            "current_season": self.current_season,
            "season_day": self.season_day,
            "weather": self.weather,
            "weather_day": self.weather_day,
            "next_weather": self.next_weather,
            "active_events": self.active_events,
            "event_history": self.event_history,
            "danger_level": self.danger_level,
            "announcements": self.announcements,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GroupGameState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
