# -*- coding: utf-8 -*-
"""
待办便签小部件 —— 玻璃质感的桌面待办清单。
- 双击列表空白处：添加待办
- 点击条目左侧圆圈：标记完成/未完成（完成文字划线变暗）
- 点击条目右侧 X：删除该条
- 双击某条：编辑文字
- 按住鼠标右键任意区域：拖动窗口；顶部三横线把手/标题行也可拖
- 拖动边缘或四角：调整大小（窗口始终限制在屏幕内）
- 位置、大小、待办内容自动保存
"""
import sys
import os
import json
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, QRectF, QRect, QPointF, QSize
from PySide6.QtGui import (QColor, QPainter, QPainterPath, QFont, QBrush,
                           QPen, QRegion, QLinearGradient, QRadialGradient)
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QListWidget, QListWidgetItem,
                               QAbstractItemView, QSizePolicy, QInputDialog)

# ----------------------------------------------------------------------------
# 基础常量
# ----------------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent
if getattr(sys, "frozen", False):
    DATA_DIR = Path(os.environ["APPDATA"]) / "DesktopGlassWidget"
else:
    DATA_DIR = APP_DIR
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    DATA_DIR = APP_DIR
CONFIG_PATH = DATA_DIR / "todo_config.json"

EDGE = 8                 # 边缘热区宽度（像素），用于调整大小
MIN_W, MIN_H = 220, 240  # 最小尺寸
HEADER_H = 34            # 顶部栏高度
GRIP_H = 18              # 顶部拖动把手条高度（画着三横线标记，按住即可拖动窗口）

