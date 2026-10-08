# -*- coding: utf-8 -*-
"""
自动化截图脚本（交作业用，不属于作业本体）：
开窗口 -> 自动填号码 -> 触发检测 -> 用 PrintWindow 直接离屏渲染窗口截图。
不用屏幕抓屏，所以不怕被别的窗口挡住，标题栏也能一起截进来。
"""
import ctypes
from ctypes import windll, wintypes

try:
    # 高分屏缩放时坐标要 1:1，不然截图会偏
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import importlib.util
from PIL import Image

spec = importlib.util.spec_from_file_location("lot", "彩票中奖检测系统.py")
lot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lot)


class BMI(ctypes.Structure):
    _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
                ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
                ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
                ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
                ("biClrImportant", ctypes.c_uint32)]


def grab_window(win, path):
    """把整个窗口（含标题栏）渲染成一张 png"""
    # tkinter 的 winfo_id 是内部子窗口，要往上找到真正的顶层窗口
    GA_ROOT = 2
    hwnd = windll.user32.GetAncestor(win.winfo_id(), GA_ROOT)
    rect = wintypes.RECT()
    windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    hdc = windll.user32.GetWindowDC(hwnd)
    mem = windll.gdi32.CreateCompatibleDC(hdc)
    bmp = windll.gdi32.CreateCompatibleBitmap(hdc, w, h)
    windll.gdi32.SelectObject(mem, bmp)
    windll.user32.PrintWindow(hwnd, mem, 2)   # 2 = PW_RENDERFULLCONTENT
    bmi = BMI()
    bmi.biSize = ctypes.sizeof(BMI)
    bmi.biWidth = w
    bmi.biHeight = -h        # 负数表示从上往下存
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    buf = ctypes.create_string_buffer(w * h * 4)
    windll.gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bmi), 0)
    img = Image.frombuffer("RGBA", (w, h), buf.raw, "raw", "BGRA", 0, 1)
    img.convert("RGB").save(path)
    windll.gdi32.DeleteObject(bmp)
    windll.gdi32.DeleteDC(mem)
    windll.user32.ReleaseDC(hwnd, hdc)
    print("已保存:", path, "(%dx%d)" % (w, h))


# 截图要保证三组号码的判定结果可复现，所以关掉自动获取线程，
# 改成在主线程里手动"拉取最新一期并应用"，效果和真实运行一样
lot.AUTO_FETCH = False
win = lot.create_window()
win.attributes("-topmost", True)
win.update_idletasks()
win.update()
lot.apply_latest(lot.fetch_latest_dlt())   # 模拟启动自动获取完成后的状态
win.update_idletasks()
win.update()

# 三组测试号码：全中 / 中一部分 / 没中
tests = [
    ([9, 11, 18, 26, 33], [9, 11], "界面截图1_一等奖.png"),
    ([9, 11, 18, 20, 25], [9, 11], "界面截图2_六等奖.png"),
    ([1, 2, 3, 4, 5], [6, 7], "界面截图3_未中奖.png"),
]

for front, back, fname in tests:
    for i in range(5):
        e = lot.front_entries[i]
        e.delete(0, "end")
        e.insert(0, "%02d" % front[i])
    for i in range(2):
        e = lot.back_entries[i]
        e.delete(0, "end")
        e.insert(0, "%02d" % back[i])
    lot.on_check()
    win.update_idletasks()
    win.update()
    grab_window(win, fname)

win.destroy()
