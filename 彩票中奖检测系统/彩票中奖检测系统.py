# -*- coding: utf-8 -*-
"""
超级大乐透 中奖检测系统（tkinter 作业）

界面上的开奖号码，默认每次启动都会联网从体彩官网拉最新一期来用；
万一没网、或者接口抽风，就退回老师给的中奖号码图（第 26101 期，
2026-09-05 开奖）：前区 09 11 18 26 33，后区 09 11。想纯手动就把
下面的 AUTO_FETCH 改成 False，一直用内置这期；机器上没装 requests
的话它也会自己降级成手动模式。反正不能因为网络问题把程序搞崩。

中奖规则就是 PPT 上那张表：前区 01~35 选 5 个、后区 01~12 选 2 个，
按"前区中了几个 + 后区中了几个"对上奖级，顺序无所谓只看个数：
    一等奖 5+2    二等奖 5+1    三等奖 5+0
    四等奖 4+2    五等奖 4+1    六等奖 3+2    七等奖 4+0
    八等奖 3+1 或 2+2
    九等奖 3+0 或 1+2 或 2+1 或 0+2

做的时候踩过两个坑，记在这里免得以后再犯：
一是前区和后区是两个独立的号池，跨区重号是合法的。开奖号自己就是
前区 09、后区 09，所以查重复只能在各自区内查，不能跨区。
二是判定只看中几个不看顺序，那就别堆一大坨 if，直接数命中数查表。

判定逻辑单独放在 check_prize 里，跟界面完全分开，不开窗口也能测。
测试_中奖判定.py 就是直接调它，穷举 18 种命中组合对着规则核过。
"""

from tkinter import *
from tkinter import messagebox
from tkinter.ttk import Separator
import threading      # 后台线程联网拉数据，不让界面卡住

try:
    import requests   # 联网用的，环境里没装也不影响程序跑（只是不联网）
except Exception:
    requests = None

# 开奖号码与联网设置
# AUTO_FETCH 控制要不要启动时联网更新：改成 False 就一直用内置号码
AUTO_FETCH = True

# 内置的参考开奖号码（= 老师给的中奖号码图，也是没网时的兜底）
WIN_FRONT = [9, 11, 18, 26, 33]   # 前区，01~35 里选 5 个
WIN_BACK = [9, 11]                # 后区，01~12 里选 2 个

# 界面信息行显示的内容（联网成功后会换成最新一期）
CUR = {"issue": "26101", "date": "2026-09-05", "note": "（内置号码）"}

# 体彩官网的接口：gameNo=85 就是超级大乐透，pageSize=1 只取最新一期
DLT_API = ("https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
           "?gameNo=85&provinceId=0&pageSize=1&isVerify=1&pageNo=1")
NET_HEADERS = {
    'user-agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/120.0.0.0 Safari/537.36'),
    'referer': 'https://www.lottery.gov.cn/',
}

# 中奖规则表：(前区命中数, 后区命中数) -> 奖级
# 一条条对着 PPT 上的规则抄下来的，查表比写一大坨 if 清楚
PRIZE_TABLE = {
    (5, 2): "一等奖",
    (5, 1): "二等奖",
    (5, 0): "三等奖",
    (4, 2): "四等奖",
    (4, 1): "五等奖",
    (3, 2): "六等奖",
    (4, 0): "七等奖",
    (3, 1): "八等奖",
    (2, 2): "八等奖",
    (3, 0): "九等奖",
    (1, 2): "九等奖",
    (2, 1): "九等奖",
    (0, 2): "九等奖",
}


