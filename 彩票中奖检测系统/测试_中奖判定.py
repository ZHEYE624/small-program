# -*- coding: utf-8 -*-
"""
中奖判定逻辑的测试脚本（不开界面，直接测函数）

测两块：
1. 穷举：前区命中 0~5 个 × 后区命中 0~2 个，共 18 种组合，
   每种都跟 PPT 上的规则表核对，一个都不能错。
2. 输入校验：没填、非数字、超范围、区内重复、跨区重号这些边界情况。

跑法：python 测试_中奖判定.py ，全部通过会打印「全部通过」。
"""
import importlib.util

spec = importlib.util.spec_from_file_location("lot", "彩票中奖检测系统.py")
lot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lot)

# 期望奖级表，这份是照着 PPT 规则重新抄的，跟代码里的 PRIZE_TABLE 相互独立，
# 两边一致才说明代码没写错
EXPECTED = {
    (5, 2): "一等奖", (5, 1): "二等奖", (5, 0): "三等奖",
    (4, 2): "四等奖", (4, 1): "五等奖", (3, 2): "六等奖", (4, 0): "七等奖",
    (3, 1): "八等奖", (2, 2): "八等奖",
    (3, 0): "九等奖", (1, 2): "九等奖", (2, 1): "九等奖", (0, 2): "九等奖",
}

fail_count = 0

# ---------- 第 1 块：穷举 18 种命中组合 ----------
for f in range(6):
    for b in range(3):
        # 造一组号码：前区 f 个中奖号 + 补几个不中奖的号，后区同理
        front = lot.WIN_FRONT[:f]
        for n in range(1, 36):          # 从 1~35 里找不在开奖号里的补位
            if len(front) >= 5:
                break
            if n not in lot.WIN_FRONT and n not in front:
                front.append(n)
        back = lot.WIN_BACK[:b]
        for n in range(1, 13):
            if len(back) >= 2:
                break
            if n not in lot.WIN_BACK and n not in back:
                back.append(n)
        # 顺便把顺序打乱，验证"顺序不限"这一点
        front.reverse()
        back.reverse()

        prize, fh, bh = lot.check_prize(front, back)
        want = EXPECTED.get((f, b))
        if prize != want or fh != f or bh != b:
            fail_count = fail_count + 1
            print("FAIL 前中%d后中%d: 得到 %s（命中%d+%d），期望 %s"
                  % (f, b, prize, fh, bh, want))
        else:
            print("PASS 前中%d 后中%d -> %s" % (f, b, prize if prize else "未中奖"))

# ---------- 第 2 块：输入校验的边界情况 ----------
class FakeEntry:
    """假装是输入框，get() 返回预设的文字，这样不用开窗口就能测校验"""
    def __init__(self, text):
        self.text = text
    def get(self):
        return self.text

def try_input(front_texts, back_texts):
    lot.front_entries = [FakeEntry(t) for t in front_texts]
    lot.back_entries = [FakeEntry(t) for t in back_texts]
    return lot.read_entries()

cases = [
    # (说明, 前区输入, 后区输入, 期望：错误提示是空还是报错)
    ("正常一组", ["09", "11", "18", "26", "33"], ["09", "11"], ""),
    ("不带前导0也行", ["9", "1", "18", "26", "33"], ["1", "2"], ""),
    ("前区有空格", [" 09 ", "11", "18", "26", "33"], ["09", "11"], ""),
    ("没填满要报错", ["09", "11", "18", "26", ""], ["09", "11"], "没填"),
    ("非数字要报错", ["09", "11", "1a", "26", "33"], ["09", "11"], "数字"),
    ("前区36超范围", ["09", "11", "18", "26", "36"], ["09", "11"], "01~35"),
    ("前区0超范围", ["00", "11", "18", "26", "33"], ["09", "11"], "01~35"),
    ("后区13超范围", ["09", "11", "18", "26", "33"], ["09", "13"], "01~12"),
    ("前区重复要报错", ["09", "09", "18", "26", "33"], ["09", "11"], "前区号码有重复"),
    ("后区重复要报错", ["09", "11", "18", "26", "33"], ["11", "11"], "后区号码有重复"),
    ("跨区重号是合法的", ["09", "11", "18", "26", "33"], ["09", "10"], ""),
]
for name, ft, bt, want_err in cases:
    front, back, err = try_input(ft, bt)
    if want_err == "":
        ok = (err == "")
    else:
        ok = (err != "" and want_err in err)
    if ok:
        print("PASS 校验：%s" % name)
    else:
        fail_count = fail_count + 1
        print("FAIL 校验：%s -> 提示是「%s」" % (name, err))

print("-" * 40)
if fail_count == 0:
    print("全部通过，判定逻辑和输入校验都没有 BUG")
else:
    print("有 %d 处失败，回头改代码" % fail_count)
