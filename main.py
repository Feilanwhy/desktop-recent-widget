# -*- coding: utf-8 -*-
"""
桌面玻璃小部件 —— 显示最近打开的文件/软件，按时间从新到旧排列，双击直接打开。
顶部有锁形按钮：上锁后点击不再打开任何项目，再点一次解锁。
大小可以像窗口一样自由调整（拖动边缘/四角）；按住顶部标题行或列表空白处可拖动位置。
"""

import sys
import os
import json
import ctypes
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPoint, QRectF, QRect, QSize, QPointF, QFileSystemWatcher
from PySide6.QtGui import (QColor, QPainter, QPainterPath, QPixmap, QFont,
                           QImage, QBrush, QPen, QRegion)
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QListWidget, QListWidgetItem,
                               QAbstractItemView, QSizePolicy)

# ----------------------------------------------------------------------------
# 基础常量
# ----------------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent
if getattr(sys, "frozen", False):
    # 打包成 exe 后，配置写入系统用户目录（%APPDATA%），避免单文件模式下丢失
    DATA_DIR = Path(os.environ["APPDATA"]) / "DesktopGlassWidget"
else:
    DATA_DIR = APP_DIR
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    DATA_DIR = APP_DIR
CONFIG_PATH = DATA_DIR / "widget_config.json"
RECENT_DIR = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Recent"

EDGE = 8                 # 边缘热区宽度（像素），用于调整大小
MIN_W, MIN_H = 200, 220  # 最小尺寸
MAX_ITEMS = 30           # 最多显示多少条最近记录
REFRESH_MS = 30_000      # 兜底自动刷新间隔（毫秒）；主刷新靠文件系统监听，几乎即时
HEADER_H = 34            # 顶部栏高度

GLASS_BORDER = QColor(255, 255, 255, 80)  # 玻璃描边（纯透明背景只保留这条轮廓）

# ----------------------------------------------------------------------------
# 最近记录收集：读取 Windows「最近访问」文件夹里的 .lnk 快捷方式
# ----------------------------------------------------------------------------
def collect_recent(limit=MAX_ITEMS):
    """返回按打开时间从新到旧排列的最近记录列表。"""
    items = []
    try:
        if RECENT_DIR.exists():
            for lnk in RECENT_DIR.iterdir():
                if lnk.suffix.lower() != ".lnk":
                    continue
                try:
                    st = lnk.stat()
                    items.append({"mtime": st.st_mtime, "name": lnk.stem, "path": str(lnk)})
                except OSError:
                    continue
    except OSError:
        pass
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items[:limit]

# ----------------------------------------------------------------------------
# 图标提取：用 Shell API 拿到快捷方式对应的文件/软件图标
# ----------------------------------------------------------------------------
class _SHFILEINFO(ctypes.Structure):
    _fields_ = [
        ("hIcon", ctypes.c_void_p),
        ("iIcon", ctypes.c_int),
        ("dwAttributes", ctypes.c_uint),
        ("szDisplayName", ctypes.c_wchar * 260),
        ("szTypeName", ctypes.c_wchar * 80),
    ]

_icon_cache = {}

