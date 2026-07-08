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
import asyncio
import traceback

# 确保插件目录在 sys.path 中（解决 AstrBot 安装后导入失败的问题）
_plugin_dir = os.path.dirname(os.path.abspath(__file__))
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

# 清除旧字节码缓存，防止新增枚举成员后热加载报错
# 同时清除插件目录 + AstrBot 全局缓存中本插件的 pyc
import shutil
_plugin_name = os.path.basename(_plugin_dir)
for _base in [_plugin_dir]:
    for root, dirs, files in os.walk(_base):
        if "__pycache__" in dirs:
            shutil.rmtree(os.path.join(root, "__pycache__"), ignore_errors=True)
# 额外：清除 sys.modules 中本插件的旧缓存，强制重新加载
for _mod in list(sys.modules.keys()):
    if _mod.startswith(_plugin_name) or _mod in ("models", "engine", "content", "llm_events"):
        sys.modules.pop(_mod, None)

# AstrBot Star 基类 + 事件系统
try:
    from astrbot.api.star import Context, Star
    from astrbot.api.event import filter, AstrMessageEvent
    from astrbot.api import logger, AstrBotConfig
    from astrbot.api.message_components import At
except ImportError:
    # 开发环境 mock
    class Star:
        def __init__(self, context=None, config=None):
            pass
    Context = None
    AstrBotConfig = dict
    At = None

    class AstrMessageEvent:
        message_str = ""
        def get_sender_name(self): return "TestPlayer"
        def get_sender_id(self): return "test_user"
        def get_group_id(self): return "test_group"
        def stop_event(self): pass
        def plain_result(self, text):
            class PlainResult:
                def __init__(self, text): self.text = text
            return PlainResult(text)
        def get_messages(self): return []  # 消息链，开发环境为空
        message_obj = None  # 结构化消息对象

    class filter:
        class EventMessageType:
            ALL = "ALL"
            GROUP_MESSAGE = "GROUP_MESSAGE"
            PRIVATE_MESSAGE = "PRIVATE_MESSAGE"
        @staticmethod
        def event_message_type(*args, **kwargs):
            def decorator(func):
                return func
            return decorator
        @staticmethod
        def command(name, description=""):
            def decorator(func):
                return func
            return decorator

from models import PlayerState, GroupGameState, ItemCategory, Item
from engine import SurvivorEngine, EXPLORE_HUNGER_COST, EXPLORE_THIRST_COST
from content import (
    init_all_content, ItemRegistry, BuildingRegistry,
    EventRegistry, SkillRegistry, RecipeRegistry,
    AchievementRegistry, ClassRegistry
)


def _resolve_data_dir(plugin_name: str) -> str:
    """解析插件持久化数据目录。

    优先使用 AstrBot 框架提供的 data/plugin_data/{plugin_name}/ 目录；
    开发环境回退到插件目录下的 data/。
    """
    try:
        from astrbot.core.utils.astrbot_path import get_astrbot_data_path
        from pathlib import Path
        return str(Path(get_astrbot_data_path()) / "plugin_data" / plugin_name)
    except ImportError:
        return os.path.join(os.path.dirname(__file__), "data")


import llm_events

# ================================================================
# 命令常量 —— 使用 @filter.command 注册到 AstrBot 指令系统
# ================================================================
CMD_START = "开始生存"
CMD_EXPLORE = "探索"
CMD_CHOOSE = "选择"
CMD_STATUS = "状态"
CMD_INVENTORY = "背包"
CMD_BUILD_LIST = "建造列表"
CMD_BUILD = "建造"
CMD_RECIPE = "配方"
CMD_CRAFT = "合成"
CMD_USE = "使用"
CMD_EQUIP = "装备"
CMD_CLASS_LIST = "职业列表"
CMD_SKILL_LIST = "技能列表"
CMD_UPGRADE_SKILL = "升级技能"
CMD_ACHIEVEMENTS = "成就"
CMD_TITLE_LIST = "称号列表"
CMD_SET_TITLE = "佩戴称号"
CMD_PVP = "偷袭"
CMD_LEADERBOARD = "排行榜"
CMD_RESPAWN = "重生"
CMD_HELP = "帮助"
CMD_WEATHER = "天气"
CMD_LLM_STATUS = "llm状态"
CMD_LLM_TOGGLE = "llm开关"
CMD_LLM_RATIO = "llm比例"
# 中文别名
CMD_LLM_STATUS_CN = "大模型状态"
CMD_LLM_TOGGLE_CN = "大模型开关"
CMD_LLM_RATIO_CN = "大模型比例"


