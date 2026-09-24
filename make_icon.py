# -*- coding: utf-8 -*-
"""生成小部件的程序图标（玻璃圆角面板 + 锁形）。"""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (QPixmap, QPainter, QColor, QPen, QBrush,
                           QPainterPath)

app = QApplication([])

S = 256
pm = QPixmap(S, S)
pm.fill(Qt.GlobalColor.transparent)

p = QPainter(pm)
p.setRenderHint(QPainter.RenderHint.Antialiasing)

# 玻璃圆角面板
panel = QRectF(24, 24, S - 48, S - 48)
path = QPainterPath()
path.addRoundedRect(panel, 36, 36)
p.fillPath(path, QBrush(QColor(255, 255, 255, 36)))
p.setPen(QPen(QColor(255, 255, 255, 210), 7))
p.drawPath(path)

# 锁：梁 + 体
cx, cy = S / 2, S / 2 + 14
bw, bh = 92.0, 74.0
pen = QPen(QColor(255, 255, 255, 235), 11,
           Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
p.setPen(pen)
# 锁梁
arc = QRectF(cx - 26, cy - 62, 52, 78)
p.drawArc(arc, 0, 180 * 16)
# 锁体（实心）
body = QPainterPath()
body.addRoundedRect(QRectF(cx - bw / 2, cy - bh / 2, bw, bh), 18, 18)
p.fillPath(body, QBrush(QColor(255, 255, 255, 235)))
# 锁孔
p.setPen(QPen(QColor(60, 60, 70), 9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
p.drawLine(QPointF(cx, cy - 16), QPointF(cx, cy + 6))
p.drawEllipse(QRectF(cx - 10, cy + 4, 20, 20))
p.end()

pm.save("widget_icon.png", "PNG")
img = pm.toImage()
ok = img.save("widget_icon.ico", "ICO")
print("ICO 保存:", ok)
