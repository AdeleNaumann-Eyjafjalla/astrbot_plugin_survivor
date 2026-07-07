"""
末日生存游戏 - 游戏内容注册表

采用注册表模式(Registry Pattern)，所有游戏内容通过注册表管理。
新增内容只需创建新的注册函数或配置文件即可，无需修改核心逻辑。
"""

import random
from typing import Dict, List, Optional, Type, Callable, Any
from models import (
    Item, ItemCategory, Building, BuildingType, GameEvent,
    EventType, Skill, ResourceType, Achievement, PlayerClass
)


class ItemRegistry:
    """物品注册表 - 管理所有物品定义"""

    _items: Dict[str, Item] = {}

    @classmethod
    def register(cls, item: Item):
        """注册物品"""
        cls._items[item.id] = item

    @classmethod
    def get(cls, item_id: str) -> Optional[Item]:
        """获取物品定义"""
        return cls._items.get(item_id)

    @classmethod
    def get_all(cls) -> List[Item]:
        """获取所有物品"""
        return list(cls._items.values())

    @classmethod
    def get_by_category(cls, category: ItemCategory) -> List[Item]:
        """按分类获取物品"""
        return [i for i in cls._items.values() if i.category == category]


class BuildingRegistry:
    """建筑注册表 - 管理所有建筑定义"""

    _buildings: Dict[str, Building] = {}

    @classmethod
    def register(cls, building: Building):
        cls._buildings[building.id] = building

    @classmethod
    def get(cls, building_id: str) -> Optional[Building]:
        return cls._buildings.get(building_id)

    @classmethod
    def get_all(cls) -> List[Building]:
        return list(cls._buildings.values())


class EventRegistry:
    """事件注册表 - 管理所有游戏事件"""

    _events: Dict[str, GameEvent] = {}

    @classmethod
    def register(cls, event: GameEvent):
        cls._events[event.id] = event

    @classmethod
    def get(cls, event_id: str) -> Optional[GameEvent]:
        return cls._events.get(event_id)

    @classmethod
    def get_by_type(cls, event_type: EventType) -> List[GameEvent]:
        return [e for e in cls._events.values() if e.event_type == event_type]

    @classmethod
    def get_all(cls) -> List[GameEvent]:
        return list(cls._events.values())

    @classmethod
    def get_random_event(cls, event_type: Optional[EventType] = None) -> Optional[GameEvent]:
        """按权重随机获取事件"""
        candidates = cls.get_all()
        if event_type:
            candidates = cls.get_by_type(event_type)
        if not candidates:
            return None

        total_weight = sum(e.weight for e in candidates)
        r = random.uniform(0, total_weight)
        cumulative = 0
        for event in candidates:
            cumulative += event.weight
            if r <= cumulative:
                return event
        return candidates[-1]


class SkillRegistry:
    """技能注册表"""

    _skills: Dict[str, Skill] = {}

    @classmethod
    def register(cls, skill: Skill):
        cls._skills[skill.id] = skill

    @classmethod
    def get(cls, skill_id: str) -> Optional[Skill]:
        return cls._skills.get(skill_id)

    @classmethod
    def get_all(cls) -> List[Skill]:
        return list(cls._skills.values())


class RecipeRegistry:
    """合成配方注册表"""

    _recipes: Dict[str, dict] = {}

    @classmethod
    def register(cls, result_item_id: str, materials: Dict[str, int],
                 description: str = "", required_building: Optional[str] = None,
                 min_level: int = 1):
        """注册合成配方"""
        cls._recipes[result_item_id] = {
            "result": result_item_id,
            "materials": materials,
            "description": description,
            "required_building": required_building,
            "min_level": min_level,
        }

    @classmethod
    def get(cls, item_id: str) -> Optional[dict]:
        return cls._recipes.get(item_id)

    @classmethod
    def get_all(cls) -> Dict[str, dict]:
        return cls._recipes


class AchievementRegistry:
    """成就注册表"""

    _achievements: Dict[str, Achievement] = {}

    @classmethod
    def register(cls, achievement: Achievement):
        cls._achievements[achievement.id] = achievement

    @classmethod
    def get(cls, achievement_id: str) -> Optional[Achievement]:
        return cls._achievements.get(achievement_id)

    @classmethod
    def get_all(cls) -> List[Achievement]:
        return list(cls._achievements.values())

    @classmethod
    def get_by_category(cls, category: str) -> List[Achievement]:
        return [a for a in cls._achievements.values() if a.category == category]