def fetch_latest_dlt():
    """调体彩官网接口拿最新一期大乐透，成功返回 dict，失败返回 None。

    成功的话给 {'issue': 期号, 'date': 日期, 'front': [5 个前区],
    'back': [2 个后区]}。网络断了、接口报错、返回格式不对，统统返回
    None，让外面继续用内置号码。反正不能让网络把程序搞崩。
    """
    if requests is None:
        return None
    try:
        resp = requests.get(DLT_API, headers=NET_HEADERS, timeout=5)
        obj = resp.json()
        if obj.get("errorCode") != "0":      # 接口自己报错
            return None
        lst = (obj.get("value") or {}).get("list") or []
        if not lst:
            return None
        rec = lst[0]
        nums = rec.get("lotteryDrawResult", "").split()   # "09 11 18 26 33 09 11"
        if len(nums) != 7:                   # 大乐透应该是 5 前 + 2 后
            return None
        front = []
        for s in nums[:5]:
            front.append(int(s))
        back = []
        for s in nums[5:]:
            back.append(int(s))
        return {"issue": rec.get("lotteryDrawNum"),
                "date": rec.get("lotteryDrawTime"),
                "front": front, "back": back}
    except Exception:
        return None


def apply_latest(res):
    """后台拿回结果后的收尾：把开奖号码换掉，再把界面刷新一遍"""
    global WIN_FRONT, WIN_BACK
    if res is None:
        CUR["note"] = "（联网失败，显示内置号码）"
    else:
        WIN_FRONT = res["front"]
        WIN_BACK = res["back"]
        CUR["issue"] = res["issue"]
        CUR["date"] = res["date"]
        CUR["note"] = "（已自动获取最新一期）"
    redraw_winning()


def check_prize(front, back):
    """核心判定函数，跟界面无关，方便单独测试。

    front、back 都是 int 列表（已经过校验的合法号码）。
    返回 (奖级文字, 前区命中数, 后区命中数)，没中奖时奖级是 None。
    """
    f_hits = 0
    for n in front:
        if n in WIN_FRONT:
            f_hits = f_hits + 1
    b_hits = 0
    for n in back:
        if n in WIN_BACK:
            b_hits = b_hits + 1
    prize = PRIZE_TABLE.get((f_hits, b_hits))
    return prize, f_hits, b_hits


def read_entries():
    """把 7 个输入框读出来，一边读一边做校验。

    返回 (前区列表, 后区列表, 错误提示)，全对的话错误提示是空字符串。
    按顺序查：有没有漏填、是不是数字、范围对不对、区内有没有重复。
    """
    front = []
    back = []
    for e in front_entries:
        s = e.get().strip()
        if s == "":
            return None, None, "还有号码没填，7 个框都要填满"
        if not s.isdigit():
            return None, None, "号码只能是数字（比如 09 或 9），你输入的是「" + s + "」"
        n = int(s)
        if n < 1 or n > 35:
            return None, None, "前区号码必须在 01~35 之间，「" + s + "」超范围了"
        front.append(n)
    for e in back_entries:
        s = e.get().strip()
        if s == "":
            return None, None, "还有号码没填，7 个框都要填满"
        if not s.isdigit():
            return None, None, "号码只能是数字（比如 09 或 9），你输入的是「" + s + "」"
        n = int(s)
        if n < 1 or n > 12:
            return None, None, "后区号码必须在 01~12 之间，「" + s + "」超范围了"
        back.append(n)
    # 重复检查：只在各自的区里查。前区和后区之间允许重号（见文件开头说明）
    for n in front:
        if front.count(n) > 1:
            return None, None, "前区号码有重复：%02d 出现了多次，一张彩票前区不能选重复的号" % n
    for n in back:
        if back.count(n) > 1:
            return None, None, "后区号码有重复：%02d 出现了多次，一张彩票后区不能选重复的号" % n
    return front, back, ""


def draw_ball(cv, x, y, r, num, color):
    """在画布上画一个号码球：圆形底 + 居中的两位数号码"""
    cv.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="")
    cv.create_text(x, y, text="%02d" % num, fill="white",
                   font=("Arial", 12, "bold"))


