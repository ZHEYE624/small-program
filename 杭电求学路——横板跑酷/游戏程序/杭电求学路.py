# -*- coding: utf-8 -*-
# 《杭电求学路》——原创 tkinter 横版跑酷：杭电学子按一日日程在五大校区地标间赶路上课，
# 零第三方依赖（禁用列表推导式）；落点含排序/查找/递归/恺撒/自定义异常/继承/文件。校训：笃学力行、守正求新
import json, math, os, random, time, tkinter as tk; from time import perf_counter
from tkinter import messagebox, simpledialog
try:
    import winsound                      # 仅 Windows 可用，用于简易音效
except ImportError:
    winsound = None
# ============ 一、常量配置 ============
TITLE = "杭电求学路"; WIDTH, HEIGHT = 960, 540; GROUND_Y = 460            # 地面基准线（玩家脚底 y）
FPS_MS = 10               # after() 心跳间隔（约 100 帧/秒目标，渲染速度取决于机器）
DT_CLAMP = 0.05           # dt 上限：切后台回来不会瞬移穿模
MAX_STEP = 8.0            # 碰撞子步进阈值
# 物理与体型按 1.3 倍等比放大：跳高/跳距同步放大，手感与可达性校验不变
GRAVITY, JUMP_V, RUN_V = 3120.0, 1170.0, 520.0   # 重力 / 起跳速度 / 水平速度
SAFE = 0.8                # 可达性校验安全系数
PLAYER_W, PLAYER_H, SLIDE_H = 44, 72, 36         # 站立与滑铲碰撞盒
PLAYER_SCREEN_X = 220; SEED = 1956; SAVE_FILE = "hdu_save.dat"
HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(HERE) == "__pycache__":     # 误从字节码缓存运行：回到游戏根目录找图片和存档
    HERE = os.path.dirname(HERE)
MAP_FILE = os.path.join(HERE, "地图底图.png")   # 选关底图：校区图隐去地名后生成
BG_DIR = os.path.join(HERE, "背景图")           # 关卡背景图目录（可选，PNG 格式）
# 五个地点在底图上的标注位置（宽高比例，顺序同 SCENES，取自画圈地图红圈质心）
LEVEL_POS = ((0.465, 0.867), (0.470, 0.619), (0.237, 0.575), (0.435, 0.165), (0.565, 0.280))
MOTTO, SCHOOL_MOTTO = "守正求新", "笃学力行、守正求新"
HDU_BLUE, HDU_GOLD = "#1e4d8c", "#f2c14e"; SOUND_ON = True

# 五个关卡 = 杭电学生的一天：沿用五大实景地标，各配一个"一天时段"小标题（name 用于背景图文件名）
SCENES = (
    {"name": "南大门", "title": "晨光启程", "note": "清晨 7:00 · 校门迎新", "sky": "#9fd0ef", "far": "#7fb3d5",
     "ground": "#6f8f5a", "need": 8, "limit": 62, "speed": 1.00},
    {"name": "问鼎广场", "title": "早八冲刺", "note": "上午 8:00 · 冲向教室", "sky": "#2b3f66", "far": "#3c5580",
     "ground": "#4f6f4a", "need": 12, "limit": 64, "speed": 1.10},
    {"name": "风雨操场", "title": "体测拼搏", "note": "上午 10:30 · 体育课", "sky": "#8dd0d8", "far": "#6fb6c1",
     "ground": "#5f8a6a", "need": 16, "limit": 66, "speed": 1.20},
    {"name": "寝室楼", "title": "午后小憩", "note": "午后 13:30 · 回生活区", "sky": "#f3c9a0", "far": "#e0a878",
     "ground": "#7a8f4f", "need": 20, "limit": 68, "speed": 1.30},
    {"name": "梅花餐厅", "title": "晚饭冲刺", "note": "傍晚 18:30 · 干饭上晚课", "sky": "#f7d9e3", "far": "#e6b3c7",
     "ground": "#6f9a5f", "need": 24, "limit": 72, "speed": 1.40},
)
DIFFICULTY = {"轻松": 0.88, "标准": 1.00, "硬核": 1.15}