class ClassRegistry:
    """职业注册表"""

    _classes: Dict[str, Dict] = {}

    @classmethod
    def register(cls, class_id: str, name: str, description: str,
                 bonuses: Dict[str, Any] = None, starting_items: Dict[str, int] = None,
                 starting_resources: Dict[str, int] = None):
        cls._classes[class_id] = {
            "id": class_id,
            "name": name,
            "description": description,
            "bonuses": bonuses or {},
            "starting_items": starting_items or {},
            "starting_resources": starting_resources or {},
        }

    @classmethod
    def get(cls, class_id: str) -> Optional[Dict]:
        return cls._classes.get(class_id)

    @classmethod
    def get_all(cls) -> Dict[str, Dict]:
        return cls._classes


# ============================================================
# 初始化默认游戏内容
# ============================================================

def init_default_items():
    """初始化默认物品"""

    # === 武器 ===
    ItemRegistry.register(Item(
        id="rusty_knife", name="生锈的小刀", category=ItemCategory.WEAPON,
        description="一把生锈的小刀，勉强能用。",
        attack_bonus=3, durability=50, max_durability=50, rarity="common"
    ))
    ItemRegistry.register(Item(
        id="baseball_bat", name="棒球棍", category=ItemCategory.WEAPON,
        description="一根结实的棒球棍，近战利器。",
        attack_bonus=8, durability=80, max_durability=80, rarity="common"
    ))
    ItemRegistry.register(Item(
        id="hunting_rifle", name="猎枪", category=ItemCategory.WEAPON,
        description="一把老式猎枪，远程攻击的好帮手。",
        attack_bonus=20, durability=60, max_durability=60, rarity="uncommon"
    ))
    ItemRegistry.register(Item(
        id="fire_axe", name="消防斧", category=ItemCategory.WEAPON,
        description="消防斧，劈砍力惊人，还能破门。",
        attack_bonus=15, durability=100, max_durability=100, rarity="uncommon"
    ))
    ItemRegistry.register(Item(
        id="crossbow", name="十字弩", category=ItemCategory.WEAPON,
        description="无声的远程武器，适合暗杀。",
        attack_bonus=25, durability=70, max_durability=70, rarity="rare"
    ))
    ItemRegistry.register(Item(
        id="flame_sword", name="火焰剑", category=ItemCategory.WEAPON,
        description="附魔了火焰的利剑，传说级别的武器！",
        attack_bonus=50, durability=150, max_durability=150, rarity="legendary"
    ))

    # === 防具 ===
    ItemRegistry.register(Item(
        id="leather_jacket", name="皮夹克", category=ItemCategory.ARMOR,
        description="一件旧皮夹克，能提供基本防护。",
        defense_bonus=5, durability=60, max_durability=60, rarity="common"
    ))
    ItemRegistry.register(Item(
        id="riot_shield", name="防暴盾牌", category=ItemCategory.ARMOR,
        description="警用防暴盾牌，防御力不错。",
        defense_bonus=12, durability=90, max_durability=90, rarity="uncommon"
    ))
    ItemRegistry.register(Item(
        id="military_vest", name="军用防弹衣", category=ItemCategory.ARMOR,
        description="军用级别的防弹衣，重但可靠。",
        defense_bonus=20, durability=120, max_durability=120, rarity="rare"
    ))

    # === 消耗品 ===
    ItemRegistry.register(Item(
        id="canned_food", name="罐头食品", category=ItemCategory.CONSUMABLE,
        description="一罐不知什么肉做的罐头，能填饱肚子。",
        hunger_restore=30, rarity="common"
    ))
    ItemRegistry.register(Item(
        id="bottled_water", name="瓶装水", category=ItemCategory.CONSUMABLE,
        description="一瓶干净的饮用水，末日中的奢侈品。",
        thirst_restore=35, rarity="common"
    ))
    ItemRegistry.register(Item(
        id="bandage", name="绷带", category=ItemCategory.CONSUMABLE,
        description="简易绷带，能止血包扎。",
        heal_amount=20, rarity="common"
    ))
    ItemRegistry.register(Item(
        id="first_aid_kit", name="急救包", category=ItemCategory.CONSUMABLE,
        description="专业急救包，能治疗较重的伤势。",
        heal_amount=60, rarity="uncommon"
    ))
    ItemRegistry.register(Item(
        id="mre", name="军用口粮", category=ItemCategory.CONSUMABLE,
        description="军用即食口粮，营养全面。",
        hunger_restore=60, thirst_restore=20, rarity="uncommon"
    ))
    ItemRegistry.register(Item(
        id="stimpack", name="兴奋剂", category=ItemCategory.CONSUMABLE,
        description="临时提升战斗力的注射剂，有副作用。",
        heal_amount=30, rarity="rare"
    ))
    ItemRegistry.register(Item(
        id="antidote", name="解毒剂", category=ItemCategory.CONSUMABLE,
        description="能解多种毒素的万能解毒剂。",
        heal_amount=40, rarity="rare"
    ))

    # === 材料 ===
    for mat_id, mat_name in [
        ("scrap_metal", "废金属"), ("cloth", "布料"), ("rope", "绳索"),
        ("nails", "钉子"), ("glass", "玻璃"), ("electronics", "电子零件"),
        ("gunpowder", "火药"), ("herb", "草药"), ("leather", "皮革"),
        ("plastic", "塑料"),
    ]:
        ItemRegistry.register(Item(
            id=mat_id, name=mat_name, category=ItemCategory.MATERIAL,
            description=f"基础材料：{mat_name}", rarity="common"
        ))

    # === 特殊物品 ===
    ItemRegistry.register(Item(
        id="survivor_journal", name="幸存者日记", category=ItemCategory.SPECIAL,
        description="一本记录着末日生存技巧的日记，阅读可获得经验。",
        rarity="uncommon"
    ))
    ItemRegistry.register(Item(
        id="radio", name="无线电", category=ItemCategory.SPECIAL,
        description="一台还能工作的无线电，或许能收到其他幸存者的信号。",
        rarity="rare"
    ))