def icon_for(path, size=32):
    if path in _icon_cache:
        return _icon_cache[path]
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    try:
        sfi = _SHFILEINFO()
        # SHGFI_ICON(0x100) | SHGFI_LARGEICON(0x0)
        ret = ctypes.windll.shell32.SHGetFileInfoW(
            path, 0, ctypes.byref(sfi), ctypes.sizeof(sfi), 0x100)
        if ret and sfi.hIcon:
            img = QImage.fromHICON(int(sfi.hIcon))
            if not img.isNull():
                pm = QPixmap.fromImage(img).scaled(
                    size, size, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
            ctypes.windll.user32.DestroyIcon(ctypes.c_void_p(sfi.hIcon))
    except Exception:
        pass
    _icon_cache[path] = pm
    return pm

# ----------------------------------------------------------------------------
# 锁形按钮：用 QPainter 手绘，上锁/解锁两种状态
# ----------------------------------------------------------------------------
class LockButton(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(26, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("点击锁定：锁定后点击列表不会打开任何项目；再点一次解锁")
        self.locked = False
        self._color = QColor(255, 255, 255, 210)

    def set_locked(self, locked):
        self.locked = locked
        self._color = QColor(255, 179, 0) if locked else QColor(255, 255, 255, 210)
        self.setToolTip("已锁定，点击解锁" if locked
                        else "点击锁定：锁定后点击列表不会打开任何项目")
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        bw, bh = 16.0, 13.0
        bx, by = (w - bw) / 2.0, (h - bh) / 2.0 + 3.0
        pen = QPen(self._color, 2.2, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)

        # 锁梁（圆弧）：锁定 = 扣入锁体；解锁 = 悬空打开
        arc = QRectF(bx + 4.5, by - 10.5, bw - 9.0, 14.0)
        if self.locked:
            p.drawArc(arc, 0, 180 * 16)
        else:
            p.drawArc(arc, 20 * 16, 160 * 16)

        # 锁体：锁定 = 实心填充；解锁 = 空心描边
        body = QPainterPath()
        body.addRoundedRect(QRectF(bx, by, bw, bh), 3.0, 3.0)
        if self.locked:
            p.fillPath(body, QBrush(self._color))
        else:
            p.drawPath(body)

        # 锁孔
        hole_pen = QPen(QColor(24, 24, 30), 1.6,
                        Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(hole_pen)
        cx = bx + bw / 2.0
        p.drawLine(QPointF(cx, by + 3.5), QPointF(cx, by + 8.0))
        p.drawEllipse(QRectF(cx - 2.0, by + 6.5, 4.0, 4.0))
        p.end()


# ----------------------------------------------------------------------------
# 关闭按钮：画一个 X，悬停时变红
# ----------------------------------------------------------------------------
class CloseButton(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(26, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("关闭小部件")
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
        color = QColor(255, 90, 90) if self._hover else QColor(255, 255, 255, 210)
        pen = QPen(color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        m = 7.0
        p.drawLine(QPointF(m, m), QPointF(self.width() - m, self.height() - m))
        p.drawLine(QPointF(self.width() - m, m), QPointF(m, self.height() - m))
        p.end()

# ----------------------------------------------------------------------------
# 列表控件：锁定状态下点击不产生任何反应
# ----------------------------------------------------------------------------
class RecentList(QListWidget):
    def __init__(self, owner):
        super().__init__()
        self._owner = owner
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if self._owner.locked:
            event.ignore()
            return
        # indexAt 需要视口坐标
        lp = self.viewport().mapFrom(self, event.position().toPoint())
        if not self.indexAt(lp).isValid():
            # 列表空白处不处理，冒泡给父窗口用于拖动窗口
            event.ignore()
            return
        super().mousePressEvent(event)

# ----------------------------------------------------------------------------
# 主体窗口
# ----------------------------------------------------------------------------
class GlassWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.locked = False
        self._edges = 0
        self._moving = False
        self._move_off = QPoint()
        self._press_global = QPoint()
        self._press_geo = QRect()

        # 无边框 + 工具窗（不占任务栏）+ 始终停在桌面底层
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.Tool
                            | Qt.WindowType.WindowStaysOnBottomHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("最近打开")
        self.setMouseTracking(True)

        self._build_ui()
        self._load_config()
        self._refresh()

        # 文件系统监听：Windows「最近访问」目录一变就立刻刷新，打开文件后几乎即时出现
        self._watcher = QFileSystemWatcher(self)
        try:
            if RECENT_DIR.exists():
                self._watcher.addPath(str(RECENT_DIR))
        except Exception:
            pass
        self._watcher.directoryChanged.connect(self._refresh)

        # 兜底：每 30 秒自动刷新一次，防止个别情况下监听漏掉
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(REFRESH_MS)

        # 纯透明窗口必须强制声明整个矩形为可点击区域，
        # 否则 Windows 会把没有内容的透明部分判定为“可穿透”，导致无法拖动/缩放
        self.setMask(QRegion(self.rect()))

    # ---------------- 界面 ----------------
    def _build_ui(self):
        font = QFont("Microsoft YaHei UI", 10)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 10)
        root.setSpacing(4)

        # 顶部栏：标题居中，右侧是锁 + 关闭按钮
        header = QHBoxLayout()
        header.setSpacing(4)
        # 左侧占位与右侧按钮区等宽，保证标题文字真正居中
        header.addSpacing(26 + 4 + 26)
        header.addStretch(1)
        self.title_label = QLabel("最近打开")
        self.title_label.setFont(QFont("Microsoft YaHei UI", 9))
        self.title_label.setStyleSheet(
            "color: rgba(255,255,255,220); background: transparent;")
        # 关键：标题文字不“吃掉”鼠标事件，按在标题上也能拖动窗口
        self.title_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        header.addWidget(self.title_label)
        header.addStretch(1)
        self.lock_btn = LockButton()
        self.lock_btn.mousePressEvent = self._on_lock_press
        header.addWidget(self.lock_btn)
        self.close_btn = CloseButton()
        self.close_btn.mousePressEvent = self._on_close_press
        header.addWidget(self.close_btn)
        root.addLayout(header)

        # 空状态提示
        self.empty_label = QLabel("暂无最近记录\n（打开几个文件后会自动出现）")
        self.empty_label.setFont(font)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: rgba(255,255,255,120);")
        self.empty_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.empty_label.hide()
        root.addWidget(self.empty_label)

        # 列表
        self.list = RecentList(self)
        self.list.setFont(font)
        self.list.setIconSize(QSize(30, 30))
        self.list.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._LIST_SS = """
            QListWidget {
                background: transparent; border: none; outline: none;
                padding: 2px;
            }
            QListWidget::item {
                color: rgba(255,255,255,235);
                padding: 5px 8px;
                border-radius: 8px;
                margin: 1px 0;
            }
            QListWidget::item:hover {
                background: rgba(255,255,255,26);
            }
            QListWidget::item:selected {
                background: rgba(255,255,255,42);
                color: #FFFFFF;
            }
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
        """
        self.list.setStyleSheet(self._LIST_SS)
        self.list.setSizePolicy(QSizePolicy.Policy.Expanding,
                                QSizePolicy.Policy.Expanding)
        # 双击打开；单击只做选中
        self.list.itemDoubleClicked.connect(self._open_item)
        root.addWidget(self.list)

        self.setMinimumSize(MIN_W, MIN_H)

    # ---------------- 数据 ----------------
    def _refresh(self):
        items = collect_recent(MAX_ITEMS)
        self.list.clear()
        if items:
            self.empty_label.hide()
            self.list.show()
            for it in items:
                item = QListWidgetItem(icon_for(it["path"]), it["name"])
                item.setData(Qt.ItemDataRole.UserRole, it["path"])
                item.setToolTip(it["path"])
                self.list.addItem(item)
        else:
            self.list.hide()
            self.empty_label.show()

    def _open_item(self, item):
        if self.locked:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.exists(path):
            try:
                os.startfile(path)
            except OSError:
                pass

    def _on_lock_press(self, event):
        self.set_locked(not self.locked)
        self._save_config()

    def _on_close_press(self, event):
        self.close()

    def set_locked(self, locked):
        self.locked = locked
        self.lock_btn.set_locked(locked)
        # 锁定时让列表文字微微变暗，解锁恢复
        if locked:
            self.list.setStyleSheet(self._LIST_SS + """
                QListWidget::item { color: rgba(255,255,255,150); }
                QListWidget::item:hover { background: transparent; }
            """)
        else:
            self.list.setStyleSheet(self._LIST_SS)

    # ---------------- 拖动与调整大小 ----------------
    def edge_at(self, pos):
        r = self.rect()
        edges = 0
        if pos.x() <= EDGE:
            edges |= 1   # 左
        if pos.x() >= r.width() - EDGE:
            edges |= 2   # 右
        if pos.y() <= EDGE:
            edges |= 4   # 上
        if pos.y() >= r.height() - EDGE:
            edges |= 8   # 下
        return edges

    def _cursor_for(self, edges):
        if edges in (1, 2):          # 左右
            return Qt.CursorShape.SizeHorCursor
        if edges in (4, 8):          # 上下
            return Qt.CursorShape.SizeVerCursor
        if edges in (1 | 4, 2 | 8):  # 左上 / 右下
            return Qt.CursorShape.SizeFDiagCursor
        if edges in (2 | 4, 1 | 8):  # 右上 / 左下
            return Qt.CursorShape.SizeBDiagCursor
        return Qt.CursorShape.ArrowCursor

    def _clamp_to_screen(self, geo):
        """把窗口几何完全限制在屏幕可用区域内，永远无法拖出屏幕。"""
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
        # 正在调整大小
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
        # 正在拖动位置
        if self._moving:
            target = event.globalPosition().toPoint() - self._move_off
            geo = QRect(target, self.size())
            self.move(self._clamp_to_screen(geo).topLeft())
            event.accept()
            return
        # 悬停时切换调整大小的鼠标样式
        self.setCursor(self._cursor_for(self.edge_at(pos)))
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        if event.button() == Qt.MouseButton.LeftButton:
            edges = self.edge_at(pos)
            if edges:
                self._edges = edges
                self._press_global = event.globalPosition().toPoint()
                self._press_geo = QRect(self.geometry())
                event.accept()
                return
            # 拖动热区：顶部标题整行，以及列表的空白区域
            if self._is_drag_area(pos):
                self._moving = True
                self._move_off = event.globalPosition().toPoint() \
                    - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def _is_drag_area(self, pos):
        """返回该位置是否可以作为窗口拖动热区（避开按钮、边缘、列表条目）。"""
        if self.lock_btn.geometry().contains(pos) \
                or self.close_btn.geometry().contains(pos):
            return False
        if pos.y() <= HEADER_H:
            return True  # 顶部整行（含标题文字）都能拖
        if self.list.geometry().contains(pos):
            lp = self.list.viewport().mapFrom(self, pos)
            if not self.list.indexAt(lp).isValid():
                return True  # 列表空白处也能拖
        return False

    def mouseReleaseEvent(self, event):
        was_resizing = self._edges != 0
        self._edges = 0
        self._moving = False
        if was_resizing:
            self._save_config()
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        # 尺寸变化后同步刷新可点击区域
        self.setMask(QRegion(self.rect()))
        super().resizeEvent(event)

    # ---------------- 玻璃绘制 ----------------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, 14, 14)
        # 纯透明：不填充任何底色，只描边勾勒出长条轮廓
        p.setPen(QPen(GLASS_BORDER, 1.0))
        p.drawPath(path)
        p.end()

    # ---------------- 配置持久化 ----------------
    def _load_config(self):
        geo = None
        try:
            if CONFIG_PATH.exists():
                cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                geo = cfg.get("geometry")
                if cfg.get("locked"):
                    self.set_locked(True)
        except Exception:
            pass
        g = None
        if geo and len(geo) == 4:
            g = QRect(geo[0], geo[1], max(geo[2], MIN_W), max(geo[3], MIN_H))
            # 如果保存的位置中心不在任何屏幕内（上次退出时窗口在屏幕外），
            # 回退到默认位置，避免窗口“卡出屏幕”找不到
            if QApplication.screenAt(g.center()) is None:
                g = None
            else:
                g = self._clamp_to_screen(g)
        if g is not None:
            self.setGeometry(g)
        else:
            screen = QApplication.primaryScreen().availableGeometry()
            w, h = 280, 460
            self.resize(w, h)
            self.move(screen.right() - w - 32, screen.top() + 32)

    def _save_config(self):
        try:
            g = self._clamp_to_screen(QRect(self.geometry()))
            self.setGeometry(g)  # 同步实际位置，防止分辨率变化后落在屏幕外
            cfg = {
                "geometry": [g.x(), g.y(), g.width(), g.height()],
                "locked": self.locked,
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
    w = GlassWidget()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
