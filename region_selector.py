
from PyQt5.QtWidgets import QWidget, QApplication, QLabel
from PyQt5.QtCore import Qt, QRect, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen

class RegionSelector(QWidget):
    """用于选择截图区域的PyQt5窗口"""

    selection_completed = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        self.selected_region = None
        self.begin = None
        self.end = None
        self.initUI()

    def initUI(self):
        # 设置窗口标志以确保窗口始终在顶部并捕获所有事件
        self.setWindowFlags(
            Qt.FramelessWindowHint |  # 无窗口框架
            Qt.WindowStaysOnTopHint |  # 始终在顶部
            Qt.Tool  # 不显示在任务栏
        )

        # 设置半透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 150);")  # 黑色半透明覆盖层
        self.setMouseTracking(True)  # 追踪鼠标移动

        # 获取屏幕几何并设置窗口覆盖整个屏幕
        screen = QApplication.desktop().screenGeometry()
        self.setGeometry(screen)

        # 添加指示标签
        self.label = QLabel("点击并拖动选择截图区域", self)
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                padding: 5px;
                background-color: transparent;
                border-radius: 5px;
            }
        """)
        self.label.adjustSize()
        self.label.move(screen.width()//2 - self.label.width()//2, 50)

        # 确保窗口激活并抓取所有输入
        self.activateWindow()
        self.raise_()
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)

        if self.begin and self.end:
            # 创建选择矩形
            rect = QRect(self.begin, self.end)
            normalized_rect = rect.normalized()

            # 绘制半透明黑色覆盖层
            painter.fillRect(self.rect(), QColor(0, 0, 0, 150))

            # 清除选择区域（使其透明）
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(normalized_rect, Qt.transparent)

            # 绘制选择边框
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(0, 174, 255), 2, Qt.SolidLine))  # 蓝色边框
            painter.drawRect(normalized_rect)

            # 绘制选择句柄
            handle_size = 6
            handle_color = QColor(0, 174, 255)
            painter.setBrush(handle_color)

            # 在每个角和中点绘制句柄
            handles = [
                QRect(normalized_rect.left() - handle_size//2, normalized_rect.top() - handle_size//2, handle_size, handle_size),
                QRect(normalized_rect.right() - handle_size//2, normalized_rect.top() - handle_size//2, handle_size, handle_size),
                QRect(normalized_rect.left() - handle_size//2, normalized_rect.bottom() - handle_size//2, handle_size, handle_size),
                QRect(normalized_rect.right() - handle_size//2, normalized_rect.bottom() - handle_size//2, handle_size, handle_size),
                QRect(normalized_rect.center().x() - handle_size//2, normalized_rect.top() - handle_size//2, handle_size, handle_size),
                QRect(normalized_rect.center().x() - handle_size//2, normalized_rect.bottom() - handle_size//2, handle_size, handle_size),
                QRect(normalized_rect.left() - handle_size//2, normalized_rect.center().y() - handle_size//2, handle_size, handle_size),
                QRect(normalized_rect.right() - handle_size//2, normalized_rect.center().y() - handle_size//2, handle_size, handle_size)
            ]

            for handle in handles:
                painter.drawRect(handle)

            # 绘制尺寸指示
            size_text = f"{normalized_rect.width()} x {normalized_rect.height()}"
            painter.setPen(Qt.white)
            painter.setFont(self.font())
            text_rect = painter.fontMetrics().boundingRect(size_text)
            text_x = normalized_rect.center().x() - text_rect.width() // 2
            text_y = normalized_rect.bottom() + 20
            painter.drawText(text_x, text_y, size_text)
        else:
            # 仅绘制半透明覆盖层
            painter.fillRect(self.rect(), QColor(0, 0, 0, 150))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.begin = event.pos()
            self.end = self.begin
            self.update()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:  # 仅在左键按下时更新
            self.end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.begin and self.end:
            self.selected_region = self.get_region()
            if self.selected_region:
                self.selection_completed.emit(self.selected_region)
            self.close()

    def keyPressEvent(self, event):
        # 允许ESC键取消
        if event.key() == Qt.Key_Escape:
            self.releaseMouse()
            self.close()

    def get_region(self):
        if self.begin and self.end:
            return (
                min(self.begin.x(), self.end.x()),
                min(self.begin.y(), self.end.y()),
                abs(self.end.x() - self.begin.x()),
                abs(self.end.y() - self.begin.y())
            )
        return None