def init_default_buildings():
    """初始化默认建筑"""

    BuildingRegistry.register(Building(
        id="shelter", name="避难所", building_type=BuildingType.SHELTER,
        description="你的安身之所，提高生存能力。",
        level=1, max_level=10,
        build_cost={"wood": 20, "stone": 10},
        effect_per_level={"defense": 2, "max_health": 10}
    ))
    BuildingRegistry.register(Building(
        id="farm", name="农场", building_type=BuildingType.FARM,
        description="种植作物，每天产出食物。",
        level=0, max_level=5,
        build_cost={"wood": 10, "water": 5},
        effect_per_level={"food_per_day": 5}
    ))
    BuildingRegistry.register(Building(
        id="well", name="水井", building_type=BuildingType.WELL,
        description="取水设施，每天产出净水。",
        level=0, max_level=5,
        build_cost={"stone": 10, "wood": 5},
        effect_per_level={"water_per_day": 5}
    ))
    BuildingRegistry.register(Building(
        id="workshop", name="工坊", building_type=BuildingType.WORKSHOP,
        description="制作和修理物品的场所。",
        level=0, max_level=5,
        build_cost={"wood": 15, "iron": 5, "stone": 5},
        effect_per_level={"craft_speed": 0.2}
    ))
    BuildingRegistry.register(Building(
        id="watchtower", name="瞭望塔", building_type=BuildingType.WATCHTOWER,
        description="提高预警能力，减少被突袭的概率。",
        level=0, max_level=5,
        build_cost={"wood": 20, "stone": 15, "iron": 5},
        effect_per_level={"scout_range": 1}
    ))
    BuildingRegistry.register(Building(
        id="storage", name="仓库", building_type=BuildingType.STORAGE,
        description="扩大资源存储上限。",
        level=0, max_level=5,
        build_cost={"wood": 25, "stone": 10},
        effect_per_level={"storage_bonus": 50}
    ))
    BuildingRegistry.register(Building(
        id="hospital", name="医疗站", building_type=BuildingType.HOSPITAL,
        description="提供医疗护理，加速伤势恢复。",
        level=0, max_level=5,
        build_cost={"wood": 10, "stone": 10, "medicine": 5},
        effect_per_level={"heal_per_day": 10}
    ))
    BuildingRegistry.register(Building(
        id="trap", name="陷阱装置", building_type=BuildingType.TRAP,
        description="设置陷阱捕获小动物，每天产出额外食物。",
        level=0, max_level=5,
        build_cost={"wood": 8, "rope": 3, "scrap_metal": 2},
        effect_per_level={"food_per_day": 3}
    ))
    BuildingRegistry.register(Building(
        id="armory", name="军械库", building_type=BuildingType.ARMORY,
        description="生产和管理武器装备，每天产出弹药。",
        level=0, max_level=5,
        build_cost={"wood": 15, "stone": 15, "iron": 10},
        effect_per_level={"ammo_per_day": 2}
    ))


