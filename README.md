# 🏚️ 末日生存 - AstrBot 文字游戏插件

一个以末日生存为主题的 QQ 群文字游戏插件，偏向挂机玩法，支持建造、合成、探索、战斗等系统。

## ✨ 特性

- 🎮 **多事件选择系统** - 探索触发随机事件，每个事件有多个选项
- 🏗️ **建造系统** - 建造农场、水井、工坊等建筑，每日自动产出
- 🔨 **合成系统** - 收集材料，合成武器、防具、消耗品
- ⚔️ **战斗系统** - 遭遇丧尸、掠夺者，进行回合制战斗
- 📊 **技能系统** - 5种技能树，提升战斗、生存、搜索等能力
- 🌍 **世界演化** - 游戏天数推进、季节更替、危险等级递增
- ⏱️ **挂机友好** - 30秒行动冷却，每小时自动结算每日消耗和建筑产出
- 💾 **自动存档** - 数据持久化，重启不丢失
- 🔌 **高可扩展性** - 注册表模式，新增物品/事件/建筑只需添加配置

## 📁 项目结构

```
astrbot_plugin_survivor/
├── metadata.yaml          # 插件元信息
├── requirements.txt       # 依赖
├── main.py                # 插件主类 (AstrBot 入口)
├── models.py              # 数据模型定义
├── content.py             # 游戏内容注册表 (物品、事件、建筑等)
├── engine.py              # 核心游戏引擎
├── README.md              # 本文件
└── data/
    └── save_data.json     # 存档数据 (自动生成)
```

## 🚀 安装

```bash
# 在 AstrBot 中使用插件安装指令
plugin i https://github.com/yourname/astrbot_plugin_survivor.git
```

或手动放入 `addons/plugins/astrbot_plugin_survivor/` 目录。

## 🎮 指令列表

### 基础操作
| 指令 | 说明 |
|------|------|
| `开始生存` | 创建角色，开始游戏 |
| `探索` / `行动` | 外出探索，触发随机事件 |
| `选择 [数字]` | 在事件中做出选择 |
| `状态` | 查看生存状态 |
| `背包` | 查看背包物品 |
| `帮助` | 显示完整帮助 |

### 建造系统
| 指令 | 说明 |
|------|------|
| `建造列表` | 查看可建造建筑 |
| `建造 [名称]` | 建造或升级建筑 |

### 合成系统
| 指令 | 说明 |
|------|------|
| `配方` | 查看合成配方 |
| `合成 [名称] [数量]` | 合成物品 |

### 物品使用
| 指令 | 说明 |
|------|------|
| `使用 [名称]` | 使用消耗品 |
| `装备 [名称]` | 装备武器或防具 |

### 其他
| 指令 | 说明 |
|------|------|
| `排行榜` | 查看群内排行 |
| `世界状态` | 查看世界进度 |
| `重生` | 死亡后重新开始 |

## 🏗️ 建筑一览

| 建筑 | 效果 |
|------|------|
| 避难所 | 提高防御和生命上限 |
| 农场 | 每日产出食物 |
| 水井 | 每日产出净水 |
| 工坊 | 解锁高级合成配方 |
| 瞭望塔 | 提高预警，减少被突袭概率 |
| 仓库 | 扩大存储上限 |
| 医疗站 | 每日自动恢复生命 |

## 🔌 扩展指南

项目采用**注册表模式 (Registry Pattern)**，新增内容非常简单：

### 添加新物品

在 `content.py` 的 `init_default_items()` 中添加：

```python
ItemRegistry.register(Item(
    id="new_sword", name="新武器", category=ItemCategory.WEAPON,
    description="一把新武器", attack_bonus=30, rarity="epic"
))
```

### 添加新事件

在 `content.py` 的 `init_default_events()` 中添加：

```python
EventRegistry.register(GameEvent(
    id="new_event", name="新事件",
    event_type=EventType.RESOURCE, weight=2.0,
    description="你遇到了一个新事件！",
    choices=[
        {
            "text": "选项1",
            "result": {
                "resources": {"food": (5, 10)},
                "description": "你获得了一些食物。"
            }
        },
    ]
))
```

### 添加新建筑

在 `content.py` 的 `init_default_buildings()` 中添加：

```python
BuildingRegistry.register(Building(
    id="new_building", name="新建筑", building_type=BuildingType.SHELTER,
    description="一个新建筑", level=0, max_level=5,
    build_cost={"wood": 20, "stone": 10},
    effect_per_level={"defense": 2}
))
```

### 添加新技能

在 `content.py` 的 `init_default_skills()` 中添加：

```python
SkillRegistry.register(Skill(
    id="new_skill", name="新技能",
    description="技能描述", max_level=10,
    effect_per_level={"attack": 1.5}
))
```

### 添加合成配方

在 `content.py` 的 `init_default_recipes()` 中添加：

```python
RecipeRegistry.register(
    "result_item_id", {"material1": 3, "material2": 2},
    description="制作描述", required_building="workshop", min_level=2
)
```

## 📝 待扩展功能

以下是可以后续添加的功能方向：

- [ ] PvP 系统 - 玩家之间互相掠夺
- [ ] 联盟系统 - 多人合作建造大型建筑
- [ ] 更多事件类型 - 探索废墟、解救幸存者等
- [ ] 宠物系统 - 驯服变异生物
- [ ] 科技树 - 解锁更高级的科技
- [ ] 天气灾害 - 酸雨、辐射风暴等
- [ ] 商人系统 - 动态定价交易
- [ ] 成就系统 - 解锁成就获得奖励

## 📄 许可

MIT License
