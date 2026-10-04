#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地个人工作台服务（仅 Python 标准库，零第三方依赖）
====================================================
- 只绑定 127.0.0.1，仅本机可访问，不上云、不同步
- 提供 REST API：任务 / 项目 / 资料文件夹 / Obsidian 笔记 / 打开文件夹 / 目录浏览 / 配置 / 备份
- 业务数据保存在 ./data/*.json（已被 .gitignore 忽略）
- 启动后自动打开浏览器

本工作台为本地运行方案（用户明确要求不使用云端同步）。
"""
import json
import os
import re
import sys
import threading
import urllib.parse
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ---------------- 基础路径与配置 ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
INDEX_HTML = os.path.join(BASE_DIR, "index.html")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

HOST = "127.0.0.1"
DEFAULT_PORT = 8765

DEFAULT_CONFIG = {
    "obsidian_vault": r"D:\DappFile\Obsidian1.10.6\UpdateWork\Obsidian_to_WorkBuddy_Project",
    "port": DEFAULT_PORT
}

os.makedirs(DATA_DIR, exist_ok=True)


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    # 环境变量优先（.env 说明见 .env.example），其次 config.json
    env_vault = os.environ.get("OBSIDIAN_VAULT")
    env_port = os.environ.get("WORKSPACE_PORT")
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:
            log("配置读取失败，使用默认配置: %s" % e)
    if env_vault:
        cfg["obsidian_vault"] = env_vault
    if env_port:
        try:
            cfg["port"] = int(env_port)
        except ValueError:
            pass
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg), flush=True)


# ---------------- 数据存取（data/*.json） ----------------
def _data_file(name):
    return os.path.join(DATA_DIR, name + ".json")


def load_data(name, default):
    p = _data_file(name)
    if not os.path.exists(p):
        return default
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log("数据读取失败 %s: %s" % (name, e))
        return default


def save_data(name, obj):
    p = _data_file(name)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def uid():
    return "id-" + datetime.now().strftime("%Y%m%d%H%M%S%f")


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


# ---------------- 文件夹 / 路径工具 ----------------
def sanitize_name(name):
    """去掉 Windows 文件名非法字符与首尾空白"""
    name = (name or "").strip()
    name = re.sub(r'[\\/:*?"<>|]', "-", name)
    name = re.sub(r"\s+", " ", name)
    return name[:80]


def abs_path(p):
    """规整为绝对路径并展开用户目录"""
    p = (p or "").strip().strip('"')
    p = os.path.expandvars(os.path.expanduser(p))
    return os.path.abspath(p)


def list_drives():
    import string
    drives = []
    for c in string.ascii_uppercase:
        d = c + ":\\"
        if os.path.exists(d):
            drives.append(d)
    return drives


def list_subdirs(path):
    """列出某目录下的子文件夹（跳过隐藏/系统目录）"""
    result = []
    try:
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            if os.path.isdir(full) and not name.startswith((".", "$")):
                result.append(name)
    except PermissionError:
        pass
    except FileNotFoundError:
        return None
    return result


def scan_vault(vault):
    """扫描 Obsidian 库：顶层文件夹 + 最近修改的 md 笔记"""
    out = {"folders": [], "recent": []}
    if not vault or not os.path.isdir(vault):
        return out
    out["folders"] = [n for n in list_subdirs(vault) or [] if not n.startswith(".")]
    items = []
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in files:
            if fn.lower().endswith(".md"):
                full = os.path.join(root, fn)
                try:
                    st = os.stat(full)
                    items.append({
                        "name": fn[:-3],
                        "folder": os.path.relpath(root, vault),
                        "mtime": int(st.st_mtime),
                        "mtimeStr": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
                    })
                except OSError:
                    pass
    items.sort(key=lambda x: -x["mtime"])
    out["recent"] = items[:40]
    return out


# ---------------- 示例数据（首次运行预置，可一键清空） ----------------
def seed_if_empty():
    tasks = load_data("tasks", None)
    if tasks is None:
        t = today_str()
        # 逾期示例：截止日设为昨天
        y, m, d = map(int, t.split("-"))
        import datetime as _dt
        yesterday = (_dt.date(y, m, d) - _dt.timedelta(days=1)).strftime("%Y-%m-%d")
        tasks = [
            {"id": uid(), "title": "整理 BOM 表并核对物料库存", "priority": "P0",
             "due": yesterday, "status": "待办", "projectId": "", "createdAt": now_str(), "sample": True},
            {"id": uid(), "title": "编写 SSD 高低温测试报告", "priority": "P1",
             "due": t, "status": "进行中", "projectId": "", "createdAt": now_str(), "sample": True},
            {"id": uid(), "title": "归档上批次 RMA 返修记录", "priority": "P2",
             "due": "", "status": "待办", "projectId": "", "createdAt": now_str(), "sample": True},
        ]
        save_data("tasks", tasks)
        log("已预置示例任务 3 条")
    projects = load_data("projects", None)
    if projects is None:
        projects = [
            {"id": uid(), "name": "示例-SSD 固件升级验证", "parentPath": "", "folderPath": "",
             "status": "进行中", "createdAt": now_str(), "completedAt": "", "sample": True},
            {"id": uid(), "name": "示例-老化测试治具改造", "parentPath": "", "folderPath": "",
             "status": "已完结", "createdAt": now_str(), "completedAt": now_str(), "sample": True},
        ]
        save_data("projects", projects)
        log("已预置示例项目 2 个")
    resources = load_data("resources", None)
    if resources is None:
        resources = [
            {"id": uid(), "name": "示例-测试数据", "parentPath": "", "folderPath": "",
             "category": "测试数据", "createdAt": now_str(), "sample": True},
            {"id": uid(), "name": "示例-维修记录", "parentPath": "", "folderPath": "",
             "category": "维修记录", "createdAt": now_str(), "sample": True},
        ]
        save_data("resources", resources)
        log("已预置示例资料 2 条")


# ---------------- HTTP 服务 ----------------
class Handler(BaseHTTPRequestHandler):
    server_version = "LocalWorkbench/1.0"

    # ---------- 响应工具 ----------
    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _ok(self, data=None):
        self._json({"ok": True, "data": data or {}})

    def _err(self, msg, status=400):
        self._json({"ok": False, "error": str(msg)}, status)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def log_message(self, fmt, *args):
        pass  # 静默默认访问日志

    # ---------- GET ----------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        route = parsed.path
        cfg = load_config()
        if route == "/" or route == "/index.html":
            if os.path.exists(INDEX_HTML):
                with open(INDEX_HTML, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            else:
                self._err("index.html 缺失", 500)
        elif route == "/api/state":
            data = {
                "tasks": load_data("tasks", []),
                "projects": load_data("projects", []),
                "resources": load_data("resources", []),
                "config": {
                    "obsidian_vault": cfg.get("obsidian_vault", ""),
                    "vaultOk": bool(cfg.get("obsidian_vault")) and os.path.isdir(cfg.get("obsidian_vault", "")),
                    "port": cfg.get("port", DEFAULT_PORT)
                },
                "vault": scan_vault(cfg.get("obsidian_vault", "")),
                "today": today_str()
            }
            self._ok(data)
        elif route == "/api/export":
            # 整站备份（不含 Obsidian 与磁盘文件夹本身）
            payload = {
                "exportedAt": now_str(),
                "tasks": load_data("tasks", []),
                "projects": load_data("projects", []),
                "resources": load_data("resources", []),
                "config": {"obsidian_vault": cfg.get("obsidian_vault", "")}
            }
            body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=workbench-backup.json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self._err("未知接口: " + route, 404)

    # ---------- POST ----------
    def do_POST(self):
        try:
            self._route_post()
        except Exception as e:
            log("接口异常: %s" % e)
            self._err("服务内部错误: " + str(e), 500)

    def _route_post(self):
        route = urllib.parse.urlparse(self.path).path
        b = self._body()
        action = b.get("action", "")

        if route == "/api/task":
            return self._handle_task(b, action)
        if route == "/api/project":
            return self._handle_project(b, action)
        if route == "/api/resource":
            return self._handle_resource(b, action)
        if route == "/api/note":
            return self._handle_note(b, action)
        if route == "/api/open":
            return self._handle_open(b)
        if route == "/api/browse":
            return self._handle_browse(b)
        if route == "/api/config":
            return self._handle_config(b, action)
        if route == "/api/clear-sample":
            return self._handle_clear_sample()
        self._err("未知接口: " + route, 404)

    # ----- 任务 -----
    def _handle_task(self, b, action):
        tasks = load_data("tasks", [])
        if action == "add":
            title = (b.get("title") or "").strip()
            if not title:
                return self._err("任务标题不能为空")
            task = {
                "id": uid(), "title": title,
                "priority": b.get("priority") or "P1",
                "due": (b.get("due") or "").strip(),
                "status": b.get("status") or "待办",
                "projectId": b.get("projectId") or "",
                "createdAt": now_str(), "sample": False
            }
            tasks.insert(0, task)
            save_data("tasks", tasks)
            return self._ok(task)
        if action == "update":
            tid = b.get("id")
            for t in tasks:
                if t["id"] == tid:
                    for k in ("title", "priority", "due", "status", "projectId"):
                        if k in b and b[k] is not None:
                            t[k] = b[k]
                    if b.get("status") == "已完成" and not t.get("completedAt"):
                        t["completedAt"] = now_str()
                    if b.get("status") and b["status"] != "已完成":
                        t["completedAt"] = ""
                    save_data("tasks", tasks)
                    return self._ok(t)
            return self._err("任务不存在", 404)
        if action == "delete":
            tasks = [t for t in tasks if t["id"] != b.get("id")]
            save_data("tasks", tasks)
            return self._ok()
        return self._err("未知 action: " + action)

    # ----- 项目 -----
    def _handle_project(self, b, action):
        projects = load_data("projects", [])
        if action == "add":
            name = sanitize_name(b.get("name"))
            if not name:
                return self._err("项目名称不能为空")
            parent = abs_path(b.get("parentPath") or "")
            folder_path = ""
            created = False
            if parent:
                if not os.path.isdir(parent):
                    return self._err("父路径不存在，请检查: " + parent)
                folder_path = os.path.join(parent, name)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                    created = True
                elif not os.path.isdir(folder_path):
                    return self._err("同名路径已存在且不是文件夹: " + folder_path)
            else:
                # 示例/未指定路径的项目，仅记录
                folder_path = ""
            proj = {
                "id": uid(), "name": name,
                "parentPath": parent, "folderPath": folder_path,
                "status": b.get("status") or "进行中",
                "createdAt": now_str(), "completedAt": "", "sample": False,
                "folderCreated": created
            }
            projects.insert(0, proj)
            save_data("projects", projects)
            msg = "已创建项目文件夹: " + folder_path if created else "已记录项目（未创建文件夹）"
            return self._ok({"project": proj, "message": msg})
        if action == "update_status":
            for p in projects:
                if p["id"] == b.get("id"):
                    p["status"] = b.get("status") or p["status"]
                    p["completedAt"] = now_str() if p["status"] == "已完结" else ""
                    save_data("projects", projects)
                    return self._ok(p)
            return self._err("项目不存在", 404)
        if action == "update":
            for p in projects:
                if p["id"] == b.get("id"):
                    if b.get("name"):
                        p["name"] = sanitize_name(b["name"])
                    if "parentPath" in b:
                        p["parentPath"] = abs_path(b.get("parentPath") or "")
                    save_data("projects", projects)
                    return self._ok(p)
            return self._err("项目不存在", 404)
        if action == "delete":
            projects = [p for p in projects if p["id"] != b.get("id")]
            save_data("projects", projects)
            return self._ok()
        return self._err("未知 action: " + action)

    # ----- 数据资料 -----
    def _handle_resource(self, b, action):
        resources = load_data("resources", [])
        if action == "add":
            name = sanitize_name(b.get("name"))
            if not name:
                return self._err("文件夹名称不能为空")
            parent = abs_path(b.get("parentPath") or "")
            if not parent:
                return self._err("请指定存放路径")
            if not os.path.isdir(parent):
                return self._err("路径不存在，请检查: " + parent)
            folder_path = os.path.join(parent, name)
            created = False
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                created = True
            res = {
                "id": uid(), "name": name,
                "parentPath": parent, "folderPath": folder_path,
                "category": b.get("category") or "其他",
                "createdAt": now_str(), "sample": False, "folderCreated": created
            }
            resources.insert(0, res)
            save_data("resources", resources)
            return self._ok({"resource": res, "message": ("已创建文件夹: " if created else "文件夹已存在，已记录: ") + folder_path})
        if action == "delete":
            resources = [r for r in resources if r["id"] != b.get("id")]
            save_data("resources", resources)
            return self._ok()
        return self._err("未知 action: " + action)

    # ----- 笔记（写入 Obsidian 库） -----
    def _handle_note(self, b, action):
        cfg = load_config()
        vault = cfg.get("obsidian_vault", "")
        if not vault or not os.path.isdir(vault):
            return self._err("尚未配置有效的 Obsidian 库路径，请到「个人中心」设置")
        if action == "add":
            title = sanitize_name(b.get("title"))
            if not title:
                return self._err("笔记标题不能为空")
            folder = (b.get("folder") or "").strip()
            folder = re.sub(r'[\\/:*?"<>|]', "-", folder) if folder else "03 项目任务"
            target_dir = os.path.join(vault, folder)
            os.makedirs(target_dir, exist_ok=True)
            filename = "%s %s.md" % (today_str(), title)
            full = os.path.join(target_dir, filename)
            content = b.get("content") or ""
            front = (
                "---\n"
                "title: %s\n"
                "date: %s\n"
                "source: 本地工作台\n"
                "---\n\n" % (title, now_str())
            )
            if os.path.exists(full) and not b.get("overwrite"):
                return self._json({"ok": False, "error": "同名笔记已存在: " + filename, "exists": True}, 409)
            with open(full, "w", encoding="utf-8") as f:
                f.write(front + content.strip() + "\n")
            return self._ok({"path": full, "message": "笔记已写入 Obsidian: " + os.path.relpath(full, vault)})
        return self._err("未知 action: " + action)

    # ----- 打开文件夹/文件（进入资源管理器） -----
    def _handle_open(self, b):
        p = abs_path(b.get("path") or "")
        if not p or not os.path.exists(p):
            return self._err("路径不存在: " + p)
        try:
            if sys.platform == "win32":
                os.startfile(p)  # noqa 打开文件夹=进入该文件夹
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", p])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", p])
            log("已打开: " + p)
            return self._ok({"path": p})
        except Exception as e:
            return self._err("打开失败: " + str(e))

    # ----- 目录浏览（路径选择器） -----
    def _handle_browse(self, b):
        raw = (b.get("path") or "").strip()
        if not raw:
            return self._ok({"path": "", "parent": "", "dirs": list_drives(), "drives": True})
        p = abs_path(raw)
        if not os.path.isdir(p):
            return self._err("目录不存在: " + p)
        parent = os.path.dirname(p) if os.path.dirname(p) != p else ""
        return self._ok({"path": p, "parent": parent, "dirs": list_subdirs(p) or [], "drives": False})

    # ----- 配置 -----
    def _handle_config(self, b, action):
        cfg = load_config()
        if action == "save":
            if "obsidian_vault" in b:
                v = abs_path(b.get("obsidian_vault"))
                if v and not os.path.isdir(v):
                    return self._err("Obsidian 库路径不存在: " + v)
                cfg["obsidian_vault"] = v
            if b.get("port"):
                try:
                    cfg["port"] = int(b["port"])
                except ValueError:
                    pass
            save_config(cfg)
            return self._ok({"config": {"obsidian_vault": cfg.get("obsidian_vault", ""),
                                        "vaultOk": os.path.isdir(cfg.get("obsidian_vault", ""))},
                             "message": "配置已保存（端口修改需重启服务生效）"})
        return self._err("未知 action: " + action)

    # ----- 清空示例 -----
    def _handle_clear_sample(self):
        for name in ("tasks", "projects", "resources"):
            items = load_data(name, [])
            items = [x for x in items if not x.get("sample")]
            save_data(name, items)
        return self._ok({"message": "示例数据已清空（真实数据保留）"})


def find_free_port(start):
    """端口被占用时向后自动寻找可用端口"""
    import socket
    port = start
    for _ in range(30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((HOST, port))
                return port
            except OSError:
                port += 1
    return start


def main():
    cfg = load_config()
    seed_if_empty()
    port = find_free_port(int(cfg.get("port", DEFAULT_PORT)))
    httpd = ThreadingHTTPServer((HOST, port), Handler)
    url = "http://%s:%d" % (HOST, port)
    print("=" * 56, flush=True)
    print("  本地个人工作台已启动（仅本机可访问）", flush=True)
    print("  地址: %s" % url, flush=True)
    if port != int(cfg.get("port", DEFAULT_PORT)):
        print("  （默认端口被占用，已自动改用 %d）" % port, flush=True)
    print("  数据目录: %s" % DATA_DIR, flush=True)
    print("  关闭请直接关闭本窗口或按 Ctrl+C", flush=True)
    print("=" * 56, flush=True)
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log("服务已停止")


if __name__ == "__main__":
    main()