def init_default_events():
    """初始化默认事件"""

    # === 资源事件 ===
    EventRegistry.register(GameEvent(
        id="abandoned_house", name="废弃房屋",
        event_type=EventType.RESOURCE, weight=3.0,
        description="你发现了一栋废弃的房屋，要进去搜刮吗？",
        choices=[
            {
                "text": "🔍 仔细搜索",
                "result": {
                    "resources": {"food": (2, 8), "water": (1, 5), "wood": (3, 10)},
                    "items": {"canned_food": (0, 2), "bandage": (0, 1)},
                    "description": "你仔细搜索了房屋，找到了不少有用的物资！"
                }
            },
            {
                "text": "⚡ 快速搜索",
                "result": {
                    "resources": {"food": (1, 4)},
                    "description": "你快速扫了一眼，拿了点食物就走了。"
                }
            },
            {
                "text": "🚶 绕过去",
                "result": {
                    "description": "你选择绕道而行，安全第一。"
                }
            }
        ]
    ))

    EventRegistry.register(GameEvent(
        id="supply_crate", name="空投补给",
        event_type=EventType.RESOURCE, weight=1.5,
        description="你看到远处有一个空投补给箱！",
        choices=[
            {
                "text": "🏃 冲过去抢",
                "result": {
                    "resources": {"food": (5, 15), "medicine": (2, 5), "ammo": (3, 10)},
                    "items": {"mre": (1, 3), "first_aid_kit": (0, 1)},
                    "description": "你成功抢到了补给箱，收获颇丰！"
                }
            },
            {
                "text": "🔭 先观察周围",
                "result": {
                    "resources": {"food": (3, 10), "medicine": (1, 3)},
                    "description": "确认安全后你去拿补给，但有人抢先拿走了一部分。"
                }
            },
            {
                "text": "❌ 太危险了，不去",
                "result": {
                    "description": "你决定不去冒险，补给箱被别人拿走了。"
                }
            }
        ]
    ))

    EventRegistry.register(GameEvent(
        id="river_found", name="发现河流",
        event_type=EventType.RESOURCE, weight=2.0,
        description="你在探索中发现了一条小河！",
        choices=[
            {
                "text": "💧 取水",
                "result": {
                    "resources": {"water": (5, 15)},
                    "description": "你装了好几瓶河水，虽然需要净化但总比没有好。"
                }
            },
            {
                "text": "🎣 试着钓鱼",
                "result": {
                    "resources": {"food": (3, 10)},
                    "description": "运气不错，你钓到了几条鱼！"
                }
            },
        ]
    ))

    # === 危险事件 ===
    EventRegistry.register(GameEvent(
        id="zombie_encounter", name="遭遇丧尸",
        event_type=EventType.DANGER, weight=2.5,
        description="前方出现了几只游荡的丧尸！",
        choices=[
            {
                "text": "⚔️ 正面迎战",
                "result": {
                    "combat": {"enemy_attack": 10, "enemy_health": 30},
                    "rewards": {"exp": (20, 50)},
                    "description_win": "你消灭了丧尸，获得了战斗经验。",
                    "description_lose": "你被丧尸抓伤了，赶紧处理伤口！"
                }
            },
            {
                "text": "🏃 快速逃跑",
                "result": {
                    "escape_chance": 0.7,
                    "description_escape": "你成功甩掉了丧尸。",
                    "description_fail": "逃跑失败！丧尸追上了你。",
                    "fail_damage": (5, 15)
                }
            },
            {
                "text": "🤫 悄悄绕开",
                "result": {
                    "stealth_chance": 0.85,
                    "description_stealth": "你小心翼翼地绕过了丧尸群。",
                    "description_fail": "你不小心踩到了枯枝，惊动了丧尸！",
                    "fail_damage": (10, 20)
                }
            }
        ]
    ))

    EventRegistry.register(GameEvent(
        id="raider_attack", name="掠夺者袭击",
        event_type=EventType.DANGER, weight=1.0,
        description="一伙掠夺者盯上了你的物资！他们正在靠近！",
        choices=[
            {
                "text": "⚔️ 奋起反抗",
                "result": {
                    "combat": {"enemy_attack": 18, "enemy_health": 50},
                    "rewards": {"exp": (50, 100), "items": {"scrap_metal": (1, 3), "ammo": (1, 5)}},
                    "description_win": "你击退了掠夺者，从他们身上搜到了一些物资！",
                    "description_lose": "掠夺者打败了你，抢走了部分物资...",
                    "lose_resources": {"food": 0.3, "water": 0.2, "medicine": 0.3}
                }
            },
            {
                "text": "💰 交出部分物资",
                "result": {
                    "lose_resources": {"food": 0.5, "water": 0.3},
                    "description": "你交出了部分物资，掠夺者满意地离开了。"
                }
            },
        ]
    ))

    EventRegistry.register(GameEvent(
        id="storm", name="暴风雨",
        event_type=EventType.DANGER, weight=1.5,
        description="一场猛烈的暴风雨来袭！",
        choices=[
            {
                "text": "🏠 躲进避难所",
                "result": {
                    "description": "你躲进了避难所，安全度过了暴风雨。"
                }
            },
            {
                "text": "🌧️ 冒雨收集雨水",
                "result": {
                    "resources": {"water": (5, 10)},
                    "health_damage": (5, 15),
                    "description": "你冒着雨收集了不少水，但有点着凉了。"
                }
            },
        ]
    ))

    # === 机遇事件 ===
    EventRegistry.register(GameEvent(
        id="survivor_camp", name="幸存者营地",
        event_type=EventType.OPPORTUNITY, weight=1.0,
        description="你遇到了一个小型幸存者营地，他们看起来还算友善。",
        choices=[
            {
                "text": "🤝 交易物资",
                "result": {
                    "trade": True,
                    "description": "你和幸存者们交换了一些物资，各取所需。"
                }
            },
            {
                "text": "📚 交流情报",
                "result": {
                    "exp": (30, 60),
                    "description": "你从幸存者那里学到了不少生存技巧。"
                }
            },
            {
                "text": "🛡️ 请求帮助",
                "result": {
                    "heal": 30,
                    "description": "好心的幸存者帮你处理了伤势。"
                }
            }
        ]
    ))

    EventRegistry.register(GameEvent(
        id="hidden_bunker", name="发现地堡",
        event_type=EventType.OPPORTUNITY, weight=0.5,
        description="你偶然发现了一个隐藏的地堡入口！",
        choices=[
            {
                "text": "⬇️ 深入探索",
                "result": {
                    "items": {"hunting_rifle": (0, 1), "military_vest": (0, 1),
                              "first_aid_kit": (1, 3), "ammo": (5, 20)},
                    "resources": {"food": (5, 15), "water": (5, 15), "fuel": (3, 10)},
                    "description": "地堡里物资丰富！这是一次大丰收！"
                }
            },
        ]
    ))

    # === 天气事件 ===
    EventRegistry.register(GameEvent(
        id="heatwave", name="热浪",
        event_type=EventType.WEATHER, weight=1.0,
        description="今天气温异常炎热，水资源消耗加剧。",
        auto_result={
            "thirst_decay_extra": 10,
            "description": "酷热的天气让你汗流浃背，需要更多饮水。"
        }
    ))

    EventRegistry.register(GameEvent(
        id="cold_snap", name="寒潮",
        event_type=EventType.WEATHER, weight=1.0,
        description="一股寒潮来袭，气温骤降！",
        auto_result={
            "hunger_decay_extra": 10,
            "description": "寒冷天气消耗了更多能量，你需要更多食物来保暖。"
        }
    ))

    # === 社交事件 ===
    EventRegistry.register(GameEvent(
        id="wandering_merchant", name="流浪商人",
        event_type=EventType.SOCIAL, weight=1.0,
        description="一个神秘的流浪商人出现了，他愿意用稀有物品交换物资。",
        choices=[
            {
                "text": "💱 进行交易",
                "result": {
                    "trade_special": True,
                    "description": "商人展示了他的货物，看看有没有你需要的。"
                }
            },
            {
                "text": "👋 婉拒",
                "result": {
                    "description": "你礼貌地拒绝了商人。"
                }
            }
        ]
    ))

    # === 事件链：军方地堡 ===
    EventRegistry.register(GameEvent(
        id="bunker_chain_1", name="神秘的无线电信号",
        event_type=EventType.CHAIN, weight=0.8,
        description="你的无线电接收到了一段加密信号：「...这里是回声基地...需要支援...坐标...」信号断断续续。",
        chain_id="military_bunker", chain_order=1,
        choices=[
            {
                "text": "📡 记录坐标，追踪信号",
                "result": {
                    "description": "你记下了大概的坐标方向。信号源似乎在城市北部。"
                }
            },
            {
                "text": "🔇 忽略信号",
                "result": {
                    "description": "你决定不去管它，也许是陷阱。"
                }
            }
        ]
    ))
    EventRegistry.register(GameEvent(
        id="bunker_chain_2", name="追踪信号源",
        event_type=EventType.CHAIN, weight=0.6,
        description="你顺着之前记录的坐标方向前进，发现了一扇隐藏在山体中的金属大门。上面写着「回声基地 - 授权人员准入」。",
        chain_id="military_bunker", chain_order=2,
        choices=[
            {
                "text": "🔓 尝试破解密码锁",
                "result": {
                    "escape_chance": 0.5,
                    "description_escape": "你成功破解了密码锁！大门缓缓打开...",
                    "description_fail": "密码锁触发了警报！基地防御系统启动了。",
                    "fail_damage": (15, 30)
                }
            },
            {
                "text": "🔧 用工具撬开",
                "result": {
                    "description": "你花了些时间，终于撬开了门。",
                    "resources": {"iron": (2, 5), "scrap_metal": (1, 3)},
                    "items": {"fire_axe": (0, 1)}
                }
            },
            {
                "text": "🚶 标记位置，以后再来",
                "result": {
                    "description": "你在地图上标记了这个位置。"
                }
            }
        ]
    ))
    EventRegistry.register(GameEvent(
        id="bunker_chain_3", name="回声基地内部",
        event_type=EventType.CHAIN, weight=0.4,
        description="基地内部一片漆黑，应急灯闪烁着微光。你能看到远处的武器库和物资仓库。但走廊里似乎有动静...",
        chain_id="military_bunker", chain_order=3,
        choices=[
            {
                "text": "🔫 直奔武器库",
                "result": {
                    "combat": {"enemy_attack": 25, "enemy_health": 60},
                    "rewards": {
                        "exp": (80, 150),
                        "items": {"hunting_rifle": (1, 1), "ammo": (10, 30), "crossbow": (0, 1)},
                        "resources": {"fuel": (5, 15)}
                    },
                    "description_win": "你击败了守卫机器人，洗劫了武器库！",
                    "description_lose": "守卫机器人太强了，你不得不撤退..."
                }
            },
            {
                "text": "📦 直奔物资仓库",
                "result": {
                    "resources": {"food": (10, 30), "water": (10, 30), "medicine": (5, 15), "fuel": (5, 20)},
                    "items": {"mre": (2, 5), "first_aid_kit": (1, 3), "military_vest": (0, 1)},
                    "description": "你避开危险，在物资仓库找到了大量补给！"
                }
            },
            {
                "text": "💻 搜索情报室",
                "result": {
                    "exp": (100, 200),
                    "items": {"survivor_journal": (1, 2), "radio": (0, 1)},
                    "description": "你在情报室找到了重要资料，获得了大量经验和知识。"
                }
            }
        ]
    ))

    # === 天气专属事件 ===
    EventRegistry.register(GameEvent(
        id="rain_collection", name="天然集水",
        event_type=EventType.RESOURCE, weight=3.0,
        description="雨水哗哗地下着，这是收集水资源的好机会！",
        weather_only=["rain"],
        auto_result={
            "resources": {"water": (8, 20)},
            "description": "你摆出容器收集雨水，收获了不少净水！"
        }
    ))
    EventRegistry.register(GameEvent(
        id="fog_mystery", name="雾中魅影",
        event_type=EventType.DANGER, weight=2.0,
        description="浓雾中你听到了奇怪的声音...似乎有什么东西在雾中移动。",
        weather_only=["fog"],
        choices=[
            {
                "text": "🔍 循声探去",
                "result": {
                    "combat": {"enemy_attack": 12, "enemy_health": 35},
                    "rewards": {"exp": (30, 60), "items": {"electronics": (1, 3)}},
                    "description_win": "你击败了雾中的变异生物！",
                    "description_lose": "雾中的东西比你想象的更危险..."
                }
            },
            {
                "text": "🚶 悄悄离开",
                "result": {
                    "stealth_chance": 0.8,
                    "description_stealth": "你悄无声息地离开了雾区。",
                    "description_fail": "你不小心发出了声响！",
                    "fail_damage": (10, 20)
                }
            }
        ]
    ))
    EventRegistry.register(GameEvent(
        id="storm_shelter", name="风暴避难",
        event_type=EventType.WEATHER, weight=2.0,
        description="暴风雨肆虐，外面根本无法探索。",
        weather_only=["storm"],
        auto_result={
            "hunger_decay_extra": 5,
            "description": "你蜷缩在避难所里等待风暴过去。饱食度略有额外消耗。"
        }
    ))


