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
                 min_level: int = 1, resource_costs: Optional[Dict[str, int]] = None):
        """注册合成配方。
        materials: 需要消耗的物品 {item_id: count}
        resource_costs: 需要消耗的资源 {resource_type: count}
        """
        cls._recipes[result_item_id] = {
            "result": result_item_id,
            "materials": materials,
            "description": description,
            "required_building": required_building,
            "min_level": min_level,
            "resource_costs": resource_costs or {},
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
        description="一把老式猎枪，远程攻击的好帮手。每次战斗消耗弹药。",
        attack_bonus=20, durability=60, max_durability=60, rarity="uncommon",
        is_ranged=True
    ))
    ItemRegistry.register(Item(
        id="fire_axe", name="消防斧", category=ItemCategory.WEAPON,
        description="消防斧，劈砍力惊人，还能破门。",
        attack_bonus=15, durability=100, max_durability=100, rarity="uncommon"
    ))
    ItemRegistry.register(Item(
        id="crossbow", name="十字弩", category=ItemCategory.WEAPON,
        description="无声的远程武器，适合暗杀。每次战斗消耗弹药。",
        attack_bonus=25, durability=70, max_durability=70, rarity="rare",
        is_ranged=True
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

    # === 基础资源（可作为合成产物） ===
    _res_cat = getattr(ItemCategory, "RESOURCE", None) or ItemCategory.MATERIAL
    for res_id, res_name, res_desc in [
        ("food", "食物", "基础食物资源，维持饱食度"),
        ("water", "水", "基础水资源，维持口渴度"),
        ("wood", "木材", "基础建材，建造和合成的必需品"),
        ("stone", "石料", "基础石料，用于建造防御设施"),
        ("iron", "铁", "金属资源，制作高级武器和防具"),
        ("medicine", "药品", "医疗资源，制作药物和治疗伤病"),
        ("ammo", "弹药", "弹药资源，远程武器的消耗品"),
        ("fuel", "燃料", "燃料资源，驱动设备和熔炼金属"),
    ]:
        ItemRegistry.register(Item(
            id=res_id, name=res_name, category=_res_cat,
            description=res_desc, rarity="common"
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
                    "rewards": {"exp": (50, 100), "items": {"scrap_metal": (1, 3)}, "resources": {"ammo": (1, 5)}},
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
                              "first_aid_kit": (1, 3)},
                    "resources": {"food": (5, 15), "water": (5, 15), "fuel": (3, 10), "ammo": (5, 20)},
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
                        "items": {"hunting_rifle": (1, 1), "crossbow": (0, 1)},
                        "resources": {"fuel": (5, 15), "ammo": (10, 30)}
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

    # ================================================================
    # 补充事件 —— 资源类 (25个)
    # ================================================================

    EventRegistry.register(GameEvent(
        id="abandoned_supermarket", name="废弃超市",
        event_type=EventType.RESOURCE, weight=2.5,
        description="一座废弃的超市矗立在前方，货架虽然被翻过，但应该还有遗漏的物资。",
        choices=[
            {"text": "🛒 翻找货架", "result": {"resources": {"food": (3, 12), "water": (2, 8)}, "items": {"canned_food": (0, 3), "bottled_water": (0, 2)}, "description": "你在角落里找到了几罐没被发现的罐头和水！"}},
            {"text": "🔦 搜索仓库", "result": {"resources": {"food": (5, 20), "water": (3, 10), "wood": (2, 5)}, "items": {"mre": (0, 2)}, "combat": {"enemy_attack": 8, "enemy_health": 20}, "rewards": {"exp": (15, 30)}, "description_win": "你赶走了仓库里的流浪动物，收获了不少存货。", "description_lose": "仓库里有东西袭击了你！"}},
            {"text": "🚶 太明显了，不去", "result": {"description": "超市太显眼了，你觉得那里可能有其他幸存者或掠夺者。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="warehouse_ruins", name="仓库废墟",
        event_type=EventType.RESOURCE, weight=2.0,
        description="一座发生过火灾的仓库，虽然大部分烧毁了，但金属框架还立着。",
        choices=[
            {"text": "🔩 搜刮金属材料", "result": {"resources": {"iron": (3, 10), "stone": (1, 3)}, "items": {"scrap_metal": (2, 5), "nails": (1, 3)}, "description": "废墟里残留了不少可用的金属和零件。"}},
            {"text": "📦 翻找幸存箱子", "result": {"resources": {"food": (1, 5)}, "items": {"canned_food": (0, 1), "cloth": (1, 3)}, "description": "几个没有完全烧毁的箱子还留有一些物资。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="fruit_tree", name="野生果树",
        event_type=EventType.RESOURCE, weight=2.5,
        description="路边有几棵野果树，树上挂满了果实，看起来已经成熟了。",
        choices=[
            {"text": "🧗 爬树采摘", "result": {"resources": {"food": (4, 12), "water": (1, 3)}, "health_damage": (3, 8), "description": "你爬上去摘了不少果子，但不小心擦伤了。"}},
            {"text": "🪨 用石头砸", "result": {"resources": {"food": (2, 8)}, "description": "你用石头砸下了一些果实，不过有些摔烂了。"}},
            {"text": "🔍 先检查是否有毒", "result": {"exp": (10, 20), "resources": {"food": (3, 10)}, "description": "你谨慎地辨认了果实，确定无毒后安心享用。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="abandoned_vehicle", name="废弃车辆",
        event_type=EventType.RESOURCE, weight=2.0,
        description="路边停着一辆落满灰尘的废弃汽车。",
        choices=[
            {"text": "🔧 拆零件", "result": {"items": {"scrap_metal": (2, 4), "electronics": (0, 2), "plastic": (1, 3)}, "resources": {"iron": (1, 5), "fuel": (1, 3)}, "description": "你拆下了可用的零件和剩余的燃油。"}},
            {"text": "📦 翻后备箱", "result": {"items": {"rope": (0, 1), "cloth": (1, 2)}, "resources": {"food": (0, 3), "water": (0, 2)}, "description": "后备箱里有一些零碎物资。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="hunters_cache", name="猎人储藏点",
        event_type=EventType.RESOURCE, weight=1.5,
        description="一棵大树的树洞中藏着一个猎人的小储藏箱。",
        choices=[
            {"text": "🎁 打开看看", "result": {"items": {"crossbow": (0, 1), "rope": (1, 3), "leather": (2, 5)}, "resources": {"food": (3, 8)}, "exp": (20, 40), "description": "猎人的藏货真不错！你找到了弓弩和皮料。"}},
            {"text": "🔄 原样放回", "result": {"description": "你觉得这可能是有主的，决定不碰。但记下了这个位置。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="pharmacy_ruins", name="药房废墟",
        event_type=EventType.RESOURCE, weight=1.5,
        description="一家已经坍塌了一半的药店，柜台后面的药柜还勉强立着。",
        choices=[
            {"text": "💊 搜索药柜", "result": {"resources": {"medicine": (3, 10)}, "items": {"bandage": (1, 3), "first_aid_kit": (0, 2), "herb": (1, 3)}, "description": "你找到了一些还没过期的药品和医疗用品。"}},
            {"text": "🔬 搜索实验室", "result": {"resources": {"medicine": (1, 5)}, "items": {"antidote": (0, 1), "stimpack": (0, 1), "electronics": (0, 1)}, "description": "药房后面的小实验室里有些特殊药物。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="gas_station", name="废弃加油站",
        event_type=EventType.RESOURCE, weight=2.0,
        description="一座废弃的加油站，加油机早已停用，但地下储油罐可能还有剩余。",
        choices=[
            {"text": "⛽ 抽取储油罐", "result": {"resources": {"fuel": (5, 15)}, "items": {"plastic": (1, 3)}, "description": "你成功地抽出了剩余的燃油！"}},
            {"text": "🏪 搜索便利店", "result": {"resources": {"food": (1, 5), "water": (1, 3)}, "items": {"canned_food": (0, 2)}, "description": "加油站的小便利店还有些存货。"}},
            {"text": "🚬 点根烟冷静一下", "result": {"description": "你差点犯了大错——在这种地方点火等于自杀。你赶紧掐灭了烟头。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="raided_convoy", name="被劫车队",
        event_type=EventType.RESOURCE, weight=1.5,
        description="一支明显被劫掠过的军用运输车队，车辆残骸散落在路面上。",
        choices=[
            {"text": "🔍 仔细翻找残骸", "result": {"resources": {"ammo": (3, 12), "iron": (3, 8)}, "items": {"gunpowder": (1, 3), "scrap_metal": (2, 5), "mre": (0, 2)}, "description": "劫掠者漏掉了一些弹药和军用口粮。"}},
            {"text": "🧭 追踪劫掠者踪迹", "result": {"exp": (20, 50), "description": "你分析了劫掠者的撤离路线，摸清了他们的活动范围。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="old_farm", name="废弃农场",
        event_type=EventType.RESOURCE, weight=1.5,
        description="一座荒废的农场，田地早已荒芜，但谷仓还立着。",
        choices=[
            {"text": "🌾 搜索谷仓", "result": {"resources": {"food": (5, 15), "wood": (3, 8)}, "items": {"rope": (1, 2), "cloth": (1, 3)}, "description": "谷仓里还堆着几袋发霉的谷物，虽然大部分不能吃，但总有些还能用的。"}},
            {"text": "🔧 搜索工具房", "result": {"items": {"fire_axe": (0, 1), "nails": (2, 5)}, "resources": {"iron": (2, 5)}, "description": "工具房里找到了还不错的工具。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="fishing_spot", name="钓鱼宝地",
        event_type=EventType.RESOURCE, weight=2.0,
        description="一个清澈的湖泊出现在眼前，水面不时泛起涟漪。",
        choices=[
            {"text": "🎣 制作鱼竿钓鱼", "result": {"resources": {"food": (5, 15), "water": (2, 5)}, "exp": (15, 30), "description": "湖里的鱼又大又肥！你今天钓了好几条。"}},
            {"text": "🏊 下水摸鱼", "result": {"resources": {"food": (3, 8)}, "health_damage": (5, 10), "description": "你下水摸了几条鱼，但湖水冰冷刺骨。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="water_well", name="古老水井",
        event_type=EventType.RESOURCE, weight=2.0,
        description="一口古老的石井藏在灌木丛后面，井水看起来还算干净。",
        choices=[
            {"text": "🪣 打水饮用", "result": {"resources": {"water": (8, 20)}, "description": "井水甘甜清澈，你装满了所有的水壶。"}},
            {"text": "🔍 检查井底", "result": {"resources": {"water": (5, 10)}, "items": {"scrap_metal": (0, 2), "glass": (1, 3)}, "exp": (10, 25), "description": "井底居然有些被人藏起来的物资。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="apiary_ruins", name="废弃蜂场",
        event_type=EventType.RESOURCE, weight=1.0,
        description="一片废弃的养蜂场，蜂箱已经破败，但似乎还有蜜蜂在活动。",
        choices=[
            {"text": "🍯 小心取蜜", "result": {"resources": {"food": (5, 12)}, "health_damage": (3, 8), "description": "你冒着被蛰的风险取了一些蜂蜜，虽然被蛰了几下但值得。"}},
            {"text": "🔥 用烟熏走蜜蜂", "result": {"resources": {"food": (3, 8), "wood": (1, 3)}, "description": "你用烟把大部分蜜蜂熏走后取了蜜。"}},
            {"text": "🚶 算了，不想被蛰", "result": {"description": "你决定不去招惹那些蜜蜂。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="tool_shed", name="工具棚",
        event_type=EventType.RESOURCE, weight=2.0,
        description="路边有个上了锁的工具棚，看起来是某个工程队的遗留物。",
        choices=[
            {"text": "🔨 撬锁进入", "result": {"items": {"fire_axe": (0, 1), "nails": (3, 8), "rope": (1, 2)}, "resources": {"wood": (2, 5), "iron": (1, 3)}, "description": "工具棚里的工具保存得很好！"}},
            {"text": "🔓 试着开锁", "result": {"escape_chance": 0.5, "description_escape": "你用小工具打开了锁！", "description_fail": "锁坏了，你打不开门。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="abandoned_camp", name="被遗弃的营地",
        event_type=EventType.RESOURCE, weight=1.5,
        description="一个显然被仓促遗弃的露营地，帐篷还立着，篝火已经冰冷。",
        choices=[
            {"text": "🏕️ 搜刮营地", "result": {"resources": {"food": (3, 10), "wood": (2, 8), "water": (2, 5)}, "items": {"cloth": (1, 3), "rope": (0, 2)}, "description": "前任主人走得太匆忙，留下了不少好东西。"}},
            {"text": "🔍 调查遗弃原因", "result": {"exp": (20, 50), "items": {"survivor_journal": (0, 1)}, "description": "你发现了一本日记，记录了附近丧尸群的移动规律。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="mushroom_grove", name="蘑菇丛",
        event_type=EventType.RESOURCE, weight=1.5,
        description="一片阴暗的树林中长满了各种蘑菇，颜色各异。",
        choices=[
            {"text": "🍄 采集可食用蘑菇", "result": {"resources": {"food": (3, 10)}, "exp": (15, 30), "description": "凭借你的知识，你采集了一大袋可食用蘑菇。"}},
            {"text": "🧪 全都采走", "result": {"resources": {"food": (5, 15), "medicine": (2, 5)}, "health_damage": (5, 15), "description": "你采了不少，但误食了一些有毒的，肚子不太舒服。"}},
            {"text": "📖 先研究再决定", "result": {"exp": (30, 60), "description": "你花时间学习了蘑菇的鉴别知识，为以后做好了准备。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="old_library", name="旧图书馆",
        event_type=EventType.RESOURCE, weight=1.0,
        description="一座老旧的图书馆，大部分书籍已经腐朽，但或许有些有用的资料。",
        choices=[
            {"text": "📚 搜索知识典籍", "result": {"exp": (50, 120), "items": {"survivor_journal": (1, 2)}, "description": "你找到了几本幸存者指南和植物图鉴，学到了很多。"}},
            {"text": "🔍 搜索管理员办公室", "result": {"items": {"radio": (0, 1), "electronics": (1, 2)}, "resources": {"food": (1, 3)}, "description": "管理员办公室里有一台还能用的收音机。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="hardware_store", name="五金店",
        event_type=EventType.RESOURCE, weight=1.5,
        description="一家五金店，招牌歪了半边门还锁着，看来还没被洗劫过。",
        choices=[
            {"text": "🔨 砸开锁进去", "result": {"items": {"nails": (3, 10), "scrap_metal": (3, 8), "rope": (1, 3)}, "resources": {"wood": (3, 8), "iron": (2, 5), "stone": (1, 3)}, "description": "五金店简直是建材天堂！你往包里塞满了材料。"}},
            {"text": "🪟 从窗户进去", "result": {"items": {"nails": (2, 5), "glass": (1, 2)}, "resources": {"wood": (1, 3), "iron": (1, 3)}, "health_damage": (3, 8), "description": "你翻窗时不慎被玻璃划伤了。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="abandoned_garden", name="废弃菜园",
        event_type=EventType.RESOURCE, weight=1.5,
        description="一片被遗忘的菜园，虽然杂草丛生，但还有一些生命力顽强的蔬菜。",
        choices=[
            {"text": "🥬 采摘蔬菜", "result": {"resources": {"food": (5, 15)}, "items": {"herb": (1, 3)}, "description": "萝卜和土豆长得还不错，你收获了一大袋蔬菜。"}},
            {"text": "🌱 收集种子", "result": {"resources": {"food": (2, 5)}, "exp": (20, 30), "description": "你收集了一些可以种植的种子，说不定以后能用上。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="cave_entrance_res", name="洞穴入口",
        event_type=EventType.RESOURCE, weight=1.0,
        description="山脚下有个不起眼的洞穴入口，里面黑漆漆的。",
        choices=[
            {"text": "🔦 探索洞穴", "result": {"resources": {"iron": (5, 15), "stone": (5, 10)}, "items": {"herb": (2, 4), "scrap_metal": (1, 2)}, "description": "洞穴里有丰富的矿石和洞穴药材！"}},
            {"text": "🔥 举火把探路", "result": {"resources": {"iron": (3, 10), "stone": (3, 8)}, "combat": {"enemy_attack": 12, "enemy_health": 30}, "rewards": {"exp": (20, 50)}, "description_win": "火光惊动了洞穴里的蝙蝠，但你成功驱散了它们。", "description_lose": "成群的蝙蝠向你扑来！"}},
            {"text": "📍 做标记，以后再来", "result": {"description": "你在地图上标记了洞穴的位置，等准备好了再探索。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="berry_bushes", name="浆果丛",
        event_type=EventType.RESOURCE, weight=2.5,
        description="灌木丛中长满了野生的浆果，红得发紫。",
        choices=[
            {"text": "🫐 尽情采摘", "result": {"resources": {"food": (4, 10), "water": (1, 3)}, "description": "浆果甜美多汁，你吃了一顿饱的还带了不少。"}},
            {"text": "🧺 大量采集储备", "result": {"resources": {"food": (3, 12)}, "items": {"herb": (0, 2)}, "description": "你把能摘的都摘了，有些浆果还可以晒干储存。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="forest_clearing", name="林间空地",
        event_type=EventType.RESOURCE, weight=1.5,
        description="密林中突然出现了一片开阔的空地，地面上长满了可食用的野菜。",
        choices=[
            {"text": "🌿 采集野菜", "result": {"resources": {"food": (3, 8), "medicine": (1, 3)}, "items": {"herb": (2, 5)}, "description": "这里的野菜种类丰富，有一些还有药用价值。"}},
            {"text": "🪓 顺便砍柴", "result": {"resources": {"wood": (5, 15), "food": (2, 5)}, "description": "空地周边的枯木是很好的柴火。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="corn_field", name="玉米地",
        event_type=EventType.RESOURCE, weight=2.0,
        description="一片野生的玉米地，虽然无人照料但玉米长得还不错。",
        choices=[
            {"text": "🌽 掰玉米", "result": {"resources": {"food": (8, 20)}, "description": "玉米丰收！你掰了好几十个，够吃很多天了。"}},
            {"text": "🔥 就地烤玉米", "result": {"resources": {"food": (3, 8), "wood": (1, 2)}, "exp": (10, 20), "description": "你生了一小堆火烤玉米，热乎乎的玉米很香甜。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="ruined_church", name="废墟教堂",
        event_type=EventType.RESOURCE, weight=1.0,
        description="一座被炮火炸毁了一半的教堂，彩色玻璃碎片散落一地。",
        choices=[
            {"text": "⛪ 搜索地下室", "result": {"resources": {"food": (5, 15), "water": (5, 15), "medicine": (2, 5)}, "items": {"canned_food": (2, 5), "cloth": (2, 4)}, "description": "教堂的地下室被用作应急避难所，储备了大量物资！"}},
            {"text": "🕯️ 在祭坛前祈祷", "result": {"exp": (20, 40), "description": "在末日中片刻的宁静也是一种力量。你感觉心情好多了。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="parking_garage", name="停车场废墟",
        event_type=EventType.RESOURCE, weight=1.5,
        description="一座多层停车场，里面还停着不少报废的车辆。",
        choices=[
            {"text": "🔧 拆车零件", "result": {"items": {"scrap_metal": (3, 8), "electronics": (1, 3), "plastic": (2, 5)}, "resources": {"fuel": (3, 10), "iron": (3, 8)}, "description": "停车场就是一座零件矿山，你拆到了不少好东西。"}},
            {"text": "🚗 检查还能开的车", "result": {"escape_chance": 0.3, "description_escape": "有一辆居然还能发动！你开了一段路，省了不少脚力。", "description_fail": "你试了几辆都不行，电瓶早就没电了。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="junkyard", name="废品回收站",
        event_type=EventType.RESOURCE, weight=1.5,
        description="一个巨大的废品回收站，堆满了各种金属和电子垃圾。",
        choices=[
            {"text": "🔩 淘金属", "result": {"items": {"scrap_metal": (5, 15), "electronics": (1, 3)}, "resources": {"iron": (5, 12)}, "description": "废品站简直就是材料宝库！你满载而归。"}},
            {"text": "💡 淘电子元件", "result": {"items": {"electronics": (3, 8), "glass": (1, 3)}, "resources": {"iron": (1, 3)}, "description": "你专门挑电子设备，找到了不少还能用的零件。"}},
        ]
    ))

    # ================================================================
    # 补充事件 —— 危险类 (20个)
    # ================================================================

    EventRegistry.register(GameEvent(
        id="bandit_ambush", name="土匪埋伏",
        event_type=EventType.DANGER, weight=1.5,
        description="几个埋伏在路边废墟中的土匪突然跳了出来！「把手举起来！」",
        choices=[
            {"text": "⚔️ 拼死一搏", "result": {"combat": {"enemy_attack": 20, "enemy_health": 50}, "rewards": {"exp": (60, 120), "items": {"scrap_metal": (2, 5)}, "resources": {"ammo": (2, 8)}}, "description_win": "你反杀了土匪，从他们身上缴获了武器和物资。", "description_lose": "土匪人多势众，你被打倒在地..."}},
            {"text": "💰 交出一半物资", "result": {"lose_resources": {"food": 0.5, "water": 0.5, "ammo": 0.5}, "description": "破财消灾，你交出了部分物资换了一条命。"}},
            {"text": "💬 试图谈判", "result": {"escape_chance": 0.4, "description_escape": "你成功说服了他们去找更肥的目标。", "description_fail": "土匪不吃这一套！他们一拥而上。", "fail_damage": (15, 30)}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="zombie_horde", name="丧尸群",
        event_type=EventType.DANGER, weight=1.5,
        description="前方街道上聚集了一大群丧尸，至少有二十多只！",
        choices=[
            {"text": "🥷 潜行绕路", "result": {"stealth_chance": 0.6, "description_stealth": "你贴着墙根，悄无声息地穿过了街区。", "description_fail": "一只丧尸突然转过头来！", "fail_damage": (10, 25)}},
            {"text": "🏃 全速冲刺", "result": {"escape_chance": 0.5, "description_escape": "你一路狂奔，在丧尸反应过来之前冲了过去。", "description_fail": "丧尸堵住了去路，你被包围了。", "fail_damage": (20, 40)}},
            {"text": "💣 引爆炸药分散它们", "result": {"combat": {"enemy_attack": 15, "enemy_health": 60}, "rewards": {"exp": (80, 150)}, "description_win": "你利用爆炸引开了大部分丧尸，逐个击破！", "description_lose": "爆炸引来的丧尸比你预想的还多..."}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="mutant_dog", name="变异犬",
        event_type=EventType.DANGER, weight=1.5,
        description="一只浑身长着肿瘤的变异犬拦住了去路，它呼哧呼哧地瞪着你。",
        choices=[
            {"text": "⚔️ 正面迎战", "result": {"combat": {"enemy_attack": 15, "enemy_health": 40}, "rewards": {"exp": (40, 80), "items": {"leather": (1, 3)}}, "description_win": "变异犬虽然凶猛但毕竟只是动物，你成功击杀了它。", "description_lose": "变异犬的速度超乎你的想象！"}},
            {"text": "🍖 丢食物引开", "result": {"lose_resources": {"food": 0.3}, "description": "你扔出了一块肉，变异犬追着肉跑开了。"}},
            {"text": "🤫 慢慢后退", "result": {"stealth_chance": 0.6, "description_stealth": "你盯着它的眼睛，慢慢退出了它的领地。", "description_fail": "变异犬以为你在挑衅它！", "fail_damage": (10, 20)}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="collapse_building", name="建筑坍塌",
        event_type=EventType.DANGER, weight=1.0,
        description="你正经过一座摇摇欲坠的建筑时，它突然开始坍塌！",
        choices=[
            {"text": "🏃 拼命跑开", "result": {"escape_chance": 0.7, "description_escape": "你在最后一秒跳出了坍塌范围！", "description_fail": "碎石砸中了你！", "fail_damage": (15, 30)}},
            {"text": "🛡️ 找掩体躲避", "result": {"health_damage": (5, 15), "description": "你躲在一个坚固的墙角，虽然被飞溅的碎石擦伤，但没有大碍。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="poisonous_smoke", name="毒烟区",
        event_type=EventType.DANGER, weight=1.0,
        description="前方飘来一阵黄绿色的烟雾，像是化学品燃烧产生的毒烟。",
        choices=[
            {"text": "😷 捂住口鼻快跑", "result": {"escape_chance": 0.6, "description_escape": "你憋住气冲过了毒烟区。", "description_fail": "你在烟雾中迷失了方向...", "fail_damage": (10, 20)}},
            {"text": "🔍 绕道寻找上风口", "result": {"resources": {"medicine": (1, 3)}, "exp": (15, 30), "description": "你聪明地从上风口绕了过去，还发现了泄漏源附近遗落的药品。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="landmine_zone", name="地雷区",
        event_type=EventType.DANGER, weight=0.8,
        description="地面上隐约可见一些不自然的凸起，这里似乎被埋了地雷！",
        choices=[
            {"text": "🐾 一步一步探路", "result": {"escape_chance": 0.6, "description_escape": "你小心翼翼地穿过了雷区。", "description_fail": "轰！你踩到了一颗地雷！", "fail_damage": (30, 60)}},
            {"text": "🔄 放弃这条路", "result": {"description": "安全第一，你选择了绕道，虽然多花了些时间。"}},
            {"text": "🔧 尝试拆雷", "result": {"escape_chance": 0.3, "description_escape": "你竟然成功拆除了几颗地雷并安全通过！", "description_fail": "拆除失败！", "fail_damage": (20, 50)}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="rabid_animal", name="疯动物",
        event_type=EventType.DANGER, weight=1.0,
        description="一只口吐白沫的动物歪歪扭扭地向你走来，看起来感染了某种病毒。",
        choices=[
            {"text": "⚔️ 迅速击杀", "result": {"combat": {"enemy_attack": 10, "enemy_health": 25}, "rewards": {"exp": (25, 50)}, "description_win": "你一棍子打倒了它，最好别碰它的尸体。", "description_lose": "你被咬了！需要尽快找抗生素..."}},
            {"text": "🏹 远程射杀", "result": {"resources": {"food": (2, 5)}, "description": "你用远程武器干净利落地解决了它。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="toxic_leak", name="毒气泄漏",
        event_type=EventType.DANGER, weight=1.0,
        description="路边一辆翻倒的罐车正在泄漏不明气体，空气中弥漫着刺鼻的味道。",
        choices=[
            {"text": "🏃 快速通过", "result": {"health_damage": (5, 15), "description": "你屏住呼吸冲了过去，但还是吸入了一些毒气。"}},
            {"text": "🔄 绕远路", "result": {"resources": {"wood": (1, 3), "stone": (1, 2)}, "description": "虽然多走了一段路，但安全最重要。顺路捡了些材料。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="sniper_threat", name="狙击手威胁",
        event_type=EventType.DANGER, weight=0.8,
        description="你发现远处楼顶有反光——是狙击镜！有人在瞄准你！",
        choices=[
            {"text": "🏃 蛇形走位逃跑", "result": {"escape_chance": 0.7, "description_escape": "你的蛇形走位让狙击手无法瞄准，安全脱身了。", "description_fail": "一颗子弹擦着你的肩膀过去了！", "fail_damage": (15, 30)}},
            {"text": "🏚️ 躲进附近建筑", "result": {"description": "你一个翻滚躲进了旁边的废楼，狙击手丢失了目标。"}},
            {"text": "🔫 尝试反狙击", "result": {"combat": {"enemy_attack": 25, "enemy_health": 30}, "rewards": {"exp": (80, 150), "items": {"hunting_rifle": (0, 1)}}, "description_win": "你端起步枪冷静瞄准，一枪把对方拿下了！", "description_lose": "对方是专业狙击手，你没能伤到他..."}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="trap_building", name="陷阱建筑",
        event_type=EventType.DANGER, weight=1.0,
        description="你走进了一栋看似完好的建筑，突然脚下的地板碎裂了！",
        choices=[
            {"text": "🤸 抓住边缘", "result": {"escape_chance": 0.6, "description_escape": "你反应迅速，抓住了断裂的边缘爬了上去。", "description_fail": "你掉了下去！", "fail_damage": (20, 40)}},
            {"text": "🪢 用绳索固定", "result": {"health_damage": (5, 10), "resources": {"iron": (1, 3)}, "description": "你用绳索稳住了身体，慢慢下降到底层还发现了些废铁。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="wild_bear", name="野熊",
        event_type=EventType.DANGER, weight=1.5,
        description="一只巨大的棕熊正从树林那边走过来，它看起来心情不太好。",
        choices=[
            {"text": "⚔️ 准备战斗", "result": {"combat": {"enemy_attack": 25, "enemy_health": 80}, "rewards": {"exp": (80, 150), "items": {"leather": (3, 8)}, "resources": {"food": (10, 30)}}, "description_win": "你居然干掉了一头熊！这可是末日里的传奇战绩！", "description_lose": "熊的力量远超你的预期..."}},
            {"text": "🐻 装死不动", "result": {"escape_chance": 0.5, "description_escape": "熊闻了闻你，以为你死了，无趣地离开了。", "description_fail": "熊不吃这一套！", "fail_damage": (25, 50)}},
            {"text": "🤫 悄悄后退", "result": {"stealth_chance": 0.7, "description_stealth": "你蹑手蹑脚地退出了熊的领地。", "description_fail": "咔嚓！你踩断了一根树枝！", "fail_damage": (15, 30)}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="contaminated_water", name="污染水源",
        event_type=EventType.DANGER, weight=1.5,
        description="这里的水源被严重污染了，水面上漂浮着油污和不明物质。",
        choices=[
            {"text": "🧪 尝试净化", "result": {"resources": {"water": (3, 8), "medicine": (1, 2)}, "exp": (15, 30), "description": "你利用简易过滤装置净化了一些水，还学到了更多净化技巧。"}},
            {"text": "🥤 冒险饮用", "result": {"resources": {"water": (5, 10)}, "health_damage": (10, 25), "description": "你实在口渴难耐，喝了一些——但肚子开始翻江倒海..."}},
            {"text": "🚶 继续寻找干净水源", "result": {"description": "你不会冒险喝污染水，继续上路寻找干净的水源。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="wildfire", name="野火蔓延",
        event_type=EventType.DANGER, weight=1.0,
        description="远处升起了浓烟，野火正在向你所在的方向蔓延！",
        choices=[
            {"text": "🏃 逆风逃跑", "result": {"escape_chance": 0.7, "description_escape": "你沿着逆风方向成功跑出了火灾区域。", "description_fail": "风向突然变了！", "fail_damage": (15, 25)}},
            {"text": "💧 用湿布捂住口鼻穿过去", "result": {"health_damage": (5, 15), "lose_resources": {"water": 0.3}, "description": "你消耗了一些水来浸湿布料，穿过了较安全的区域。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="bridge_collapse", name="断桥",
        event_type=EventType.DANGER, weight=0.8,
        description="你正要走上一座桥时，桥面突然断裂了！",
        choices=[
            {"text": "🤸 跳过去", "result": {"escape_chance": 0.5, "description_escape": "你一个箭步跳到了对面！", "description_fail": "你没跳过去，掉进了下方的河沟...", "fail_damage": (15, 30)}},
            {"text": "🪢 找绳索荡过去", "result": {"description": "你找到了一条绳索固定在高处，像人猿泰山一样荡了过去，酷毙了！"}},
            {"text": "🔄 沿河找其他过河点", "result": {"resources": {"wood": (2, 5)}, "description": "你沿着河岸找到了一个浅滩，安全涉水过去，还捡了些漂流木。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="insect_swarm", name="变异虫群",
        event_type=EventType.DANGER, weight=1.0,
        description="一大群变异的巨型昆虫嗡嗡地向你飞来！",
        choices=[
            {"text": "🔥 点燃火把驱虫", "result": {"combat": {"enemy_attack": 8, "enemy_health": 50}, "rewards": {"exp": (30, 60)}, "description_win": "火焰驱散了虫群，剩下的被你消灭了。", "description_lose": "虫子太多了！"}},
            {"text": "🏃 狂奔逃跑", "result": {"escape_chance": 0.6, "description_escape": "你跑得比虫子快，找了栋建筑躲了进去。", "description_fail": "虫子铺天盖地地追上了你...", "fail_damage": (10, 20)}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="avalanche", name="雪崩",
        event_type=EventType.DANGER, weight=0.8,
        description="山间传来隆隆巨响——雪崩正滚落下来！",
        choices=[
            {"text": "🏃 横向逃离", "result": {"escape_chance": 0.6, "description_escape": "你冲出了雪崩路径，看着积雪从身边呼啸而过。", "description_fail": "雪崩追上了你！", "fail_damage": (20, 40)}},
            {"text": "🏔️ 找坚固掩体", "result": {"health_damage": (5, 15), "description": "你躲在一块巨岩后面，雪流从两侧绕过。虽然被溅起的碎冰砸了几下，但没有大碍。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="cult_ritual", name="邪教仪式",
        event_type=EventType.DANGER, weight=0.8,
        description="你撞见了一群穿着黑袍的人正在进行诡异的仪式，空气中弥漫着血腥味。",
        choices=[
            {"text": "🤫 悄悄离开", "result": {"stealth_chance": 0.7, "description_stealth": "你没有惊动任何人，悄悄地退了出去。", "description_fail": "一个教徒发现了你！", "fail_damage": (15, 30)}},
            {"text": "⚔️ 打断仪式", "result": {"combat": {"enemy_attack": 18, "enemy_health": 60}, "rewards": {"exp": (60, 120), "items": {"fire_axe": (0, 1)}, "resources": {"medicine": (2, 5)}}, "description_win": "你击败了邪教徒，从他们的供台上缴获了不少东西。", "description_lose": "教徒们一拥而上..."}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="acid_rain", name="酸雨来袭",
        event_type=EventType.DANGER, weight=1.0,
        description="天空突然下起了带着刺鼻气味的雨——是酸雨！淋久了皮肤会灼伤。",
        choices=[
            {"text": "🏠 寻找遮蔽处", "result": {"description": "你迅速在一处屋檐下躲避，等酸雨过去。"}},
            {"text": "🛡️ 用废弃物遮挡", "result": {"health_damage": (3, 8), "items": {"plastic": (1, 3)}, "description": "你捡起废弃的塑料板挡雨，虽然还是溅到了一些，但找到了些塑料材料。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="raider_roadblock", name="掠夺者路障",
        event_type=EventType.DANGER, weight=1.0,
        description="前方的道路被掠夺者设置了路障，几个全副武装的人在把守。",
        choices=[
            {"text": "🥷 绕道潜行", "result": {"stealth_chance": 0.6, "description_stealth": "你绕了小路，成功避开了他们。", "description_fail": "掠夺者的哨兵发现了你！", "fail_damage": (10, 20)}},
            {"text": "💰 缴纳过路费", "result": {"lose_resources": {"food": 0.3, "water": 0.3}, "description": "你交了一些物资当买路钱，他们放你过去了。"}},
            {"text": "⚔️ 强行突破", "result": {"combat": {"enemy_attack": 22, "enemy_health": 60}, "rewards": {"exp": (50, 100), "items": {"scrap_metal": (2, 4)}, "resources": {"ammo": (3, 10)}}, "description_win": "你突破了路障，反杀了守卫！", "description_lose": "寡不敌众..."}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="zombie_nest", name="丧尸巢穴",
        event_type=EventType.DANGER, weight=1.0,
        description="你误入了一个丧尸的巢穴！地上到处是骸骨和腐臭的残渣。",
        choices=[
            {"text": "🥷 小心退出", "result": {"stealth_chance": 0.5, "description_stealth": "你屏住呼吸，一步一步退出了巢穴。", "description_fail": "地上的人骨被你踩碎了！", "fail_damage": (15, 30)}},
            {"text": "💣 扔燃烧瓶清场", "result": {"combat": {"enemy_attack": 12, "enemy_health": 80}, "rewards": {"exp": (100, 200), "items": {"scrap_metal": (3, 6)}, "resources": {"iron": (2, 5)}}, "description_win": "燃烧瓶烧死了大部分丧尸，你趁机清理巢穴，搜刮了不少战利品！", "description_lose": "丧尸太多了，燃烧瓶不够..."}},
        ]
    ))

    # ================================================================
    # 补充事件 —— 机遇类 (15个)
    # ================================================================

    EventRegistry.register(GameEvent(
        id="crashed_drone", name="坠毁无人机",
        event_type=EventType.OPPORTUNITY, weight=0.8,
        description="你发现了一架坠毁的军用无人机，虽然大部分损坏了，但核心部件还在。",
        choices=[
            {"text": "🔧 拆解零件", "result": {"items": {"electronics": (3, 8), "scrap_metal": (2, 4), "gunpowder": (0, 2)}, "exp": (30, 60), "description": "无人机上的高科技零件价值不菲！"}},
            {"text": "📡 尝试读取数据", "result": {"exp": (50, 100), "items": {"radio": (0, 1)}, "description": "你成功读取了无人机存储卡，获得了周边区域的地图数据。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="survival_manual", name="生存手册",
        event_type=EventType.OPPORTUNITY, weight=1.0,
        description="在一具骸骨旁边，你发现了一本写满笔记的生存手册。",
        choices=[
            {"text": "📖 仔细研读", "result": {"exp": (50, 120), "items": {"survivor_journal": (1, 1)}, "description": "手册里记录了宝贵的生存经验和秘诀，你学到了很多。"}},
            {"text": "📸 快速浏览重点", "result": {"exp": (30, 60), "description": "你记住了一些关键要点，虽然不全面但也很实用。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="wounded_stranger", name="受伤陌生人",
        event_type=EventType.OPPORTUNITY, weight=1.0,
        description="一个受伤的陌生人躺在路边，看到你后虚弱地招手求救。",
        choices=[
            {"text": "💊 施以援手", "result": {"heal": 20, "exp": (40, 80), "description": "你帮助了陌生人处理伤口，他感激地教了你一些急救技巧。"}},
            {"text": "🔍 先搜身再救", "result": {"items": {"bandage": (1, 3), "first_aid_kit": (0, 1)}, "description": "你从他身上找到了医疗用品...然后还是决定帮他包扎。"}},
            {"text": "🚶 冷漠离开", "result": {"description": "在末日里多管闲事可能是致命的，你选择继续前进。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="abandoned_lab", name="废弃实验室",
        event_type=EventType.OPPORTUNITY, weight=0.5,
        description="你发现了一个藏在废墟下的秘密实验室，门口的密码锁还在亮着。",
        choices=[
            {"text": "🔬 破解进入", "result": {"items": {"stimpack": (1, 3), "antidote": (1, 2), "electronics": (3, 8)}, "resources": {"medicine": (5, 15)}, "exp": (60, 150), "description": "实验室里存放着大量未使用的高级药品和实验设备！"}},
            {"text": "⚠️ 太危险了，在外面标记", "result": {"description": "你不知道实验室里有什么，先标记下来等准备好了再来看。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="weapon_cache", name="武器藏匿点",
        event_type=EventType.OPPORTUNITY, weight=0.8,
        description="一面松动的墙砖后面，隐约可以看到武器的轮廓。",
        choices=[
            {"text": "🔫 取出武器", "result": {"items": {"hunting_rifle": (0, 1), "crossbow": (0, 1), "baseball_bat": (0, 1)}, "resources": {"ammo": (5, 15)}, "description": "这是某个幸存者藏起来的武器库！你毫不客气地笑纳了。"}},
            {"text": "📦 只拿弹药", "result": {"resources": {"ammo": (3, 10), "iron": (1, 3)}, "items": {"gunpowder": (1, 3)}, "description": "你只拿了弹药和材料，留了一部分给可能需要的人。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="greenhouse", name="完好的温室",
        event_type=EventType.OPPORTUNITY, weight=1.0,
        description="一座奇迹般完好的温室大棚，里面的植物还在生长！",
        choices=[
            {"text": "🌿 采摘蔬菜和草药", "result": {"resources": {"food": (8, 20), "medicine": (2, 5)}, "items": {"herb": (3, 8)}, "description": "温室里的蔬菜和草药长势喜人，你大丰收了！"}},
            {"text": "🌱 收集种子", "result": {"resources": {"food": (3, 8)}, "exp": (30, 50), "description": "你收集了各种种子，还学习了一些温室种植知识。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="backup_generator", name="还能用的发电机",
        event_type=EventType.OPPORTUNITY, weight=0.8,
        description="地下室角落里有台柴油发电机，检查后发现居然还能用！",
        choices=[
            {"text": "⚡ 启动发电机", "result": {"items": {"electronics": (2, 5), "scrap_metal": (2, 4)}, "resources": {"fuel": (3, 8)}, "exp": (30, 50), "description": "发电机启动了！你利用它给设备充电，还找到了一些配件。"}},
            {"text": "🔧 拆解零件", "result": {"items": {"scrap_metal": (3, 8), "electronics": (1, 3), "plastic": (2, 4)}, "resources": {"iron": (2, 5)}, "description": "你决定把发电机拆了，零件比整机更有用。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="med_station", name="野战医疗站",
        event_type=EventType.OPPORTUNITY, weight=0.8,
        description="一个被匆忙遗弃的军用医疗站，帐篷里还有不少医疗物资。",
        choices=[
            {"text": "💊 搜刮医疗物资", "result": {"resources": {"medicine": (5, 15)}, "items": {"bandage": (2, 5), "first_aid_kit": (1, 3), "antidote": (0, 1)}, "description": "医疗站物资充足，你的药箱一下子满了。"}},
            {"text": "🩺 给自己检查身体", "result": {"heal": 50, "description": "你用医疗站的设备给自己做了全面检查和治疗，感觉好多了。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="solar_panels", name="太阳能板",
        event_type=EventType.OPPORTUNITY, weight=1.0,
        description="一栋建筑的屋顶上装了几块太阳能板，虽然积了灰但应该还能工作。",
        choices=[
            {"text": "🔧 拆下来带走", "result": {"items": {"electronics": (3, 8), "scrap_metal": (1, 3), "glass": (2, 5)}, "exp": (20, 40), "description": "你小心翼翼地拆下了太阳能板和配套的电子设备。"}},
            {"text": "🔋 当场给设备充电", "result": {"exp": (30, 60), "items": {"electronics": (1, 2)}, "description": "你利用太阳能给设备充电，还检查出了一些还能用的电子元件。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="vault_door", name="金库大门",
        event_type=EventType.OPPORTUNITY, weight=0.5,
        description="你在一座银行的废墟下发现了一个完好的金库大门，里面可能藏着贵重物资。",
        choices=[
            {"text": "🔓 尝试打开", "result": {"escape_chance": 0.4, "description_escape": "你居然打开了金库！里面不仅有现金（虽然没用），还有应急物资。", "description_fail": "金库的安保系统还在运作，你被电击了！", "fail_damage": (10, 25)}},
            {"text": "💣 爆破开门", "result": {"items": {"scrap_metal": (2, 5)}, "resources": {"iron": (3, 8), "ammo": (1, 3)}, "description": "爆破成功了！金库里果然藏着应急物资。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="food_truck", name="餐车残骸",
        event_type=EventType.OPPORTUNITY, weight=1.0,
        description="一辆翻倒的餐车躺在路边，看起来在末日之前是一家火爆的路边摊。",
        choices=[
            {"text": "🍔 翻找冰柜", "result": {"resources": {"food": (5, 15)}, "items": {"canned_food": (2, 4), "bottled_water": (1, 3)}, "description": "冰柜虽然断电很久了，但里面有不少罐装食品和冷冻原料。"}},
            {"text": "🔧 拆厨房设备", "result": {"items": {"scrap_metal": (2, 4), "electronics": (0, 1)}, "resources": {"fuel": (1, 3)}, "description": "厨房设备里能拆出不少有用的零件。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="training_ground", name="训练场地",
        event_type=EventType.OPPORTUNITY, weight=0.8,
        description="你发现了一个军队废弃的障碍训练场，各种训练设施还完好。",
        choices=[
            {"text": "💪 体能训练", "result": {"exp": (60, 120), "health_damage": (3, 8), "description": "你在训练场上大汗淋漓，体能有了明显提升。"}},
            {"text": "🎯 射击训练", "result": {"exp": (80, 150), "lose_resources": {"ammo": 0.1}, "description": "你用训练场的靶子练习枪法，消耗了一些弹药但枪法精进了。"}},
            {"text": "🧗 障碍跑", "result": {"exp": (50, 100), "description": "你在障碍赛道上奔跑跳跃，感觉身手敏捷了不少。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="secret_tunnel", name="秘密通道",
        event_type=EventType.OPPORTUNITY, weight=0.5,
        description="一栋建筑的地下室里藏着一条秘密通道，不知通向何方。",
        choices=[
            {"text": "🔦 探索通道", "result": {"items": {"flashlight": (0, 1), "survivor_journal": (0, 1)}, "resources": {"food": (3, 8), "medicine": (2, 5)}, "exp": (40, 80), "description": "通道连接着一个秘密仓库，里面堆满了物资！"}},
            {"text": "🚧 先加固再探索", "result": {"exp": (30, 60), "description": "通道不太稳固，你先加固了支撑结构，虽然花了些时间但安全多了。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="time_capsule", name="时间胶囊",
        event_type=EventType.OPPORTUNITY, weight=0.5,
        description="你在挖地时碰到了一个金属箱子，上面刻着「末日准备者协会——2024」。",
        choices=[
            {"text": "🎁 打开时间胶囊", "result": {"items": {"first_aid_kit": (1, 2), "canned_food": (3, 5), "survivor_journal": (1, 1)}, "resources": {"food": (5, 10), "water": (5, 10), "medicine": (3, 8)}, "exp": (50, 100), "description": "这是末日准备者留下的宝藏！各种生存物资一应俱全。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="radio_tower_opp", name="废弃信号塔",
        event_type=EventType.OPPORTUNITY, weight=0.8,
        description="一座锈迹斑斑的无线电信号塔矗立在山顶，虽然废弃已久但设备还在。",
        choices=[
            {"text": "📡 尝试启动设备", "result": {"escape_chance": 0.5, "description_escape": "设备启动了！你收到了来自远方的幸存者广播。", "description_fail": "设备短路了..."}},
            {"text": "🔧 拆电子元件", "result": {"items": {"electronics": (5, 12), "scrap_metal": (3, 6)}, "description": "信号塔的设备虽然老旧，但里面有不少高端电子元件。"}},
        ]
    ))

    # ================================================================
    # 补充事件 —— 天气类 (8个)
    # ================================================================

    EventRegistry.register(GameEvent(
        id="sandstorm_hit", name="沙尘暴袭击",
        event_type=EventType.WEATHER, weight=1.5,
        description="一阵猛烈的沙尘暴席卷而来，能见度几乎为零。",
        weather_only=["sandstorm"],
        choices=[
            {"text": "🧣 遮住口鼻蹲下", "result": {"health_damage": (3, 8), "description": "你用布遮住口鼻蹲在原地，等沙尘暴减弱后继续前进。"}},
            {"text": "🏜️ 寻找岩壁躲避", "result": {"description": "你找到了一处岩壁背面，成功躲过了最猛烈的沙尘。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="thunderstorm_fear", name="雷暴恐惧",
        event_type=EventType.WEATHER, weight=1.0,
        description="天空电闪雷鸣，暴雨倾盆而下，震耳的雷声让附近的丧尸都焦躁不安。",
        weather_only=["storm"],
        choices=[
            {"text": "🏠 找制高点避雷", "result": {"exp": (20, 40), "description": "你找到了一处安全的避雷所，观察雷暴中丧尸的活动规律。"}},
            {"text": "🏃 趁着雷声掩护行动", "result": {"resources": {"food": (1, 3)}, "description": "雷声掩盖了你的脚步声，你趁机穿过了一片平时危险的区域。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="hail_damage", name="冰雹灾害",
        event_type=EventType.WEATHER, weight=1.0,
        description="核桃大小的冰雹从天而降，砸得屋顶噼啪作响。",
        choices=[
            {"text": "🛡️ 躲进坚固建筑", "result": {"description": "你迅速躲进了旁边的混凝土建筑，安全通过了。"}},
            {"text": "🧥 护住头部跑", "result": {"health_damage": (5, 12), "description": "你抱着头跑回了营地，头上被砸了几个包。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="clear_skies_boost", name="晴空万里",
        event_type=EventType.WEATHER, weight=1.5,
        description="今天是难得的晴朗好天气，阳光明媚，空气清新。",
        weather_only=["clear"],
        auto_result={
            "exp": (20, 50),
            "description": "好天气让人心情愉悦，你在阳光下感觉精力充沛。今天的探索应该会很顺利！"
        }
    ))

    EventRegistry.register(GameEvent(
        id="radiation_fog", name="辐射雾",
        event_type=EventType.WEATHER, weight=0.8,
        description="一层绿色的薄雾笼罩了区域，盖革计数器滴滴作响——这是辐射雾！",
        weather_only=["fog"],
        choices=[
            {"text": "☢️ 穿防护装备通过", "result": {"health_damage": (3, 10), "description": "你用能找到的材料做了简易防护，虽然还是受到了一些辐射。"}},
            {"text": "🔄 绕开雾区", "result": {"description": "辐射可不是开玩笑的，你花了更多时间绕道而行。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="dust_devil", name="尘卷风",
        event_type=EventType.WEATHER, weight=0.8,
        description="一个小小的尘卷风在不远处旋转，卷起了沙尘和碎片。",
        choices=[
            {"text": "🔍 观察风向避开", "result": {"exp": (10, 25), "description": "你判断了风向，轻松避开了尘卷风。"}},
            {"text": "🌀 穿过去看看", "result": {"health_damage": (3, 8), "description": "尘卷风不大，你穿过去后发现了一些被卷到空中的物资碎片。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="moonless_night", name="月黑风高",
        event_type=EventType.WEATHER, weight=1.0,
        description="今夜没有月亮，四周伸手不见五指，但这样的夜晚适合秘密行动。",
        auto_result={
            "description": "黑暗是你的保护色。今晚潜行成功率大幅提升，但同时更容易遭遇夜行丧尸。"
        }
    ))

    EventRegistry.register(GameEvent(
        id="sun_shower", name="太阳雨",
        event_type=EventType.WEATHER, weight=0.8,
        description="太阳还高挂在天上，却下起了淅淅沥沥的小雨——罕见的太阳雨。",
        auto_result={
            "resources": {"water": (3, 10)},
            "description": "太阳雨中你收集了不少干净的雨水。老人们说太阳雨是吉兆，希望你今天好运。"
        }
    ))

    # ================================================================
    # 补充事件 —— 社交类 (10个)
    # ================================================================

    EventRegistry.register(GameEvent(
        id="lost_child", name="走失的孩童",
        event_type=EventType.SOCIAL, weight=0.8,
        description="一个看上去不到十岁的小孩独自在街上游荡，眼神空洞。",
        choices=[
            {"text": "🍞 给他一些食物", "result": {"heal": 10, "exp": (30, 60), "lose_resources": {"food": 0.1}, "description": "小孩默默接过食物，塞给你一张纸条后跑走了。纸条上写着附近的掠夺者据点位置。"}},
            {"text": "🤝 询问他的情况", "result": {"exp": (20, 50), "description": "小孩带你去见了他的家人们——一群感激的幸存者，他们教了你一些生存技巧。"}},
            {"text": "🚶 保持距离", "result": {"description": "在末日里，独自出现的小孩可能是个陷阱。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="rival_group", name="竞争团队",
        event_type=EventType.SOCIAL, weight=0.8,
        description="你撞上了另一个幸存者团队，他们看起来不好惹，但对你的物资很感兴趣。",
        choices=[
            {"text": "🤝 提议合作搜索", "result": {"resources": {"food": (3, 10), "wood": (3, 8)}, "exp": (20, 50), "description": "你们临时组队搜索了一片区域，各自分到了一半的收获。"}},
            {"text": "💬 交换情报", "result": {"exp": (40, 80), "description": "你和他们交换了各自发现的地点和危险区域信息，双方都受益。"}},
            {"text": "⚔️ 展示武力威吓", "result": {"exp": (20, 40), "description": "你展示了自己的装备，对方决定不找麻烦，各自离开了。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="trade_caravan", name="贸易商队",
        event_type=EventType.SOCIAL, weight=1.0,
        description="一支武装精良的贸易商队路过，他们用骡子驮着各种物资。",
        choices=[
            {"text": "💱 拿出物资交易", "result": {"trade": True, "description": "商队的货物种类很多，从武器到药品一应俱全。"}},
            {"text": "📰 打听远方消息", "result": {"exp": (30, 60), "description": "商队从南方来，分享了远方定居点的消息和可能的路况。"}},
            {"text": "🤝 申请加入商队一段路", "result": {"exp": (40, 80), "description": "商队同意你跟随一段路，路上你学到了很多商队的生存之道。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="radio_message", name="无线电广播",
        event_type=EventType.SOCIAL, weight=1.0,
        description="你的收音机突然收到了一个清晰的信号！有人在广播。",
        choices=[
            {"text": "📻 仔细收听", "result": {"exp": (40, 80), "items": {"radio": (0, 1)}, "description": "广播是一个幸存者聚居区发布的，包含了物资交换信息和近期天气预警。"}},
            {"text": "📞 尝试回应", "result": {"exp": (20, 50), "description": "你试着回应了广播，虽然对方没收到，但你修好了收音机的发射功能。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="hermit_shack", name="隐士小屋",
        event_type=EventType.SOCIAL, weight=0.8,
        description="深山里有一座小屋，门口坐着一位白发苍苍的老人。他看起来在这里住了很久了。",
        choices=[
            {"text": "🍵 陪老人喝茶聊天", "result": {"exp": (60, 120), "heal": 30, "description": "老人讲了许多末日初期发生的事，还给你泡了一杯药茶。"}},
            {"text": "🏹 向老人请教狩猎", "result": {"exp": (50, 100), "items": {"leather": (1, 3)}, "description": "老人是个老猎人，教了你几手追踪和狩猎的绝活。"}},
            {"text": "🛒 用物资换取草药", "result": {"resources": {"medicine": (3, 10)}, "items": {"herb": (3, 6)}, "lose_resources": {"food": 0.2}, "description": "老人用自己种的草药和你交换了一些食物。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="escaped_prisoner", name="逃犯",
        event_type=EventType.SOCIAL, weight=0.8,
        description="一个面目不善的人从废墟中走出来，手腕上还戴着掰断的手铐。",
        choices=[
            {"text": "⚠️ 保持警惕，观察他", "result": {"exp": (20, 40), "description": "你保持距离观察，他似乎没有恶意——至少现在没有。"}},
            {"text": "🤝 给他一些物资", "result": {"exp": (30, 50), "lose_resources": {"food": 0.1}, "description": "你分了一些食物给他，他感激地告诉你附近一个隐藏的安全屋位置。"}},
            {"text": "🚶 远离他", "result": {"description": "你决定不招惹潜在的危险分子。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="wandering_musician", name="流浪乐手",
        event_type=EventType.SOCIAL, weight=0.8,
        description="废墟中传来了吉他声，一个流浪乐手正坐在废弃的公交站下弹奏。",
        choices=[
            {"text": "🎵 坐下来听一会", "result": {"exp": (30, 60), "description": "音乐在末日中是稀缺的奢侈品。你听了一曲，精神得到了极大的放松。"}},
            {"text": "🎸 一起合奏", "result": {"exp": (40, 80), "description": "你捡起旁边的破旧口琴和他合奏了一曲，乐手开心地分享了他的旅行见闻。"}},
            {"text": "🍞 用食物换一首歌", "result": {"exp": (20, 50), "lose_resources": {"food": 0.05}, "description": "乐手为你弹了一首末日前的流行曲，让你想起了从前。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="refugee_family", name="难民家庭",
        event_type=EventType.SOCIAL, weight=0.8,
        description="一个带着小孩的年轻夫妇正在路边休息，看起来又累又饿。",
        choices=[
            {"text": "🍞 分享食物", "result": {"exp": (40, 80), "heal": 20, "lose_resources": {"food": 0.15, "water": 0.1}, "description": "你的善举没有被遗忘。他们分享了宝贵的附近避难所情报。"}},
            {"text": "🗺️ 给他们指路", "result": {"exp": (20, 40), "description": "你给他们指明了安全的路线，他们满怀感激地出发了。"}},
            {"text": "🚶 资源紧张，无法帮助", "result": {"description": "你自己的物资也不多了，只能硬着心肠离开。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="bounty_hunter", name="赏金猎人",
        event_type=EventType.SOCIAL, weight=0.8,
        description="一个全副武装的赏金猎人拦住了你，拿出一张通缉令：「见过这个人吗？」",
        choices=[
            {"text": "📋 看看通缉令", "result": {"exp": (30, 60), "description": "你没见过这个人，但赏金猎人提醒了你附近有几个危险的掠夺者营地。"}},
            {"text": "🤝 提供情报交换", "result": {"exp": (50, 100), "resources": {"ammo": (2, 8)}, "description": "你分享了一些你知道的掠夺者活动情况，赏金猎人很满意，给了你一些弹药作为答谢。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="old_comrade", name="昔日战友",
        event_type=EventType.SOCIAL, weight=0.8,
        description="你竟然在废墟中遇到了末日前的同事！虽然不算朋友，但至少是个熟悉的面孔。",
        choices=[
            {"text": "🤝 合作探索一天", "result": {"resources": {"food": (3, 10), "water": (3, 8)}, "exp": (40, 80), "description": "老同事对这片区域很熟悉，带你去了一些还没搜过的地方。"}},
            {"text": "📱 交换联系方式", "result": {"exp": (30, 60), "items": {"radio": (0, 1)}, "description": "你们交换了无线电频率，约定定期互相通报安全情况。"}},
            {"text": "👋 简单叙旧后各走各路", "result": {"exp": (20, 40), "description": "聊了几句，但末日不需要太多感情。"}},
        ]
    ))

    # ================================================================
    # 补充事件 —— 事件链：信号塔 (3个)
    # ================================================================

    EventRegistry.register(GameEvent(
        id="signal_chain_1", name="楼顶的信号塔",
        event_type=EventType.CHAIN, weight=0.8,
        description="一栋高楼的屋顶上有一座大型信号塔，天线还在微微发光。如果能修好它，或许能联系到更远的地方。",
        chain_id="signal_tower", chain_order=1,
        choices=[
            {"text": "📡 上楼检查设备", "result": {"description": "你爬上楼梯检查了设备，发现需要更换几个关键零件才能修复。"}},
            {"text": "🚶 太危险，先标记", "result": {"description": "你在地图上标记了信号塔的位置，等准备好了再来。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="signal_chain_2", name="修复信号塔",
        event_type=EventType.CHAIN, weight=0.6,
        description="你带着零件回到了信号塔。更换损坏的电路板，重新连接线路...",
        chain_id="signal_tower", chain_order=2,
        choices=[
            {"text": "🔧 开始修理", "result": {"escape_chance": 0.6, "description_escape": "零件完美匹配！信号塔重新启动了！", "description_fail": "短路了！你需要更多的电子元件。", "fail_damage": (5, 15)}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="signal_chain_3", name="信号塔通讯",
        event_type=EventType.CHAIN, weight=0.4,
        description="信号塔恢复了运行！你收到了来自远方大型幸存者聚居地的通讯信号。",
        chain_id="signal_tower", chain_order=3,
        choices=[
            {"text": "🗣️ 和远方通话", "result": {"exp": (100, 200), "items": {"radio": (1, 1), "survivor_journal": (1, 2)}, "resources": {"food": (5, 15), "medicine": (3, 10)}, "description": "远方聚居地给你发送了一份附近物资点的坐标，还欢迎你加入他们的网络！"}},
        ]
    ))

    # ================================================================
    # 补充事件 —— 事件链：废弃研究所 (2个)
    # ================================================================

    EventRegistry.register(GameEvent(
        id="lab_chain_1", name="地下研究所",
        event_type=EventType.CHAIN, weight=0.6,
        description="一座被掩埋的建筑下方露出了不锈钢走廊——这是一座地下研究所！入口被锁住了。",
        chain_id="research_lab", chain_order=1,
        choices=[
            {"text": "🔓 寻找备用入口", "result": {"description": "你在通风管道找到了一个可以进入的入口，但里面可能不只有研究资料..."}},
            {"text": "💣 炸开大门", "result": {"health_damage": (5, 15), "description": "爆炸炸开了门，也触发了内部的安保系统。你硬着头皮走了进去。"}},
        ]
    ))

    EventRegistry.register(GameEvent(
        id="lab_chain_2", name="实验室核心",
        event_type=EventType.CHAIN, weight=0.4,
        description="研究所的核心实验室里，培养皿中漂浮着奇怪的生物样本。很明显这里在研究某种病毒。",
        chain_id="research_lab", chain_order=2,
        choices=[
            {"text": "⚔️ 清除实验室的变异体", "result": {"combat": {"enemy_attack": 28, "enemy_health": 80}, "rewards": {"exp": (150, 300), "items": {"stimpack": (2, 5), "antidote": (1, 3), "electronics": (3, 8)}, "resources": {"medicine": (10, 30)}}, "description_win": "你消灭了变异实验体，洗劫了研究所的药品库！", "description_lose": "变异体太强大了，你不得不撤退..."}},
            {"text": "💻 下载研究数据", "result": {"exp": (120, 250), "items": {"electronics": (2, 5)}, "description": "你成功下载了研究数据。这些关于病毒的知识可能对你在末日生存至关重要。"}},
        ]
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
    # 基础生存物品
    RecipeRegistry.register(
        "bottled_water", {"herb": 2, "plastic": 1},
        resource_costs={"water": 5},
        description="消耗水资源，用草药过滤、塑料瓶盛装，制作可饮用的瓶装水"
    )
    RecipeRegistry.register(
        "canned_food", {"scrap_metal": 2, "herb": 2, "cloth": 1},
        resource_costs={"food": 5},
        description="消耗食物资源，用金属片封装保存"
    )
    # 基础工具
    RecipeRegistry.register(
        "rusty_knife", {"scrap_metal": 3, "cloth": 1},
        description="打磨金属片，缠上布条做握柄，制作简易小刀"
    )
    RecipeRegistry.register(
        "rope", {"cloth": 3},
        description="将布料撕成条，编织成绳索"
    )
    RecipeRegistry.register(
        "military_vest", {"iron": 5, "leather": 5, "cloth": 3},
        description="用金属板和皮革制作军用防弹衣", required_building="workshop", min_level=3
    )
    RecipeRegistry.register(
        "mre", {"canned_food": 2, "cloth": 1, "plastic": 1},
        description="封装压缩食物，制作军用口粮", required_building="workshop", min_level=2
    )
    # 基础资源合成
    RecipeRegistry.register(
        "iron", {"scrap_metal": 5}, resource_costs={"fuel": 2},
        description="熔炼废金属提取铁", required_building="workshop", min_level=1
    )
    RecipeRegistry.register(
        "medicine", {"herb": 5},
        description="研磨草药制成基础药品"
    )
    RecipeRegistry.register(
        "ammo", {"scrap_metal": 2, "gunpowder": 2},
        description="制作简易弹药", required_building="workshop", min_level=2
    )
    RecipeRegistry.register(
        "fuel", {"wood": 5},
        description="加工木材制成燃料块"
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
        reward_items={"hunting_rifle": 1},
        reward_resources={"ammo": 10},
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
        reward_items={"crossbow": 1},
        reward_resources={"ammo": 20},
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