# 障碍：宽 / 高 / 颜色 / 说明（hang 表示悬空低杆，必须滑铲通过）
OBSTACLES = {
    "闹钟": {"w": 52, "h": 56, "color": "#e8552d", "note": "早八闹钟"},
    "报告": {"w": 60, "h": 52, "color": "#b03a2e", "note": "实验报告DDL"},
    "跨栏": {"w": 44, "h": 72, "color": "#8e6e2f", "note": "体测跨栏"},
    "预警": {"w": 34, "h": 90, "color": "#7a1f1f", "note": "挂科预警（窄障碍）"},
    "低杆": {"w": 124, "h": 44, "color": "#4a6fa5", "note": "涵洞低杆·需滑铲", "hang": 44},
}
# 道具：半径 / 分值 / 颜色 / 特殊效果
ITEMS = {
    "学分": {"r": 17, "score": 1, "color": "#f2c14e", "effect": ""},
    "奖牌": {"r": 20, "score": 5, "color": "#d9a520", "effect": ""},
    "offer": {"r": 23, "score": 10, "color": "#2e8b57", "effect": ""},
    "饭票": {"r": 19, "score": 2, "color": "#e8875a", "effect": "shield"},
    "咖啡": {"r": 19, "score": 3, "color": "#6f4e37", "effect": "invincible"},
    "校徽": {"r": 26, "score": 20, "color": HDU_BLUE, "effect": "egg"},   # 校庆彩蛋道具（形似校徽）
}
# 地形块：(名称, 宽, 平台[(x,抬升,宽)], 障碍[(x,抬升,类型)], 道具[(x,抬升,类型)])
# 抬升 = 平台顶面距地高度；道具抬升"平台+45"跑过可拾，120~150 需起跳（跳跃奖励）
CHUNKS = (
    ("平坦大道", 400, ((0, 0, 400),), (), ((320, 45, "学分"),)),
    ("读书长廊", 560, ((0, 0, 560),), ((300, 0, "闹钟"),),
     ((150, 45, "学分"), (450, 45, "学分"))),
    ("月雅断桥", 460, ((0, 0, 170), (290, 0, 170)), (), ((230, 120, "学分"),)),
    ("一级台阶", 400, ((0, 0, 140), (140, 70, 260)), (), ((260, 110, "学分"),)),
    ("下坡捷径", 400, ((0, 90, 140), (140, 0, 260)), ((300, 0, "报告"),), ((220, 45, "饭票"),)),
    ("高台望远", 460, ((70, 0, 130), (200, 110, 260)), (), ((320, 150, "奖牌"),)),
    ("双子水坑", 640, ((0, 0, 140), (210, 0, 170), (470, 0, 170)), (),
     ((175, 120, "学分"), (555, 45, "学分"))),
    ("阶梯教室", 480, ((0, 0, 110), (110, 55, 120), (230, 110, 250)), (), ((330, 150, "学分"),)),
    ("涵洞低杆", 420, ((0, 0, 420),), ((210, 0, "低杆"),), ((320, 45, "咖啡"),)),
    ("体测跑道", 500, ((0, 0, 500),), ((180, 0, "跨栏"), (360, 0, "跨栏")), ((270, 45, "学分"),)),
    ("挂科预警", 460, ((0, 0, 460),), ((240, 0, "预警"),),
     ((160, 45, "学分"), (380, 140, "offer"))),
    ("终段冲刺", 420, ((0, 0, 420),), (), ((210, 45, "奖牌"),)),
)
# ============ 二、工具函数 ============
def log_err(msg):
    try:   # 图片等资源加载异常写入 debug.log，方便排查运行环境问题
        with open(os.path.join(HERE, "debug.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("[%Y-%m-%d %H:%M:%S] ") + msg + "\n")
    except Exception:
        pass
def jump_limit(vy=JUMP_V, g=GRAVITY, vx=RUN_V):
    """由物理参数推导跳跃能力 (跳高, 滞空, 跳距)，是可达性校验的理论基础"""
    return vy * vy / (2 * g), 2 * vy / g, vx * (2 * vy / g)
def caesar(text, shift=3, mode="encode"):
    """恺撒密码：移位思想推广到 Unicode 码位，故能加密含中文的存档（推广创新）"""
    if mode == "decode":
        shift = -shift
    out = []
    for ch in text:
        out.append(chr((ord(ch) + shift) % 65536))
    return "".join(out)
# 校庆彩蛋：第 5 关校徽道具，通关解恺撒谜题得 70 周年祝福。答案明文仅存程序、画面只给密文
EGG_ANS = "七秩风华"; EGG_CIPHER = caesar(EGG_ANS, 3)          # 恺撒加密的谜题密文（展示给玩家）
EGG_BLESS = "钱塘潮涌，七秩风华。\n感谢你把求学之路走完——愿你如杭电之芯，\n点亮家国，奔赴属于自己的星辰大海。"
class SaveCorruptedError(Exception):
    """自定义异常：存档损坏（解密失败或 JSON 解析失败）"""
def beep(freq=660, ms=40):
    """简易音效，未开启或系统不支持时静默跳过"""
    try:
        if SOUND_ON and winsound is not None:
            winsound.Beep(int(freq), int(ms))
    except Exception:
        pass
# ============ 三、四大排序（课堂所学）与顺序查找 ============
def bubble_sort(data):
    """冒泡排序：相邻比较交换，O(n²)"""
    a = list(data); n = len(a); c = 0; s = 0; i = 0
    while i < n - 1:
        j = 0
        while j < n - 1 - i:
            c += 1
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]; s += 1
            j += 1
        i += 1
    return a, c, s
def select_sort(data):
    """选择排序：每轮选最小值放到前面，O(n²)"""
    a = list(data); n = len(a); c = 0; s = 0; i = 0
    while i < n - 1:
        mi = i; j = i + 1
        while j < n:
            c += 1
            if a[j] < a[mi]:
                mi = j
            j += 1
        if mi != i:
            a[i], a[mi] = a[mi], a[i]; s += 1
        i += 1
    return a, c, s
def insert_sort(data):
    """插入排序：把元素插入已排序区，O(n²)，近乎有序时很快"""
    a = list(data); n = len(a); c = 0; s = 0; i = 1
    while i < n:
        key = a[i]; j = i - 1
        while j >= 0:
            c += 1
            if a[j] <= key:
                break
            a[j + 1] = a[j]; s += 1; j -= 1
        a[j + 1] = key; i += 1
    return a, c, s
def _quick_part(a, low, high, st):
    """快速排序的划分：取末元素为基准，小的放左边"""
    pivot = a[high]; i = low - 1; j = low
    while j < high:
        st[0] += 1
        if a[j] <= pivot:
            i += 1
            if i != j:
                a[i], a[j] = a[j], a[i]; st[1] += 1
        j += 1
    if i + 1 != high:
        a[i + 1], a[high] = a[high], a[i + 1]; st[1] += 1
    return i + 1
def _quick_rec(a, low, high, st):
    """快速排序主体：递归分治（课堂重点——递归）"""
    if low < high:
        p = _quick_part(a, low, high, st); _quick_rec(a, low, p - 1, st)
        _quick_rec(a, p + 1, high, st)
def quick_sort(data):
    """快速排序：分治 + 递归，平均 O(n log n)，排行榜实际使用"""
    a = list(data); st = [0, 0]; _quick_rec(a, 0, len(a) - 1, st)
    return a, st[0], st[1]
def seq_search(seq, key, keyfunc=None):
    """顺序（遍历）查找，返回下标，找不到返回 -1；障碍很少，O(n) 够用（课堂所学）"""
    i = 0
    while i < len(seq):
        v = keyfunc(seq[i]) if keyfunc is not None else seq[i]
        if v == key:
            return i
        i += 1
    return -1
# ============ 四、游戏对象类体系（class + 继承） ============
class GameObject(object):
    """所有游戏对象基类：统一世界坐标与 AABB 碰撞"""
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h; self.alive = True
    def hit(self, other):
        """AABB 轴对齐矩形碰撞检测"""
        return (self.x < other.x + other.w and self.x + self.w > other.x
                and self.y < other.y + other.h and self.y + self.h > other.y)
    def screen_x(self, cam_x):
        return self.x - cam_x
class Player(GameObject):
    """玩家：杭电学子"""
    def __init__(self, x, y):
        GameObject.__init__(self, x, y, PLAYER_W, PLAYER_H)
        self.vy, self.on_ground, self.jumps = 0.0, False, 0
        self.sliding, self.shield = False, False
        self.invincible, self.hurt, self.run_phase = 0.0, 0.0, 0.0
    def jump(self, max_jump=2):
        """跳跃：地面或空中二段跳。起跳前先恢复正常碰撞盒，
        否则滑铲中起跳会把矮盒子永久留在空中（卡身高 bug 根因）"""
        if self.jumps < max_jump:
            self.stop_slide(); self.vy = -JUMP_V; self.jumps += 1
            beep(880, 30); return True
        return False
    def start_slide(self):
        """滑铲：碰撞盒变矮，用于钻过涵洞低杆（仅贴地时可发动，空中按下无效）"""
        if not self.sliding and self.on_ground:
            self.sliding = True; self.y += PLAYER_H - SLIDE_H; self.h = SLIDE_H
    def stop_slide(self):
        """结束滑铲，恢复站立碰撞盒"""
        if self.sliding:
            self.sliding = False; self.y -= PLAYER_H - SLIDE_H; self.h = PLAYER_H
    def update_physics(self, dt):
        """重力与竖直位移"""
        self.vy += GRAVITY * dt; self.y += self.vy * dt
    def draw(self, cv, cam_x):
        sx, sy, h = self.screen_x(cam_x), self.y, self.h
        if self.hurt > 0 and int(self.hurt * 20) % 2 == 1:
            return                                   # 受击闪烁
        body = "#e74c3c" if self.invincible > 0 else HDU_BLUE
        swing = 8 if (self.on_ground and int(self.run_phase * 6) % 2 == 0) else (-8 if self.on_ground else 14)
        cv.create_line(sx + 12, sy + h - 16, sx + 12 + swing, sy + h - 2, fill=body, width=5)
        cv.create_line(sx + 20, sy + h - 16, sx + 20 - swing, sy + h - 2, fill=body, width=5)
        cv.create_rectangle(sx + 8, sy + 16, sx + 26, sy + h - 14, fill=body, outline="")
        cv.create_rectangle(sx + 2, sy + 20, sx + 10, sy + 38, fill="#7f8c8d", outline="")
        cv.create_oval(sx + 8, sy + 2, sx + 28, sy + 22, fill="#f5d6b3", outline="")
        cv.create_rectangle(sx + 6, sy - 2, sx + 30, sy + 6, fill="#2c3e50", outline="")
        cv.create_line(sx + 30, sy + 4, sx + 36, sy + 12, fill="#2c3e50", width=2)
        if self.invincible > 0:
            cv.create_oval(sx - 4, sy - 8, sx + self.w + 4, sy + h + 6, outline=HDU_GOLD, width=2)
        if self.shield:
            cv.create_oval(sx - 8, sy - 10, sx + self.w + 8, sy + h + 8, outline="#5dade2", width=3)
class Obstacle(GameObject):
    def __init__(self, x, top, kind):
        info = OBSTACLES[kind]; self.kind = kind
        self.hang = info.get("hang", 0)     # 悬空低杆挂离地 hang 处，其余贴地
        y = GROUND_Y - top - (self.hang + info["h"] if self.hang else info["h"])
        GameObject.__init__(self, x, y, info["w"], info["h"])
    def draw(self, cv, cam_x):
        sx, sy, w, h = self.screen_x(cam_x), self.y, self.w, self.h
        color = OBSTACLES[self.kind]["color"]
        # 警示化：黑底黄框 + 顶部感叹号，黄/橙描边交替闪烁，让陷阱一眼可辨
        edge = "#ffd400" if int(time.time() * 4) % 2 == 0 else "#ff7a1a"
        cv.create_rectangle(sx - 6, sy - 6, sx + w + 6, sy + h + 6,
                            fill="#1a1a1a", outline=edge, width=3)
        cv.create_polygon(sx + w / 2 - 12, sy - 12, sx + w / 2 + 12, sy - 12,
                          sx + w / 2, sy - 32, fill=edge, outline="#1a1a1a")
        cv.create_text(sx + w / 2, sy - 25, text="!", fill="#1a1a1a", font=("Arial", 13, "bold"))
        if self.kind == "闹钟":
            cv.create_oval(sx, sy + 10, sx + w, sy + h, fill=color, outline="")
            cv.create_arc(sx - 8, sy + 2, sx + 8, sy + 18, start=180, extent=180, fill=color, outline="")
            cv.create_arc(sx + w - 8, sy + 2, sx + w + 8, sy + 18, start=180, extent=180, fill=color, outline="")
        elif self.kind == "跨栏":
            cv.create_rectangle(sx, sy, sx + 6, sy + h, fill=color, outline="")
            cv.create_rectangle(sx + w - 6, sy, sx + w, sy + h, fill=color, outline="")
            cv.create_rectangle(sx, sy + h / 3, sx + w, sy + h / 3 + 6, fill=color, outline="")
        else:
            cv.create_rectangle(sx, sy, sx + w, sy + h, fill=color, outline="")
            tip = "DDL" if self.kind == "报告" else ("!" if self.kind == "预警" else "↓滑铲")
            cv.create_text(sx + w / 2, sy + h / 2, text=tip, fill="#fff", font=("Microsoft YaHei", 9, "bold"))
class Collectible(GameObject):
    def __init__(self, x, top, kind):
        info = ITEMS[kind]; r = info["r"]
        self.kind, self.score, self.effect, self.color = kind, info["score"], info["effect"], info["color"]
        self.top = top                  # 记录道具中心离地高度，便于生成后整理
        self.base_y = GROUND_Y - top - r; self.t = random.random() * 6.28
        GameObject.__init__(self, x - r, self.base_y, r * 2, r * 2)
    def float_update(self, dt):
        self.t += dt * 3; self.y = self.base_y + (3 if int(self.t) % 2 == 0 else -3)
    def draw(self, cv, cam_x):
        r = self.w / 2.0; cx, cy = self.screen_x(cam_x) + r, self.y + r
        if self.kind == "校徽":                       # 彩蛋道具：绘制迷你校徽
            draw_logo(cv, cx, cy, r)
            cv.create_oval(cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2,
                           outline="#ffd400", width=2)   # 金边提示可拾取
            return
        cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=self.color, outline="#fff")
        cv.create_text(cx, cy, text="OFFER" if self.kind == "offer" else self.kind,
                       fill="#fff", font=("Microsoft YaHei", 8, "bold"))