def init_default_skills():
    """初始化默认技能"""

    SkillRegistry.register(Skill(
        id="combat", name="战斗技巧",
        description="提高战斗中的攻击力。",
        max_level=10,
        effect_per_level={"attack": 2}
    ))
    SkillRegistry.register(Skill(
        id="survival", name="生存技能",
        description="减少每日资源消耗。",
        max_level=10,
        effect_per_level={"hunger_decay_reduce": 0.05, "thirst_decay_reduce": 0.05}
    ))
    SkillRegistry.register(Skill(
        id="scavenging", name="搜索技巧",
        description="提高搜索物资的收获量。",
        max_level=10,
        effect_per_level={"loot_bonus": 0.1}
    ))
    SkillRegistry.register(Skill(
        id="crafting", name="制作技能",
        description="解锁更高级的合成配方。",
        max_level=10,
        effect_per_level={"craft_level": 1}
    ))
    SkillRegistry.register(Skill(
        id="medicine", name="医疗知识",
        description="提高治疗效果。",
        max_level=10,
        effect_per_level={"heal_bonus": 0.1}
    ))


def init_default_recipes():
    """初始化默认合成配方"""

    RecipeRegistry.register(
        "bandage", {"cloth": 2},
        description="用布料制作绷带"
    )
    RecipeRegistry.register(
        "first_aid_kit", {"bandage": 3, "medicine": 2, "cloth": 1},
        description="制作急救包", required_building="workshop", min_level=1
    )
    RecipeRegistry.register(
        "baseball_bat", {"wood": 3, "nails": 2},
        description="制作棒球棍", required_building="workshop", min_level=1
    )
    RecipeRegistry.register(
        "fire_axe", {"iron": 5, "wood": 2},
        description="打造消防斧", required_building="workshop", min_level=2
    )
    RecipeRegistry.register(
        "crossbow", {"wood": 5, "iron": 3, "rope": 2},
        description="制作十字弩", required_building="workshop", min_level=3
    )
    RecipeRegistry.register(
        "leather_jacket", {"leather": 5, "cloth": 3},
        description="缝制皮夹克", required_building="workshop", min_level=1
    )
    RecipeRegistry.register(
        "riot_shield", {"iron": 5, "plastic": 3},
        description="打造防暴盾牌", required_building="workshop", min_level=2
    )
    RecipeRegistry.register(
        "hunting_rifle", {"iron": 10, "wood": 5, "gunpowder": 3},
        description="组装猎枪", required_building="workshop", min_level=3
    )
    RecipeRegistry.register(
        "stimpack", {"medicine": 3, "herb": 2, "electronics": 1},
        description="制作兴奋剂", required_building="workshop", min_level=3
    )
    RecipeRegistry.register(
        "antidote", {"medicine": 3, "herb": 3},
        description="制作解毒剂", required_building="workshop", min_level=2
    )


