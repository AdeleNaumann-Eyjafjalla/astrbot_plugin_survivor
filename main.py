"""
末日生存游戏插件 - 主入口

AstrBot 插件主类，负责：
1. 注册命令处理器
2. 解析用户消息
3. 格式化输出
4. 定时每日结算
"""

import re
import json
import os
import sys
import threading
import time
import traceback
from typing import Tuple, Optional

# 确保插件目录在 sys.path 中（解决 AstrBot 安装后导入失败的问题）
_plugin_dir = os.path.dirname(os.path.abspath(__file__))
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

# AstrBot Star 基类
try:
    from astrbot.api.star import Context, Star
except ImportError:
    # 开发环境 mock
    class Star:
        def __init__(self, context=None):
            pass
    Context = None

# AstrBot 消息依赖
try:
    from nakuru.entities.components import Plain, Image, At
    from nakuru import GroupMessage, FriendMessage
    from cores.qqbot.global_object import AstrMessageEvent
except ImportError:
    # 开发环境 mock
    class Plain:
        def __init__(self, text): self.text = text
    class AstrMessageEvent:
        pass

from models import PlayerState, GroupGameState, ItemCategory
from engine import SurvivorEngine, ACTION_COOLDOWN
from content import (
    init_all_content, ItemRegistry, BuildingRegistry,
    EventRegistry, SkillRegistry, RecipeRegistry,
    AchievementRegistry, ClassRegistry
)

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SAVE_FILE = os.path.join(DATA_DIR, "save_data.json")