def redraw_winning():
    """按当前的 WIN_FRONT/WIN_BACK，把「期号信息行 + 开奖号码球」重画一遍。
    联网拿到新一期后也是调这个来刷新界面。
    """
    if info_lb is None or balls_cv is None:
        return
    info_lb.configure(text="第 %s 期　开奖日期：%s　%s"
                      % (CUR["issue"], CUR["date"], CUR["note"]))
    balls_cv.delete("all")                 # 先清空再重画
    balls_cv.create_text(52, 24, text="开奖号码", fill="#555555",
                         font=("Microsoft YaHei", 10, "bold"))
    x = 128
    for n in WIN_FRONT:                    # 前区画红球
        draw_ball(balls_cv, x, 24, 16, n, "#d84335")
        x = x + 40
    x = x + 8
    for n in WIN_BACK:                     # 后区画蓝球
        draw_ball(balls_cv, x, 24, 16, n, "#1565c0")
        x = x + 40
    balls_cv.create_text(330, 51, text="前区（01~35）", fill="#bb4444",
                         font=("Microsoft YaHei", 8))
    balls_cv.create_text(452, 51, text="后区（01~12）", fill="#3366bb",
                         font=("Microsoft YaHei", 8))


def on_check():
    """点「检测」按钮：先校验输入，再查表给结果"""
    front, back, err = read_entries()
    if err != "":
        messagebox.showwarning("输入有误", err)
        return
    prize, f, b = check_prize(front, back)
    detail = "（前区命中 %d 个，后区命中 %d 个）" % (f, b)
    if prize is None:
        result_lb.configure(text="很遗憾，本期未中奖" + detail, fg="#888888")
    elif prize == "一等奖":
        result_lb.configure(text="恭喜！中得一等奖！" + detail, fg="#c62828")
    else:
        result_lb.configure(text="恭喜，中得" + prize + "！" + detail, fg="#e65100")


def on_clear():
    """清空按钮：7 个框全清掉，结果也复位"""
    for e in front_entries + back_entries:
        e.delete(0, END)
    result_lb.configure(text="", fg="#888888")


