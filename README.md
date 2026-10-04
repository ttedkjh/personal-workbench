# 本地个人工作台（LocalWorkbench）

为硬件工程师定制的本机工作台：任务清单 / 项目工程 / 数据资料管理 / 知识笔记（Obsidian 直写）/ 个人中心。
**只在本机运行，不联网、不上云、不同步**；业务数据保存在本地 JSON 文件中。

## 功能

| 板块 | 说明 |
|---|---|
| 任务清单 | 待办任务（P0/P1/P2 优先级、截止日、关联项目），逾期/今日到期自动置顶标红，显示进行中的项目 |
| 项目工程 | 新建项目 = 在指定路径创建同名文件夹；显示进行中/已完结；「打开文件夹」即进入该项目目录 |
| 数据资料管理 | 新建文件夹归类存放测试数据、维修记录等，可分类筛选、一键打开 |
| 知识笔记 | Markdown 直写 Obsidian 库（可选目标文件夹），Obsidian 内即时可见，列出最近笔记 |
| 个人中心 | 工作统计、Obsidian 库路径设置、JSON 备份导出、清空示例、迁移与 Git 说明 |

## 快速开始

1. 安装 Python 3.8+（安装时勾选 **Add Python to PATH**）
2. 双击 `start.bat` —— 自动启动服务并打开浏览器（`http://127.0.0.1:8765`）
3. 首次运行会预置示例数据（含 1 条逾期任务），可在「个人中心 → 清空示例数据」一键清除

> 只依赖 Python 标准库，**无需 pip 安装任何第三方包**。
> 可先双击 `install.bat` 做环境自检。

## 迁移到其他电脑

1. 把整个 `LocalWorkbench` 文件夹拷贝到目标电脑（U盘/网盘均可）
2. 目标电脑装好 Python 3.8+
3. 双击 `start.bat` —— 数据随 `data\` 文件夹一起迁移，环境依赖零安装

> 安全性：服务只绑定 `127.0.0.1`，局域网内其他设备无法访问。

## 版本管理（GitHub）

仓库已配置好忽略规则，可直接 `git init` 并推送：

```
git init
git add .
git commit -m "init: 本地个人工作台"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

**.gitignore 已忽略（不会进仓库）：**

| 忽略项 | 原因 |
|---|---|
| `data/` | 业务数据（任务/项目/资料记录），属个人数据 |
| `config.json` | 含本机磁盘路径（Obsidian 库路径等敏感配置） |
| `.env` | 敏感环境变量（若使用） |
| `__pycache__/`、`*.pyc` | Python 运行产物 |

**敏感配置处理：**

- `config.example.json` 是配置模板（可提交），真实 `config.json` 不提交
- `.env.example` 是环境变量模板（可提交）；如需用环境变量覆盖配置，复制为 `.env` 并填写
- 优先级：系统环境变量 > `.env` 中变量 > `config.json`
- 其他电脑克隆后：复制 `config.example.json` 为 `config.json`（或在「个人中心」里设置 Obsidian 路径）即可

## 目录结构

```
LocalWorkbench/
├── app.py               # 本地服务（API + 页面托管），仅标准库
├── index.html           # 前端单文件（全内联，无外部依赖）
├── start.bat            # 一键启动（自动检测 Python）
├── install.bat          # 环境自检
├── config.json          # 真实配置（勿提交，首次运行自动生成）
├── config.example.json  # 配置模板
├── .env.example         # 环境变量模板说明
├── .gitignore           # Git 忽略规则
├── README.md
└── data/                # 业务数据（tasks/projects/resources.json，勿提交）
```

## 常见问题

- **端口被占用？** 服务会自动尝试 8765 起的后续端口，也可以在 `config.json` 里改 `port`
- **「打开文件夹」没反应？** 确认路径存在；示例数据没有真实路径，会提示无法打开
- **笔记没出现在 Obsidian？** 检查「个人中心」里的库路径是否有效（会显示 ✓/✗）
- **删除项目/资料记录会删文件夹吗？** 不会，只删工作台里的记录，磁盘文件始终安全