class SurvivorPlugin(Star):
    """
    末日生存游戏插件

    指令列表：
    - 开始生存 [名字] [职业]         开始游戏（必须选择职业）
    - 探索 / 行动                   执行一次探索行动
    - 选择 [1-4]                    选择事件选项
    - 状态 / 我的状态                查看当前状态
    - 背包 / 物品                    查看背包和资源
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

    def __init__(self, context: Context = None, config: AstrBotConfig = None):
        """初始化插件"""
        super().__init__(context)
        self.context = context
        self.config = config if config else {}

        # 插件元数据（AstrBot Star 系统通过属性读取）
        self.name = "astrbot_plugin_survivor"
        self.desc = "末日生存文字游戏 v2.6 - 基础资源可合成、配方按分类展示、材料支持资源池消耗"
        self.author = "AdeleNaumann"
        self.version = "v2.6.0"

        # 线程安全锁（保护定时器线程与主线程的数据读写）
        self._data_lock = threading.RLock()

        # 解析并确保数据目录存在（优先使用 AstrBot 持久化目录）
        self.data_dir = _resolve_data_dir(self.name)
        self.save_file = os.path.join(self.data_dir, "save_data.json")
        os.makedirs(self.data_dir, exist_ok=True)

        # 旧数据迁移：如果旧位置有存档而新位置没有，则复制过来
        self._migrate_old_save()

        # 初始化游戏内容
        init_all_content()

        # 创建游戏引擎
        self.engine = SurvivorEngine()

        # 加载存档
        self._load_data()

        # 启动每日结算定时器
        self._daily_timer_running = True
        self._start_daily_timer()

        try:
            logger.info("[Survivor] 末日生存游戏插件已加载！")
        except NameError:
            print("[Survivor] 末日生存游戏插件已加载！")

    async def initialize(self):
        """Star 插件初始化钩子（异步），在此启动后台定时任务"""
        # 尝试启用 LLM 事件生成
        await self._init_llm_events()

    # ================================================================
    # 兜底监听：等待起名 + 数字选择（当有待处理事件时）
    # ================================================================

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_message(self, event: AstrMessageEvent):
        """
        Catch-all 兜底：
        1. 如果玩家正在等待起名，任何群消息都作为名字处理
        2. 如果玩家有待处理选择，数字 1-4 也作为选择处理
        其他消息交给 @filter.command 处理
        """
        try:
            user_id = str(event.get_sender_id())
            group_id = str(event.get_group_id())
            msg = (event.message_str or "").strip()
            if not msg or not user_id or not group_id:
                return

            # 等待起名状态 —— 任何消息都作为名字
            if self.engine.has_pending_name(user_id, group_id):
                event.stop_event()
                result = self._cmd_set_name(user_id, group_id, msg)
                yield event.plain_result(result)
                return

            # 数字选择（当玩家有待处理选择事件时）
            if msg in ("1", "2", "3", "4") and self.engine.has_pending_choice(user_id, group_id):
                event.stop_event()
                result = self._cmd_choice(user_id, group_id, int(msg))
                yield event.plain_result(result)
                return

            # LLM 指令（混英文命令名 @filter.command 匹配有问题，在这里兜底）
            if msg == "llm状态":
                event.stop_event()
                if not self._is_admin(user_id):
                    yield event.plain_result(self.NO_ADMIN_MSG)
                else:
                    yield event.plain_result(self._cmd_llm_status())
                return
            if msg == "llm开关":
                event.stop_event()
                if not self._is_admin(user_id):
                    yield event.plain_result(self.NO_ADMIN_MSG)
                else:
                    yield event.plain_result(self._cmd_llm_toggle())
                return
            if msg == "llm比例" or msg.startswith("llm比例 "):
                event.stop_event()
                if not self._is_admin(user_id):
                    yield event.plain_result(self.NO_ADMIN_MSG)
                else:
                    ratio_str = msg.replace("llm比例", "", 1).strip()
                    yield event.plain_result(self._cmd_llm_ratio(ratio_str))
                return

        except Exception as e:
            traceback.print_exc()
            yield event.plain_result(f"⚠️ 插件错误：{str(e)}")

    # ================================================================
    # @filter.command 指令处理 —— 每个游戏指令独立注册
    # ================================================================

    @filter.command(CMD_START, "开始生存，创建角色（必须选择职业）")
    async def handle_start(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id())
        nickname = event.get_sender_name() or ""
        # 提取参数: "开始生存 张三分 战士" → args="张三分 战士"
        msg = (event.message_str or "").strip()
        args = msg[len("开始生存"):].strip() if msg.startswith("开始生存") else ""
        result = self._cmd_start(user_id, group_id, nickname, args=args if args else None)
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_EXPLORE, "外出探索，触发随机事件")
    async def handle_explore(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id())
        result = self._cmd_explore(user_id, group_id)
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_CHOOSE, "在事件中做出选择")
    async def handle_choose(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id())
        msg = (event.message_str or "").strip()
        match = re.match(r'^选择\s*(\d+)', msg)
        choice_idx = int(match.group(1)) if match else 0
        result = self._cmd_choice(user_id, group_id, choice_idx) if choice_idx else "⚠️ 请输入「选择 数字」，例如「选择 1」"
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_STATUS, "查看生存状态")
    async def handle_status(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id())
        result = self._cmd_status(user_id, group_id)
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_INVENTORY, "查看背包物品")
    async def handle_inventory(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id())
        result = self._cmd_inventory(user_id, group_id)
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_BUILD_LIST, "查看可建造建筑")
    async def handle_build_list(self, event: AstrMessageEvent):
        result = self._cmd_build_list()
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_BUILD, "建造或升级建筑")
    async def handle_build(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id())
        building_name = (event.message_str or "").replace("建造", "", 1).strip()
        if not building_name:
            result = "⚠️ 请输入「建造 [建筑名]」，例如「建造 避难所」"
        else:
            result = self._cmd_build(user_id, group_id, building_name)
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_RECIPE, "查看合成配方")
    async def handle_recipe(self, event: AstrMessageEvent):
        result = self._cmd_recipe_list()
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_CRAFT, "合成物品")
    async def handle_craft(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id())
        parts = (event.message_str or "").replace("合成", "", 1).strip().split()
        if not parts:
            result = "⚠️ 请输入「合成 [物品名] [数量]」"
        else:
            item_name = parts[0]
            count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
            result = self._cmd_craft(user_id, group_id, item_name, count)
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_USE, "使用消耗品")
    async def handle_use_item(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id())
        item_name = (event.message_str or "").replace("使用", "", 1).strip()
        if not item_name:
            result = "⚠️ 请输入「使用 [物品名]」"
        else:
            result = self._cmd_use_item(user_id, group_id, item_name)
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_EQUIP, "装备武器或防具")
    async def handle_equip(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id())
        item_name = (event.message_str or "").replace("装备", "", 1).strip()
        if not item_name:
            result = "⚠️ 请输入「装备 [物品名]」"
        else:
            result = self._cmd_equip_item(user_id, group_id, item_name)
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_CLASS_LIST, "查看可选职业")
    async def handle_class_list(self, event: AstrMessageEvent):
        result = self._cmd_class_list()
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_SKILL_LIST, "查看技能列表")
    async def handle_skill_list(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id())
        result = self._cmd_skill_list(user_id, group_id)
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_UPGRADE_SKILL, "升级技能")
    async def handle_upgrade_skill(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id())
        skill_name = (event.message_str or "").replace("升级技能", "", 1).strip()
        if not skill_name:
            result = "⚠️ 请输入「升级技能 [技能名]」"
        else:
            result = self._cmd_upgrade_skill(user_id, group_id, skill_name)
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_ACHIEVEMENTS, "查看成就")
    async def handle_achievements(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id())
        result = self._cmd_achievements(user_id, group_id)
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_TITLE_LIST, "查看已解锁称号")
    async def handle_title_list(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id())
        result = self._cmd_title_list(user_id, group_id)
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_SET_TITLE, "佩戴称号")
    async def handle_set_title(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id())
        title = (event.message_str or "").replace("佩戴称号", "", 1).strip()
        if not title:
            result = "⚠️ 请输入「佩戴称号 [称号名]」，或「佩戴称号 取消」取消称号"
        else:
            result = self._cmd_set_title(user_id, group_id, title)
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_PVP, "偷袭其他玩家")
    async def handle_pvp(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id())
        # 优先从 @mention 提取目标 QQ 号
        at_qq = self._extract_at_target(event)
        if at_qq:
            # 排除@自己的情况（需要从 message_str 回退）
            if at_qq == user_id:
                result = "⚠️ 你不能偷袭自己！"
            else:
                result = self._cmd_pvp(user_id, group_id, at_qq)
        else:
            # 未 @ 任何人，从文本中提取目标
            target_info = (event.message_str or "").replace("偷袭", "", 1).strip()
            if not target_info:
                result = "⚠️ 请输入「偷袭 [玩家名/QQ号]」或直接 @ 对方，例如「偷袭 @某人」"
            else:
                result = self._cmd_pvp(user_id, group_id, target_info)
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_LEADERBOARD, "查看群内生存排行")
    async def handle_leaderboard(self, event: AstrMessageEvent):
        group_id = str(event.get_group_id())
        result = self._cmd_leaderboard(group_id)
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_RESPAWN, "死亡后重生")
    async def handle_respawn(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id())
        nickname = event.get_sender_name() or ""
        result = self._cmd_respawn(user_id, group_id, nickname)
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_HELP, "显示帮助信息")
    async def handle_help(self, event: AstrMessageEvent):
        result = self._cmd_help()
        event.stop_event()
        yield event.plain_result(result)

    @filter.command(CMD_WEATHER, "查看天气和世界状态")
    async def handle_weather(self, event: AstrMessageEvent):
        group_id = str(event.get_group_id())
        result = self._cmd_world_status(group_id)
        event.stop_event()
        yield event.plain_result(result)

    # LLM 指令统一在 catch-all 中处理（混英文命令名 @filter.command 匹配有问题）
    @filter.command(CMD_LLM_STATUS_CN, "查看大模型事件状态")
    async def handle_llm_status_cn(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        event.stop_event()
        if not self._is_admin(user_id):
            yield event.plain_result(self.NO_ADMIN_MSG)
        else:
            yield event.plain_result(self._cmd_llm_status())

    @filter.command(CMD_LLM_TOGGLE_CN, "开关大模型事件生成")
    async def handle_llm_toggle_cn(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        event.stop_event()
        if not self._is_admin(user_id):
            yield event.plain_result(self.NO_ADMIN_MSG)
        else:
            yield event.plain_result(self._cmd_llm_toggle())

    @filter.command(CMD_LLM_RATIO_CN, "设置大模型事件比例")
    async def handle_llm_ratio_cn(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        msg = (event.message_str or "").strip()
        parts = msg.replace("大模型比例", "", 1).strip().split()
        ratio_str = parts[0] if parts else ""
        event.stop_event()
        if not self._is_admin(user_id):
            yield event.plain_result(self.NO_ADMIN_MSG)
        else:
            yield event.plain_result(self._cmd_llm_ratio(ratio_str))

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

        # 必须带名字
        if not custom_name:
            return (
                f"🏚️ ===== 末日生存 =====\n"
                f"欢迎来到末日世界，幸存者！\n"
                f"\n"
                f"⚠️ 请使用「开始生存 [名字] [职业]」来创建角色\n"
                f"💡 使用「职业列表」查看可选职业\n"
                f"\n"
                f"⚠️ 名字和职业一旦确定将无法更改！\n"
                f"⚠️ 必须选择一个职业才能开始生存！"
            )

        # 必须选职业
        if not player_class:
            classes = ClassRegistry.get_all()
            class_list = "\n".join(
                f"  • {c['name']}（{c['id']}）：{c.get('description', '')}"
                for c in classes.values()
            )
            return (
                f"⚠️ 必须选择一个职业才能开始生存！\n"
                f"\n"
                f"可选职业：\n"
                f"{class_list}\n"
                f"\n"
                f"请使用「开始生存 {custom_name} [职业]」重新开始\n"
                f"例如：「开始生存 {custom_name} 拾荒者」"
            )

        return self._create_new_player(user_id, group_id, custom_name, player_class)

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
            f"💡 使用「背包」查看你的初始物资\n"
            f"💡 使用「状态」查看你的生存状态\n"
            f"💡 使用「探索」开始你的第一次行动\n"
            f"💡 使用「帮助」查看所有指令"
        )

    def _cmd_explore(self, user_id: str, group_id: str) -> str:
        """探索行动"""
        player = self.engine.get_player(user_id, group_id)
        if not player:
            return "⚠️ 你还没有开始生存！请先使用「开始生存 [名字] [职业]」创建角色。"

        can_act, reason = self.engine.can_act(player)
        if not can_act:
            return reason

        group = self.engine.ensure_group(group_id)
        result = self.engine.do_action(player, group)

        if result["type"] == "empty":
            return result["message"]

        # 构建事件消息
        is_llm = result.get('event_id', '').startswith('llm_')
        llm_badge = " 🤖AI生成" if is_llm else ""
        lines = [
            f"🎲 ===== 探索结果{llm_badge} =====",
            f"📌 {result['event_name']}",
            f"",
            f"📝 {result['description']}",
        ]

        if result["auto"]:
            lines.append(f"")
            lines.append(result["auto_message"])
            lines.append(f"")
            lines.append(f"🍖 饱食 -{EXPLORE_HUNGER_COST} | 💧 口渴 -{EXPLORE_THIRST_COST}（每次探索消耗）")
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

        # 检查待处理事件是否为 LLM 生成
        pending = self.engine._get_pending_choice(user_id, group_id)
        is_llm = (pending is not None and pending.get("event") is not None
                  and pending["event"].id.startswith("llm_"))

        result = self.engine.handle_choice(player, choice_index)

        if result["type"] == "error":
            return result["message"]

        llm_badge = " 🤖AI生成" if is_llm else ""
        lines = [f"📋 ===== 行动结果{llm_badge} ====="]

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
        lines.append(f"🍖 饱食 -{EXPLORE_HUNGER_COST} | 💧 口渴 -{EXPLORE_THIRST_COST}（每次探索消耗）")

        if player.status == "dead":
            lines.append(f"")
            lines.append(f"💀 你死了...使用「重生」重新开始。")

        # 有实质性数据变更后保存
        self._save_data()

        return "\n".join(lines)

    def _cmd_status(self, user_id: str, group_id: str) -> str:
        """查看状态"""
        player = self.engine.get_player(user_id, group_id)
        if not player:
            return "⚠️ 你还没有开始生存！请先使用「开始生存 [名字] [职业]」创建角色。"

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

        # 离线升级通知（兼容旧版存档无此字段）
        offline_level_notice = ""
        offline_levels = getattr(player, "unread_level_ups", 0)
        if offline_levels > 0:
            offline_level_notice = (
                f"🎉 离线期间自动搜集升级了 {offline_levels} 次！"
                f"当前 Lv.{player.level}，获得 {offline_levels * 2} 个技能点。\n"
            )
            object.__setattr__(player, "unread_level_ups", 0)

        lines = [
            f"{emoji} ===== {player.nickname or '幸存者'}{title_str} 的状态 =====",
            f"",
            class_info,
        ]
        if offline_level_notice:
            lines.append(offline_level_notice)
            lines.append("")
        lines.extend([
            f"📊 等级: Lv.{player.level} | 经验: {player.exp}/{player.level * 100}",
            f"⭐ 技能点: {player.skill_points}",
            f"❤️ 生命: {player.health}/{player.max_health}",
            f"🍖 饱食度: {player.hunger}/100",
            f"💧 口渴度: {player.thirst}/100",
            f"🧠 理智值: {player.sanity}/100",
            f"⚔️ 攻击: {player.attack} | 🛡️ 防御: {player.defense}",
        ])

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
            season_names = {"spring": "🌸春季", "summer": "☀️夏季", "autumn": "🍂秋季", "winter": "❄️冬季"}
            lines.append(f"🌍 世界第 {group.current_day} 天 | {season_names.get(group.current_season, group.current_season)} | 危险等级 {'⭐' * group.danger_level}")
            lines.append(f"⏳ 全自动搜集中 · 每游戏天自动入账")

        return "\n".join(lines)

    def _cmd_inventory(self, user_id: str, group_id: str) -> str:
        """查看背包"""
        player = self.engine.get_player(user_id, group_id)
        if not player:
            return "⚠️ 你还没有开始生存！"

        lines = ["🎒 ===== 背包物品 =====", ""]

        # 基础资源（放在背包最前面）
        res_display = {"food": ("🍖", "食物"), "water": ("💧", "水"), "wood": ("🪵", "木材"),
                       "stone": ("🪨", "石料"), "iron": ("🔩", "铁"), "medicine": ("💊", "药品"),
                       "ammo": ("🔫", "弹药"), "fuel": ("⛽", "燃料")}
        has_resources = any(player.resources.get(r, 0) > 0 for r in res_display)
        if has_resources:
            lines.append("📦 基础资源：")
            for res_id, (icon, name) in res_display.items():
                amount = player.resources.get(res_id, 0)
                if amount > 0:
                    lines.append(f"  {icon} {name} x{amount}")
            lines.append("")

        if not player.inventory:
            if has_resources:
                lines.append("💡 你的物品栏暂时没有道具。")
            else:
                return "🎒 你的背包是空的。"
            return "\n".join(lines)

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
                    rarity_cn = {"common": "普通", "uncommon": "稀有", "rare": "精良", "epic": "史诗", "legendary": "传说"}
                    cat_items.append(f"  {item.name} x{count} ({rarity_cn.get(item.rarity, item.rarity)})")
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

            # 格式化建造消耗（区分资源和物品）
            res_icons = {"food": "🍖食物", "water": "💧水", "wood": "🪵木材", "stone": "🪨石料",
                        "iron": "🔩铁", "medicine": "💊药品", "ammo": "🔫弹药", "fuel": "⛽燃料"}
            cost_parts = []
            for k, v in building.build_cost.items():
                if k in res_icons:
                    cost_parts.append(f"{res_icons[k]}x{v}")
                else:
                    item = ItemRegistry.get(k)
                    cost_parts.append(f"{(item.name if item else k)}x{v}")
            lines.append(f"   建造消耗: {'  '.join(cost_parts)}")

            # 格式化效果描述
            effect_text = self._format_building_effect(building.effect_per_level)
            lines.append(f"   每级效果: {effect_text}")
            lines.append("")

        lines.append("💡 使用「建造 [建筑名]」来建造或升级")
        return "\n".join(lines)

    @staticmethod
    def _format_building_effect(effects: dict) -> str:
        """将建筑效果 dict 转为可读文本"""
        mapping = {
            "defense": "防御+{v}",
            "max_health": "生命上限+{v}",
            "food_per_day": "每日食物+{v}",
            "water_per_day": "每日净水+{v}",
            "craft_speed": "制作速度+{p}%",
            "scout_range": "侦查范围+{v}",
            "storage_bonus": "存储上限+{v}",
            "heal_per_day": "每日治疗+{v}",
            "ammo_per_day": "每日弹药+{v}",
        }
        parts = []
        for k, v in effects.items():
            fmt = mapping.get(k, "{k}+{v}")
            text = fmt.replace("{k}", k).replace("{v}", str(int(v)) if v == int(v) else str(v))
            text = text.replace("{p}", str(int(v * 100)) if v < 1 else str(int(v)))
            parts.append(text)
        return "，".join(parts) if parts else "无"

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

        self._save_data()

        # 展示消耗
        res_icons = {"food": "🍖食物", "water": "💧水", "wood": "🪵木材", "stone": "🪨石料",
                    "iron": "🔩铁", "medicine": "💊药品", "ammo": "🔫弹药", "fuel": "⛽燃料"}
        cost_parts = []
        for k, v in result["cost"].items():
            if k in res_icons:
                cost_parts.append(f"{res_icons[k]}x{v}")
            else:
                item = ItemRegistry.get(k)
                cost_parts.append(f"{(item.name if item else k)}x{v}")
        return (
            f"{result['message']}\n"
            f"消耗: {'  '.join(cost_parts)}\n"
            f"💡 使用「状态」查看你的建筑情况。"
        )

    @staticmethod
    def _item_name(item_id: str) -> str:
        """获取物品中文名（优先注册表，fallback 到内置映射）"""
        return ItemRegistry.get_name(item_id)

    def _format_recipe_entry(self, item_id, recipe, item):
        """格式化单条配方条目"""
        item_name = item.name if item else self._item_name(item_id)
        parts = []
        for res_key, res_amt in recipe.get("resource_costs", {}).items():
            parts.append(f"{self._item_name(res_key)} ×{res_amt}")
        for mid, amt in recipe["materials"].items():
            parts.append(f"{self._item_name(mid)} ×{amt}")
        mat_str = " + ".join(parts)
        req = ""
        if recipe.get("required_building"):
            bld = BuildingRegistry.get(recipe["required_building"])
            req = f" [需要{bld.name if bld else recipe['required_building']} Lv.{recipe['min_level']}]"
        return f"  📌 {item_name}{req}\n     材料: {mat_str}"

    def _cmd_recipe_list(self) -> str:
        """查看合成配方"""
        # 诊断：输出已注册数量，方便确认代码版本
        recipe_count = len(RecipeRegistry.get_all())
        item_count = len(ItemRegistry.get_all())
        res_items = [i for i in ItemRegistry.get_all() if i.category == ItemCategory.RESOURCE]
        lines = [
            f"🔨 ===== 合成配方 (注册配方:{recipe_count}, 物品:{item_count}, 资源项:{len(res_items)}) =====",
            ""
        ]

        # 手动维护：基础生存物品（不需要工坊即可合成的日常补给）
        survival_ids = {"bottled_water", "canned_food", "rusty_knife", "rope"}

        # 按产出分类分组
        category_order = [
            ("survival", "🍞 生存补给"),
            (ItemCategory.WEAPON, "⚔️ 武器"),
            (ItemCategory.ARMOR, "🛡️ 防具"),
            (ItemCategory.CONSUMABLE, "🍖 消耗品"),
            (ItemCategory.RESOURCE, "⛏️ 基础资源"),
            (ItemCategory.MATERIAL, "🔧 材料/工具"),
            (ItemCategory.SPECIAL, "📦 特殊"),
        ]

        # 按分类归组（生存补给手动提取）
        grouped = {}
        survival_recipes = []
        for item_id, recipe in RecipeRegistry.get_all().items():
            if item_id in survival_ids:
                item = ItemRegistry.get(item_id)
                survival_recipes.append((item_id, recipe, item))
                continue
            item = ItemRegistry.get(item_id)
            cat = item.category if item else ItemCategory.MATERIAL
            grouped.setdefault(cat, []).append((item_id, recipe, item))

        # 按顺序输出
        for cat, label in category_order:
            if cat is None:
                continue
            if cat == "survival":
                entries = survival_recipes
            else:
                entries = grouped.pop(cat, [])
            if not entries:
                continue
            lines.append(label)
            lines.append("─" * 20)
            for item_id, recipe, item in entries:
                lines.append(self._format_recipe_entry(item_id, recipe, item))
            lines.append("")

        # 兜底：未归类配方
        if grouped:
            lines.append("📦 其他")
            lines.append("─" * 20)
            for _cat, recipes_in_cat in grouped.items():
                for item_id, recipe, item in recipes_in_cat:
                    lines.append(self._format_recipe_entry(item_id, recipe, item))
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
        if result.get("type") == "success":
            self._save_data()
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

    def _cmd_equip_item(self, user_id: str, group_id: str, item_name: str) -> str:
        """装备武器或防具（只允许武器和防具类别）"""
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

        item = ItemRegistry.get(item_id)
        if item and item.category not in (ItemCategory.WEAPON, ItemCategory.ARMOR):
            return f"⚠️ 「{item.name}」不是武器或防具，无法装备。请使用「使用 [物品名]」来使用消耗品。"

        result = self.engine.use_item(player, item_id)
        if result.get("type") == "success":
            self._save_data()
        return result["message"]

    def _cmd_leaderboard(self, group_id: str) -> str:
        """查看排行榜"""
        players = self.engine._players.get(group_id, {})
        if not players:
            return "📊 本群还没有幸存者！使用「开始生存 [名字] [职业]」加入吧。"

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
            return "🌍 这个世界还没有幸存者...使用「开始生存 [名字] [职业]」创造历史吧！"

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

    NO_ADMIN_MSG = "⚠️ 只有管理员才能使用 LLM 指令。请在插件配置中设置管理员 QQ。"

    def _is_admin(self, user_id: str) -> bool:
        """检查用户是否为管理员。未配置管理员时允许所有人使用。"""
        admin_list = self.config.get("admin_qq", [])
        if not admin_list:
            return True  # 未配置管理员名单时，允许所有人使用（向后兼容）
        return str(user_id) in [str(a) for a in admin_list]

    def _cmd_llm_status(self) -> str:
        """查看 LLM 事件生成状态"""
        enabled = self.engine.llm_enabled
        ratio = self.engine.llm_event_ratio
        cache = llm_events.cache_size()

        if not enabled:
            return (
                f"🤖 ===== LLM 事件生成 =====\n"
                f"\n"
                f"❌ 状态：已禁用\n"
                f"\n"
                f"📋 说明：插件启动时会自动检测 AstrBot 的大模型是否可用。\n"
                f"   如果 AstrBot 能正常 AI 聊天，这里就能工作。\n"
                f"   使用「llm开关」可手动启用/禁用。\n"
                f"   使用「llm比例 [10-100]」调整 LLM 事件出现概率。"
            )

        return (
            f"🤖 ===== LLM 事件生成 =====\n"
            f"\n"
            f"✅ 状态：已启用\n"
            f"📊 替换比例：{int(ratio * 100)}%（探索时 {int(ratio * 100)}% 概率用大模型生成的事件，其余用内置事件）\n"
            f"📦 缓存事件：{cache} 个（上限 {llm_events.MAX_CACHE_SIZE}，不足 {llm_events.REFILL_THRESHOLD} 时补充）\n"
            f"🔄 每天自动补充一次，补满至 {llm_events.MAX_CACHE_SIZE} 个\n"
            f"\n"
            f"💡 使用「llm开关」禁用/启用\n"
            f"💡 使用「llm比例 [10-100]」调整出现概率\n"
            f"💡 LLM 事件更丰富多样，有 2 分钟调用冷却防止频繁请求"
        )

    def _cmd_llm_toggle(self) -> str:
        """开关 LLM 事件生成"""
        # 如果是关闭状态且想开启，需要检查是否有 provider
        if not self.engine.llm_enabled:
            self.engine.llm_enabled = True
            return (
                f"🤖 LLM 事件生成已 ✅ 启用\n"
                f"   替换比例：{int(self.engine.llm_event_ratio * 100)}%\n"
                f"   如果 AstrBot 未配置大模型，将自动降级为内置事件。"
            )
        else:
            self.engine.llm_enabled = False
            return (
                f"🤖 LLM 事件生成已 ❌ 禁用\n"
                f"   现在探索只会使用内置事件。\n"
                f"   使用「llm开关」可重新启用。"
            )

    def _cmd_llm_ratio(self, ratio_str: str) -> str:
        """设置 LLM 事件替换比例"""
        if not ratio_str:
            current = int(self.engine.llm_event_ratio * 100)
            return (
                f"🤖 当前 LLM 事件替换比例：{current}%\n"
                f"   使用「llm比例 [10-100]」调整，例如「llm比例 50」"
            )

        try:
            val = int(ratio_str)
        except ValueError:
            return "⚠️ 请输入有效数字，例如「llm比例 50」"

        if val < 0 or val > 100:
            return "⚠️ 比例范围 0-100，0 表示完全不使用 LLM 事件（等同于关闭）"

        self.engine.llm_event_ratio = val / 100.0

        if val == 0:
            return (
                f"🤖 LLM 事件替换比例已设为 0%\n"
                f"   实际上等同于关闭 LLM 事件生成。\n"
                f"   使用「llm开关」或设回大于 0 的值可重新启用。"
            )

        return (
            f"🤖 LLM 事件替换比例已设为 {val}%\n"
            f"   现在探索时有约 {val}% 概率使用大模型生成的事件。\n"
            f"   建议范围 20-50%，太高会增加 API 调用频率。"
        )

    def _cmd_help(self) -> str:
        """帮助信息"""
        return (
            f"🏚️ ===== 末日生存 v2.6 帮助 =====\n"
            f"\n"
            f"🎮 基础操作：\n"
            f"  · 开始生存 [名字] [职业] - 创建角色\n"
            f"  · 探索 - 外出搜索，触发随机事件（额外收益）\n"
            f"  · 选择 [数字] - 在事件中做出选择\n"
            f"  · 状态 - 查看生存状态\n"
            f"  · 背包 - 查看背包物品和资源\n"
            f"  · 使用 [物品名] - 使用消耗品\n"
            f"  · 装备 [物品名] - 装备武器或防具\n"
            f"  · 帮助 - 显示本帮助\n"
            f"\n"
            f"👤 职业系统：\n"
            f"  · 职业列表 - 查看可选职业\n"
            f"  · 6种职业各有独特加成（也影响每日自动搜集收益）\n"
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
            f"  · 偷袭 [玩家名/QQ号] - 偷袭其他玩家（支持 @对方）\n"
            f"  · 胜利可抢夺对方资源和物品\n"
            f"  · 冷却10分钟，新手保护2小时\n"
            f"\n"
            f"🌤️ 天气系统：\n"
            f"  · 天气 - 查看当前天气\n"
            f"  · 不同天气影响探索事件\n"
            f"\n"
            f"🤖 LLM 事件生成（需 AstrBot 已配置大模型）：\n"
            f"  · llm状态 - 查看 LLM 事件生成状态\n"
            f"  · llm开关 - 启用/禁用大模型事件\n"
            f"  · llm比例 [10-100] - 设置 LLM 事件出现概率\n"
            f"  · 启用后约 35% 的探索事件由 AI 生成，每天补充 300 个\n"
            f"\n"
            f"📊 其他：\n"
            f"  · 排行榜 - 群内排行\n"
            f"  · 重生 - 死亡后重新开始\n"
            f"\n"
            f"⏱️ 机制说明：\n"
            f"  · 全自动搜集：创建角色后每游戏天自动入账，无需任何操作\n"
            f"  · 探索是额外收益方式，可主动触发随机事件\n"
            f"  · 每次探索消耗 🍖饱食{EXPLORE_HUNGER_COST} 💧口渴{EXPLORE_THIRST_COST}，无冷却时间\n"
            f"  · 每1小时结算一个游戏天\n"
            f"  · 建筑每日自动产出资源\n"
            f"  · 天气随机变化，影响探索体验"
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

    def _extract_at_target(self, event):
        """从消息事件中提取 @mention 的第一个目标 QQ 号。未 @ 任何人时返回 None。"""
        try:
            messages = event.get_messages()
        except Exception:
            # 非 AstrBot 环境（开发/测试）容错
            return None
        for comp in messages:
            if At is not None and isinstance(comp, At):
                return str(comp.qq)
        return None

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

        # PvP 修改了双方数据，立即保存
        self._save_data()

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
            if result.get("ammo_msg"):
                lines.append("")
                lines.append(result["ammo_msg"])

            return "\n".join(lines)

        else:
            ammo_line = f"\n{result['ammo_msg']}\n" if result.get("ammo_msg") else ""
            return (
                f"💥 ===== 偷袭失败！ =====\n"
                f"\n"
                f"你偷袭 {result['target_display']} 失败了！（胜率 {result['win_chance']:.0%}）\n"
                f"反被造成了 {result['damage_taken']} 点伤害！{ammo_line}"
                f"{'💀 你已死亡！使用「重生」重新开始。' if result.get('attacker_died') else ''}"
            )

    async def _init_llm_events(self):
        """初始化 LLM 事件生成器：直接用 AstrBot 内置大模型尝试生成，成功则启用"""
        if not self.context:
            self.engine.llm_enabled = False
            return

        # 不手动检测 provider，让 AstrBot 自己决定用哪个 LLM
        self.engine.llm_enabled = True
        self.engine.llm_event_ratio = 0.35  # 35% 概率使用 LLM 事件

        try:
            logger.info("[Survivor] 正在检测大模型可用性...")
        except NameError:
            print("[Survivor] 正在检测大模型可用性...")

        # 直接尝试生成一个事件来验证 LLM 是否可用
        n = await self._refill_llm_events()
        if n > 0:
            try:
                logger.info(f"[Survivor] 大模型事件生成已启用（占比 35%），缓存 {llm_events.cache_size()} 个事件")
            except NameError:
                print(f"[Survivor] 大模型事件生成已启用（占比 35%），缓存 {llm_events.cache_size()} 个事件")
            # 启动后台定期补充
            asyncio.create_task(self._llm_refill_loop())
        else:
            self.engine.llm_enabled = False
            try:
                logger.info("[Survivor] 大模型不可用，事件生成已降级为内置事件。如已配置 LLM，请检查 AstrBot 设置。")
            except NameError:
                print("[Survivor] 大模型不可用，事件生成已降级为内置事件。如已配置 LLM，请检查 AstrBot 设置。")

    async def _refill_llm_events(self):
        """补充 LLM 事件缓存，每次补到 MAX_CACHE_SIZE（300）"""
        if not self.engine.llm_enabled or not self.context:
            return 0

        current = llm_events.cache_size()
        if current >= llm_events.MAX_CACHE_SIZE:
            return 0

        print(f"[Survivor] 开始补充 LLM 事件缓存... (当前 {current}/{llm_events.MAX_CACHE_SIZE})")

        # 获取一个群组的状态作为背景
        groups = self.engine._groups
        if groups:
            group_id = next(iter(groups))
            group = groups[group_id]
        else:
            # 没有群组时使用默认状态
            from models import GroupGameState
            group = GroupGameState(group_id="default")

        total_added = 0
        # 循环生成直到缓存满或失败
        while llm_events.cache_size() < llm_events.MAX_CACHE_SIZE:
            n = await llm_events.generate_batch(
                self.context,
                season=group.current_season,
                weather=group.weather,
                danger_level=group.danger_level,
                day=group.current_day,
                force=True,  # 跳过冷却，允许批量补充
            )
            if n <= 0:
                break  # LLM 调用失败则停止
            total_added += n
            # 批次间短暂间隔，避免频繁请求
            await asyncio.sleep(3)

        if total_added > 0:
            try:
                logger.info(f"[Survivor] LLM 补充了 {total_added} 个事件，缓存总数: {llm_events.cache_size()}")
            except NameError:
                print(f"[Survivor] LLM 补充了 {total_added} 个事件，缓存总数: {llm_events.cache_size()}")
        else:
            print(f"[Survivor] ⚠️ LLM 事件补充失败或无需补充 (缓存 {llm_events.cache_size()} 个)")

        return total_added

    async def _llm_refill_loop(self):
        """后台循环：每 24 小时补充一次 LLM 事件缓存到 300 个"""
        while self.engine.llm_enabled:
            await asyncio.sleep(86400)  # 每 24 小时（一天）检查一次
            if not self.engine.llm_enabled:
                break
            await self._refill_llm_events()

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
        with self._data_lock:
            for group_id in list(self.engine._groups.keys()):
                try:
                    self.engine.daily_tick(group_id)
                except Exception as e:
                    print(f"[Survivor] 群 {group_id} 每日结算失败: {e}")

            self._save_data_nolock()

    # ================================================================
    # 数据持久化
    # ================================================================

    def _migrate_old_save(self):
        """将旧位置的存档迁移到新的 AstrBot 持久化目录"""
        old_dir = os.path.join(os.path.dirname(__file__), "data")
        old_file = os.path.join(old_dir, "save_data.json")
        if os.path.isfile(old_file) and not os.path.exists(self.save_file):
            try:
                import shutil
                shutil.copy2(old_file, self.save_file)
                print(f"[Survivor] 已从旧目录迁移存档: {old_file} → {self.save_file}")
            except Exception as e:
                print(f"[Survivor] 迁移旧存档失败: {e}")

    def _load_data(self):
        """加载存档"""
        try:
            if os.path.exists(self.save_file):
                with open(self.save_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.engine.import_data(data)
                print(f"[Survivor] 存档已加载: {self.save_file}")
        except Exception as e:
            print(f"[Survivor] 加载存档失败: {e}")

    def _save_data_nolock(self):
        """保存存档（调用者必须持有 self._data_lock）"""
        try:
            data = self.engine.export_data()
            with open(self.save_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Survivor] 保存存档失败: {e}")

    def _save_data(self):
        """保存存档（带锁，线程安全）"""
        with self._data_lock:
            self._save_data_nolock()

    # ================================================================
    # 生命周期
    # ================================================================

    async def terminate(self):
        """插件卸载时保存数据并停止定时器"""
        self._daily_timer_running = False
        self._save_data()