def init_default_achievements():
    """初始化成就系统"""

    AchievementRegistry.register(Achievement(
        id="first_blood", name="第一滴血",
        description="击杀第一个丧尸",
        category="combat",
        condition="zombies_killed >= 1",
        reward_description="获得锈刀和 50 经验",
        reward_items={"rusty_knife": 1},
        reward_exp=50,
    ))
    AchievementRegistry.register(Achievement(
        id="zombie_slayer", name="丧尸杀手",
        description="累计击杀 20 个丧尸",
        category="combat",
        condition="zombies_killed >= 20",
        reward_description="获得猎枪和 200 经验",
        reward_items={"hunting_rifle": 1, "ammo": 10},
        reward_exp=200,
        reward_title="丧尸杀手",
    ))
    AchievementRegistry.register(Achievement(
        id="zombie_exterminator", name="丧尸灭绝者",
        description="累计击杀 100 个丧尸",
        category="combat",
        condition="zombies_killed >= 100",
        reward_description="获得火焰剑、500经验，解锁称号「灭绝者」",
        reward_items={"flame_sword": 1},
        reward_exp=500,
        reward_title="灭绝者",
    ))
    AchievementRegistry.register(Achievement(
        id="survivor_10", name="生存十天",
        description="存活超过 10 天",
        category="survival",
        condition="days_survived >= 10",
        reward_description="获得 100 经验",
        reward_exp=100,
    ))
    AchievementRegistry.register(Achievement(
        id="survivor_50", name="生存五十天",
        description="存活超过 50 天",
        category="survival",
        condition="days_survived >= 50",
        reward_description="获得 500 经验和军用防弹衣，解锁称号「老兵」",
        reward_exp=500,
        reward_items={"military_vest": 1},
        reward_title="老兵",
    ))
    AchievementRegistry.register(Achievement(
        id="survivor_100", name="百天幸存者",
        description="存活超过 100 天",
        category="survival",
        condition="days_survived >= 100",
        reward_description="获得 1000 经验，解锁称号「末日传奇」",
        reward_exp=1000,
        reward_title="末日传奇",
    ))
    AchievementRegistry.register(Achievement(
        id="builder_5", name="初级建造者",
        description="建造 5 次建筑",
        category="building",
        condition="total_builds >= 5",
        reward_description="获得木材和石料",
        reward_resources={"wood": 30, "stone": 30},
        reward_exp=100,
    ))
    AchievementRegistry.register(Achievement(
        id="master_crafter", name="工匠大师",
        description="累计合成 50 个物品",
        category="building",
        condition="items_crafted >= 50",
        reward_description="获得 300 经验，解锁称号「工匠」",
        reward_exp=300,
        reward_title="工匠",
    ))
    AchievementRegistry.register(Achievement(
        id="pvp_first_win", name="首战告捷",
        description="在 PvP 偷袭中获胜一次",
        category="combat",
        condition="pvp_wins >= 1",
        reward_description="获得 200 经验",
        reward_exp=200,
    ))
    AchievementRegistry.register(Achievement(
        id="pvp_veteran", name="PVP老手",
        description="PvP 累计获胜 10 次",
        category="combat",
        condition="pvp_wins >= 10",
        reward_description="获得十字弩和 500 经验，解锁称号「猎人」",
        reward_items={"crossbow": 1, "ammo": 20},
        reward_exp=500,
        reward_title="猎人",
    ))
    AchievementRegistry.register(Achievement(
        id="level_10", name="十级幸存者",
        description="达到等级 10",
        category="general",
        condition="level >= 10",
        reward_description="获得 300 经验，解锁称号「精英」",
        reward_exp=300,
        reward_title="精英",
    ))


