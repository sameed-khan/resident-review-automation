import os
import sys
import pytesseract as pyts
import logging
import signal
import time
import traceback
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, List, Optional

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from dotenv import load_dotenv

from auto import run


class ApplicationMode(Enum):
    DRAW = auto()
    RUN = auto()
    NORMAL = auto()


class DrawingMode(Enum):
    SCROLL = auto()
    HEADER = auto()
    FIRST_ROW = auto()


@dataclass
class AppState:
    """Application state management using Python dataclass"""

    _mode: ApplicationMode = ApplicationMode.NORMAL
    _observers: List[Callable[[ApplicationMode], None]] = None
    rectangles: dict[str, tuple[int, int, int, int]] = None
    drawing_window: Optional["DrawingWindow"] = None
    main_window: Optional["MainWindow"] = None

    def __post_init__(self):
        self._observers = []
        self.rectangles = {}

    def add_observer(self, callback: Callable[[ApplicationMode], None]):
        self._observers.append(callback)

    def remove_observer(self, callback: Callable[[ApplicationMode], None]):
        if callback in self._observers:
            self._observers.remove(callback)

    @property
    def mode(self) -> ApplicationMode:
        return self._mode

    @mode.setter
    def mode(self, value: ApplicationMode):
        if self._mode != value:
            old_mode = self._mode
            self._mode = value
            self._handle_mode_transition(old_mode, value)
            for callback in self._observers:
                callback(value)

    def _handle_mode_transition(
        self, old_mode: ApplicationMode, new_mode: ApplicationMode
    ):
        if new_mode == ApplicationMode.DRAW:
            if not self.drawing_window:
                self.drawing_window = DrawingWindow(self)
        elif new_mode == ApplicationMode.RUN:
            if self.drawing_window:
                self.drawing_window.close()
                self.drawing_window = None
            if self.main_window:
                self.main_window.showMinimized()
        elif new_mode == ApplicationMode.NORMAL:
            if self.drawing_window:
                self.drawing_window.close()
                self.drawing_window = None
            if self.main_window:
                self.main_window.showNormal()


class StyledToolBar(QToolBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QToolBar {
                background-color: #f0f0f0;
                border: none;
                padding: 4px;
            }
        """)


class StyledRadioButton(QRadioButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QRadioButton {
                background-color: #f0f0f0;
                padding: 4px;
                border-radius: 4px;
            }
            QRadioButton:hover {
                background-color: #e0e0e0;
            }
        """)


class StyledPushButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                padding: 6px 12px;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)


class DrawingArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drawing = False
        self.rectangles = {
            DrawingMode.SCROLL: None,
            DrawingMode.HEADER: None,
            DrawingMode.FIRST_ROW: None,
        }
        self.global_rectangles = {
            DrawingMode.SCROLL: None,
            DrawingMode.HEADER: None,
            DrawingMode.FIRST_ROW: None,
        }
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.current_mode = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def setDrawingMode(self, mode):
        self.current_mode = mode

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.current_mode:
            self.drawing = True
            self.start_point = event.pos()
            self.end_point = self.start_point

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            self.drawing = False
            rect = QRect(self.start_point, self.end_point).normalized()
            self.rectangles[self.current_mode] = rect

            gstart_point = self.mapToGlobal(self.start_point)
            gend_point = self.mapToGlobal(self.end_point)
            grect = QRect(gstart_point, gend_point).normalized()
            self.global_rectangles[self.current_mode] = grect

            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(128, 128, 128, 64))

        pen = QPen()
        pen.setWidth(2)

        for mode, rect in self.rectangles.items():
            if rect:
                if mode == DrawingMode.SCROLL:
                    pen.setColor(QColor(0, 0, 255))
                elif mode == DrawingMode.HEADER:
                    pen.setColor(QColor(255, 255, 0))
                elif mode == DrawingMode.FIRST_ROW:
                    pen.setColor(QColor(255, 0, 0))
                painter.setPen(pen)
                painter.drawRect(rect)

        if self.drawing and self.current_mode:
            current_rect = QRect(self.start_point, self.end_point).normalized()
            if self.current_mode == DrawingMode.SCROLL:
                pen.setColor(QColor(0, 0, 255))
            elif self.current_mode == DrawingMode.HEADER:
                pen.setColor(QColor(255, 255, 0))
            elif self.current_mode == DrawingMode.FIRST_ROW:
                pen.setColor(QColor(255, 0, 0))
            painter.setPen(pen)
            painter.drawRect(current_rect)

    def getRectanglesDimensions(self):
        screen = QApplication.primaryScreen()
        device_pixel_ratio = screen.devicePixelRatio()

        dimensions = {}
        for mode, rect in self.global_rectangles.items():
            if rect:
                print(rect.x(), rect.y(), rect.width(), rect.height())
                scaled_x = int(rect.x() * device_pixel_ratio)
                scaled_y = int(rect.y() * device_pixel_ratio)
                scaled_width = int(rect.width() * device_pixel_ratio)
                scaled_height = int(rect.height() * device_pixel_ratio)

                dimensions[mode] = {
                    "x": scaled_x,
                    "y": scaled_y,
                    "width": scaled_width,
                    "height": scaled_height,
                }
        return dimensions


