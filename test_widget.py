# -*- coding: utf-8 -*-
"""离屏自动化测试：锁开关、拖动（顶部/列表空白/标题文字）、调整大小、双击打开、锁定拦截、标题居中、关闭按钮。"""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt, QPoint

import main

app = QApplication([])
app.setQuitOnLastWindowClosed(False)

# 拦截真实打开文件动作
opened = []
_real_startfile = os.startfile
os.startfile = lambda p: opened.append(p)

w = main.GlassWidget()
w.show()
app.processEvents()


def drag(widget, start, steps, delta,
         button=Qt.MouseButton.LeftButton):
    """从 start 按下，分 steps 步移动 delta，再释放。
    每个用例先把窗口复位到固定位置，避免 offscreen 平台 QTest
    全局坐标偏差在窗口移动后累积导致断言失真。"""
    widget.window().move(100, 100)
    app.processEvents()
    QTest.mousePress(widget, button, pos=start)
    for i in range(1, steps + 1):
        QTest.mouseMove(widget, pos=start + QPoint(delta.x() * i // steps,
                                                   delta.y() * i // steps))
        app.processEvents()
    QTest.mouseRelease(widget, button, pos=start + delta)
    app.processEvents()


# 1) 锁开关
assert w.locked is False
QTest.mouseClick(w.lock_btn, Qt.MouseButton.LeftButton)
app.processEvents()
assert w.locked is True
QTest.mouseClick(w.lock_btn, Qt.MouseButton.LeftButton)
app.processEvents()
assert w.locked is False
print("PASS 锁开关")

# 2) 顶部空白处拖动
g0 = w.geometry()
drag(w, QPoint(60, 16), 8, QPoint(48, 24))
assert (w.geometry().x(), w.geometry().y()) != (g0.x(), g0.y()), \
    f"顶部空白拖动应移动窗口: {g0} -> {w.geometry()}"
print("PASS 顶部空白拖动")

# 3) 标题文字上拖动（验证鼠标穿透，标题不再吃掉事件）
g0 = w.geometry()
drag(w.title_label, w.title_label.rect().center(), 8, QPoint(40, 10))
assert (w.geometry().x(), w.geometry().y()) != (g0.x(), g0.y()), \
    f"标题文字拖动应移动窗口: {g0} -> {w.geometry()}"
print("PASS 标题文字拖动")

# 4) 列表空白处拖动（先用短列表造出空白）
from PySide6.QtWidgets import QListWidgetItem
w.list.clear()
for i in range(3):
    w.list.addItem(QListWidgetItem(f"test-item-{i}"))
app.processEvents()
g0 = w.geometry()
blank = QPoint(w.list.geometry().center().x(),
               w.list.geometry().bottom() - 4)
drag(w, blank, 8, QPoint(-30, 10))
assert (w.geometry().x(), w.geometry().y()) != (g0.x(), g0.y()), \
    f"列表空白拖动应移动窗口: {g0} -> {w.geometry()}"
w._refresh()  # 恢复真实列表
app.processEvents()
print("PASS 列表空白拖动")

# 4.5) 右键任意区域拖动（含列表条目上）
w.list.clear()
for i in range(3):
    w.list.addItem(QListWidgetItem(f"test-item-{i}"))
app.processEvents()
g0 = w.geometry()
item = w.list.item(0)
rect = w.list.visualItemRect(item)
center = w.list.viewport().mapTo(w.list, rect.center())
drag(w, center, 8, QPoint(35, -12), button=Qt.MouseButton.RightButton)
assert (w.geometry().x(), w.geometry().y()) != (g0.x(), g0.y()), \
    f"右键在列表条目上应能拖动窗口: {g0} -> {w.geometry()}"
w._refresh()  # 恢复真实列表
app.processEvents()
print("PASS 右键任意区域拖动（含列表条目上）")

# 5) 调整大小
g0 = w.geometry()
corner = QPoint(w.width() - 2, w.height() - 2)
drag(w, corner, 8, QPoint(40, 40))
assert w.geometry().width() > g0.width() and w.geometry().height() > g0.height(), \
    f"窗口应变大: {g0} -> {w.geometry()}"
print("PASS 调整大小")

# 6) 单击不打开、双击打开（拦截 os.startfile）
assert w.list.count() > 0, "列表应有数据"
item = w.list.item(0)
rect = w.list.visualItemRect(item)
center = w.list.viewport().mapTo(w.list, rect.center())
opened.clear()
QTest.mouseClick(w.list.viewport(), Qt.MouseButton.LeftButton, pos=center)
app.processEvents()
assert opened == [], f"单击不应打开文件: {opened}"
QTest.mouseDClick(w.list.viewport(), Qt.MouseButton.LeftButton, pos=center)
app.processEvents()
assert len(opened) == 1, f"双击应打开一个文件: {opened}"
assert opened[0] == item.data(Qt.ItemDataRole.UserRole)
print("PASS 双击打开（单击不打开）")

# 7) 锁定状态下双击不打开
opened.clear()
w.set_locked(True)
QTest.mouseDClick(w.list.viewport(), Qt.MouseButton.LeftButton, pos=center)
app.processEvents()
assert opened == [], f"锁定时双击不应打开: {opened}"
w.set_locked(False)
print("PASS 锁定时双击被拦截")

# 8) 标题居中
title_center_x = w.title_label.geometry().center().x()
win_center_x = w.width() // 2
assert abs(title_center_x - win_center_x) < 12, \
    f"标题应居中: {title_center_x} vs {win_center_x}"
print("PASS 标题居中")

# 9) 关闭按钮
assert w.isVisible()
QTest.mouseClick(w.close_btn, Qt.MouseButton.LeftButton)
app.processEvents()
assert not w.isVisible()
print("PASS 关闭按钮")

print("ALL TESTS PASSED")