# ============ 五、关卡生成器（核心难点 A：保证随机地形 100% 可通过） ============
# 思路：地形拆成自带元数据的"地形块 chunk"，拼接时用玩家真实跳跃能力（物理推导的跳高/跳距）做可达性校验，接不上就重选，生成时即保证有解。
class LevelGenerator(object):
    def __init__(self, scene_idx, seed=SEED):
        self.rnd = random.Random(seed + scene_idx * 977); self.scene = SCENES[scene_idx]
        self.h_max, self.t_air, self.d_max = jump_limit()
        self.safe_h, self.safe_d = self.h_max * SAFE, self.d_max * SAFE
        self.platforms, self.obstacles, self.items = [], [], []
    def edges(self, chunk):
        """取地形块的首平台与末平台，用于拼接校验"""
        first = last = chunk[2][0]
        for p in chunk[2]:
            if p[0] < first[0]:
                first = p
            if p[0] + p[2] > last[0] + last[2]:
                last = p
        return first, last
    def can_link(self, prev, cur):
        """校验：能否从 prev 的出口跳到 cur 的入口。
        条件一（水平）跨越间隙 ≤ 安全跳距；条件二（竖直）需抬升高度 ≤ 安全跳高。"""; _, lprev = self.edges(prev)
        fcur, _ = self.edges(cur)
        gap = (lprev[0] + lprev[2]) - prev[1] + fcur[0]     # 上一块末端到本块首平台的空隙
        rise = fcur[1] - lprev[1]                           # 需抬升高度（正数=往上跳）
        if lprev[2] < 170 and (fcur[0] > 0 or fcur[2] < 170):
            return False    # 窄台出口若再跨坑或接窄台，300px 定距跳会飞越落点，真死局
        return gap <= self.safe_d and rise <= self.safe_h
    def internal_ok(self, chunk):
        """校验地形块内部：相邻平台之间也必须跳得过去"""
        plats, _, _ = insert_sort(chunk[2])      # 用课堂所学插入排序按 x 排好
        i = 0
        while i < len(plats) - 1:
            gap = plats[i + 1][0] - (plats[i][0] + plats[i][2])
            rise = plats[i + 1][1] - plats[i][1]
            if gap > self.safe_d or rise > self.safe_h:
                return False
            i += 1
        return True
    def add_chunk(self, chunk, base_x, last_ob_x):
        """把地形块铺到世界坐标 base_x 处，返回最后一个障碍的位置"""
        for (px, top, pw) in chunk[2]:
            self.platforms.append((base_x + px, top, pw))
        for (ox, otop, kind) in chunk[3]:
            wx = base_x + ox
            if wx - last_ob_x < 240:         # 陷阱更稀疏：留足反应+捡分空档，避免连续贴脸
                continue
            self.obstacles.append(Obstacle(wx, otop, kind)); last_ob_x = wx
        for (ix, itop, kind) in chunk[4]:
            self.items.append(Collectible(base_x + ix, itop, kind))
        return last_ob_x
    def drop_safe(self, ob_x):
        """跳过障碍后的落点区间 [障碍+160, 障碍+360] 是否全程有平台（防死局）"""
        pos = ob_x + 160
        while pos < ob_x + 360:
            covered = False
            for (px, top, pw) in self.platforms:
                if px <= pos <= px + pw:
                    covered = True
                    break
            if not covered:
                return False
            pos += 20
        return True
    def total_score(self):
        s = 0
        for it in self.items:
            s += it.score
        return s
    def plant(self, it, cx, top):
        it.top = top; it.x = cx - it.w / 2.0
        it.base_y = GROUND_Y - top - it.w / 2.0; it.y = it.base_y
    def space_items(self):
        """道具整理：保证"陷阱全可躲 + 道具全可拾"。低空道具若撞进贴地障碍的反应区，
        优先把它挪到该陷阱一侧 80px 的空地保持"跑过即拾"（易得分）；挪不开的普通障碍
        才上抬到弧线高度兜底，低杆两侧无空地则保持原位（滑铲通道本可拾）。"""
        def flat_at(cx):
            for (px, top, pw) in self.platforms:
                if top == 0 and px <= cx <= px + pw:
                    return True
            return False
        def free_at(cx):
            for o in self.obstacles:
                if o.x - 20 < cx < o.x + o.w + 20:
                    return False
            return True
        for it in self.items:
            if it.top > 80:                 # 高空奖励天然高于障碍，无需处理
                continue
            r = it.w / 2.0; hit = None
            for o in self.obstacles:        # 找与道具水平相撞/逼到眼前的同地面障碍
                if o.x <= it.x + it.w + 30 and o.x + o.w >= it.x - 30:
                    hit = o; break
            if hit is None:
                continue
            moved = False
            for cx in (hit.x + hit.w + 80, hit.x - 80):
                if flat_at(cx) and free_at(cx):
                    self.plant(it, cx, 45); moved = True; break
            if not moved and hit.kind != "低杆":   # 低杆两侧无空地就不动(滑铲通道本可拾)；
                self.plant(it, it.x + r, 150)      # 普通障碍挪不开才上抬到起跳高度兜底
    def build(self):
        need, flat, x, last_ob_x, prev = self.scene["need"], CHUNKS[0], 0, -999, None
        last_ob_x = self.add_chunk(flat, x, last_ob_x)      # 出生安全平台
        x += flat[1]; prev = flat; guard = 0
        while self.total_score() < need * 2.6 or guard < 9:   # 分数余量给足，收集更从容
            guard += 1
            if guard > 60:
                break
            cur = None
            for _ in range(10):                             # 挑一个接得上的地形块
                cand = self.rnd.choice(CHUNKS)
                if self.internal_ok(cand) and self.can_link(prev, cand):
                    cur = cand
                    break
            if cur is None:
                cur = flat                                  # 兜底：退回平地保证可通
            last_ob_x = self.add_chunk(cur, x, last_ob_x); x += cur[1]; prev = cur
        last_ob_x = self.add_chunk(CHUNKS[-1], x, last_ob_x); x += CHUNKS[-1][1]
        self.length, self.finish_x = x - 120, x - 200
        # 死局清理：跳过障碍后的落点必须有平台，否则直接移除该障碍
        safe = []
        for ob in self.obstacles:
            if self.drop_safe(ob.x):
                safe.append(ob)
        self.obstacles = safe; self.space_items()                 # 道具整理：消除"低空道具卡在障碍通道"的死角
        return self