# ----------------------------------------------------------------------------
# 条目控件：左侧圆圈（完成勾选）
# ----------------------------------------------------------------------------
class TodoCheck(QLabel):
    def __init__(self, checked=False):
        super().__init__()
        self.setFixedSize(20, 20)
        self.checked = checked
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("点击标记完成 / 未完成")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(2, 2, 16, 16)
        if self.checked:
            p.setBrush(QBrush(QColor(255, 255, 255, 215)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(r)
            pen = QPen(QColor(44, 48, 56), 2.2, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.drawLine(QPointF(6, 10.5), QPointF(9.5, 14))
            p.drawLine(QPointF(9.5, 14), QPointF(14.5, 6.5))
        else:
            p.setPen(QPen(QColor(255, 255, 255, 170), 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(r)
        p.end()

# ----------------------------------------------------------------------------
# 条目控件：右侧删除 X
# ----------------------------------------------------------------------------
class TodoDelete(QLabel):
    def __init__(self):
        super().__init__()
        self.setFixedSize(18, 18)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("删除这条待办")
        self._hover = False

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(255, 90, 90) if self._hover else QColor(255, 255, 255, 150)
        pen = QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        m = 5.0
        p.drawLine(QPointF(m, m), QPointF(self.width() - m, self.height() - m))
        p.drawLine(QPointF(self.width() - m, m), QPointF(m, self.height() - m))
        p.end()

# ----------------------------------------------------------------------------
# 钉子按钮：点击固定位置（固定后不能拖动/缩放），再点解除
# ----------------------------------------------------------------------------
class PinButton(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(26, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("点击固定位置（固定后不能拖动/缩放）；再点一次解除")
        self.pinned = False
        self._hover = False

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def set_pinned(self, pinned):
        self.pinned = pinned
        self.setToolTip("已固定位置，点击解除" if pinned
                        else "点击固定位置（固定后不能拖动/缩放）")
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.pinned:
            color = QColor(255, 179, 0)
        elif self._hover:
            color = QColor(255, 255, 255, 255)
        else:
            color = QColor(255, 255, 255, 200)
        head = QRectF(5.5, 2.5, 13, 13)
        if self.pinned:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(color))
            p.drawEllipse(head)
        else:
            p.setPen(QPen(color, 1.8))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(head)
        p.setPen(QPen(color, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        if self.pinned:
            p.drawLine(QPointF(12, 15.5), QPointF(12, 21.5))
            p.drawLine(QPointF(7, 21.5), QPointF(17, 21.5))
        else:
            p.drawLine(QPointF(12, 15.5), QPointF(17.5, 21))
        p.end()

# ----------------------------------------------------------------------------
# 单个待办条目（圆圈 + 文字 + 删除）
# ----------------------------------------------------------------------------
class TodoItemWidget(QWidget):
    def __init__(self, text, done, on_toggle, on_delete):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 3, 6, 3)
        lay.setSpacing(6)
        self.check = TodoCheck(done)
        self.check.mousePressEvent = lambda e: on_toggle(e)
        lay.addWidget(self.check)
        self.label = QLabel(text)
        self.label.setFont(QFont("Microsoft YaHei UI", 10))
        self.label.setWordWrap(True)
        lay.addWidget(self.label, 1)
        self.del_btn = TodoDelete()
        self.del_btn.mousePressEvent = lambda e: on_delete(e)
        lay.addWidget(self.del_btn)
        self.set_done(done)

    def set_done(self, done):
        if done:
            self.label.setStyleSheet(
                "color: rgba(255,255,255,110); background: transparent;"
                " text-decoration: line-through;")
        else:
            self.label.setStyleSheet(
                "color: rgba(255,255,255,235); background: transparent;")

    def set_text(self, text):
        self.label.setText(text)

# ----------------------------------------------------------------------------
# 列表：右键冒泡给父窗口拖动；双击空白添加、双击条目编辑
# ----------------------------------------------------------------------------
class TodoList(QListWidget):
    def __init__(self, owner):
        super().__init__()
        self._owner = owner
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            event.ignore()  # 右键任意位置冒泡给父窗口，用于拖动
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        lp = self.viewport().mapFrom(self, event.position().toPoint())
        row = self.indexAt(lp).row()
        if row < 0:
            self._owner.add_todo()   # 双击空白处 → 添加
        else:
            self._owner.edit_todo(row)  # 双击条目 → 编辑
        event.accept()

# ----------------------------------------------------------------------------
# 主体窗口
# ----------------------------------------------------------------------------
class GlassTodo(QWidget):
    def __init__(self):
        super().__init__()
        self._todos = []          # [{"text": ..., "done": ...}]
        self._edges = 0
        self._moving = False
        self._move_off = QPoint()
        self._press_global = QPoint()
        self._press_geo = QRect()
        self._grip_hover = False
        self.pinned = False

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.Tool
                            | Qt.WindowType.WindowStaysOnBottomHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("待办事项")
        self.setMouseTracking(True)

        self._build_ui()
        self._load_config()
        self._render()
        self.setMask(QRegion(self.rect()))

    # ---------------- 界面 ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, GRIP_H + 8, 10, 10)
        root.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(4)
        header.addSpacing(26 + 4 + 26)
        header.addStretch(1)
        self.title_label = QLabel("待办事项")
        self.title_label.setFont(QFont("Microsoft YaHei UI", 9))
        self.title_label.setStyleSheet(
            "color: rgba(255,255,255,220); background: transparent;")
        self.title_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        header.addWidget(self.title_label)
        header.addStretch(1)
        self.pin_btn = PinButton()
        self.pin_btn.mousePressEvent = self._on_pin_press
        header.addWidget(self.pin_btn)
        self.close_btn = TodoDelete()
        self.close_btn.setFixedSize(26, 26)
        self.close_btn.mousePressEvent = self._on_close_press
        header.addWidget(self.close_btn)
        root.addLayout(header)

        self.empty_label = QLabel("双击空白处添加待办")
        self.empty_label.setFont(QFont("Microsoft YaHei UI", 10))
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: rgba(255,255,255,130);")
        self.empty_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        root.addWidget(self.empty_label)

        self.list = TodoList(self)
        self.list.setFont(QFont("Microsoft YaHei UI", 10))
        self.list.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setStyleSheet("""
            QListWidget { background: transparent; border: none; outline: none; }
            QListWidget::item { background: transparent; border: none; }
            QListWidget::item:selected { background: rgba(255,255,255,30); }
            QScrollBar:vertical {
                background: transparent; width: 6px; margin: 2px 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,60);
                border-radius: 3px; min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,100);
            }
            QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
            QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
        """)
        self.list.setSizePolicy(QSizePolicy.Policy.Expanding,
                                QSizePolicy.Policy.Expanding)
        root.addWidget(self.list)
        self.setMinimumSize(MIN_W, MIN_H)

    # ---------------- 数据 ----------------
    def _render(self):
        self.list.clear()
        if self._todos:
            self.empty_label.hide()
            self.list.show()
            for i, td in enumerate(self._todos):
                item = QListWidgetItem()
                item.setSizeHint(QSize(200, 34))
                wgt = TodoItemWidget(
                    td["text"], td["done"],
                    on_toggle=lambda e, idx=i: self.toggle_todo(idx),
                    on_delete=lambda e, idx=i: self.delete_todo(idx))
                self.list.addItem(item)
                self.list.setItemWidget(item, wgt)
        else:
            self.list.hide()
            self.empty_label.show()

    def _ask(self, title, prompt, prefill=""):
        text, ok = QInputDialog.getText(self, title, prompt, text=prefill)
        text = text.strip()
        return text if ok and text else None

    def add_todo(self):
        text = self._ask("添加待办", "内容：")
        if text is None:
            return
        self._todos.insert(0, {"text": text, "done": False})
        self._render()
        self._save_config()

    def edit_todo(self, row):
        if not (0 <= row < len(self._todos)):
            return
        text = self._ask("编辑待办", "内容：", self._todos[row]["text"])
        if text is None:
            return
        self._todos[row]["text"] = text
        self._render()
        self._save_config()

    def toggle_todo(self, row):
        if 0 <= row < len(self._todos):
            self._todos[row]["done"] = not self._todos[row]["done"]
            self._render()
            self._save_config()

    def delete_todo(self, row):
        if 0 <= row < len(self._todos):
            del self._todos[row]
            self._render()
            self._save_config()

    def _on_pin_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        self.set_pinned(not self.pinned)
        self._save_config()

    def set_pinned(self, pinned):
        self.pinned = pinned
        self.pin_btn.set_pinned(pinned)

    def _on_close_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        self.close()

    # ---------------- 拖动与调整大小 ----------------
    def edge_at(self, pos):
        r = self.rect()
        edges = 0
        if pos.x() <= EDGE:
            edges |= 1
        if pos.x() >= r.width() - EDGE:
            edges |= 2
        if pos.y() <= EDGE:
            edges |= 4
        if pos.y() >= r.height() - EDGE:
            edges |= 8
        return edges

    def _cursor_for(self, edges):
        if edges in (1, 2):
            return Qt.CursorShape.SizeHorCursor
        if edges in (4, 8):
            return Qt.CursorShape.SizeVerCursor
        if edges in (1 | 4, 2 | 8):
            return Qt.CursorShape.SizeFDiagCursor
        if edges in (2 | 4, 1 | 8):
            return Qt.CursorShape.SizeBDiagCursor
        return Qt.CursorShape.ArrowCursor

    def _clamp_to_screen(self, geo):
        screen = QApplication.primaryScreen().availableGeometry()
        if geo.width() > screen.width():
            geo.setWidth(screen.width())
        if geo.height() > screen.height():
            geo.setHeight(screen.height())
        if geo.right() > screen.right():
            geo.moveRight(screen.right())
        if geo.left() < screen.left():
            geo.moveLeft(screen.left())
        if geo.bottom() > screen.bottom():
            geo.moveBottom(screen.bottom())
        if geo.top() < screen.top():
            geo.moveTop(screen.top())
        return geo

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        if self.pinned:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            if self._grip_hover:
                self._grip_hover = False
                self.update()
            super().mouseMoveEvent(event)
            return
        if self._edges:
            gp = event.globalPosition().toPoint()
            dx = gp.x() - self._press_global.x()
            dy = gp.y() - self._press_global.y()
            geo = QRect(self._press_geo)
            if self._edges & 1:
                geo.setLeft(self._press_geo.left() + dx)
            if self._edges & 2:
                geo.setRight(self._press_geo.right() + dx)
            if self._edges & 4:
                geo.setTop(self._press_geo.top() + dy)
            if self._edges & 8:
                geo.setBottom(self._press_geo.bottom() + dy)
            if geo.width() >= MIN_W and geo.height() >= MIN_H:
                self.setGeometry(self._clamp_to_screen(geo))
            event.accept()
            return
        if self._moving:
            target = event.globalPosition().toPoint() - self._move_off
            geo = QRect(target, self.size())
            self.move(self._clamp_to_screen(geo).topLeft())
            event.accept()
            return
        hover = pos.y() <= GRIP_H
        if hover:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(self._cursor_for(self.edge_at(pos)))
        if hover != self._grip_hover:
            self._grip_hover = hover
            self.update()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        if self.pinned:
            # 固定位置：禁止拖动与缩放，列表交互照常
            super().mousePressEvent(event)
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._moving = True
            self._move_off = event.globalPosition().toPoint() \
                - self.frameGeometry().topLeft()
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            edges = self.edge_at(pos)
            if edges:
                self._edges = edges
                self._press_global = event.globalPosition().toPoint()
                self._press_geo = QRect(self.geometry())
                event.accept()
                return
            if pos.y() <= GRIP_H + HEADER_H:  # 顶部把手 + 标题行
                self._moving = True
                self._move_off = event.globalPosition().toPoint() \
                    - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        was_resizing = self._edges != 0
        self._edges = 0
        self._moving = False
        if was_resizing:
            self._save_config()
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        self.setMask(QRegion(self.rect()))
        super().resizeEvent(event)

    # ---------------- 玻璃绘制 ----------------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, 16, 16)

        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(255, 255, 255, 72))
        grad.setColorAt(0.45, QColor(255, 255, 255, 34))
        grad.setColorAt(1.0, QColor(255, 255, 255, 20))
        p.fillPath(path, QBrush(grad))

        p.save()
        p.setClipPath(path)
        p.setPen(QPen(QColor(255, 255, 255, 120), 2.0))
        p.drawLine(0, 3, int(self.width()), 3)
        cx, cy = self.width() * 0.20, self.height() * 0.08
        radius = self.width() * 0.45
        spot = QRadialGradient(cx, cy, radius)
        spot.setColorAt(0.0, QColor(255, 255, 255, 46))
        spot.setColorAt(0.55, QColor(255, 255, 255, 12))
        spot.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillRect(QRectF(cx - radius, cy - radius, radius * 2, radius * 2),
                   QBrush(spot))
        p.setPen(QPen(QColor(255, 255, 255, 40), 1.0))
        p.drawLine(0, int(self.height()) - 3, int(self.width()),
                   int(self.height()) - 3)
        p.restore()

        p.setPen(QPen(QColor(255, 255, 255, 120), 1.2))
        p.drawPath(path)
        self._paint_grip(p)
        p.end()

    def _paint_grip(self, p):
        w = self.width()
        bar_w = 22.0
        x0 = (w - bar_w) / 2.0
        y0 = (GRIP_H - 10.0) / 2.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 36) if self._grip_hover
                   else QColor(255, 255, 255, 14))
        p.drawRoundedRect(QRectF(x0 - 8, y0 - 3, bar_w + 16, 16), 8, 8)
        p.setPen(QPen(QColor(255, 255, 255, 150) if self._grip_hover
                      else QColor(255, 255, 255, 85), 2.0,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for i in range(3):
            y = y0 + i * 4.0
            p.drawLine(QPointF(x0, y), QPointF(x0 + bar_w, y))

    def leaveEvent(self, event):
        if self._grip_hover:
            self._grip_hover = False
            self.update()
        super().leaveEvent(event)

    # ---------------- 配置持久化 ----------------
    def _load_config(self):
        geo = None
        try:
            if CONFIG_PATH.exists():
                cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                geo = cfg.get("geometry")
                todos = cfg.get("todos")
                if cfg.get("pinned"):
                    self.set_pinned(True)
                if isinstance(todos, list):
                    self._todos = [
                        {"text": str(t.get("text", "")), "done": bool(t.get("done", False))}
                        for t in todos if isinstance(t, dict) and t.get("text")
                    ]
        except Exception:
            pass
        g = None
        if geo and len(geo) == 4:
            g = QRect(geo[0], geo[1], max(geo[2], MIN_W), max(geo[3], MIN_H))
            if QApplication.screenAt(g.center()) is None:
                g = None
            else:
                g = self._clamp_to_screen(g)
        if g is not None:
            self.setGeometry(g)
        else:
            screen = QApplication.primaryScreen().availableGeometry()
            w, h = 260, 340
            self.resize(w, h)
            self.move(screen.left() + 48, screen.top() + 48)

    def _save_config(self):
        try:
            g = self._clamp_to_screen(QRect(self.geometry()))
            self.setGeometry(g)
            cfg = {
                "geometry": [g.x(), g.y(), g.width(), g.height()],
                "todos": self._todos,
                "pinned": self.pinned,
            }
            CONFIG_PATH.write_text(
                json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def closeEvent(self, event):
        self._save_config()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    w = GlassTodo()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
