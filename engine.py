"""
末日生存游戏 - 核心游戏引擎

负责处理游戏逻辑：玩家行动、事件触发、战斗结算、建筑产出等。
所有逻辑通过 Engine 类集中管理，便于测试和扩展。
"""

import random
import time
from typing import Dict, List, Optional, Tuple, Any

from models import (
    PlayerState, GroupGameState, Item, Building, GameEvent, Skill,
    ItemCategory, EventType, ResourceType, PlayerStatus,
    MerchantOffer, MerchantState
)
from content import (
    ItemRegistry, BuildingRegistry, EventRegistry,
    SkillRegistry, RecipeRegistry, AchievementRegistry, ClassRegistry
)
import llm_events


# 行动冷却时间（秒）
ACTION_COOLDOWN = 30  # 已废弃：探索不再有冷却，改为消耗饱食/口渴
EXPLORE_HUNGER_COST = 5    # 每次探索消耗饱食度
EXPLORE_THIRST_COST = 8    # 每次探索消耗口渴度
# 每日结算间隔（秒），实际使用时建议设长一些，这里为了测试设短一点
DAY_DURATION = 3600  # 1小时 = 1游戏天


class SurvivorEngine:
    """
    末日生存游戏引擎

    核心职责：
    1. 管理玩家数据和群组游戏状态
    2. 处理玩家行动（探索、建造、合成、使用物品等）
    3. 每日结算（资源消耗、建筑产出、随机事件）
    4. 战斗系统
    """

    def __init__(self):
        """初始化引擎"""
        # 玩家数据存储: {group_id: {user_id: PlayerState}}
        self._players: Dict[str, Dict[str, PlayerState]] = {}
        # 群组状态存储: {group_id: GroupGameState}
        self._groups: Dict[str, GroupGameState] = {}
        # 玩家当前待处理的事件: {group_id: {user_id: GameEvent}}
        self._pending_events: Dict[str, Dict[str, GameEvent]] = {}
        # 玩家事件选择等待: {group_id: {user_id: {"event": GameEvent, "choices": [...]}}}
        self._pending_choices: Dict[str, Dict[str, Dict]] = {}
        # 等待起名的玩家: {group_id: {user_id: True}}
        self._pending_names: Dict[str, Dict[str, bool]] = {}

        # LLM 事件开关及比例（0.0 ~ 1.0，默认 30% 概率使用大模型生成的事件）
        self.llm_event_ratio: float = 0.3
        self.llm_enabled: bool = True

        # 商人状态: {group_id: MerchantState}
        self._merchants: Dict[str, MerchantState] = {}

    # ================================================================
    # 内部工具方法
    # ================================================================

    def _get_pending_event(self, user_id: str, group_id: str) -> Optional[GameEvent]:
        return self._pending_events.get(group_id, {}).get(user_id)

    def _set_pending_event(self, user_id: str, group_id: str, event: GameEvent):
        if group_id not in self._pending_events:
            self._pending_events[group_id] = {}
        self._pending_events[group_id][user_id] = event

    def _del_pending_event(self, user_id: str, group_id: str):
        if group_id in self._pending_events:
            self._pending_events[group_id].pop(user_id, None)

    def _get_pending_choice(self, user_id: str, group_id: str) -> Optional[Dict]:
        return self._pending_choices.get(group_id, {}).get(user_id)

    def _set_pending_choice(self, user_id: str, group_id: str, data: Dict):
        if group_id not in self._pending_choices:
            self._pending_choices[group_id] = {}
        self._pending_choices[group_id][user_id] = data

    def _pop_pending_choice(self, user_id: str, group_id: str) -> Optional[Dict]:
        if group_id in self._pending_choices:
            return self._pending_choices[group_id].pop(user_id, None)
        return None

    def has_pending_choice(self, user_id: str, group_id: str) -> bool:
        """检查是否有待处理的选择"""
        return group_id in self._pending_choices and user_id in self._pending_choices[group_id]

    def has_pending_name(self, user_id: str, group_id: str) -> bool:
        """检查是否在等待起名"""
        return group_id in self._pending_names and user_id in self._pending_names[group_id]

    def set_pending_name(self, user_id: str, group_id: str):
        """标记玩家等待起名"""
        if group_id not in self._pending_names:
            self._pending_names[group_id] = {}
        self._pending_names[group_id][user_id] = True

    def clear_pending_name(self, user_id: str, group_id: str):
        """清除等待起名状态"""
        if group_id in self._pending_names:
            self._pending_names[group_id].pop(user_id, None)

    # ================================================================
    # 玩家管理
    # ================================================================

    def get_player(self, user_id: str, group_id: str) -> Optional[PlayerState]:
        """获取玩家状态"""
        return self._players.get(group_id, {}).get(user_id)

    def create_player(self, user_id: str, group_id: str, nickname: str = "",
                      player_class: str = None) -> PlayerState:
        """创建新玩家"""
        if group_id not in self._players:
            self._players[group_id] = {}
        if group_id not in self._groups:
            self._groups[group_id] = GroupGameState(group_id=group_id)

        player = PlayerState(
            user_id=user_id,
            group_id=group_id,
            nickname=nickname,
            created_at=time.time(),
            last_action_time=0.0,
            player_class=player_class,
        )

        # 应用职业加成
        if player_class:
            class_data = ClassRegistry.get(player_class)
            if class_data:
                bonuses = class_data.get("bonuses", {})
                if "attack_bonus" in bonuses:
                    player.attack += bonuses["attack_bonus"]
                # 初始物品
                for item_id, count in class_data.get("starting_items", {}).items():
                    player.add_item(item_id, count)
                # 初始资源加成
                for res, amount in class_data.get("starting_resources", {}).items():
                    player.add_resource(res, amount)
                # 商人物资加成
                if "start_boost" in bonuses:
                    for res in ["food", "water", "wood", "stone"]:
                        if res in player.resources:
                            new_val = int(player.resources[res] * (1 + bonuses["start_boost"]))
                            delta = new_val - player.resources[res]
                            if delta > 0:
                                player.add_resource(res, delta)

                # 医生免疫疾病
                if bonuses.get("immune_sick"):
                    player.status_effects["immune_sick"] = 1

        # PvP 初始保护（2小时 = 7200秒），所有新玩家都有
        player.pvp_shield_until = time.time() + 7200

        self._players[group_id][user_id] = player
        return player

    def get_group(self, group_id: str) -> Optional[GroupGameState]:
        """获取群组状态"""
        return self._groups.get(group_id)

    def ensure_group(self, group_id: str) -> GroupGameState:
        """确保群组存在"""
        if group_id not in self._groups:
            self._groups[group_id] = GroupGameState(group_id=group_id)
        return self._groups[group_id]

    # ================================================================
    # 行动系统
    # ================================================================

    def can_act(self, player: PlayerState) -> Tuple[bool, str]:
        """检查玩家是否可以行动（无冷却，但需足够饱食/口渴）"""
        if not player.is_alive():
            return False, "💀 你已经死亡，无法行动。请使用「重生」指令重新开始。"

        if player.hunger <= 0:
            return False, "🍖 饱食度过低，无法行动。请先进食补充体力。"
        if player.thirst <= 0:
            return False, "💧 口渴度过低，无法行动。请先饮水补充水分。"

        return True, ""

    def do_action(self, player: PlayerState, group: GroupGameState) -> Dict[str, Any]:
        """
        执行一次行动（探索）

        随机触发一个事件，返回事件信息和选项。
        每次探索消耗饱食度 {EXPLORE_HUNGER_COST} 和口渴度 {EXPLORE_THIRST_COST}。
        """
        # 消耗饱食度和口渴度
        player.hunger = max(0, player.hunger - EXPLORE_HUNGER_COST)
        player.thirst = max(0, player.thirst - EXPLORE_THIRST_COST)

        # 根据当前状态选择事件类型权重
        event = self._pick_event(player, group)
        if not event:
            player.last_action_time = time.time()
            player.total_actions += 1
            return {
                "type": "empty",
                "message": "🌫️ 你在荒野中搜索了一圈，什么也没有发现...\n🍖饱食 -{} | 💧口渴 -{}".format(EXPLORE_HUNGER_COST, EXPLORE_THIRST_COST)
            }

        # 存储待处理事件
        self._set_pending_event(player.user_id, player.group_id, event)

        result = {
            "type": "event",
            "event_id": event.id,
            "event_name": event.name,
            "event_type": event.event_type.value,
            "description": event.description,
            "choices": [],
            "auto": False,
        }

        # 如果有自动结算结果
        if event.auto_result:
            auto_msg = self._apply_auto_result(player, event.auto_result)
            result["auto"] = True
            result["auto_message"] = auto_msg
            # 清除待处理事件
            self._del_pending_event(player.user_id, player.group_id)
        else:
            # 构建选项列表
            for i, choice in enumerate(event.choices):
                result["choices"].append({
                    "index": i + 1,
                    "text": choice["text"],
                })
            # 存储选择等待
            self._set_pending_choice(player.user_id, player.group_id, {
                "event": event,
                "choices": event.choices,
            })

        # 更新玩家状态
        player.last_action_time = time.time()
        player.total_actions += 1
        player.stats["events_triggered"] += 1
        player.days_survived = group.current_day

        return result

    def handle_choice(self, player: PlayerState, choice_index: int) -> Dict[str, Any]:
        """处理玩家的事件选择"""
        user_id = player.user_id
        group_id = player.group_id

        pending = self._pop_pending_choice(user_id, group_id)
        if pending is None:
            return {"type": "error", "message": "⚠️ 你当前没有待处理的事件。"}

        event = pending["event"]
        choices = pending["choices"]

        if choice_index < 1 or choice_index > len(choices):
            # 恢复待处理状态
            self._set_pending_choice(user_id, group_id, pending)
            return {"type": "error", "message": f"⚠️ 请输入有效选项 (1-{len(choices)})。"}

        choice = choices[choice_index - 1]
        result = choice["result"]

        messages = []
        resources_gained = {}
        items_gained = {}
        damage_taken = 0
        exp_gained = 0

        # 处理战斗
        if "combat" in result:
            combat_result = self._resolve_combat(player, result["combat"])
            if combat_result["win"]:
                messages.append(result.get("description_win", combat_result["message"]))
                # 战利品
                if "rewards" in result:
                    rewards = result["rewards"]
                    if "exp" in rewards:
                        e = self._roll_range(rewards["exp"])
                        player.exp += e
                        exp_gained += e
                # 战斗胜利后的物品奖励（来自事件定义的 rewards.items）
                if "rewards" in result and "items" in result["rewards"]:
                    for item_id, (min_n, max_n) in result["rewards"]["items"].items():
                        count = random.randint(min_n, max_n)
                        if count > 0:
                            if self._is_resource_id(item_id):
                                player.add_resource(item_id, count)
                                resources_gained[item_id] = resources_gained.get(item_id, 0) + count
                            else:
                                player.add_item(item_id, count)
                                items_gained[item_id] = items_gained.get(item_id, 0) + count
                # 战斗胜利后的资源奖励（来自事件定义的 rewards.resources）
                if "rewards" in result and "resources" in result["rewards"]:
                    for res, (min_n, max_n) in result["rewards"]["resources"].items():
                        amount = random.randint(min_n, max_n)
                        if amount > 0:
                            player.add_resource(res, amount)
                            resources_gained[res] = resources_gained.get(res, 0) + amount
            else:
                messages.append(result.get("description_lose", combat_result["message"]))
                # combat_result 中已经扣过血了，不再重复扣 lose_damage
                damage_taken += combat_result.get("damage", 0)
                if "lose_resources" in result:
                    for res, ratio in result["lose_resources"].items():
                        lost = int(player.resources.get(res, 0) * ratio)
                        player.consume_resource(res, lost)

        # 处理逃跑/潜行
        if "escape_chance" in result:
            if random.random() < result["escape_chance"]:
                messages.append(result.get("description_escape", "你成功逃脱了。"))
            else:
                damage = self._roll_range(result.get("fail_damage", (5, 15)))
                player.health = max(0, player.health - damage)
                damage_taken += damage
                messages.append(result.get("description_fail", "逃跑失败！"))

        if "stealth_chance" in result:
            if random.random() < result["stealth_chance"]:
                messages.append(result.get("description_stealth", "你悄悄绕了过去。"))
            else:
                damage = self._roll_range(result.get("fail_damage", (5, 15)))
                player.health = max(0, player.health - damage)
                damage_taken += damage
                messages.append(result.get("description_fail", "被发现了！"))

        # 处理资源获得
        if "resources" in result:
            for res, (min_n, max_n) in result["resources"].items():
                amount = random.randint(min_n, max_n)
                if amount > 0:
                    # 应用搜索技能加成
                    scav_level = player.skills.get("scavenging", 0)
                    bonus = scav_level * 0.1
                    amount = int(amount * (1 + bonus))
                    player.add_resource(res, amount)
                    resources_gained[res] = resources_gained.get(res, 0) + amount

        # 处理物品获得
        if "items" in result:
            for item_id, (min_n, max_n) in result["items"].items():
                count = random.randint(min_n, max_n)
                if count > 0:
                    if self._is_resource_id(item_id):
                        player.add_resource(item_id, count)
                        resources_gained[item_id] = resources_gained.get(item_id, 0) + count
                    else:
                        player.add_item(item_id, count)
                        items_gained[item_id] = items_gained.get(item_id, 0) + count

        # 处理经验获得
        if "exp" in result:
            e = self._roll_range(result["exp"])
            player.exp += e
            exp_gained += e

        # 处理治疗
        if "heal" in result:
            heal = result["heal"]
            med_level = player.skills.get("medicine", 0)
            heal = int(heal * (1 + med_level * 0.1))
            player.health = min(player.max_health, player.health + heal)

        # 处理生命伤害
        if "health_damage" in result:
            dmg = self._roll_range(result["health_damage"])
            player.health = max(0, player.health - dmg)
            damage_taken += dmg

        # 处理资源损失
        if "lose_resources" in result:
            for res, ratio in result["lose_resources"].items():
                lost = int(player.resources.get(res, 0) * ratio)
                player.consume_resource(res, lost)

        # 添加描述消息
        if "description" in result:
            messages.append(result["description"])
        if result.get("trade", False):
            messages.append("你可以使用「交易」指令与幸存者交换物资。")
        if result.get("trade_special", False):
            messages.append("商人展示了特殊商品，使用「商人」指令查看。")

        # 检查死亡
        if player.health <= 0:
            player.status = "dead"
            player.stats["deaths"] += 1
            # 清理该玩家的所有待处理状态
            self._del_pending_event(user_id, group_id)
            self.clear_pending_name(user_id, group_id)

        # 更新事件链进度
        if event.chain_id and event.chain_order > 0:
            player.chain_progress[event.chain_id] = max(
                player.chain_progress.get(event.chain_id, 0),
                event.chain_order
            )

        # 检查升级
        level_up = self._check_level_up(player)

        # 检查成就
        group = self.ensure_group(group_id)
        new_achievements = self._check_achievements(player, group)

        # 清除事件选择状态（如果还没死亡的话也要清理）
        if player.is_alive():
            self._del_pending_event(user_id, group_id)

        return {
            "type": "result",
            "messages": messages,
            "resources_gained": resources_gained,
            "items_gained": items_gained,
            "damage_taken": damage_taken,
            "exp_gained": exp_gained,
            "level_up": level_up,
            "new_achievements": new_achievements,
        }

    # ================================================================
    # 建造系统
    # ================================================================

    def build_structure(self, player: PlayerState, building_id: str) -> Dict[str, Any]:
        """建造或升级建筑"""
        building_def = BuildingRegistry.get(building_id)
        if not building_def:
            return {"type": "error", "message": "⚠️ 未知的建筑类型。"}

        # 当前等级
        current_level = player.buildings.get(building_id, 0)
        if current_level >= building_def.max_level:
            return {"type": "error", "message": f"🏗️ {building_def.name}已达到最高等级！"}

        # 计算消耗
        temp_building = Building(
            id=building_def.id, name=building_def.name,
            building_type=building_def.building_type,
            level=current_level + 1, max_level=building_def.max_level,
            build_cost=building_def.build_cost,
            upgrade_cost_multiplier=building_def.upgrade_cost_multiplier,
        )

        # 首次建造用 build_cost，升级用 get_upgrade_cost
        if current_level == 0:
            cost = building_def.build_cost.copy()
        else:
            cost = temp_building.get_upgrade_cost()

        # 工程师职业：建造折扣
        if player.player_class == "engineer":
            class_data = ClassRegistry.get("engineer")
            if class_data and "build_discount" in class_data.get("bonuses", {}):
                discount = class_data["bonuses"]["build_discount"]
                cost = {k: max(1, int(v * (1 - discount))) for k, v in cost.items()}

        # 检查资源和物品消耗
        # 注意：wood/water/stone/iron/medicine/ammo/fuel 同时存在于 ItemRegistry(RESOURCE) 和资源池，
        # 消耗时应优先从玩家资源池扣除（而非背包）
        RESOURCE_KEYS = {"food", "water", "wood", "stone", "iron", "medicine", "ammo", "fuel"}
        res_names = {"food": "🍖食物", "water": "💧水", "wood": "🪵木材", "stone": "🪨石料",
                    "iron": "🔩铁", "medicine": "💊药品", "ammo": "🔫弹药", "fuel": "⛽燃料"}
        for cost_id, amount in cost.items():
            item = ItemRegistry.get(cost_id)
            is_resource = cost_id in RESOURCE_KEYS or (item and item.category == ItemCategory.RESOURCE)
            if is_resource:
                # 资源消耗，检查玩家资源池
                if player.get_resource(cost_id) < amount:
                    res_label = res_names.get(cost_id, cost_id)
                    return {
                        "type": "error",
                        "message": f"⚠️ 资源不足！需要 {amount} {res_label}，你只有 {player.get_resource(cost_id)}。"
                    }
            elif item:
                # 物品消耗，检查背包
                if not player.has_item(cost_id, amount):
                    return {
                        "type": "error",
                        "message": f"⚠️ 材料不足！需要 {item.name} x{amount}，背包中数量不足。"
                    }
            else:
                # 未知消耗项，尝试从资源池扣
                if player.get_resource(cost_id) < amount:
                    return {
                        "type": "error",
                        "message": f"⚠️ 资源不足！需要 {cost_id} x{amount}，你只有 {player.get_resource(cost_id)}。"
                    }

        # 消耗资源和物品
        for cost_id, amount in cost.items():
            item = ItemRegistry.get(cost_id)
            is_resource = cost_id in RESOURCE_KEYS or (item and item.category == ItemCategory.RESOURCE)
            if is_resource:
                player.consume_resource(cost_id, amount)
            elif item:
                player.remove_item(cost_id, amount)
            else:
                player.consume_resource(cost_id, amount)

        # 升级
        new_level = current_level + 1
        player.buildings[building_id] = new_level
        player.total_builds = getattr(player, "total_builds", 0) + 1

        return {
            "type": "success",
            "message": f"🏗️ {building_def.name} 已{'建造' if current_level == 0 else '升级到'} Lv.{new_level}！",
            "building_name": building_def.name,
            "new_level": new_level,
            "cost": cost,
        }

    # ================================================================
    # 避难所休息（挂机）
    # ================================================================

    def start_shelter_rest(self, player: PlayerState) -> Dict[str, Any]:
        """进入避难所休息"""
        shelter_level = player.buildings.get("shelter", 0)
        if shelter_level <= 0:
            return {"type": "error", "message": "⚠️ 你还没有建造避难所！先使用「建造 避难所」建造一个。"}

        if player.is_resting:
            return {"type": "error", "message": "😴 你已经在避难所中休息了！"}

        if not player.is_alive():
            return {"type": "error", "message": "💀 死者无法休息..."}

        player.is_resting = True
        heal_per_day = shelter_level * 10
        shelter_bld = BuildingRegistry.get("shelter")
        shelter_name = shelter_bld.name if shelter_bld else "避难所"
        return {
            "type": "success",
            "message": (
                f"😴 你进入了 {shelter_name} Lv.{shelter_level} 中休息。\n"
                f"💤 期间饱食度和口渴度消耗极低\n"
                f"💚 每日自动恢复 {heal_per_day} 点生命值\n"
                f"🧠 理智值自然恢复加快\n"
                f"⏳ 自动搜集正常进行\n\n"
                f"使用「离开避难所」退出休息。"
            ),
        }

    def end_shelter_rest(self, player: PlayerState) -> Dict[str, Any]:
        """离开避难所"""
        if not player.is_resting:
            return {"type": "error", "message": "⚠️ 你并没有在避难所中休息。"}

        player.is_resting = False
        return {
            "type": "success",
            "message": "🚶 你离开了避难所，重新回到废土世界。",
        }

    # ================================================================
    # 合成系统
    # ================================================================

    def craft_item(self, player: PlayerState, item_id: str, count: int = 1) -> Dict[str, Any]:
        """合成物品"""
        recipe = RecipeRegistry.get(item_id)
        if not recipe:
            return {"type": "error", "message": "⚠️ 该物品无法合成。"}

        item_def = ItemRegistry.get(item_id)

        # 检查建筑需求
        if recipe.get("required_building"):
            bld_id = recipe["required_building"]
            bld_level = player.buildings.get(bld_id, 0)
            if bld_level < recipe.get("min_level", 1):
                bld_def = BuildingRegistry.get(bld_id)
                return {
                    "type": "error",
                    "message": f"⚠️ 需要 {bld_def.name} Lv.{recipe['min_level']} 才能合成此物品。"
                }

        # 工程师职业：合成折扣
        craft_discount = 0.0
        if player.player_class == "engineer":
            class_data = ClassRegistry.get("engineer")
            if class_data and "craft_discount" in class_data.get("bonuses", {}):
                craft_discount = class_data["bonuses"]["craft_discount"]

        # 工坊建筑：合成折扣（与职业折扣叠加）
        workshop_level = player.buildings.get("workshop", 0)
        if workshop_level > 0:
            ws_bld = BuildingRegistry.get("workshop")
            if ws_bld:
                ws_discount = workshop_level * ws_bld.effect_per_level.get("craft_discount", 0)
                craft_discount = min(0.6, craft_discount + ws_discount)

        # 复制材料（应用折扣）
        materials = {
            k: max(1, int(v * (1 - craft_discount)))
            for k, v in recipe["materials"].items()
        }

        # 复制资源消耗（应用折扣）
        resource_costs = {
            k: max(1, int(v * (1 - craft_discount)))
            for k, v in recipe.get("resource_costs", {}).items()
        }

        # 检查资源消耗
        for res_key, res_amount in resource_costs.items():
            needed = res_amount * count
            current = player.resources.get(res_key, 0)
            if current < needed:
                res_names = {
                    "food": "食物", "water": "水", "wood": "木材",
                    "stone": "石料", "iron": "铁", "medicine": "药品",
                    "ammo": "弹药", "fuel": "燃料",
                }
                res_name = res_names.get(res_key, res_key)
                return {
                    "type": "error",
                    "message": f"⚠️ 资源不足！需要 {res_name}x{needed}，当前仅有 {current}。"
                }

        # 检查材料（先查背包，再查基础资源，最后算组合）
        for mat_id, mat_amount in materials.items():
            needed = mat_amount * count
            inv_count = player.inventory.get(mat_id, 0)
            res_count = player.resources.get(mat_id, 0)
            total = inv_count + res_count
            if total < needed:
                mat_def = ItemRegistry.get(mat_id)
                mat_name = mat_def.name if mat_def else mat_id
                return {
                    "type": "error",
                    "message": f"⚠️ 材料不足！需要 {needed} 个{mat_name}，你只有 {total} 个。"
                }

        # 消耗资源（resource_costs 从玩家资源池扣除）
        for res_key, res_amount in resource_costs.items():
            player.consume_resource(res_key, res_amount * count)

        # 消耗材料（优先扣背包物品，不够再从资源池扣）
        for mat_id, mat_amount in materials.items():
            needed = mat_amount * count
            inv_have = player.inventory.get(mat_id, 0)
            if inv_have >= needed:
                player.remove_item(mat_id, needed)
            else:
                # 先把背包里的扣完，剩下的从资源池扣
                if inv_have > 0:
                    player.remove_item(mat_id, inv_have)
                player.consume_resource(mat_id, needed - inv_have)

        # 获得成品：资源类产出写入资源池，普通物品写入背包
        if item_def and getattr(item_def, "category", None) and item_def.category.value == "resource":
            player.add_resource(item_id, count)
        else:
            player.add_item(item_id, count)
        player.stats["items_crafted"] += count

        item_name = item_def.name if item_def else item_id
        discount_note = "（工程师折扣已应用）" if craft_discount > 0 else ""
        return {
            "type": "success",
            "message": f"🔨 成功制作了 {count} 个 {item_name}！{discount_note}",
            "item_name": item_name,
            "count": count,
        }

    # ================================================================
    # 物品使用
    # ================================================================

    def use_item(self, player: PlayerState, item_id: str) -> Dict[str, Any]:
        """使用物品"""
        if not player.has_item(item_id):
            return {"type": "error", "message": "⚠️ 你没有这个物品。"}

        item_def = ItemRegistry.get(item_id)
        if not item_def:
            return {"type": "error", "message": "⚠️ 未知物品。"}

        messages = []

        # 消耗品
        if item_def.category == ItemCategory.CONSUMABLE:
            player.remove_item(item_id)

            if item_def.heal_amount > 0:
                med_level = player.skills.get("medicine", 0)
                heal = int(item_def.heal_amount * (1 + med_level * 0.1))
                actual_heal = min(player.max_health - player.health, heal)
                player.health = min(player.max_health, player.health + heal)
                messages.append(f"💚 恢复了 {actual_heal} 点生命值。")

            if item_def.hunger_restore > 0:
                player.hunger = min(100, player.hunger + item_def.hunger_restore)
                messages.append(f"🍖 恢复了 {item_def.hunger_restore} 点饱食度。")

            if item_def.thirst_restore > 0:
                player.thirst = min(100, player.thirst + item_def.thirst_restore)
                messages.append(f"💧 恢复了 {item_def.thirst_restore} 点口渴度。")

            return {
                "type": "success",
                "message": f"使用了 {item_def.name}。\n" + "\n".join(messages),
            }

        # 装备武器
        elif item_def.category == ItemCategory.WEAPON:
            # 卸下旧武器
            if player.equipped_weapon:
                old = ItemRegistry.get(player.equipped_weapon)
                if old:
                    player.attack = max(0, player.attack - old.attack_bonus)
                    player.add_item(player.equipped_weapon)

            player.remove_item(item_id)
            player.equipped_weapon = item_id
            player.attack += item_def.attack_bonus
            return {
                "type": "success",
                "message": f"⚔️ 装备了 {item_def.name}，攻击力 +{item_def.attack_bonus}！"
            }

        # 装备防具
        elif item_def.category == ItemCategory.ARMOR:
            if player.equipped_armor:
                old = ItemRegistry.get(player.equipped_armor)
                if old:
                    player.defense = max(0, player.defense - old.defense_bonus)
                    player.add_item(player.equipped_armor)

            player.remove_item(item_id)
            player.equipped_armor = item_id
            player.defense += item_def.defense_bonus
            return {
                "type": "success",
                "message": f"🛡️ 装备了 {item_def.name}，防御力 +{item_def.defense_bonus}！"
            }

        # 特殊物品
        elif item_def.category == ItemCategory.SPECIAL:
            player.remove_item(item_id)
            if item_id == "survivor_journal":
                exp = random.randint(50, 150)
                player.exp += exp
                messages.append(f"📖 你阅读了幸存者日记，获得了 {exp} 点经验。")
            elif item_id == "radio":
                messages.append("📻 无线电中传来断断续续的声音...似乎有其他幸存者在附近。")
                player.add_resource("food", random.randint(3, 10))
            elif item_id == "molotov":
                exp = random.randint(100, 200)
                player.exp += exp
                scrap = random.randint(3, 6)
                iron_gain = random.randint(2, 5)
                player.add_item("scrap_metal", scrap)
                player.add_resource("iron", iron_gain)
                messages.append(f"🔥 你投掷了燃烧瓶！烈焰吞噬了敌人。获得 {exp} 经验、{scrap} 废金属、{iron_gain} 铁。")
            elif item_id == "night_gear":
                exp = random.randint(80, 200)
                player.exp += exp
                food_gain = random.randint(5, 20)
                water_gain = random.randint(5, 15)
                player.add_resource("food", food_gain)
                player.add_resource("water", water_gain)
                messages.append(f"🌙 夜行装备让你在夜间如鱼得水！获得 {exp} 经验、{food_gain} 食物、{water_gain} 水。")
            elif item_id == "firestarter":
                food_gain = random.randint(8, 20)
                heal = 20
                player.add_resource("food", food_gain)
                player.health = min(player.max_health, player.health + heal)
                messages.append(f"🔥 你生起篝火烹饪食物、取暖休息。获得 {food_gain} 食物，恢复了 {heal} 生命值。")
            elif item_id == "trap_kit":
                food_gain = random.randint(10, 25)
                leather_gain = random.randint(2, 5)
                player.add_resource("food", food_gain)
                player.add_item("leather", leather_gain)
                messages.append(f"🪤 陷阱成功捕获了猎物！获得 {food_gain} 食物、{leather_gain} 皮革。")

            return {
                "type": "success",
                "message": f"使用了 {item_def.name}。\n" + "\n".join(messages),
            }

        return {"type": "error", "message": "⚠️ 该物品无法直接使用。"}

    # ================================================================
    # 每日结算
    # ================================================================

    def daily_tick(self, group_id: str) -> Dict[str, Any]:
        """
        每日结算：对所有群成员的资源消耗、建筑产出、随机事件进行处理
        """
        group = self.ensure_group(group_id)
        group.advance_day()

        players = self._players.get(group_id, {})
        if not players:
            return {
                "day": group.current_day,
                "season": group.current_season,
                "danger_level": group.danger_level,
                "announcements": [],
                "player_count": 0,
            }

        announcements = []

        for user_id, player in list(players.items()):
            if not player.is_alive():
                continue

            # 1. 自然消耗（避难所休息中消耗极低）
            if player.is_resting:
                player.apply_rest_decay()
            else:
                player.apply_daily_decay()

            # 2. 建筑产出
            self._apply_building_production(player)

            # 3. 建筑被动增益（防御、血量等）
            self._apply_building_buffs(player)

            # 4. 技能被动效果
            surv_level = player.skills.get("survival", 0)
            if surv_level > 0:
                hunger_save = int(15 * surv_level * 0.05)
                thirst_save = int(20 * surv_level * 0.05)
                player.hunger = min(100, player.hunger + hunger_save)
                player.thirst = min(100, player.thirst + thirst_save)

            # 5. 医疗站自动治疗
            hospital_level = player.buildings.get("hospital", 0)
            if hospital_level > 0 and player.health < player.max_health:
                heal = hospital_level * 10
                player.health = min(player.max_health, player.health + heal)

            # 5b. 避难所休息自动回血
            if player.is_resting and player.health < player.max_health:
                shelter_level = player.buildings.get("shelter", 0)
                if shelter_level > 0:
                    shelter_heal = shelter_level * 10
                    player.health = min(player.max_health, player.health + shelter_heal)

            # 6. 全自动搜集——直接入账
            self._auto_gather(player)
            player.days_survived += 1

        # 7. 商人补货
        self.check_and_refresh_merchant(group_id)

        # 8. 群组公告
        if group.current_day % 5 == 0:
            announcements.append(f"📢 第 {group.current_day} 天，危险等级: {'⭐' * group.danger_level}")

        # 季节变化公告
        if group.season_day == 1:
            season_names = {"spring": "🌸 春季", "summer": "☀️ 夏季",
                           "autumn": "🍂 秋季", "winter": "❄️ 冬季"}
            announcements.append(f"🌍 季节更替：{season_names.get(group.current_season, group.current_season)}")

        # 9. 构建幸存者状态摘要
        alive_lines = []
        dead_names = []
        for uid, p in players.items():
            name = p.nickname or f"玩家{uid[-4:]}"
            if p.is_alive():
                cls_name = ""
                if p.player_class:
                    cd = ClassRegistry.get(p.player_class)
                    if cd:
                        cls_name = f" {cd['name']}"
                rest_tag = "😴" if p.is_resting else "✅"
                alive_lines.append(
                    f"  {rest_tag} {name} Lv.{p.level}{cls_name}: "
                    f"❤️{p.health}/{p.max_health} 🍖{p.hunger} 💧{p.thirst}"
                )
            else:
                dead_names.append(name)

        summary_lines = [f"🌅 ===== 第 {group.current_day} 天结算 ====="]
        summary_lines.append(f"👥 幸存者状态 (存活 {len(alive_lines)} / 总计 {len(players)}):")
        if alive_lines:
            summary_lines.extend(alive_lines)
        else:
            summary_lines.append("  (无幸存者)")
        if dead_names:
            summary_lines.append(f"💀 已死亡: {', '.join(dead_names)}")
        summary = "\n".join(summary_lines)

        return {
            "day": group.current_day,
            "season": group.current_season,
            "danger_level": group.danger_level,
            "announcements": announcements,
            "player_count": len(players),
            "summary": summary,
        }

    # ================================================================
    # 内部辅助方法
    # ================================================================

    def _pick_event(self, player: PlayerState, group: GroupGameState) -> Optional[GameEvent]:
        """根据玩家和群组状态选择事件"""
        # 优先检查是否有进行中的事件链
        chain_event = self._check_chain_event(player, group)
        if chain_event:
            return chain_event

        # 根据危险等级和天气调整事件类型权重
        weather = group.weather
        weather_weights = {
            "clear": {},
            "cloudy": {EventType.RESOURCE: -0.5},
            "rain": {EventType.RESOURCE: 1.0, EventType.DANGER: -0.3},
            "storm": {EventType.DANGER: 0.5, EventType.RESOURCE: -1.0},
            "fog": {EventType.DANGER: 0.8, EventType.RESOURCE: -0.8},
            "heatwave": {EventType.WEATHER: 1.5, EventType.RESOURCE: -0.5},
            "cold_snap": {EventType.WEATHER: 1.5, EventType.DANGER: 0.3},
        }

        weights = {
            EventType.RESOURCE: max(0.1, 3.0 - group.danger_level * 0.2),
            EventType.DANGER: 1.0 + group.danger_level * 0.3,
            EventType.OPPORTUNITY: 1.5,
            EventType.WEATHER: 1.0,
            EventType.SOCIAL: 1.0,
            EventType.CHAIN: 0.8,
        }

        # 应用天气修正
        for etype, modifier in weather_weights.get(weather, {}).items():
            if etype in weights:
                weights[etype] = max(0.1, weights[etype] + modifier)

        # 加权随机选择事件类型
        total = sum(weights.values())
        r = random.random() * total
        cumulative = 0
        chosen_type = EventType.RESOURCE
        for etype, w in weights.items():
            cumulative += w
            if r <= cumulative:
                chosen_type = etype
                break

        # 获取该类型的候选事件，过滤天气专属事件
        candidates = EventRegistry.get_by_type(chosen_type)
        if weather != "clear":
            # 优先选择天气专属事件
            weather_candidates = [e for e in candidates if e.weather_only and weather in e.weather_only]
            if weather_candidates and random.random() < 0.6:
                candidates = weather_candidates

        # 尝试使用 LLM 生成的事件（按比例替换内置事件）
        if self.llm_enabled and random.random() < self.llm_event_ratio:
            llm_event = llm_events.pop_event()
            if llm_event:
                print(f"[LLM] 抽中 LLM 事件: {llm_event.name} (类型: {llm_event.event_type.value})")
                return llm_event
            # 缓存为空时会走内置事件，pop_event 内部已打印日志

        if not candidates:
            return None

        total_weight = sum(e.weight for e in candidates)
        r = random.uniform(0, total_weight)
        cum = 0
        for event in candidates:
            cum += event.weight
            if r <= cum:
                return event
        return candidates[-1] if candidates else None

    def _check_chain_event(self, player: PlayerState, group: GroupGameState) -> Optional[GameEvent]:
        """检查是否有进行中的事件链"""
        for chain_id, step in player.chain_progress.items():
            # 查找该链下一步的事件
            chain_events = [e for e in EventRegistry.get_all()
                          if e.chain_id == chain_id and e.chain_order == step + 1]
            if chain_events:
                # 有概率触发（避免每次都触发链事件）
                if random.random() < 0.3:
                    return chain_events[0]
        return None

    def _apply_auto_result(self, player: PlayerState, result: Dict) -> str:
        """应用自动结算结果"""
        messages = []

        if "description" in result:
            messages.append(result["description"])

        if "resources" in result:
            for res, (min_n, max_n) in result["resources"].items():
                amount = random.randint(min_n, max_n)
                player.add_resource(res, amount)

        if "thirst_decay_extra" in result:
            player.thirst = max(0, player.thirst - result["thirst_decay_extra"])
            messages.append(f"💧 口渴度额外下降 {result['thirst_decay_extra']} 点。")

        if "hunger_decay_extra" in result:
            player.hunger = max(0, player.hunger - result["hunger_decay_extra"])
            messages.append(f"🍖 饱食度额外下降 {result['hunger_decay_extra']} 点。")

        return "\n".join(messages) if messages else "事件已自动结算。"

    def _use_ammo(self, player: PlayerState, count_range: tuple) -> tuple:
        """使用弹药。返回 (攻击力扣除值, 弹药消耗信息字符串)。
        如果玩家装备了远程武器且有弹药，消耗弹药，扣除0。
        如果有远程武器但无弹药，扣除该武器的全部 attack_bonus（等于远程武器无法使用）。
        如果无远程武器，扣除0。
        """
        weapon_id = player.equipped_weapon
        if not weapon_id:
            return 0, ""

        weapon = ItemRegistry.get(weapon_id)
        if not weapon or not getattr(weapon, "is_ranged", False):
            return 0, ""

        current_ammo = player.resources.get("ammo", 0)
        if current_ammo <= 0:
            return weapon.attack_bonus, "⚠️ 弹药耗尽！远程武器无法使用，本次战斗无武器加成。"

        cost = random.randint(count_range[0], min(count_range[1], current_ammo))
        player.consume_resource("ammo", cost)
        return 0, f"🔫 消耗了 {cost} 弹药。剩余 {player.resources['ammo']}。"

    def _resolve_combat(self, player: PlayerState, combat_data: Dict) -> Dict[str, Any]:
        """战斗结算"""
        enemy_attack = combat_data["enemy_attack"]
        enemy_health = combat_data["enemy_health"]

        # 弹药消耗（PVE: 1-3发），弹药耗尽时远程武器攻击加成完全失效
        ammo_penalty, ammo_msg = self._use_ammo(player, (1, 3))

        # 玩家战斗力
        player_power = player.attack - ammo_penalty + player.defense * 0.5
        combat_level = player.skills.get("combat", 0)
        player_power += combat_level * 2

        # 敌人战斗力
        enemy_power = enemy_attack + enemy_health * 0.3

        # 战斗判定 (玩家胜率基于实力对比)
        win_chance = player_power / (player_power + enemy_power)
        win = random.random() < win_chance

        if win:
            player.stats["zombies_killed"] += 1
            msg = f"⚔️ 战斗胜利！你击败了敌人！（胜率 {win_chance:.0%}）"
            if ammo_msg:
                msg += "\n" + ammo_msg
            return {"win": True, "message": msg}
        else:
            damage = random.randint(5, enemy_attack)
            # 防御减免
            damage = max(1, damage - player.defense // 3)
            player.health = max(0, player.health - damage)
            msg = f"💥 战斗失败！受到了 {damage} 点伤害。"
            if ammo_msg:
                msg += "\n" + ammo_msg
            return {
                "win": False,
                "message": msg,
                "damage": damage,
            }

    def _apply_building_production(self, player: PlayerState):
        """应用建筑每日产出"""
        # 农场
        farm_level = player.buildings.get("farm", 0)
        if farm_level > 0:
            food_prod = farm_level * 5
            player.add_resource("food", food_prod)

        # 水井
        well_level = player.buildings.get("well", 0)
        if well_level > 0:
            water_prod = well_level * 5
            player.add_resource("water", water_prod)

        # 工坊被动产出（随机材料）
        workshop_level = player.buildings.get("workshop", 0)
        if workshop_level > 0 and random.random() < 0.3:
            mats = ["scrap_metal", "electronics", "nails"]
            player.add_item(random.choice(mats), random.randint(1, workshop_level))

        # 陷阱装置：捕获小动物获得食物
        trap_level = player.buildings.get("trap", 0)
        if trap_level > 0 and random.random() < 0.4:
            food_gain = trap_level * random.randint(2, 6)
            player.add_resource("food", food_gain)

        # 军械库被动：生产弹药
        armory_level = player.buildings.get("armory", 0)
        if armory_level > 0:
            ammo_gain = armory_level * 2
            player.add_resource("ammo", ammo_gain)

    def _apply_building_buffs(self, player: PlayerState):
        """应用建筑被动增益（防御、血量等），通过增量法避免覆盖装备加成"""
        # 避难所：防御和血量
        shelter_level = player.buildings.get("shelter", 0)
        bld_def = BuildingRegistry.get("shelter")
        if shelter_level > 0 and bld_def:
            def_per_level = bld_def.effect_per_level.get("defense", 0)
            hp_per_level = bld_def.effect_per_level.get("max_health", 0)
            new_defense = int(shelter_level * def_per_level)
            new_max_hp = int(shelter_level * hp_per_level)
        else:
            new_defense = 0
            new_max_hp = 0

        # 增量法：计算新旧差值，避免覆盖装备/升级带来的数值
        def_delta = new_defense - player.building_defense_bonus
        hp_delta = new_max_hp - player.building_max_health_bonus

        player.defense += def_delta
        player.max_health += hp_delta
        player.building_defense_bonus = new_defense
        player.building_max_health_bonus = new_max_hp

    # ================================================================
    # 全自动搜集（每游戏天直接入账）
    # ================================================================

    def _auto_gather(self, player: PlayerState):
        """每游戏天自动搜集资源，直接入账。所有存活玩家自动获得。"""
        old_level = player.level
        base = {"food": 4, "water": 3, "wood": 2, "stone": 1}

        level_bonus = 1.0 + (player.level // 5) * 0.2
        scav_level = player.skills.get("scavenging", 0)
        skill_bonus = 1.0 + scav_level * 0.08

        class_bonus = 1.0
        class_resources = {}
        if player.player_class == "scavenger":
            class_bonus = 1.25
        elif player.player_class == "survivalist":
            class_resources = {"food": 1.5, "water": 1.5}
        elif player.player_class == "engineer":
            class_resources = {"wood": 2.0, "stone": 2.0, "iron": 2.0}
        elif player.player_class == "merchant":
            class_resources = {"medicine": 2.0}

        for res, amount in base.items():
            gain = int(amount * level_bonus * skill_bonus * class_bonus)
            if res in class_resources:
                gain = int(gain * class_resources[res])
            player.add_resource(res, max(1, gain))

        # 仓库建筑：额外采集加成
        storage_level = player.buildings.get("storage", 0)
        if storage_level > 0:
            storage_bld = BuildingRegistry.get("storage")
            if storage_bld:
                gather_bonus = storage_level * storage_bld.effect_per_level.get("gather_multiplier", 0)
                for res, amount in base.items():
                    bonus_gain = int(amount * gather_bonus)
                    if bonus_gain > 0:
                        player.add_resource(res, bonus_gain)

        if random.random() < min(0.3 + player.level * 0.02, 0.7):
            bonus_items = ["scrap_metal", "nails", "rope", "electronics", "cloth", "herb", "wood_plank"]
            player.add_item(random.choice(bonus_items), 1)

        if random.random() < 0.03:
            rare_items = ["bandage", "matchbox", "canned_food", "battery"]
            player.add_item(random.choice(rare_items), 1)

        if random.random() < 0.15:
            player.exp += random.randint(5, 15 + player.level * 2)
            self._check_level_up(player)

        # 记录离线升级次数（兼容旧版存档无此字段）
        if player.level > old_level:
            prev = getattr(player, "unread_level_ups", 0)
            object.__setattr__(player, "unread_level_ups", prev + (player.level - old_level))

        if player.health < player.max_health:
            heal = 1 + (player.level // 10)
            if player.player_class == "doctor":
                heal = int(heal * 1.5)
            player.health = min(player.max_health, player.health + heal)

    def _check_level_up(self, player: PlayerState) -> Optional[int]:
        """检查并处理升级，支持连续多级升级"""
        leveled = False
        while True:
            exp_needed = player.level * 100
            if player.exp < exp_needed:
                break
            player.level += 1
            player.exp -= exp_needed
            player.max_health += 10
            player.health = min(player.max_health, player.health + 10)
            player.attack += 2
            player.defense += 1
            player.skill_points += 2  # 每级获得2个技能点
            leveled = True
        return player.level if leveled else None

    def _roll_range(self, range_tuple: Tuple[int, int]) -> int:
        """在范围内随机取值"""
        return random.randint(range_tuple[0], range_tuple[1])

    # 合法的资源类型 ID 集合（用于防止资源被错误加入背包）
    _RESOURCE_IDS = {"food", "water", "wood", "stone", "iron", "medicine", "ammo", "fuel"}

    def _is_resource_id(self, item_id: str) -> bool:
        """判断一个 ID 是否是资源类型（而非物品）"""
        return item_id in self._RESOURCE_IDS

    # ================================================================
    # 玩家重生
    # ================================================================

    def respawn_player(self, user_id: str, group_id: str, nickname: str = "") -> PlayerState:
        """重生玩家"""
        # 保存旧玩家的统计
        old_player = self._players.get(group_id, {}).get(user_id)
        old_deaths = old_player.stats.get("deaths", 0) if old_player else 0
        old_events = old_player.stats.get("events_triggered", 0) if old_player else 0
        old_zombies = old_player.stats.get("zombies_killed", 0) if old_player else 0
        old_crafted = old_player.stats.get("items_crafted", 0) if old_player else 0
        old_actions = old_player.total_actions if old_player else 0
        old_class = old_player.player_class if old_player else None
        old_achievements = old_player.unlocked_achievements if old_player else []
        old_titles = old_player.unlocked_titles if old_player else []
        old_chain = old_player.chain_progress if old_player else {}
        old_pvp_wins = old_player.pvp_wins if old_player else 0
        old_pvp_losses = old_player.pvp_losses if old_player else 0

        player = self.create_player(user_id, group_id, nickname, player_class=old_class)
        # 保留旧统计数据
        player.stats["deaths"] = old_deaths + 1
        player.stats["events_triggered"] = old_events
        player.stats["zombies_killed"] = old_zombies
        player.stats["items_crafted"] = old_crafted
        player.total_actions = old_actions
        player.unlocked_achievements = old_achievements
        player.unlocked_titles = old_titles
        player.chain_progress = old_chain
        player.pvp_wins = old_pvp_wins
        player.pvp_losses = old_pvp_losses
        return player

    # ================================================================
    # 成就系统
    # ================================================================

    def _check_achievements(self, player: PlayerState, group: GroupGameState) -> List[Dict]:
        """检查并解锁成就"""
        new_achievements = []
        # 更新存活天数
        player.days_survived = group.current_day

        for achievement in AchievementRegistry.get_all():
            if achievement.id in player.unlocked_achievements:
                continue
            if self._eval_achievement_condition(player, achievement.condition):
                player.unlocked_achievements.append(achievement.id)
                # 发放奖励
                for item_id, count in achievement.reward_items.items():
                    if self._is_resource_id(item_id):
                        player.add_resource(item_id, count)
                    else:
                        player.add_item(item_id, count)
                for res, amount in achievement.reward_resources.items():
                    player.add_resource(res, amount)
                if achievement.reward_exp > 0:
                    player.exp += achievement.reward_exp
                if achievement.reward_title:
                    player.unlocked_titles.append(achievement.reward_title)
                    if not player.active_title:
                        player.active_title = achievement.reward_title
                new_achievements.append({
                    "name": achievement.name,
                    "description": achievement.reward_description,
                    "title": achievement.reward_title,
                })

        return new_achievements

    def _eval_achievement_condition(self, player: PlayerState, condition: str) -> bool:
        """评估成就条件"""
        try:
            # 构建安全的评估环境
            safe_dict = {
                "zombies_killed": player.stats.get("zombies_killed", 0),
                "items_crafted": player.stats.get("items_crafted", 0),
                "events_triggered": player.stats.get("events_triggered", 0),
                "deaths": player.stats.get("deaths", 0),
                "days_survived": player.days_survived,
                "level": player.level,
                "total_actions": player.total_actions,
                "pvp_wins": player.pvp_wins,
                "pvp_losses": player.pvp_losses,
                "total_builds": getattr(player, "total_builds", 0),
            }
            return bool(eval(condition, {"__builtins__": {}}, safe_dict))
        except Exception:
            return False

    # ================================================================
    # 技能加点系统
    # ================================================================

    def upgrade_skill(self, player: PlayerState, skill_id: str) -> Dict[str, Any]:
        """升级技能"""
        skill_def = SkillRegistry.get(skill_id)
        if not skill_def:
            return {"type": "error", "message": "⚠️ 未知的技能。"}

        if player.skill_points <= 0:
            return {"type": "error", "message": "⚠️ 没有可用的技能点！升级可以获得技能点。"}

        current_level = player.skills.get(skill_id, 0)
        if current_level >= skill_def.max_level:
            return {"type": "error", "message": f"📚 {skill_def.name} 已达到最高等级 Lv.{skill_def.max_level}！"}

        # 消耗技能点
        player.skill_points -= 1
        player.skills[skill_id] = current_level + 1

        new_level = current_level + 1
        effects = []
        if "attack" in skill_def.effect_per_level:
            bonus = int(skill_def.effect_per_level["attack"] * new_level)
            effects.append(f"攻击力 +{bonus}")
        if "heal_bonus" in skill_def.effect_per_level:
            effects.append(f"治疗效果 +{int(skill_def.effect_per_level['heal_bonus'] * new_level * 100)}%")
        if "loot_bonus" in skill_def.effect_per_level:
            effects.append(f"搜索收益 +{int(skill_def.effect_per_level['loot_bonus'] * new_level * 100)}%")
        if "hunger_decay_reduce" in skill_def.effect_per_level:
            effects.append(f"每日消耗 -{int(skill_def.effect_per_level['hunger_decay_reduce'] * new_level * 100)}%")

        effect_str = "、".join(effects) if effects else "效果提升"
        return {
            "type": "success",
            "message": f"📚 {skill_def.name} 升级到 Lv.{new_level}！\n{effect_str}\n剩余技能点: {player.skill_points}",
            "skill_name": skill_def.name,
            "new_level": new_level,
        }

    # ================================================================
    # PvP 偷袭系统
    # ================================================================

    PVP_COOLDOWN = 600  # 偷袭冷却 10 分钟
    PVP_SHIELD_DURATION = 7200  # 新手保护 2 小时

    def can_pvp_attack(self, attacker: PlayerState, target: PlayerState,
                       group_id: str) -> Tuple[bool, str]:
        """检查是否可以 PvP 攻击"""
        if not attacker.is_alive():
            return False, "💀 你已经死亡，无法偷袭。"
        if not target.is_alive():
            return False, "💀 目标已经死亡。"
        if attacker.user_id == target.user_id:
            return False, "⚠️ 你不能偷袭自己。"

        # 检查攻击者冷却
        if time.time() < attacker.pvp_cooldown_until:
            remaining = int(attacker.pvp_cooldown_until - time.time())
            return False, f"⏳ 偷袭冷却中，请等待 {remaining} 秒。"

        # 检查目标保护
        if time.time() < target.pvp_shield_until:
            remaining = int(target.pvp_shield_until - time.time())
            return False, f"🛡️ 目标处于新手保护期（剩余 {remaining} 秒），无法攻击。"

        # 检查瞭望塔防御
        watchtower_level = target.buildings.get("watchtower", 0)
        if watchtower_level > 0:
            evade_chance = watchtower_level * 0.1
            if random.random() < evade_chance:
                return False, f"🔭 目标的瞭望塔发现了你的踪迹，偷袭失败！"

        return True, ""

    def execute_pvp(self, attacker: PlayerState, target: PlayerState,
                    group_id: str) -> Dict[str, Any]:
        """执行 PvP 偷袭"""

        # 设置攻击者冷却
        attacker.pvp_cooldown_until = time.time() + self.PVP_COOLDOWN

        # 弹药消耗（PVP: 2-5发），弹药耗尽时远程武器攻击加成完全失效
        ammo_penalty, ammo_msg = self._use_ammo(attacker, (2, 5))

        # 计算战斗力
        attacker_power = attacker.attack - ammo_penalty + attacker.defense * 0.5 + attacker.level * 2
        target_power = target.attack + target.defense * 0.5 + target.level * 2

        # 士兵职业加成
        if attacker.player_class == "soldier":
            attacker_power *= 1.2

        win_chance = attacker_power / (attacker_power + target_power)

        if random.random() < win_chance:
            # 攻击者胜利：抢夺资源
            target.last_attacked_by = attacker.user_id
            damage = random.randint(15, 40)
            target.health = max(0, target.health - damage)

            # 抢夺资源（最多50%）
            stolen_resources = {}
            for res in ["food", "water", "medicine", "ammo", "fuel"]:
                target_amount = target.resources.get(res, 0)
                if target_amount > 0:
                    steal = random.randint(1, max(1, target_amount // 2))
                    target.consume_resource(res, steal)
                    attacker.add_resource(res, steal)
                    stolen_resources[res] = steal

            # 抢夺物品（随机1-2种）
            stolen_items = {}
            if target.inventory:
                target_items = list(target.inventory.keys())
                random.shuffle(target_items)
                for item_id in target_items[:2]:
                    count = target.inventory.get(item_id, 0)
                    if count > 0:
                        steal_count = random.randint(1, max(1, count // 2))
                        target.remove_item(item_id, steal_count)
                        attacker.add_item(item_id, steal_count)
                        stolen_items[item_id] = steal_count

            attacker.pvp_wins += 1
            target.pvp_losses += 1
            attacker.exp += random.randint(30, 80)

            # 检查攻击者升级
            self._check_level_up(attacker)

            # 检查目标是否死亡
            if target.health <= 0:
                target.status = "dead"
                target.stats["deaths"] += 1

            return {
                "type": "win",
                "attacker_display": f"{attacker.get_title_display()}{attacker.nickname or attacker.user_id}",
                "target_display": f"{target.get_title_display()}{target.nickname or target.user_id}",
                "damage_dealt": damage,
                "stolen_resources": stolen_resources,
                "stolen_items": stolen_items,
                "win_chance": win_chance,
                "target_died": target.status == "dead",
                "ammo_msg": ammo_msg,
            }
        else:
            # 攻击者失败：自己受伤
            damage = random.randint(10, 30)
            attacker.health = max(0, attacker.health - damage)
            attacker.pvp_losses += 1
            target.pvp_wins += 1

            if attacker.health <= 0:
                attacker.status = "dead"
                attacker.stats["deaths"] += 1

            return {
                "type": "lose",
                "attacker_display": f"{attacker.get_title_display()}{attacker.nickname or attacker.user_id}",
                "target_display": f"{target.get_title_display()}{target.nickname or target.user_id}",
                "damage_taken": damage,
                "win_chance": win_chance,
                "attacker_died": attacker.status == "dead",
                "ammo_msg": ammo_msg,
            }

    # ================================================================
    # 称号系统
    # ================================================================

    def set_title(self, player: PlayerState, title: str) -> Dict[str, Any]:
        """设置玩家称号"""
        if title == "无" or title == "取消":
            player.active_title = None
            return {"type": "success", "message": "📛 已取消称号。"}

        if title not in player.unlocked_titles:
            return {"type": "error",
                    "message": f"⚠️ 你还没有解锁称号「{title}」。可用的称号：" +
                    ", ".join(player.unlocked_titles) if player.unlocked_titles else "暂无"}

        player.active_title = title
        return {"type": "success", "message": f"📛 已佩戴称号「{title}」！"}

    def get_player_list(self, group_id: str) -> List[PlayerState]:
        """获取群内所有玩家"""
        return list(self._players.get(group_id, {}).values())

    # ================================================================
    # 末日商人系统
    # ================================================================

    # 商人货品池：(item_id, 价格资源, 价格数量)
    _SIMPLE_MERCHANT_POOL = [
        # 消耗品
        ("bandage", "medicine", 5),
        ("first_aid_kit", "medicine", 12),
        ("canned_food", "wood", 6),
        ("bottled_water", "stone", 6),
        ("mre", "wood", 10),
        ("herb", "food", 4),
        # 武器/工具
        ("baseball_bat", "iron", 15),
        ("crossbow", "iron", 25),
        ("molotov", "fuel", 10),
        ("flashlight", "iron", 8),
        # 材料
        ("cloth", "food", 3),
        ("rope", "food", 3),
        ("scrap_metal", "iron", 4),
        ("electronics", "iron", 12),
        ("gunpowder", "ammo", 8),
        # 稀有物品
        ("stimpack", "medicine", 20),
        ("hunting_rifle", "iron", 35),
        ("riot_shield", "iron", 30),
        ("military_vest", "iron", 45),
    ]

    def _ensure_merchant(self, group_id: str) -> MerchantState:
        """确保商人状态存在"""
        if group_id not in self._merchants:
            self._merchants[group_id] = MerchantState(group_id=group_id)
        return self._merchants[group_id]

    def refresh_merchant_inventory(self, group_id: str, danger_level: int = 1) -> MerchantState:
        """刷新商人库存"""
        merchant = self._ensure_merchant(group_id)
        merchant.last_refresh_day = self.ensure_group(group_id).current_day
        merchant.inventory = []

        used_ids = {"food", "water"}

        # 常驻：食物和水
        merchant.inventory.append(MerchantOffer(
            item_id="food", name=ItemRegistry.get_name("food"),
            is_resource=True, stock=random.randint(8, 20),
            price_res="wood", price_amt=4,
        ))
        merchant.inventory.append(MerchantOffer(
            item_id="water", name=ItemRegistry.get_name("water"),
            is_resource=True, stock=random.randint(8, 20),
            price_res="stone", price_amt=4,
        ))

        # 随机选 4-6 个其他货品
        pool = [(i, r, a) for i, r, a in self._SIMPLE_MERCHANT_POOL if i not in used_ids]
        random.shuffle(pool)
        for item_id, price_res, price_amt in pool[:random.randint(4, 6)]:
            if item_id in used_ids:
                continue
            used_ids.add(item_id)
            item_def = ItemRegistry.get(item_id)
            item_name = item_def.name if item_def else item_id
            is_resource = item_id in self._RESOURCE_IDS
            merchant.inventory.append(MerchantOffer(
                item_id=item_id, name=item_name,
                is_resource=is_resource,
                stock=random.randint(1, 4),
                price_res=price_res, price_amt=price_amt,
            ))

        return merchant

    def check_and_refresh_merchant(self, group_id: str) -> MerchantState:
        """检查是否需要刷新商人（每日自动刷新）"""
        merchant = self._ensure_merchant(group_id)
        group = self.ensure_group(group_id)
        if group.current_day - merchant.last_refresh_day >= merchant.refresh_interval:
            self.refresh_merchant_inventory(group_id, group.danger_level)
        return merchant

    def get_merchant_inventory(self, group_id: str) -> List[MerchantOffer]:
        """获取商人当前库存（如未初始化则刷新）"""
        merchant = self._ensure_merchant(group_id)
        if not merchant.inventory:
            self.refresh_merchant_inventory(group_id)
        return merchant.inventory

    def buy_from_merchant(self, player: PlayerState, offer_index: int,
                          quantity: int = 1) -> Dict[str, Any]:
        """玩家从商人购买物品"""
        group_id = player.group_id
        merchant = self._ensure_merchant(group_id)
        if not merchant.inventory:
            return {"type": "error", "message": "🚚 商人暂时没有货物，请等待补货。"}

        if offer_index < 1 or offer_index > len(merchant.inventory):
            return {"type": "error",
                    "message": f"⚠️ 无效的货品编号 (1-{len(merchant.inventory)})。"}

        offer = merchant.inventory[offer_index - 1]
        if offer.stock <= 0:
            return {"type": "error", "message": f"📦 {offer.name} 已售罄！"}

        quantity = min(quantity, offer.stock)
        quantity = max(1, quantity)

        # 计算总价
        total_cost = offer.price_amt * quantity
        res_name = ItemRegistry.get_name(offer.price_res)

        # 商人职业：40% 折扣
        trade_bonus = 1.0
        if player.player_class == "merchant":
            class_data = ClassRegistry.get("merchant")
            if class_data and "trade_bonus" in class_data.get("bonuses", {}):
                trade_bonus = 1.0 - class_data["bonuses"]["trade_bonus"]
                total_cost = max(1, int(total_cost * trade_bonus))

        # 检查资源是否足够
        if player.get_resource(offer.price_res) < total_cost:
            return {
                "type": "error",
                "message": f"⚠️ 资源不足！需要 {res_name} x{total_cost}，你只有 {player.get_resource(offer.price_res)}。"
            }

        # 消耗资源
        player.consume_resource(offer.price_res, total_cost)

        # 发放物品
        if offer.is_resource:
            player.add_resource(offer.item_id, quantity)
        else:
            player.add_item(offer.item_id, quantity)

        # 减少库存
        offer.stock -= quantity

        discount_note = "（商人折扣已应用）" if trade_bonus < 1.0 else ""
        return {
            "type": "success",
            "message": f"🛒 购买了 {offer.name} x{quantity}！{discount_note}\n"
                       f"💸 支付：{res_name} -{total_cost}",
            "item_name": offer.name,
            "quantity": quantity,
            "cost": {offer.price_res: total_cost},
        }

    # ================================================================
    # 数据序列化
    # ================================================================

    def export_data(self) -> Dict[str, Any]:
        """导出所有数据"""
        players_data = {}
        for group_id, group_players in self._players.items():
            players_data[group_id] = {
                uid: p.to_dict() for uid, p in group_players.items()
            }

        groups_data = {
            gid: g.to_dict() for gid, g in self._groups.items()
        }

        return {
            "players": players_data,
            "groups": groups_data,
        }

    def import_data(self, data: Dict[str, Any]):
        """导入数据"""
        for group_id, group_players in data.get("players", {}).items():
            if group_id not in self._players:
                self._players[group_id] = {}
            for uid, pdata in group_players.items():
                self._players[group_id][uid] = PlayerState.from_dict(pdata)

        for gid, gdata in data.get("groups", {}).items():
            self._groups[gid] = GroupGameState.from_dict(gdata)