class DrawingWindow(QMainWindow):
    def __init__(self, app_state: AppState, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.initUI()

    def closeEvent(self, event):
        """Override close event to update state"""
        if self.app_state.mode == ApplicationMode.DRAW:
            self.app_state.mode = ApplicationMode.NORMAL
        super().closeEvent(event)

    def initUI(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.toolbar = StyledToolBar()
        self.toolbar.setFloatable(False)
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        self.scroll_radio = StyledRadioButton("Scroll Window")
        self.header_radio = StyledRadioButton("Header Row")
        self.first_row_radio = StyledRadioButton("First Row")

        self.button_group = QButtonGroup(self)
        self.button_group.addButton(self.scroll_radio)
        self.button_group.addButton(self.header_radio)
        self.button_group.addButton(self.first_row_radio)

        self.confirm_btn = StyledPushButton("Confirm")
        self.quit_btn = StyledPushButton("Quit Drawing")

        for widget in [
            self.scroll_radio,
            self.header_radio,
            self.first_row_radio,
            self.confirm_btn,
            self.quit_btn,
        ]:
            self.toolbar.addWidget(widget)

        self.drawing_area = DrawingArea()
        layout.addWidget(self.drawing_area)

        self.scroll_radio.toggled.connect(
            lambda checked: self.onModeChanged(checked, DrawingMode.SCROLL)
        )
        self.header_radio.toggled.connect(
            lambda checked: self.onModeChanged(checked, DrawingMode.HEADER)
        )
        self.first_row_radio.toggled.connect(
            lambda checked: self.onModeChanged(checked, DrawingMode.FIRST_ROW)
        )
        self.confirm_btn.clicked.connect(self.onConfirm)
        self.quit_btn.clicked.connect(self.close)

        self.showMaximized()

    def onModeChanged(self, checked, mode):
        if checked:
            self.drawing_area.setDrawingMode(mode)

    def onConfirm(self):
        dimensions = self.drawing_area.getRectanglesDimensions()
        self.app_state.rectangles = dimensions
        for mode, dims in dimensions.items():
            print(f"{mode.name}: {dims}")
        self.close()


class MainWindow(QMainWindow):
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        self.app_state.main_window = self
        self.app_state.add_observer(self.onApplicationModeChanged)
        self.initUI()

    def initUI(self):
        self.toolbar = StyledToolBar()
        self.toolbar.setFloatable(False)
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        self.draw_btn = StyledPushButton("Draw")
        self.run_btn = StyledPushButton("Run")

        self.toolbar.addWidget(self.draw_btn)
        self.toolbar.addWidget(self.run_btn)

        self.draw_btn.clicked.connect(self.toggleDrawingMode)
        self.run_btn.clicked.connect(self.setRunMode)

        self.setWindowTitle("Drawing Tool")
        self.setGeometry(100, 100, 400, 100)

    def onApplicationModeChanged(self, mode: ApplicationMode):
        self.draw_btn.setEnabled(mode == ApplicationMode.NORMAL)
        self.run_btn.setEnabled(mode == ApplicationMode.NORMAL)

    def toggleDrawingMode(self):
        if self.app_state.mode == ApplicationMode.NORMAL:
            self.app_state.mode = ApplicationMode.DRAW

    def setRunMode(self):
        self.app_state.mode = ApplicationMode.RUN
        self._run_automation()

    def _run_automation(self):
        print("COMMENCING AUTOMATION IN 5 SECONDS!")
        time.sleep(5)
        try:
            scroll_bounds = tuple(
                self.app_state.rectangles[DrawingMode.SCROLL].values()
            )
            header_bounds = tuple(
                self.app_state.rectangles[DrawingMode.HEADER].values()
            )
            run(
                scroll_bounds,
                header_bounds,
            )
        except Exception as e:
            print(f"Error running automation: {e}")
            traceback.print_exc()
        self.app_state.mode = ApplicationMode.NORMAL


def signal_handler(signum, frame):
    print("\nSignal received. Closing application...")
    QApplication.quit()


def main():
    load_dotenv()
    pyts.pytesseract.tesseract_cmd=os.getenv("TESSERACT_LOCATION")
    # signal.signal(signal.SIGINT, signal_handler)

    # app = QApplication(sys.argv)
    # app.setStyle("Fusion")

    # app_state = AppState()
    # window = MainWindow(app_state)
    # window.show()

    # print("Press Ctrl+C to exit")
    # return app.exec()

    # Dirty coordinates
    # scroll_bounds = (13, 186, 1872, 843)
    # header_bounds = (14, 188, 1867, 23)

    # Clean coordinates
    # header_bounds = (15, 185, 1870, 25)
    # scroll_bounds = (15, 185, 1870, 850)
    # run(scroll_bounds, header_bounds)

    # Dev multiscreen coordinates
    # scroll_bounds = (-1906, 210, 1900, 819)
    # header_bounds = (-1906, 189, 1900, 22)
    # run(scroll_bounds, header_bounds)

    # Prod coordinates
    scroll_bounds = (5216, 209, 1870, 827)
    header_bounds = (5215, 188, 1887, 20)
    run(scroll_bounds, header_bounds)


if __name__ == "__main__":
    start_logger = logging.getLogger('main')
    logging.basicConfig()
    logging.root.setLevel(logging.NOTSET)
    start_logger.setLevel(logging.INFO)

    start_logger.info("Automation commencing")
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    start_logger.info("Changed working directory to ../../src/main.py")
    sys.exit(main())