def create_window():
    """把整个界面搭出来，返回主窗口（返回窗口是为了能被测试脚本复用）"""
    global result_lb, info_lb, balls_cv
    win = Tk()
    win.title("超级大乐透 中奖检测系统")
    win.resizable(False, False)
    bg = "#faf8f5"
    win.configure(bg=bg)

    # 环境里有没有 requests、开没开自动获取，决定信息行先显示什么状态
    fetch_on = AUTO_FETCH and requests is not None
    if fetch_on:
        CUR["note"] = "（正在联网获取最新一期…）"
    else:
        CUR["note"] = "（内置号码）"

    # 顶部画个 logo：一排从低到高升起的彩色小球，算是凑作业的加分项
    logo = Canvas(win, width=540, height=72, bg=bg, highlightthickness=0)
    logo.grid(row=0, column=0, columnspan=9, pady=(10, 0))
    ball_colors = ["#e53935", "#fb8c00", "#43a047", "#1e88e5", "#8e24aa"]
    for i in range(5):
        r = 6 + i * 2
        cx = 46 + i * 25
        cy = 58 - i * 8
        logo.create_oval(cx - r, cy - r, cx + r, cy + r, fill=ball_colors[i], outline="")
    logo.create_text(300, 28, text="超级大乐透", fill="#c62828",
                     font=("Microsoft YaHei", 23, "bold"))
    logo.create_text(300, 55, text="SUPER LOTTO · 中奖检测系统", fill="#999999",
                     font=("Microsoft YaHei", 10))

    # 期号信息行 + 开奖号码展示，具体画成什么样由 redraw_winning 决定
    info_lb = Label(win, text="", bg=bg, fg="#555555",
                    font=("Microsoft YaHei", 10))
    info_lb.grid(row=1, column=0, columnspan=9, pady=(2, 0))
    balls_cv = Canvas(win, width=540, height=58, bg=bg, highlightthickness=0)
    balls_cv.grid(row=2, column=0, columnspan=9)
    redraw_winning()

    Separator(win).grid(row=3, column=0, columnspan=9, sticky="ew", padx=20, pady=6)

    # 输入区：5 个前区框 + 2 个后区框，宽度全部设成一样（加分项3）
    tip_lb = Label(win, text="请输入你预测的号码", bg=bg, fg="#333333",
                   font=("Microsoft YaHei", 11, "bold"))
    tip_lb.grid(row=4, column=0, columnspan=9, pady=(4, 2))
    front_lb = Label(win, text="前区", bg=bg, fg="#d84335",
                     font=("Microsoft YaHei", 11, "bold"))
    front_lb.grid(row=5, column=0, padx=(18, 4))
    for i in range(5):
        e = Entry(win, width=5, font=("Consolas", 13, "bold"),
                  justify=CENTER, highlightthickness=1)
        e.grid(row=5, column=1 + i, padx=3, ipady=4)
        front_entries.append(e)
    back_lb = Label(win, text="后区", bg=bg, fg="#1565c0",
                    font=("Microsoft YaHei", 11, "bold"))
    back_lb.grid(row=5, column=6, padx=(14, 4))
    for i in range(2):
        e = Entry(win, width=5, font=("Consolas", 13, "bold"),
                  justify=CENTER, highlightthickness=1)
        e.grid(row=5, column=7 + i, padx=3, ipady=4)
        back_entries.append(e)
    hint_lb = Label(win, text="前区选 5 个（01~35）    后区选 2 个（01~12）",
                    bg=bg, fg="#999999", font=("Microsoft YaHei", 9))
    hint_lb.grid(row=6, column=0, columnspan=9, pady=(2, 4))

    # 两个按钮并排放
    btn_f = Frame(win, bg=bg)
    btn_f.grid(row=7, column=0, columnspan=9, pady=6)
    check_btn = Button(btn_f, text="检测是否中奖", command=on_check,
                       bg="#c62828", fg="white", activebackground="#a02020",
                       activeforeground="white", relief=FLAT, cursor="hand2",
                       font=("Microsoft YaHei", 11, "bold"), width=13, pady=2)
    check_btn.pack(side=LEFT, padx=8)
    clear_btn = Button(btn_f, text="清 空", command=on_clear,
                       bg="#e0e0e0", fg="#444444", activebackground="#cfcfcf",
                       relief=FLAT, cursor="hand2",
                       font=("Microsoft YaHei", 11), width=9, pady=2)
    clear_btn.pack(side=LEFT, padx=8)
    win.bind("<Return>", lambda event: on_check())   # 回车也能检测

    # 结果就显示在这一行，中没中、中了什么奖都写在这
    result_lb = Label(win, text="", bg=bg, font=("Microsoft YaHei", 13, "bold"))
    result_lb.grid(row=8, column=0, columnspan=9, pady=(8, 2))

    Separator(win).grid(row=9, column=0, columnspan=9, sticky="ew", padx=20, pady=4)

    # 底部再贴一份奖级规则，玩的时候好对照
    rules_lb = Label(win, bg=bg, fg="#888888", justify=LEFT,
                     font=("Microsoft YaHei", 9),
                     text="中奖规则（前区命中+后区命中）：\n"
                          "一等奖 5+2   二等奖 5+1   三等奖 5+0   四等奖 4+2\n"
                          "五等奖 4+1   六等奖 3+2   七等奖 4+0   八等奖 3+1 / 2+2\n"
                          "九等奖 3+0 / 1+2 / 2+1 / 0+2")
    rules_lb.grid(row=10, column=0, columnspan=9, pady=(2, 10))

    # 联网拿最新一期放后台线程做，窗口先正常显示，不在这干等
    if fetch_on:
        def worker():
            res = fetch_latest_dlt()
            try:
                win.after(0, lambda: apply_latest(res))   # 回到主线程更新界面
            except Exception:
                pass   # 只有没进 mainloop 的怪环境才会走到这，忽略即可
        threading.Thread(target=worker, daemon=True).start()
    return win


front_entries = []   # 5 个前区输入框
back_entries = []    # 2 个后区输入框
result_lb = None     # 结果标签，create_window 里赋值
info_lb = None       # 期号信息行
balls_cv = None      # 开奖号码球的画布


def main():
    win = create_window()
    win.mainloop()


if __name__ == "__main__":
    main()