def init_default_classes():
    """初始化职业系统"""

    ClassRegistry.register(
        "scavenger", "拾荒者",
        "擅长搜索物资，在废墟中如鱼得水。搜索收益+30%。",
        bonuses={"loot_bonus": 0.3},
        starting_items={"scrap_metal": 5, "cloth": 3},
        starting_resources={"food": 5, "water": 3}
    )
    ClassRegistry.register(
        "soldier", "士兵",
        "受过专业军事训练，初始战斗能力更强。战斗+20%，初始攻击+3。",
        bonuses={"combat_bonus": 0.2, "attack_bonus": 3},
        starting_items={"rusty_knife": 1, "bandage": 3},
        starting_resources={"ammo": 5}
    )
    ClassRegistry.register(
        "doctor", "医生",
        "医疗专业知识丰富，治疗效果+50%，免疫疾病。",
        bonuses={"heal_bonus": 0.5, "immune_sick": True},
        starting_items={"bandage": 5, "first_aid_kit": 1, "herb": 3},
        starting_resources={"medicine": 5}
    )
    ClassRegistry.register(
        "engineer", "工程师",
        "精通建造和制造。建造消耗-20%，合成材料-15%。",
        bonuses={"build_discount": 0.2, "craft_discount": 0.15},
        starting_items={"scrap_metal": 3, "electronics": 2, "nails": 5},
        starting_resources={"wood": 10, "stone": 8, "iron": 3}
    )
    ClassRegistry.register(
        "survivalist", "生存专家",
        "荒野求生大师。饱食/口渴消耗-30%，理智恢复+20%。",
        bonuses={"decay_reduce": 0.3, "sanity_bonus": 0.2},
        starting_items={"canned_food": 3, "bottled_water": 3, "rope": 2},
        starting_resources={"food": 10, "water": 10}
    )
    ClassRegistry.register(
        "merchant", "商人",
        "精明的交易者。交易收益+40%，初始物资+50%。",
        bonuses={"trade_bonus": 0.4, "start_boost": 0.5},
        starting_items={"canned_food": 2, "bottled_water": 2, "bandage": 3},
        starting_resources={"food": 5, "water": 5, "wood": 3, "stone": 2}
    )


# ============================================================
# 初始化所有内容
# ============================================================

def init_all_content():
    """初始化所有游戏内容"""
    init_default_items()
    init_default_buildings()
    init_default_events()
    init_default_skills()
    init_default_recipes()
    init_default_achievements()
    init_default_classes()