class SurvivorPlugin(Star):
    """
    末日生存游戏插件

    指令列表：
    - 开始生存 / 创建角色 [职业]    开始游戏
    - 探索 / 行动                   执行一次探索行动
    - 选择 [1-4]                    选择事件选项
    - 状态 / 我的状态                查看当前状态
    - 背包 / 物品                    查看背包
    - 建造 [建筑名]                  建造/升级建筑
    - 合成 [物品名] [数量]           合成物品
    - 使用 [物品名]                  使用物品
    - 装备 [物品名]                  装备武器/防具
    - 技能列表 / 升级技能 [技能名]   查看和升级技能
    - 成就 / 我的成就                查看成就
    - 称号列表 / 佩戴称号 [称号]     管理称号
    - 职业列表                       查看可选职业
    - 偷袭 [@玩家/QQ号]              PvP 偷袭其他玩家
    - 排行榜                         查看群内排行
    - 重生                           死亡后重新开始
    - 天气                           查看当前天气
    - 帮助 / 生存帮助                查看帮助
    """

    def __init__(self, context=None):
        """初始化插件"""
        super().__init__(context)
        self.context = context

        # 确保数据目录存在
        os.makedirs(DATA_DIR, exist_ok=True)

        # 初始化游戏内容
        init_all_content()

        # 创建游戏引擎
        self.engine = SurvivorEngine()

        # 加载存档
        self._load_data()

        # 启动每日结算定时器
        self._daily_timer_running = True
        self._start_daily_timer()

        print("[Survivor] 末日生存游戏插件已加载！")

    # ================================================================
    # AstrBot 核心接口
    # ================================================================

    def run(self, ame: AstrMessageEvent) -> Tuple:
        """
        AstrBot 消息处理入口

        所有群消息都会经过此函数。
        返回 (是否处理, (成功状态, 回复内容, 指令名))
        """
        try:
            message = ame.message_str.strip() if hasattr(ame, 'message_str') else ""
            if not message:
                return False, None

            # 获取用户和群信息
            user_id = self._get_user_id(ame)
            group_id = self._get_group_id(ame)
            nickname = self._get_nickname(ame)

            if not user_id or not group_id:
                return False, None

            # 路由消息到对应处理器
            result = self._route_message(message, user_id, group_id, nickname)

            if result:
                return True, tuple([True, result, "survivor"])
            return False, None

        except Exception as e:
            traceback.print_exc()
            return True, tuple([True, f"⚠️ 插件错误：{str(e)}", "survivor"])

    def info(self):
        """返回插件元信息"""
        return {
            "name": "survivor",
            "desc": "末日生存文字游戏 - 挂机式QQ群文字游戏 v2.0",
            "help": (
                "🏚️ 末日生存 v2.0 使用说明：\n"
                "━━━━━━━━━━━━━━━\n"
                "🎮 基础指令：\n"
                "  · 开始生存 [名字] [职业] - 创建角色\n"
                "  · 探索 - 外出探索，触发随机事件\n"
                "  · 选择 [数字] - 在事件中做出选择\n"
                "  · 状态 - 查看生存状态\n"
                "  · 背包 - 查看背包物品\n"
                "  · 帮助 - 显示完整帮助\n"
                "\n"
                "👤 职业系统：\n"
                "  · 职业列表 - 查看可选职业\n"
                "  · 开始生存时选择职业获得不同加成\n"
                "\n"
                "🏗️ 建造系统：\n"
                "  · 建造列表 - 查看可建造建筑\n"
                "  · 建造 [名称] - 建造/升级建筑\n"
                "\n"
                "🔨 合成系统：\n"
                "  · 配方 - 查看合成配方\n"
                "  · 合成 [名称] [数量] - 合成物品\n"
                "\n"
                "📚 技能系统：\n"
                "  · 技能列表 - 查看技能和技能点\n"
                "  · 升级技能 [技能名] - 使用技能点升级\n"
                "\n"
                "🏆 成就称号：\n"
                "  · 成就 - 查看已解锁成就\n"
                "  · 称号列表 - 查看已解锁称号\n"
                "  · 佩戴称号 [称号] - 佩戴称号\n"
                "\n"
                "⚔️ PvP系统：\n"
                "  · 偷袭 [@玩家/QQ号] - 偷袭其他玩家\n"
                "  · 胜利可抢夺对方资源\n"
                "\n"
                "🌤️ 其他：\n"
                "  · 天气 - 查看当前天气和世界状态\n"
                "  · 排行榜 - 群内排行\n"
                "  · 重生 - 死亡后重新开始\n"
            ),
            "version": "v2.0.0",
            "author": "adelenaumann"
        }

    # ================================================================
    # 消息路由
    # ================================================================

    def _route_message(self, message: str, user_id: str, group_id: str, nickname: str) -> Optional[str]:
        """消息路由：根据消息内容分发到对应处理器"""
        msg = message.strip()

        # === 最高优先级：等待起名状态 ===
        if self.engine.has_pending_name(user_id, group_id):
            return self._cmd_set_name(user_id, group_id, msg)

        # === 游戏开始（支持「开始生存 名字 职业」格式） ===
        start_match = re.match(r'^(?:开始生存|创建角色|加入生存)\s*(.*)$', msg)
        if start_match:
            args = start_match.group(1).strip()
            return self._cmd_start(user_id, group_id, nickname, args=args if args else None)

        # === 探索行动 ===
        if msg in ["探索", "行动", "外出", "搜索"]:
            return self._cmd_explore(user_id, group_id)

        # === 事件选择 ===
        choice_match = re.match(r'^选择\s*(\d+)$', msg)
        if choice_match:
            return self._cmd_choice(user_id, group_id, int(choice_match.group(1)))

        # 也支持纯数字作为选择（当有待处理事件时）
        if re.match(r'^[1-4]$', msg) and self.engine.has_pending_choice(user_id, group_id):
            return self._cmd_choice(user_id, group_id, int(msg))

        # === 状态查看 ===
        if msg in ["状态", "我的状态", "生存状态", "信息"]:
            return self._cmd_status(user_id, group_id)

        # === 背包 ===
        if msg in ["背包", "物品", "我的物品", "仓库"]:
            return self._cmd_inventory(user_id, group_id)

        # === 建造 ===
        if msg == "建造列表":
            return self._cmd_build_list()
        if msg.startswith("建造"):
            building_name = msg[2:].strip()
            if building_name:
                return self._cmd_build(user_id, group_id, building_name)

        # === 合成 ===
        if msg in ["配方", "配方列表", "合成列表"]:
            return self._cmd_recipe_list()
        if msg.startswith("合成"):
            parts = msg[2:].strip().split()
            if parts:
                item_name = parts[0]
                count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
                return self._cmd_craft(user_id, group_id, item_name, count)

        # === 使用物品 ===
        if msg.startswith("使用"):
            item_name = msg[2:].strip()
            if item_name:
                return self._cmd_use_item(user_id, group_id, item_name)

        # === 装备 ===
        if msg.startswith("装备"):
            item_name = msg[2:].strip()
            if item_name:
                return self._cmd_use_item(user_id, group_id, item_name)

        # === 职业列表 ===
        if msg in ["职业列表", "职业", "天赋列表"]:
            return self._cmd_class_list()

        # === 技能 ===
        if msg in ["技能列表", "技能"]:
            return self._cmd_skill_list(user_id, group_id)
        if msg.startswith("升级技能"):
            skill_name = msg[4:].strip()
            if skill_name:
                return self._cmd_upgrade_skill(user_id, group_id, skill_name)

        # === 成就 ===
        if msg in ["成就", "我的成就", "成就列表"]:
            return self._cmd_achievements(user_id, group_id)

        # === 称号 ===
        if msg in ["称号列表", "我的称号", "称号"]:
            return self._cmd_title_list(user_id, group_id)
        if msg.startswith("佩戴称号"):
            title = msg[4:].strip()
            if title:
                return self._cmd_set_title(user_id, group_id, title)

        # === PvP 偷袭 ===
        if msg.startswith("偷袭"):
            target_info = msg[2:].strip()
            if target_info:
                return self._cmd_pvp(user_id, group_id, target_info, ame=None)

        # === 排行榜 ===
        if msg in ["排行榜", "排名", "生存排行"]:
            return self._cmd_leaderboard(group_id)

        # === 重生 ===
        if msg in ["重生", "重新开始", "再来一次"]:
            return self._cmd_respawn(user_id, group_id, nickname)

        # === 帮助 ===
        if msg in ["帮助", "生存帮助", "help", "指令"]:
            return self._cmd_help()

        # === 天气/世界状态 ===
        if msg in ["天气", "世界状态", "世界", "群组状态"]:
            return self._cmd_world_status(group_id)

        return None

    # ================================================================
    # 指令处理
    # ================================================================

    def _cmd_start(self, user_id: str, group_id: str, nickname: str, args: str = None) -> str:
        """开始游戏，支持「开始生存 名字 职业」"""
        player = self.engine.get_player(user_id, group_id)
        if player and player.is_alive():
            return (
                f"🏚️ 你已经在这个末日世界中生存了！\n"
                f"使用「探索」继续你的求生之旅吧。"
            )

        # 解析参数：名字 [职业]
        custom_name = None
        player_class = None
        if args:
            parts = args.split()
            custom_name = parts[0] if parts else None
            if len(parts) >= 2:
                # 查找职业
                class_map = {c["name"]: c["id"] for c in ClassRegistry.get_all().values()}
                class_map.update({c["id"]: c["id"] for c in ClassRegistry.get_all().values()})
                class_input = parts[1]
                if class_input in class_map:
                    player_class = class_map[class_input]
                # 也支持直接用职业 ID
                elif class_input in ClassRegistry.get_all():
                    player_class = class_input

        # 如果带了名字参数，直接创建
        if custom_name:
            return self._create_new_player(user_id, group_id, custom_name, player_class)

        # 否则引导起名
        self.engine.set_pending_name(user_id, group_id)
        return (
            f"🏚️ ===== 末日生存 =====\n"
            f"欢迎来到末日世界，幸存者！\n"
            f"\n"
            f"在开始之前，请告诉我你的名字：\n"
            f"💡 直接回复你的名字即可\n"
            f"💡 也可以使用「开始生存 名字 职业」一步完成\n"
            f"💡 使用「职业列表」查看可选职业\n"
            f"\n"
            f"⚠️ 名字和职业一旦确定将无法更改！"
        )

    def _cmd_set_name(self, user_id: str, group_id: str, name: str) -> str:
        """设置玩家名字"""
        # 验证名字
        name = name.strip()
        if not name:
            return "⚠️ 名字不能为空，请输入你的名字："

        if len(name) > 12:
            return "⚠️ 名字不能超过12个字，请重新输入："

        # 检查是否已存在玩家
        player = self.engine.get_player(user_id, group_id)
        if player and player.is_alive():
            self.engine.clear_pending_name(user_id, group_id)
            return "🏚️ 你已经在这个末日世界中生存了！使用「探索」继续你的求生之旅吧。"

        return self._create_new_player(user_id, group_id, name)

    def _create_new_player(self, user_id: str, group_id: str, name: str, player_class: str = None) -> str:
        """创建新玩家"""
        self.engine.clear_pending_name(user_id, group_id)
        player = self.engine.create_player(user_id, group_id, name, player_class=player_class)

        # 职业信息
        class_info = ""
        if player_class:
            cls_data = ClassRegistry.get(player_class)
            if cls_data:
                class_info = f"👤 职业：{cls_data['name']} - {cls_data['description']}\n"

        return (
            f"🏚️ ===== 末日生存 =====\n"
            f"欢迎，「{name}」！\n"
            f"文明已经崩塌，你必须在废墟中生存下去...\n"
            f"{class_info}"
            f"━━━━━━━━━━━━━━━\n"
            f"📋 初始物资：\n"
            f"  🍖 食物 x{player.resources.get('food', 0)}"
            f"    💧 水 x{player.resources.get('water', 0)}\n"
            f"  🪵 木材 x{player.resources.get('wood', 0)}"
            f"     🪨 石料 x{player.resources.get('stone', 0)}\n"
            f"  💊 药品 x{player.resources.get('medicine', 0)}"
            f"     ⚔️ 攻击力 {player.attack}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💡 使用「探索」开始你的第一次行动！\n"
            f"💡 使用「帮助」查看所有指令"
        )

    def _cmd_explore(self, user_id: str, group_id: str) -> str:
        """探索行动"""
        player = self.engine.get_player(user_id, group_id)
        if not player:
            return "⚠️ 你还没有开始生存！请先使用「开始生存」创建角色。"

        can_act, reason = self.engine.can_act(player)
        if not can_act:
            return reason

        group = self.engine.ensure_group(group_id)
        result = self.engine.do_action(player, group)

        if result["type"] == "empty":
            return result["message"]

        # 构建事件消息
        lines = [
            f"🎲 ===== 探索结果 =====",
            f"📌 {result['event_name']}",
            f"",
            f"📝 {result['description']}",
        ]

        if result["auto"]:
            lines.append(f"")
            lines.append(result["auto_message"])
            lines.append(f"")
            lines.append(f"⏳ 冷却 {ACTION_COOLDOWN} 秒后可再次探索。")
        else:
            lines.append(f"")
            lines.append(f"🤔 你的选择：")
            for choice in result["choices"]:
                lines.append(f"  [{choice['index']}] {choice['text']}")
            lines.append(f"")
            lines.append(f"💡 回复「选择 数字」做出决定。")

        return "\n".join(lines)

    def _cmd_choice(self, user_id: str, group_id: str, choice_index: int) -> str:
        """处理事件选择"""
        player = self.engine.get_player(user_id, group_id)
        if not player:
            return "⚠️ 你还没有开始生存！"

        result = self.engine.handle_choice(player, choice_index)

        if result["type"] == "error":
            return result["message"]

        lines = ["📋 ===== 行动结果 ====="]

        for msg in result["messages"]:
            lines.append(msg)

        # 资源变动
        if result["resources_gained"]:
            lines.append("")
            lines.append("📦 获得资源：")
            for res, amount in result["resources_gained"].items():
                res_names = {"food": "🍖食物", "water": "💧水", "wood": "🪵木材",
                            "stone": "🪨石料", "iron": "🔩铁", "medicine": "💊药品",
                            "ammo": "🔫弹药", "fuel": "⛽燃料"}
                lines.append(f"  {res_names.get(res, res)} +{amount}")

        # 物品变动
        if result["items_gained"]:
            lines.append("")
            lines.append("🎒 获得物品：")
            for item_id, count in result["items_gained"].items():
                item = ItemRegistry.get(item_id)
                item_name = item.name if item else item_id
                lines.append(f"  {item_name} x{count}")

        # 伤害
        if result["damage_taken"] > 0:
            lines.append(f"")
            lines.append(f"💔 受到了 {result['damage_taken']} 点伤害！")

        # 经验
        if result["exp_gained"] > 0:
            lines.append(f"")
            lines.append(f"✨ 获得了 {result['exp_gained']} 点经验！")

        # 升级
        if result["level_up"]:
            lines.append(f"")
            lines.append(f"🎉 升级了！当前等级 Lv.{player.level}！")
            lines.append(f"  生命上限 +10, 攻击 +2, 防御 +1, 获得 2 技能点")
            lines.append(f"  可用技能点: {player.skill_points}")
            lines.append(f"  💡 使用「技能列表」查看可升级技能")

        # 成就解锁
        if result.get("new_achievements"):
            lines.append(f"")
            for ach in result["new_achievements"]:
                lines.append(f"🏆 解锁成就：「{ach['name']}」")
                lines.append(f"  {ach['description']}")
                if ach.get("title"):
                    lines.append(f"  📛 解锁称号：「{ach['title']}」")

        # 当前状态摘要
        lines.append(f"")
        lines.append(f"━━━━━━━━━━━━━━━")
        lines.append(f"❤️ 生命: {player.health}/{player.max_health} | 🍖 {player.hunger} | 💧 {player.thirst}")
        lines.append(f"⏳ 冷却 {ACTION_COOLDOWN} 秒后可再次探索。")

        if player.status == "dead":
            lines.append(f"")
            lines.append(f"💀 你死了...使用「重生」重新开始。")

        return "\n".join(lines)

    def _cmd_status(self, user_id: str, group_id: str) -> str:
        """查看状态"""
        player = self.engine.get_player(user_id, group_id)
        if not player:
            return "⚠️ 你还没有开始生存！请先使用「开始生存」创建角色。"

        group = self.engine.get_group(group_id)

        status_emoji = {"alive": "💚", "injured": "💛", "sick": "🤒", "dead": "💀"}
        emoji = status_emoji.get(player.status, "❓")

        title_display = player.get_title_display()
        title_str = f" {title_display}" if title_display else ""

        class_info = ""
        if player.player_class:
            cls_data = ClassRegistry.get(player.player_class)
            if cls_data:
                class_info = f"👤 职业: {cls_data['name']}\n"

        lines = [
            f"{emoji} ===== {player.nickname or '幸存者'}{title_str} 的状态 =====",
            f"",
            class_info,
            f"📊 等级: Lv.{player.level} | 经验: {player.exp}/{player.level * 100}",
            f"⭐ 技能点: {player.skill_points}",
            f"❤️ 生命: {player.health}/{player.max_health}",
            f"🍖 饱食度: {player.hunger}/100",
            f"💧 口渴度: {player.thirst}/100",
            f"🧠 理智值: {player.sanity}/100",
            f"⚔️ 攻击: {player.attack} | 🛡️ 防御: {player.defense}",
            f"",
            f"📦 资源：",
        ]

        res_icons = {"food": "🍖", "water": "💧", "wood": "🪵", "stone": "🪨",
                    "iron": "🔩", "medicine": "💊", "ammo": "🔫", "fuel": "⛽"}
        for res, amount in player.resources.items():
            if amount > 0:
                lines.append(f"  {res_icons.get(res, '📦')} {res}: {amount}")

        # 装备
        if player.equipped_weapon or player.equipped_armor:
            lines.append(f"")
            lines.append(f"🎒 装备：")
            if player.equipped_weapon:
                weapon = ItemRegistry.get(player.equipped_weapon)
                lines.append(f"  武器: {weapon.name if weapon else player.equipped_weapon}")
            if player.equipped_armor:
                armor = ItemRegistry.get(player.equipped_armor)
                lines.append(f"  防具: {armor.name if armor else player.equipped_armor}")

        # 技能
        if player.skills:
            lines.append(f"")
            lines.append(f"📚 技能：")
            for skill_id, level in player.skills.items():
                skill = SkillRegistry.get(skill_id)
                skill_name = skill.name if skill else skill_id
                lines.append(f"  {skill_name}: Lv.{level}")

        # 统计
        lines.append(f"")
        lines.append(f"📈 统计：")
        lines.append(f"  行动次数: {player.total_actions}")
        lines.append(f"  击杀丧尸: {player.stats.get('zombies_killed', 0)}")
        lines.append(f"  合成物品: {player.stats.get('items_crafted', 0)}")

        if group:
            lines.append(f"")
            lines.append(f"🌍 世界第 {group.current_day} 天 | {group.current_season} | 危险等级 {'⭐' * group.danger_level}")

        return "\n".join(lines)

    def _cmd_inventory(self, user_id: str, group_id: str) -> str:
        """查看背包"""
        player = self.engine.get_player(user_id, group_id)
        if not player:
            return "⚠️ 你还没有开始生存！"

        if not player.inventory:
            return "🎒 你的背包是空的。"

        lines = ["🎒 ===== 背包物品 =====", ""]

        # 按分类整理
        categories = {
            ItemCategory.WEAPON: "⚔️ 武器",
            ItemCategory.ARMOR: "🛡️ 防具",
            ItemCategory.CONSUMABLE: "🧪 消耗品",
            ItemCategory.MATERIAL: "📦 材料",
            ItemCategory.TOOL: "🔧 工具",
            ItemCategory.SPECIAL: "✨ 特殊",
        }

        for cat, cat_name in categories.items():
            cat_items = []
            for item_id, count in player.inventory.items():
                item = ItemRegistry.get(item_id)
                if item and item.category == cat:
                    cat_items.append(f"  {item.name} x{count} (稀有度: {item.rarity})")
                elif not item:
                    cat_items.append(f"  {item_id} x{count}")
            if cat_items:
                lines.append(f"{cat_name}：")
                lines.extend(cat_items)
                lines.append("")

        lines.append(f"💡 使用「使用 [物品名]」来使用消耗品")
        lines.append(f"💡 使用「装备 [物品名]」来装备武器/防具")

        return "\n".join(lines)

    def _cmd_build_list(self) -> str:
        """查看可建造建筑"""
        lines = ["🏗️ ===== 可建造建筑 =====", ""]

        for building in BuildingRegistry.get_all():
            lines.append(f"📌 {building.name} (最高 Lv.{building.max_level})")
            lines.append(f"   {building.description}")
            cost_str = " ".join(f"{k}x{v}" for k, v in building.build_cost.items())
            lines.append(f"   建造消耗: {cost_str}")
            lines.append(f"   效果: {building.effect_per_level}")
            lines.append("")

        lines.append("💡 使用「建造 [建筑名]」来建造或升级")
        return "\n".join(lines)

    def _cmd_build(self, user_id: str, group_id: str, building_name: str) -> str:
        """建造建筑"""
        player = self.engine.get_player(user_id, group_id)
        if not player or not player.is_alive():
            return "⚠️ 你还没有开始生存或已死亡！"

        # 模糊匹配建筑名
        building_id = None
        for bld in BuildingRegistry.get_all():
            if bld.name == building_name or bld.id == building_name:
                building_id = bld.id
                break

        if not building_id:
            return f"⚠️ 未找到建筑「{building_name}」。使用「建造列表」查看可建造建筑。"

        result = self.engine.build_structure(player, building_id)
        if result["type"] == "error":
            return result["message"]

        # 展示消耗
        cost_str = " ".join(f"{k}x{v}" for k, v in result["cost"].items())
        return (
            f"{result['message']}\n"
            f"消耗: {cost_str}\n"
            f"💡 使用「状态」查看你的建筑情况。"
        )

    def _cmd_recipe_list(self) -> str:
        """查看合成配方"""
        lines = ["🔨 ===== 合成配方 =====", ""]

        for item_id, recipe in RecipeRegistry.get_all().items():
            item = ItemRegistry.get(item_id)
            item_name = item.name if item else item_id

            mat_str = " + ".join(
                f"{ItemRegistry.get(mid).name if ItemRegistry.get(mid) else mid} x{amt}"
                for mid, amt in recipe["materials"].items()
            )

            req = ""
            if recipe.get("required_building"):
                bld = BuildingRegistry.get(recipe["required_building"])
                req = f" [需要{bld.name if bld else recipe['required_building']} Lv.{recipe['min_level']}]"

            lines.append(f"📌 {item_name}{req}")
            lines.append(f"   材料: {mat_str}")
            lines.append("")

        lines.append("💡 使用「合成 [物品名] [数量]」来合成物品")
        return "\n".join(lines)

    def _cmd_craft(self, user_id: str, group_id: str, item_name: str, count: int) -> str:
        """合成物品"""
        player = self.engine.get_player(user_id, group_id)
        if not player or not player.is_alive():
            return "⚠️ 你还没有开始生存或已死亡！"

        # 模糊匹配物品名
        item_id = None
        for rid, recipe in RecipeRegistry.get_all().items():
            item = ItemRegistry.get(rid)
            if item and (item.name == item_name or item.id == item_name):
                item_id = rid
                break

        if not item_id:
            return f"⚠️ 未找到可合成的物品「{item_name}」。使用「配方」查看合成列表。"

        result = self.engine.craft_item(player, item_id, count)
        return result["message"]

    def _cmd_use_item(self, user_id: str, group_id: str, item_name: str) -> str:
        """使用/装备物品"""
        player = self.engine.get_player(user_id, group_id)
        if not player or not player.is_alive():
            return "⚠️ 你还没有开始生存或已死亡！"

        # 模糊匹配
        item_id = None
        for iid, count in player.inventory.items():
            item = ItemRegistry.get(iid)
            if item and (item.name == item_name or item.id == item_name):
                item_id = iid
                break

        if not item_id:
            return f"⚠️ 背包中没有「{item_name}」。"

        result = self.engine.use_item(player, item_id)
        return result["message"]

    def _cmd_leaderboard(self, group_id: str) -> str:
        """查看排行榜"""
        players = self.engine._players.get(group_id, {})
        if not players:
            return "📊 本群还没有幸存者！使用「开始生存」加入吧。"

        # 按存活天数排序
        alive = [(uid, p) for uid, p in players.items() if p.is_alive()]
        dead = [(uid, p) for uid, p in players.items() if not p.is_alive()]

        alive.sort(key=lambda x: (x[1].level, x[1].days_survived), reverse=True)

        lines = ["📊 ===== 生存排行榜 =====", ""]

        for i, (uid, p) in enumerate(alive[:10]):
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
            name = p.nickname or f"幸存者{uid[-4:]}"
            title = p.get_title_display()
            title_str = f" {title}" if title else ""
            class_str = ""
            if p.player_class:
                cls_data = ClassRegistry.get(p.player_class)
                if cls_data:
                    class_str = f" [{cls_data['name']}]"
            lines.append(
                f"{medal}{title_str} {name}{class_str} | Lv.{p.level} | "
                f"❤️{p.health}/{p.max_health} | "
                f"⚔️PvP:{p.pvp_wins}W/{p.pvp_losses}L"
            )

        if dead:
            lines.append("")
            lines.append("💀 已阵亡：")
            for uid, p in dead[:5]:
                name = p.nickname or f"幸存者{uid[-4:]}"
                lines.append(f"  {name} | 行动{p.total_actions}次 | 死亡{p.stats.get('deaths', 0)}次")

        return "\n".join(lines)

    def _cmd_respawn(self, user_id: str, group_id: str, nickname: str) -> str:
        """重生"""
        player = self.engine.get_player(user_id, group_id)
        if player and player.is_alive():
            return "⚠️ 你还活着！不需要重生。"

        # 保留原来的名字
        old_name = player.nickname if player else nickname
        player = self.engine.respawn_player(user_id, group_id, old_name)
        deaths = player.stats.get("deaths", 0)
        return (
            f"🔄 {old_name} 重生了！这是你的第 {deaths} 次生命。\n"
            f"记住：在这个末日世界里，谨慎是最好的生存策略。\n"
            f"使用「探索」开始新的冒险吧。"
        )

    def _cmd_world_status(self, group_id: str) -> str:
        """查看世界状态"""
        group = self.engine.get_group(group_id)
        if not group:
            return "🌍 这个世界还没有幸存者...使用「开始生存」创造历史吧！"

        player_count = len(self.engine._players.get(group_id, {}))
        alive_count = sum(1 for p in self.engine._players.get(group_id, {}).values() if p.is_alive())
        season_names = {"spring": "🌸 春季", "summer": "☀️ 夏季",
                       "autumn": "🍂 秋季", "winter": "❄️ 冬季"}

        weather_icons = {
            "clear": "☀️ 晴朗", "cloudy": "☁️ 多云", "rain": "🌧️ 下雨",
            "storm": "⛈️ 暴风雨", "fog": "🌫️ 大雾", "heatwave": "🔥 热浪",
            "cold_snap": "❄️ 寒潮", "sandstorm": "🏜️ 沙尘暴"
        }

        return (
            f"🌍 ===== 世界状态 =====\n"
            f"\n"
            f"📅 第 {group.current_day} 天\n"
            f"🌤️ {season_names.get(group.current_season, group.current_season)} "
            f"(第{group.season_day}/30天)\n"
            f"🌡️ 天气: {weather_icons.get(group.weather, group.weather)}\n"
            f"⚠️ 危险等级: {'⭐' * group.danger_level}\n"
            f"👥 幸存者: {alive_count}存活 / {player_count}总计\n"
            f"\n"
            f"💡 不同天气会影响探索事件的类型和收益！\n"
            f"💡 每1小时为1个游戏日，每日会自动结算消耗和产出。"
        )

    def _cmd_help(self) -> str:
        """帮助信息"""
        return (
            f"🏚️ ===== 末日生存 v2.0 帮助 =====\n"
            f"\n"
            f"🎮 基础操作：\n"
            f"  · 开始生存 [名字] [职业] - 创建角色\n"
            f"  · 探索 - 外出搜索，触发随机事件\n"
            f"  · 选择 [数字] - 在事件中做出选择\n"
            f"  · 状态 - 查看生存状态\n"
            f"  · 背包 - 查看背包物品\n"
            f"\n"
            f"👤 职业系统：\n"
            f"  · 职业列表 - 查看可选职业\n"
            f"  · 6种职业各有独特加成\n"
            f"\n"
            f"🏗️ 建造系统：\n"
            f"  · 建造列表 - 查看可建造建筑\n"
            f"  · 建造 [名称] - 建造/升级建筑\n"
            f"  · 建筑提供每日资源和被动加成\n"
            f"\n"
            f"🔨 合成系统：\n"
            f"  · 配方 - 查看合成配方\n"
            f"  · 合成 [名称] [数量] - 合成物品\n"
            f"\n"
            f"📚 技能系统：\n"
            f"  · 技能列表 - 查看技能\n"
            f"  · 升级技能 [名称] - 使用技能点升级\n"
            f"  · 升级获得 2 技能点\n"
            f"\n"
            f"🏆 成就称号：\n"
            f"  · 成就 - 查看已解锁成就\n"
            f"  · 称号列表 - 查看已解锁称号\n"
            f"  · 佩戴称号 [称号] - 佩戴称号\n"
            f"\n"
            f"⚔️ PvP系统：\n"
            f"  · 偷袭 [玩家名/QQ号] - 偷袭其他玩家\n"
            f"  · 胜利可抢夺对方资源和物品\n"
            f"  · 冷却10分钟，新手保护2小时\n"
            f"\n"
            f"🌤️ 天气系统：\n"
            f"  · 天气 - 查看当前天气\n"
            f"  · 不同天气影响探索事件\n"
            f"\n"
            f"📊 其他：\n"
            f"  · 排行榜 - 群内排行\n"
            f"  · 重生 - 死亡后重新开始\n"
            f"\n"
            f"⏱️ 挂机说明：\n"
            f"  · 每{ACTION_COOLDOWN}秒可行动一次\n"
            f"  · 每1小时结算一个游戏日\n"
            f"  · 建筑每日自动产出资源\n"
            f"  · 天气随机变化，影响游戏体验\n"
        )

    # ================================================================
    # 新系统指令处理
    # ================================================================

    def _cmd_class_list(self) -> str:
        """查看职业列表"""
        lines = ["👤 ===== 可选职业 =====", ""]
        for cls_id, cls_data in ClassRegistry.get_all().items():
            lines.append(f"📌 {cls_data['name']}")
            lines.append(f"   {cls_data['description']}")
            bonuses = cls_data.get("bonuses", {})
            bonus_strs = []
            if "loot_bonus" in bonuses:
                bonus_strs.append(f"搜索收益+{int(bonuses['loot_bonus']*100)}%")
            if "combat_bonus" in bonuses:
                bonus_strs.append(f"战斗+{int(bonuses['combat_bonus']*100)}%")
            if "attack_bonus" in bonuses:
                bonus_strs.append(f"初始攻击+{bonuses['attack_bonus']}")
            if "heal_bonus" in bonuses:
                bonus_strs.append(f"治疗效果+{int(bonuses['heal_bonus']*100)}%")
            if "immune_sick" in bonuses:
                bonus_strs.append("免疫疾病")
            if "build_discount" in bonuses:
                bonus_strs.append(f"建造消耗-{int(bonuses['build_discount']*100)}%")
            if "craft_discount" in bonuses:
                bonus_strs.append(f"合成材料-{int(bonuses['craft_discount']*100)}%")
            if "decay_reduce" in bonuses:
                bonus_strs.append(f"每日消耗-{int(bonuses['decay_reduce']*100)}%")
            if "trade_bonus" in bonuses:
                bonus_strs.append(f"交易收益+{int(bonuses['trade_bonus']*100)}%")
            if bonus_strs:
                lines.append(f"   加成: {' | '.join(bonus_strs)}")
            lines.append("")
        lines.append("💡 使用「开始生存 名字 职业名」选择职业开始游戏")
        return "\n".join(lines)

    def _cmd_skill_list(self, user_id: str, group_id: str) -> str:
        """查看技能列表"""
        player = self.engine.get_player(user_id, group_id)
        if not player or not player.is_alive():
            return "⚠️ 你还没有开始生存或已死亡！"

        lines = [
            f"📚 ===== 技能列表 =====",
            f"",
            f"⭐ 可用技能点: {player.skill_points}",
            f"",
        ]

        for skill in SkillRegistry.get_all():
            level = player.skills.get(skill.id, 0)
            bar = "█" * level + "░" * (skill.max_level - level)
            effects = []
            for key, val in skill.effect_per_level.items():
                if key == "attack":
                    effects.append(f"攻击+{int(val*level)}")
                elif key == "heal_bonus":
                    effects.append(f"治疗+{int(val*level*100)}%")
                elif key == "loot_bonus":
                    effects.append(f"搜索+{int(val*level*100)}%")
                elif "decay_reduce" in key:
                    effects.append(f"消耗-{int(val*level*100)}%")
            effect_str = " | ".join(effects) if effects else "效果提升"

            lines.append(f"📌 {skill.name} [{bar}] Lv.{level}/{skill.max_level}")
            lines.append(f"   {skill.description}")
            lines.append(f"   当前: {effect_str}")
            lines.append("")

        lines.append("💡 使用「升级技能 [技能名]」消耗技能点升级")
        return "\n".join(lines)

    def _cmd_upgrade_skill(self, user_id: str, group_id: str, skill_name: str) -> str:
        """升级技能"""
        player = self.engine.get_player(user_id, group_id)
        if not player or not player.is_alive():
            return "⚠️ 你还没有开始生存或已死亡！"

        # 模糊匹配
        skill_id = None
        for skill in SkillRegistry.get_all():
            if skill.name == skill_name or skill.id == skill_name:
                skill_id = skill.id
                break

        if not skill_id:
            return f"⚠️ 未找到技能「{skill_name}」。使用「技能列表」查看。"

        result = self.engine.upgrade_skill(player, skill_id)
        return result["message"]

    def _cmd_achievements(self, user_id: str, group_id: str) -> str:
        """查看成就"""
        player = self.engine.get_player(user_id, group_id)
        if not player:
            return "⚠️ 你还没有开始生存！"

        lines = ["🏆 ===== 成就 =====", ""]

        categories = {
            "general": "📋 通用",
            "combat": "⚔️ 战斗",
            "survival": "🏕️ 生存",
            "building": "🏗️ 建造",
            "social": "🤝 社交",
        }

        for cat, cat_name in categories.items():
            achievements = AchievementRegistry.get_by_category(cat)
            if not achievements:
                continue
            lines.append(f"{cat_name}：")
            for ach in achievements:
                unlocked = ach.id in player.unlocked_achievements
                icon = "✅" if unlocked else "🔒"
                lines.append(f"  {icon} {ach.name} - {ach.description}")
            lines.append("")

        unlocked_count = len(player.unlocked_achievements)
        total_count = len(AchievementRegistry.get_all())
        lines.append(f"进度: {unlocked_count}/{total_count}")

        return "\n".join(lines)

    def _cmd_title_list(self, user_id: str, group_id: str) -> str:
        """查看称号"""
        player = self.engine.get_player(user_id, group_id)
        if not player:
            return "⚠️ 你还没有开始生存！"

        if not player.unlocked_titles:
            return "📛 你还没有解锁任何称号。通过完成成就来解锁称号吧！"

        lines = ["📛 ===== 称号列表 =====", ""]
        current = player.active_title
        for title in player.unlocked_titles:
            marker = "⭐" if title == current else "  "
            lines.append(f"{marker} {title}")
        lines.append("")
        lines.append(f"当前佩戴: {current or '无'}")
        lines.append("💡 使用「佩戴称号 [称号名]」更换称号")
        lines.append("💡 使用「佩戴称号 取消」取消称号")

        return "\n".join(lines)

    def _cmd_set_title(self, user_id: str, group_id: str, title: str) -> str:
        """设置称号"""
        player = self.engine.get_player(user_id, group_id)
        if not player or not player.is_alive():
            return "⚠️ 你还没有开始生存或已死亡！"

        result = self.engine.set_title(player, title)
        return result["message"]

    def _cmd_pvp(self, user_id: str, group_id: str, target_info: str, ame=None) -> str:
        """PvP 偷袭"""
        attacker = self.engine.get_player(user_id, group_id)
        if not attacker or not attacker.is_alive():
            return "⚠️ 你还没有开始生存或已死亡！"

        # 查找目标玩家
        target = None
        target_id = None
        # 尝试通过昵称查找
        for uid, p in self.engine._players.get(group_id, {}).items():
            if p.nickname and target_info in p.nickname:
                target = p
                target_id = uid
                break

        # 尝试通过 QQ 号查找（去掉 @ 和空格）
        if not target:
            clean = target_info.replace("@", "").replace(" ", "").strip()
            if clean.isdigit():
                target = self.engine.get_player(clean, group_id)
                target_id = clean

        if not target:
            return f"⚠️ 未找到玩家「{target_info}」。请使用玩家的名字或QQ号。"

        # 执行 PvP 检查
        can_attack, reason = self.engine.can_pvp_attack(attacker, target, group_id)
        if not can_attack:
            return reason

        # 执行 PvP
        result = self.engine.execute_pvp(attacker, target, group_id)

        if result["type"] == "win":
            lines = [
                f"⚔️ ===== 偷袭成功！ =====",
                f"",
                f"你成功偷袭了 {result['target_display']}！（胜率 {result['win_chance']:.0%}）",
                f"造成了 {result['damage_dealt']} 点伤害！",
            ]
            if result["stolen_resources"]:
                lines.append("")
                lines.append("📦 抢夺的资源：")
                res_names = {"food": "🍖食物", "water": "💧水", "medicine": "💊药品",
                            "ammo": "🔫弹药", "fuel": "⛽燃料"}
                for res, amount in result["stolen_resources"].items():
                    if amount > 0:
                        lines.append(f"  {res_names.get(res, res)} x{amount}")
            if result["stolen_items"]:
                lines.append("")
                lines.append("🎒 抢夺的物品：")
                for item_id, count in result["stolen_items"].items():
                    item = ItemRegistry.get(item_id)
                    name = item.name if item else item_id
                    lines.append(f"  {name} x{count}")
            if result["target_died"]:
                lines.append("")
                lines.append(f"💀 {result['target_display']} 已死亡！")

            return "\n".join(lines)

        else:
            return (
                f"💥 ===== 偷袭失败！ =====\n"
                f"\n"
                f"你偷袭 {result['target_display']} 失败了！（胜率 {result['win_chance']:.0%}）\n"
                f"反被造成了 {result['damage_taken']} 点伤害！\n"
                f"{'💀 你已死亡！使用「重生」重新开始。' if result.get('attacker_died') else ''}"
            )

    # ================================================================
    # 定时任务
    # ================================================================

    def _start_daily_timer(self):
        """启动每日结算定时器"""
        def timer_loop():
            while self._daily_timer_running:
                time.sleep(3600)  # 每小时一次
                if not self._daily_timer_running:
                    break
                try:
                    self._daily_tick_all()
                except Exception as e:
                    print(f"[Survivor] 每日结算错误: {e}")

        t = threading.Thread(target=timer_loop, daemon=True)
        t.start()

    def _daily_tick_all(self):
        """对所有群组执行每日结算"""
        for group_id in list(self.engine._groups.keys()):
            try:
                self.engine.daily_tick(group_id)
            except Exception as e:
                print(f"[Survivor] 群 {group_id} 每日结算失败: {e}")

        self._save_data()

    # ================================================================
    # 数据持久化
    # ================================================================

    def _load_data(self):
        """加载存档"""
        try:
            if os.path.exists(SAVE_FILE):
                with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.engine.import_data(data)
                print(f"[Survivor] 存档已加载")
        except Exception as e:
            print(f"[Survivor] 加载存档失败: {e}")

    def _save_data(self):
        """保存存档"""
        try:
            data = self.engine.export_data()
            with open(SAVE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Survivor] 保存存档失败: {e}")

    def __del__(self):
        """析构时保存数据"""
        self._daily_timer_running = False
        self._save_data()

    # ================================================================
    # 辅助方法
    # ================================================================

    def _get_user_id(self, ame: AstrMessageEvent) -> Optional[str]:
        """从消息事件中获取用户ID"""
        try:
            if hasattr(ame, 'message_obj') and ame.message_obj:
                return str(ame.message_obj.user_id)
        except:
            pass
        return None

    def _get_group_id(self, ame: AstrMessageEvent) -> Optional[str]:
        """从消息事件中获取群ID"""
        try:
            if hasattr(ame, 'message_obj') and ame.message_obj:
                if hasattr(ame.message_obj, 'group_id'):
                    return str(ame.message_obj.group_id)
        except:
            pass
        return None

    def _get_nickname(self, ame: AstrMessageEvent) -> str:
        """从消息事件中获取用户昵称"""
        try:
            if hasattr(ame, 'message_obj') and ame.message_obj:
                if hasattr(ame.message_obj, 'sender') and ame.message_obj.sender:
                    return str(ame.message_obj.sender.nickname or "")
                if hasattr(ame.message_obj, 'nickname'):
                    return str(ame.message_obj.nickname or "")
        except:
            pass
        return ""