# ============ 六、游戏主体 ============
class Game(object):
    def __init__(self, root):
        self.root = root; self.root.title(TITLE + " v3.1　|　" + SCHOOL_MOTTO)
        self.root.geometry("%dx%d" % (WIDTH, HEIGHT)); self.root.resizable(False, False)
        self.state = "MENU"                       # MENU/LEVELSEL/PLAYING/PAUSED/DEAD/WIN/CLEAR
        self.scene_idx, self.level_no = 0, 1
        self.difficulty, self.player_name = "标准", "杭电学子"
        self.lives, self.score, self.cam_x, self.time_left = 3, 0, 0.0, 0.0
        self.collected = set(); self.egg_obtained, self.egg_asked = False, False
        self.msg, self.msg_t, self.dead_reason = "", 0.0, ""; self.data = load_save()
        self.unlocked = 1   # 每次启动从第 1 关开始；本次运行通关解锁下一关（不依赖历史存档）
        self.map_img = self.bg_img = self.menu_img = None
        self.sel_tip, self.sel_tip_t = "", 0.0
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, highlightthickness=0, bg="#9fd0ef")
        self.canvas.pack(fill="both", expand=True); self.build_menu()
        self.root.bind("<KeyPress>", self.on_key_down)
        self.root.bind("<KeyRelease>", self.on_key_up); self.last_t = perf_counter()
        self.root.after(FPS_MS, self.tick)
    # -------- 菜单（课堂控件全家桶：Entry/Checkbutton/Button + lambda 回调） --------
    def build_menu(self):
        m = tk.Frame(self.root, bg="#ffffff"); m.place(relx=0.5, rely=0.56, anchor="center")
        self.menu = m
        tk.Label(m, text="杭 电 求 学 路", bg="#fff", fg=HDU_BLUE, font=("Microsoft YaHei", 24, "bold")).grid(row=0, column=0, columnspan=3)
        tk.Label(m, text="笃学力行、守正求新　·　杭电学子的求学一日", bg="#fff", fg="#555", font=("Microsoft YaHei", 10)).grid(row=1, column=0, columnspan=3, pady=(0, 10))
        tk.Label(m, text="昵称：", bg="#fff", font=("Microsoft YaHei", 10)).grid(row=2, column=0, sticky="e")
        self.name_var = tk.StringVar(value="杭电学子")
        tk.Entry(m, textvariable=self.name_var, width=16, font=("Microsoft YaHei", 10)).grid(row=2, column=1, sticky="w", pady=3)
        self.sound_var = tk.BooleanVar(value=True)
        tk.Checkbutton(m, text="开启音效", variable=self.sound_var, bg="#fff", font=("Microsoft YaHei", 9), command=self.sync_sound).grid(row=3, column=1, sticky="w", pady=3)
        # 启动自检：图片资源缺失时在菜单上醒目提示（拷贝游戏时请整个文件夹一起拷）
        miss = []
        if not os.path.exists(MAP_FILE):
            miss.append("地图底图.png")
        if not os.path.exists(BG_DIR):
            miss.append("背景图文件夹")
        if miss:
            tk.Label(m, text="缺少 " + "、".join(miss) + "：选关地图和关卡背景无法显示，请把游戏整个文件夹一起拷贝",
                     bg="#ffe9e9", fg="#c0392b", font=("Microsoft YaHei", 9)).grid(row=5, column=0, columnspan=3, pady=(4, 0))
        bf = tk.Frame(m, bg="#fff"); bf.grid(row=4, column=0, columnspan=3, pady=12)
        # 按钮回调大量使用 lambda 传参（课堂所学）
        tk.Button(bf, text="开始求学", width=12, bg=HDU_BLUE, fg="#fff", font=("Microsoft YaHei", 11, "bold"), command=self.show_levelsel).grid(row=0, column=0, padx=5)
        tk.Button(bf, text="游戏说明", width=10, font=("Microsoft YaHei", 10), command=self.show_help).grid(row=0, column=1, padx=5)
        tk.Button(bf, text="排行榜", width=10, font=("Microsoft YaHei", 10), command=lambda: RankBoard(self.root, self.data)).grid(row=1, column=0, padx=5, pady=6)
        tk.Button(bf, text="退　出", width=10, font=("Microsoft YaHei", 10), command=self.root.destroy).grid(row=2, column=0, columnspan=2, pady=6)
    def sync_sound(self):
        global SOUND_ON
        SOUND_ON = bool(self.sound_var.get())
    # -------- 键盘事件（bind，课件未讲，属同库自学延伸） --------
    def on_key_down(self, e):
        k = e.keysym
        if self.state == "PLAYING":
            if k in ("space", "Up", "w", "W"):
                self.player.jump()
            elif k in ("Down", "s", "S"):
                self.player.start_slide()
            elif k in ("Escape", "p", "P"):
                self.state = "PAUSED"; beep(392, 50)
        elif self.state == "PAUSED" and k in ("Escape", "p", "P"):
            self.state = "PLAYING"
        elif self.state in ("DEAD", "WIN", "CLEAR") and k in ("space", "Return"):
            if self.state == "WIN":
                self.next_level()
            elif self.state == "DEAD":
                self.retry()
            else:
                self.to_menu()
    def on_key_up(self, e):
        if e.keysym in ("Down", "s", "S") and self.state == "PLAYING":
            self.player.stop_slide()
    # -------- 关卡流程 --------
    def start_game(self, idx, diff):
        self.player_name = self.name_var.get().strip() or "杭电学子"
        self.difficulty = diff; self.sync_sound()
        self.scene_idx, self.level_no = idx, idx + 1; self.lives, self.score = 3, 0
        self.collected = set(); self.egg_obtained, self.egg_asked = False, False
        self.menu.place_forget(); self.build_level(); self.state = "PLAYING"
    def load_bg(self):
        base = os.path.join(BG_DIR, self.scene["name"])
        for path in (base + ".png", base + ".gif"):
            if not os.path.exists(path):
                continue
            try:
                return tk.PhotoImage(file=path)
            except Exception as e:
                log_err("背景加载失败 %s: %r" % (path, e))
        if not os.path.exists(base + ".png"):
            log_err("背景缺失: " + base + ".png")
        return None
    def build_level(self):
        gen = LevelGenerator(self.scene_idx).build()
        self.platforms, self.obstacles, self.items = gen.platforms, gen.obstacles, gen.items
        self.length, self.finish_x, self.scene = gen.length, gen.finish_x, gen.scene
        self.cam_x, self.time_left = 0.0, float(self.scene["limit"])
        self.player = Player(PLAYER_SCREEN_X, GROUND_Y - PLAYER_H)
        self.msg, self.msg_t = "", 0.0; self.bg_img = self.load_bg()
        self.level_start_score = self.score     # 过关按"本关得分"考核，而非累计分
        if self.scene_idx == len(SCENES) - 1: self.place_egg()   # 彩蛋仅最后一关：随机可拾不逼踩坑
    def place_egg(self):        # 只选贴地长空档、避开陷阱±90 缓冲的随机落点，保证跑过即拾
        cand = []
        for (px, top, pw) in self.platforms:
            if top:
                continue
            seg = [(px, px + pw)]
            for o in self.obstacles:
                lo, hi = o.x - 90, o.x + o.w + 90; nseg = []
                for (a, b) in seg:
                    if a < lo:
                        nseg.append((a, min(b, lo)))
                    if b > hi:
                        nseg.append((max(a, hi), b))
                seg = nseg
            for (a, b) in seg:
                if b - a >= 130:
                    cand.append(((a + b) / 2.0, top))
        if cand:
            cx, top = random.choice(cand)
            self.items.append(Collectible(cx, top, "校徽"))
    def level_score(self):
        return self.score - self.level_start_score
    def next_level(self):
        # 依次解锁下一地点（会话内：本次运行可连闯，退出重开回到第 1 关）；新一站重新给 3 次补考
        self.scene_idx += 1; self.level_no = self.scene_idx + 1
        if self.unlocked < self.scene_idx + 1:
            self.unlocked = self.scene_idx + 1
        if self.scene_idx >= len(SCENES):
            self.save_record(); self.state = "CLEAR"; return
        self.lives = 3
        self.build_level(); self.state = "PLAYING"
    def retry(self):
        # 失败重试：补考只被"撞障碍"消耗（on_hit 即时扣），掉坑/时间到/学分不足不扣也不重置 lives
        self.score = self.level_start_score
        self.collected = set(); self.egg_obtained = self.egg_asked = False
        self.build_level(); self.state = "PLAYING"
    def to_menu(self):
        self.state = "MENU"; self.menu.place(relx=0.5, rely=0.56, anchor="center")
    def resume(self):
        self.state = "PLAYING"
    # -------- 地图选关（LEVELSEL）：校区底图 + 可点击地名标签，依次解锁 --------
    def show_levelsel(self):
        self.state = "LEVELSEL"; self.menu.place_forget(); self.sel_tip = ""
        if self.map_img is not None:
            return
        for path in (MAP_FILE, os.path.splitext(MAP_FILE)[0] + ".gif"):
            if not os.path.exists(path):
                continue
            try:
                img = tk.PhotoImage(file=path)
                while img.width() > 540:
                    img = img.subsample(2)
                self.map_img = img; return
            except Exception as e:
                log_err("底图加载失败 %s: %r" % (path, e))
        log_err("底图缺失: " + MAP_FILE)
    def draw_levelsel(self):
        cv = self.canvas; cv.delete("all"); img = self.map_img
        cv.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#f4f8f0", outline="")
        mw, mh = (img.width(), img.height()) if img is not None else (520, 520)
        mx, my = 8, 6
        if img is not None:
            cv.create_image(mx, my, anchor="nw", image=img)
        else:
            cv.create_rectangle(mx, my, mx + mw, my + mh, fill="#e4eed8", outline="#9fb88a", width=2)
            cv.create_text(mx + mw / 2, my + mh / 2, fill="#7a8a6a", font=("Microsoft YaHei", 11),
                           text="（未找到地图底图.png，\n请把它放在游戏同目录）")
        cv.create_text(mx + mw / 2, my + 22, fill=HDU_BLUE, font=("Microsoft YaHei", 14, "bold"),
                       text="杭电校区 · 点击地名选择求学地点")
        i = 0
        while i < len(SCENES):
            fx, fy = LEVEL_POS[i]; x, y = mx + fx * mw, my + fy * mh
            ok = i < self.unlocked; tag = "lv%d" % i
            cv.create_rectangle(x - 54, y - 15, x + 54, y + 15, tags=(tag,),
                                fill="#ffffff" if ok else "#c9c9c9",
                                outline=HDU_BLUE if ok else "#8a8a8a", width=2)
            cv.create_text(x, y, tags=(tag,), fill=HDU_BLUE if ok else "#777777",
                           text=SCENES[i]["name"], font=("Microsoft YaHei", 11, "bold"))
            cv.tag_bind(tag, "<Button-1>", lambda e, k=i: self.on_pick(k))
            cv.tag_bind(tag, "<Enter>", lambda e: cv.config(cursor="hand2"))
            cv.tag_bind(tag, "<Leave>", lambda e: cv.config(cursor="")); i += 1
        px = mx + mw + 26
        cv.create_text(px, 64, anchor="w", text="杭电学子的一日", fill=HDU_BLUE, font=("Microsoft YaHei", 22, "bold"))
        cv.create_text(px, 122, anchor="w", fill="#555555", font=("Microsoft YaHei", 11),
                       text="南大门 · 晨光启程 → 问鼎广场 · 早八冲刺\n风雨操场 · 体测 → 寝室楼 · 午后小憩\n→ 梅花餐厅 · 晚饭冲刺，一站站抵达")
        cv.create_text(px, 206, anchor="w", fill="#333333", font=("Microsoft YaHei", 12, "bold"),
                       text="已解锁 %d / %d 处" % (self.unlocked, len(SCENES)))
        if self.sel_tip and time.time() - self.sel_tip_t < 1.5:
            cv.create_text(px, 240, anchor="w", fill="#c0392b", font=("Microsoft YaHei", 11), text=self.sel_tip)
        tag = "back"
        cv.create_rectangle(WIDTH - 150, HEIGHT - 44, WIDTH - 16, HEIGHT - 14, tags=(tag,),
                            fill="#ffffff", outline=HDU_BLUE, width=2)
        cv.create_text(WIDTH - 83, HEIGHT - 29, text="返回菜单", tags=(tag,),
                       fill=HDU_BLUE, font=("Microsoft YaHei", 11, "bold"))
        cv.tag_bind(tag, "<Button-1>", lambda e: self.to_menu())
        cv.tag_bind(tag, "<Enter>", lambda e: cv.config(cursor="hand2"))
        cv.tag_bind(tag, "<Leave>", lambda e: cv.config(cursor=""))
    def on_pick(self, idx):
        if idx >= self.unlocked:
            self.sel_tip = "「%s」尚未解锁，先通过上一地点" % SCENES[idx]["name"]
            self.sel_tip_t = time.time(); return
        self.ask_difficulty(idx)
    def ask_difficulty(self, idx):
        win = tk.Toplevel(self.root); win.title("选择难度")
        win.resizable(False, False); win.transient(self.root)   # 尺寸随内容自适应（兼容高 DPI）
        tk.Label(win, text="前往「%s」" % SCENES[idx]["name"], font=("Microsoft YaHei", 13, "bold")).pack(pady=(20, 2))
        tk.Label(win, text="请选择难度：", font=("Microsoft YaHei", 10)).pack(pady=4)
        row = tk.Frame(win); row.pack(pady=6)
        for name in ("轻松", "标准", "硬核"):
            tk.Button(row, text=name, width=7, font=("Microsoft YaHei", 11, "bold"),
                      command=lambda d=name: (win.destroy(), self.start_game(idx, d))).pack(side="left", padx=6)
        tk.Button(win, text="再想想", command=win.destroy).pack(pady=4)
    def show_help(self):
        win = tk.Toplevel(self.root); win.title("游戏说明")
        win.resizable(False, False); win.transient(self.root)   # 尺寸随内容自适应（兼容高 DPI）
        tk.Label(win, text="—— 游 戏 说 明 ——", bg=HDU_BLUE, fg="#fff",
                 font=("Microsoft YaHei", 13, "bold")).pack(fill="x")
        tk.Label(win, justify="left", fg="#333333", font=("Microsoft YaHei", 11), wraplength=500,
                 text="\n".join((
                     "【背景】这是杭电学子的求学一日：晨起踏过南大门，午后再回寝室，",
                     "　　傍晚到梅花餐厅饱餐后赶晚课——一站站都去往各自的教室",
                     "【操作】空格/↑ 跳跃（可二段跳）　↓ 滑铲　ESC 暂停",
                     "【陷阱】碰到陷阱扣 1 次补考机会（共 3 次）：",
                     "　· 闹钟 / 报告 / 跨栏 / 预警：起跳越过（预警又窄又高要看准）",
                     "　· 低杆（涵洞低杆）：跳起会撞头，必须按住 ↓ 滑铲钻过",
                     "【规则】坑洞下是月雅湖，掉下去直接失败（不扣补考机会）；",
                     "　　3 次补考用完会「挂科」，返回主菜单；带黄框警示的都会伤人",
                     "【道具】学分+1　奖牌+5　offer+10　饭票=护盾　咖啡=3秒无敌",
                     "【彩蛋】最后一站有一枚会发光的杭电校徽：通关后按提示解开校徽上的密文，",
                     "　　答对便有惊喜彩蛋解锁（答错则惊喜破裂）",
                     "【行程】南大门→问鼎广场→风雨操场→寝室楼→梅花餐厅，依次抵达",
                 ))).pack(fill="both", expand=True, padx=16, pady=10)
        tk.Button(win, text="知道啦", width=10, command=win.destroy).pack(pady=4)
    def save_record(self):
        self.data["records"].append({"name": self.player_name, "score": int(self.score),
                                     "level": self.level_no, "time": time.strftime("%m-%d %H:%M")})
        save_data(self.data)
    def flash(self, text):
        self.msg, self.msg_t = text, 3.0
    # -------- 主循环 --------
    def tick(self):
        now = perf_counter(); dt = now - self.last_t; self.last_t = now
        if dt > DT_CLAMP:
            dt = DT_CLAMP                 # 钳制：切后台回来不会瞬移穿模
        if self.state == "PLAYING":
            self.update(dt)
        self.render(); self.root.after(FPS_MS, self.tick)
    def update(self, dt):
        p = self.player; self.time_left -= dt
        if self.time_left <= 0:
            self.die("时间到！早八已经开始了"); return
        dx = RUN_V * self.scene["speed"] * DIFFICULTY[self.difficulty] * dt
        prev_feet = p.y + p.h
        # 竖直位移先算整帧终点，子步推进对 y 线性内插（swept box）免"角擦误伤"；竖直不受阻挡挡，
        # 否则贴墙起跳每帧只走半步、跳高减半
        y_start = p.y; p.update_physics(dt)
        y_end = p.y
        # 水平推进 + 障碍碰撞：子步进防止高速穿模（核心难点 B）
        steps = int(abs(dx) / MAX_STEP) + 1; step_dx = dx / steps; i = 0
        while i < steps:
            nx = self.cam_x + step_dx; p.x = nx + PLAYER_SCREEN_X
            p.y = y_start + (y_end - y_start) * (i + 1) / steps
            if self.wall_ahead(p, prev_feet):   # 撞上台阶侧壁：停下等玩家起跳
                p.x = self.cam_x + PLAYER_SCREEN_X
                break
            self.cam_x = nx; ob = self.find_hit_obstacle(p)
            if ob is not None:
                self.on_hit(ob)
                if self.state != "PLAYING":
                    return
            i += 1
        p.y = y_end; self.land(p, prev_feet)
        if p.sliding and not p.on_ground:
            p.stop_slide()                # 空中不能保持滑铲
        self.pick_items(p)
        if p.invincible > 0:
            p.invincible -= dt
        if p.hurt > 0:
            p.hurt -= dt
        if p.on_ground:
            p.run_phase += dt * RUN_V / 60.0
        for it in self.items:
            if it.alive:
                it.float_update(dt)
        if self.msg_t > 0:
            self.msg_t -= dt
        if p.y + p.h > GROUND_Y + 56:      # 脚碰到月雅湖水面即失败
            self.die("掉进月雅湖了"); return
        if p.x >= self.finish_x:
            if self.level_score() >= self.scene["need"]:
                self.state = "WIN"; beep(1318, 120)
                if self.egg_obtained and not self.egg_asked:   # 拾到校徽：通关后揭晓谜题
                    self.egg_asked = True; self.root.after(400, self.try_egg_puzzle)
            else:
                self.die("学分不够，被老师点名了（需 %d 分，实得 %d 分）" % (
                    self.scene["need"], self.level_score()))
    def wall_ahead(self, p, prev_feet):
        """前方是否有挡路的台阶侧壁。以"上一帧脚的位置"为准：上一帧脚就在台面之下
        才判撞脸挡下（贴台面滑落绝不穿柱）；本帧才越过台面的属正常落地，不阻挡。"""; i = 0
        while i < len(self.platforms):
            px, top_off, pw = self.platforms[i]
            if px <= p.x + p.w * 0.8 <= px + pw and (GROUND_Y - top_off) < prev_feet - 2:
                return True
            i += 1
        return False
    def find_hit_obstacle(self, p):
        """顺序查找（课堂所学）：seq_search 配 lambda 条件找出第一个碰撞的障碍"""
        idx = seq_search(self.obstacles, True,
                         keyfunc=lambda ob: ob.alive and abs(ob.x - p.x) < 220 and p.hit(ob))
        return self.obstacles[idx] if idx >= 0 else None
    def land(self, p, prev_feet):
        p.on_ground = False
        if p.vy < 0:
            return
        feet, best, i = p.y + p.h, None, 0
        while i < len(self.platforms):
            px, top_off, pw = self.platforms[i]
            if px <= p.x + p.w * 0.5 <= px + pw:
                top = GROUND_Y - top_off
                if prev_feet <= top + 2 and feet >= top:
                    if best is None or top < best:
                        best = top
            i += 1
        if best is not None:
            p.y = best - p.h; p.vy = 0.0; p.on_ground = True; p.jumps = 0
    def pick_items(self, p):
        i = 0
        while i < len(self.items):
            it = self.items[i]
            if it.alive and abs(it.x - p.x) < 200 and p.hit(it):
                it.alive = False; self.score += it.score; self.collected.add(it.kind)
                if it.effect == "shield":
                    p.shield = True; self.flash("饭票到手·获得一次护盾")
                elif it.effect == "invincible":
                    p.invincible = 3.0; self.flash("咖啡下肚·3 秒无敌")
                elif it.effect == "egg":
                    self.egg_obtained = True; self.egg_asked = False
                    self.flash("拾到一枚杭电校徽，似乎藏着什么…"); beep(1568, 90)
                beep(988, 25)
            i += 1
    def on_hit(self, ob):
        p = self.player
        if p.invincible > 0:
            return
        if p.shield:                       # 饭票护盾顶掉一次伤害
            p.shield = False; ob.alive = False
            self.flash("饭票护盾挡下了一劫"); beep(523, 60); return
        self.lives -= 1; p.hurt = 1.0; p.invincible = 1.2; ob.alive = False
        self.flash("撞上了「%s」　剩余补考机会 %d" % (OBSTACLES[ob.kind]["note"], self.lives))
        beep(220, 120)
        if self.lives <= 0:                       # 补考机会耗尽：提示后退回主菜单
            self.state = "GAMEOVER"
            self.root.after(80, lambda: (messagebox.showinfo("挂科了", "挂科了，再接再厉吧！"),
                                         self.to_menu()))
    def die(self, reason):
        self.state, self.dead_reason = "DEAD", reason; beep(160, 240)
    def try_egg_puzzle(self):
        """校徽彩蛋：通关后弹出恺撒谜题。密文为 EGG_ANS 加密，玩家解出后彩蛋开启；
        输错则彩蛋破裂。祝福内容只在成功解锁时展示，之前不透露。"""
        while True:
            tip = ("你从这枚校徽上读出一行密文：%s\n\n"
                   "它像是恺撒密码（密钥 3）加密的四个字。\n"
                   "输入你解出的暗语，校庆彩蛋的祝福即将揭晓：")
            ans = simpledialog.askstring("校庆彩蛋", tip % EGG_CIPHER, parent=self.root)
            if ans is None:
                return                                # 玩家关闭：谜题不强制
            if ans.strip() == EGG_ANS:
                messagebox.showinfo("七十华诞 · 校庆彩蛋", EGG_BLESS); return
            messagebox.showinfo("可惜", "可惜，彩蛋破了——\n暗语不对，校庆的惊喜被你错过了。")
            return
    # -------- 渲染层（全部由 Canvas 代码绘制，无外部素材） --------
    def render(self):
        cv = self.canvas; cv.delete("all")
        if self.state == "MENU":
            self.draw_menu_bg(); return
        if self.state == "LEVELSEL":
            self.draw_levelsel(); return
        self.draw_background(); self.draw_platforms(); self.draw_entities()
        self.player.draw(cv, self.cam_x); self.draw_hud(); self.draw_overlay()
    def draw_menu_bg(self):
        cv, s = self.canvas, SCENES[0]
        # 主菜单背景：采用与第 1 关(南大门)相同的实景照片，营造"校门迎晨"氛围
        if self.menu_img is None:
            for p in (os.path.join(BG_DIR, "南大门.png"), os.path.join(BG_DIR, "南大门.gif")):
                if os.path.exists(p):
                    try:
                        self.menu_img = tk.PhotoImage(file=p)
                    except Exception:
                        self.menu_img = None
                    break
        if self.menu_img is not None:
            cv.create_image(0, 0, anchor="nw", image=self.menu_img)
            cv.create_rectangle(0, 0, WIDTH, 40, fill="#000000", stipple="gray25", outline="")
            cv.create_text(WIDTH // 2, 21, text="杭州电子科技大学　·　笃学力行、守正求新",
                           fill="#ffffff", font=("Microsoft YaHei", 10))
            return
        cv.create_rectangle(0, 0, WIDTH, HEIGHT, fill=s["sky"], outline="")
        cv.create_oval(742, 48, 828, 134, fill="#fff6d0", outline="")
        draw_logo(cv, WIDTH // 2, 108, 54)
        cv.create_text(WIDTH // 2, 186, text="杭州电子科技大学", fill=HDU_BLUE, font=("Microsoft YaHei", 16, "bold"))
        cv.create_text(WIDTH // 2, 210, text="HANGZHOU DIANZI UNIVERSITY　·　1956", fill="#ffffff", font=("Microsoft YaHei", 9))
        self.skyline(cv, -40, 900, 130, 4, s["far"])
        self.branch(cv, 118, GROUND_Y + 4, -1.5708, 58, 5); self.branch(cv, 846, GROUND_Y + 4, -1.5708, 58, 5)
        self.draw_ground(s)
    def prand(self, x, d):
        """确定性伪随机：保证每帧重画的天际线一致，不会闪烁"""
        v = math.sin(x * 12.9898 + d * 78.233) * 43758.5453
        return v - math.floor(v)
    def skyline(self, cv, x, w, h, depth, color):
        """递归生成天际线：区间一分为二、各自随机高度再递归（课堂重点——递归）"""
        if depth <= 0 or w < 10:
            cv.create_rectangle(x, GROUND_Y - h, x + w, GROUND_Y, fill=color, outline="")
            return
        half = w / 2.0
        self.skyline(cv, x, half, h * (0.62 + self.prand(x, depth) * 0.66), depth - 1, color)
        self.skyline(cv, x + half, half, h * (0.62 + self.prand(x + half, depth) * 0.66),
                     depth - 1, color)
    def branch(self, cv, x, y, ang, length, depth, color="#2f6b3a"):
        """递归绘制分形树（课堂重点——递归）"""
        if depth <= 0 or length < 5:
            return
        x2 = x + length * math.cos(ang); y2 = y + length * math.sin(ang)
        cv.create_line(x, y, x2, y2, width=max(1, depth), fill=color, capstyle="round")
        self.branch(cv, x2, y2, ang - 0.42, length * 0.68, depth - 1, color)
        self.branch(cv, x2, y2, ang + 0.36, length * 0.64, depth - 1, color)
    def draw_ground(self, s):
        cv = self.canvas
        cv.create_rectangle(0, GROUND_Y, WIDTH, HEIGHT, fill=s["ground"], outline="")
        cv.create_rectangle(0, GROUND_Y, WIDTH, GROUND_Y + 10, fill="#8fbf6a", outline="")
    def draw_background(self):
        cv, s = self.canvas, self.scene
        if self.bg_img is not None:               # 自定义背景：整幅铺底后只补地面
            cv.create_image(0, 0, anchor="nw", image=self.bg_img)
            self.draw_ground(s); return
        cv.create_rectangle(0, 0, WIDTH, HEIGHT, fill=s["sky"], outline="")
        cv.create_oval(742, 48, 828, 134, fill="#fff6d0", outline="")
        sh = int(self.cam_x * 0.25) % 460                 # 远景视差
        for k in (0, 460, 920):
            self.skyline(cv, -sh + k, 460, 150, 4, s["far"])
        ts = int(self.cam_x * 0.6) % 340                  # 近景视差
        for i in range(-1, 4):
            self.branch(cv, i * 340 - ts + 170, GROUND_Y + 6, -1.5708, 64, 4)
        self.draw_ground(s)
    def draw_platforms(self):
        cv = self.canvas
        # 月雅湖水：先铺整幅水面再盖平台，坑洞缺口处露出深水，凹陷一眼可辨
        cv.create_rectangle(0, GROUND_Y + 56, WIDTH, HEIGHT, fill="#2f5d8a", outline="")
        cv.create_rectangle(0, GROUND_Y + 56, WIDTH, GROUND_Y + 70, fill="#7db8e8", outline="")
        for (px, top, pw) in self.platforms:
            sx = px - self.cam_x
            if sx + pw < -60 or sx > WIDTH + 60:
                continue
            y = GROUND_Y - top
            cv.create_rectangle(sx, y, sx + pw, HEIGHT + 40, fill=self.scene["ground"], outline="")
            cv.create_rectangle(sx, y, sx + pw, y + 12, fill="#8fbf6a", outline="")
    def draw_entities(self):
        cv = self.canvas
        for ob in self.obstacles:
            if ob.alive and -80 < ob.x - self.cam_x < WIDTH + 80:
                ob.draw(cv, self.cam_x)
        for it in self.items:
            if it.alive and -60 < it.x - self.cam_x < WIDTH + 60:
                it.draw(cv, self.cam_x)
        fx = self.finish_x - self.cam_x                   # 终点：教学楼
        if -60 < fx < WIDTH + 60:
            cv.create_rectangle(fx, GROUND_Y - 190, fx + 34, GROUND_Y, fill="#c0392b", outline="")
            cv.create_text(fx + 17, GROUND_Y - 210, text="教室", fill="#c0392b", font=("Microsoft YaHei", 13, "bold"))
    def draw_hud(self):
        cv = self.canvas
        # Tk 不支持 #RRGGBBAA 八位颜色，半透明改用 stipple 网点实现
        cv.create_rectangle(0, 0, WIDTH, 42, fill="#000000", stipple="gray25", outline="")
        cv.create_text(14, 21, anchor="w", fill="#fff", font=("Microsoft YaHei", 12, "bold"),
                       text="第 %d 站 · %s　本关 %d/%d 学分　总分 %d　补考机会 %d　剩余 %.1fs" % (
                           self.level_no, self.scene["name"], self.level_score(),
                           self.scene["need"], self.score, self.lives, max(0.0, self.time_left)))
        cv.create_text(WIDTH - 14, 21, anchor="e", fill="#fff", font=("Microsoft YaHei", 11),
                       text=self.difficulty + "　" + self.player_name)
        prog = min(1.0, self.player.x / float(self.finish_x))    # 进度条
        cv.create_rectangle(240, 34, WIDTH - 240, 38, fill="#ffffff", stipple="gray25", outline="")
        cv.create_rectangle(240, 34, 240 + (WIDTH - 480) * prog, 38, fill=HDU_GOLD, outline="")
        if self.msg_t > 0:
            cv.create_text(WIDTH // 2, 84, text=self.msg, fill="#fff", font=("Microsoft YaHei", 14, "bold"))
    def draw_overlay(self):
        cv = self.canvas
        if self.state == "PLAYING":
            return
        cv.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#000000", stipple="gray50", outline="")
        mid = HEIGHT // 2; BIG = ("Microsoft YaHei", 30, "bold")
        MID = ("Microsoft YaHei", 14); SML = ("Microsoft YaHei", 12)
        if self.state == "PAUSED":
            cv.create_text(WIDTH // 2, mid - 56, text="暂 停 中", fill="#fff", font=BIG)
            for tag, txt, dy in (("pause_resume", "继续游戏", -6), ("pause_menu", "回到主菜单", 44)):
                cv.create_rectangle(WIDTH // 2 - 110, mid + dy, WIDTH // 2 + 110, mid + dy + 38,
                                    tags=(tag,), fill="#ffffff", outline=HDU_BLUE, width=2)
                cv.create_text(WIDTH // 2, mid + dy + 19, text=txt, tags=(tag,),
                               fill=HDU_BLUE, font=("Microsoft YaHei", 13, "bold"))
                cv.tag_bind(tag, "<Button-1>", lambda e, go=tag: (beep(660, 30),
                            self.resume() if go == "pause_resume" else self.to_menu()))
        elif self.state == "DEAD":
            cv.create_text(WIDTH // 2, mid - 34, text="求学中断", fill="#ff8a80", font=BIG)
            cv.create_text(WIDTH // 2, mid + 6, text=self.dead_reason, fill="#fff", font=MID)
            cv.create_text(WIDTH // 2, mid + 44, text="按 空格 再试一次本关", fill="#ddd", font=SML)
        elif self.state == "GAMEOVER":
            cv.create_text(WIDTH // 2, mid - 34, text="挂 科 了", fill="#ff8a80", font=BIG)
            cv.create_text(WIDTH // 2, mid + 6, text="补考机会用完，再接再厉吧！", fill="#fff", font=MID)
            cv.create_text(WIDTH // 2, mid + 44, text="即将返回主菜单…", fill="#ddd", font=SML)
        elif self.state == "WIN":
            kinds, _, _ = insert_sort(list(self.collected))
            cv.create_text(WIDTH // 2, mid - 46, text="准时到班！", fill=HDU_GOLD, font=BIG)
            cv.create_text(WIDTH // 2, mid - 6, fill="#fff", font=("Microsoft YaHei", 13),
                           text="%s · %s　本关 %d 学分（总分 %d）　收集：%s" % (
                               self.scene["name"], self.scene["title"], self.level_score(),
                               self.score, "、".join(kinds) or "无"))
            cv.create_text(WIDTH // 2, mid + 36, text="按 空格 进入下一站", fill="#ddd", font=SML)
        else:
            cv.create_text(WIDTH // 2, mid - 56, text="一天落幕，收获满满！", fill=HDU_GOLD,
                           font=("Microsoft YaHei", 30, "bold"))
            cv.create_text(WIDTH // 2, mid - 8, fill="#fff", font=MID, text="总分 %d　成绩已记入排行榜" % self.score)
            cv.create_text(WIDTH // 2, mid + 24, text=SCHOOL_MOTTO, fill="#ffe", font=("Microsoft YaHei", 13))
            cv.create_text(WIDTH // 2, mid + 56, text="按 空格 返回主菜单", fill="#ddd", font=SML)
# ============ 七、矢量校徽（Canvas 绘制，体现零图片依赖） ============
def draw_logo(cv, cx, cy, r):
    cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=HDU_BLUE, outline="")
    cv.create_oval(cx - r * 0.84, cy - r * 0.84, cx + r * 0.84, cy + r * 0.84, fill="#fff", outline="")
    cv.create_oval(cx - r * 0.74, cy - r * 0.74, cx + r * 0.74, cy + r * 0.74, fill="", outline=HDU_BLUE, width=2)
    bw, bh = r * 0.62, r * 0.30                       # 书本造型（校徽核心元素）
    cv.create_rectangle(cx - bw, cy - bh * 0.2, cx - 2, cy + bh, fill=HDU_BLUE, outline="")
    cv.create_rectangle(cx + 2, cy - bh * 0.2, cx + bw, cy + bh, fill=HDU_BLUE, outline="")
    cv.create_text(cx, cy - bh * 1.5, text="1956", fill=HDU_BLUE, font=("Microsoft YaHei", max(9, int(r * 0.26)), "bold"))
    cv.create_text(cx, cy + bh * 2.0, text="HDU", fill=HDU_BLUE, font=("Microsoft YaHei", max(8, int(r * 0.22)), "bold"))
# ============ 八、排行榜（快速排序 + JSON 持久化） ============
class RankBoard(object):
    def __init__(self, parent, data):
        self.win = tk.Toplevel(parent)
        self.win.title("求学排行榜"); self.win.geometry("420x420"); self.win.resizable(False, False)
        frame = tk.Frame(self.win, bg="#fff"); frame.pack(fill="both", expand=True)
        tk.Label(frame, text="　求学排行榜　", bg=HDU_BLUE, fg="#fff", font=("Microsoft YaHei", 14, "bold")).pack(fill="x", pady=(0, 8))
        recs = list(data["records"])
        if len(recs) == 0:
            tk.Label(frame, text="还没有记录，快去求学吧～", bg="#fff", font=("Microsoft YaHei", 12)).pack(pady=40)
            return
        scored = []; i = 0
        for r in recs:      # 第二项放倒序下标：同分按录入先后，且避免字典直接比大小
            scored.append((r.get("score", 0), len(recs) - i, r)); i += 1
        order, cmp_n, swap_n = quick_sort(scored)      # 课堂所学：快速排序
        tk.Label(frame, text="名次 / 昵称 / 分数 / 关卡 / 时间", bg="#fff", fg="#666", font=("Microsoft YaHei", 9)).pack()
        rank, pos = 1, len(order) - 1                  # 从最高分往回遍历
        while pos >= 0 and rank <= 10:
            (sc, _, r) = order[pos]
            line = "%2d　%-10s　%5d 分　第%d关　%s" % (rank, r.get("name", "?"), sc, r.get("level", 1), r.get("time", ""))
            color = HDU_GOLD if rank == 1 else ("#333" if rank <= 3 else "#666")
            tk.Label(frame, text=line, bg="#fff", fg=color, font=("Microsoft YaHei", 11)).pack(pady=2)
            rank += 1; pos -= 1
        tk.Label(frame, bg="#fff", fg="#999", font=("Microsoft YaHei", 9),
                 text="（共 %d 条记录，快排比较 %d 次、交换 %d 次）" % (
                     len(recs), cmp_n, swap_n)).pack(side="bottom", pady=8)
# ============ 九、存档：JSON + 恺撒加密 + 自定义异常容错 ============
def default_save():
    return {"records": [], "motto_cipher": caesar(MOTTO, 3), "unlocked": 1, "version": 1}
def load_save():
    """读取存档：解密 → 解析 → 结构校验，任何一步出错都走容错分支"""
    if not os.path.exists(SAVE_FILE):
        return default_save()
    try:
        f = open(SAVE_FILE, "r", encoding="utf-8"); raw = f.read(); f.close()
        obj = json.loads(caesar(raw, 3, "decode"))
        if not isinstance(obj, dict) or "records" not in obj:
            raise SaveCorruptedError("存档结构不完整")
        return obj
    except SaveCorruptedError:
        return rebuild_save("存档结构损坏")
    except ValueError:
        return rebuild_save("存档解密失败（内容已损坏）")
    except OSError:
        return default_save()
def rebuild_save(reason):
    """容错：备份损坏文件后重建新存档，保证游戏永远能启动"""
    try:
        if os.path.exists(SAVE_FILE): os.rename(SAVE_FILE, SAVE_FILE + ".bak")
    except OSError:
        pass
    data = default_save(); save_data(data); print("[存档容错] %s，已备份为 .bak 并重建" % reason)
    return data
def save_data(data):
    """写入存档：先 JSON 序列化，再用恺撒密码加密后落盘"""
    try:
        f = open(SAVE_FILE, "w", encoding="utf-8")
        f.write(caesar(json.dumps(data, ensure_ascii=False), 3)); f.close()
        return True
    except OSError:
        return False
def main():
    root = tk.Tk(); Game(root)
    root.mainloop()
if __name__ == "__main__":
    main()