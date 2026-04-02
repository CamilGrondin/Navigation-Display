import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import List, cast

from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer, QUrl
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover - optional dependency
    QWebEngineView = None


ALIGN_CENTER = getattr(Qt, 'AlignCenter', getattr(getattr(Qt, 'AlignmentFlag', Qt), 'AlignCenter'))
ALIGN_LEFT = getattr(Qt, 'AlignLeft', getattr(getattr(Qt, 'AlignmentFlag', Qt), 'AlignLeft'))
ALIGN_RIGHT = getattr(Qt, 'AlignRight', getattr(getattr(Qt, 'AlignmentFlag', Qt), 'AlignRight'))
ALIGN_VCENTER = getattr(Qt, 'AlignVCenter', getattr(getattr(Qt, 'AlignmentFlag', Qt), 'AlignVCenter'))
ALIGN_TOP = getattr(Qt, 'AlignTop', getattr(getattr(Qt, 'AlignmentFlag', Qt), 'AlignTop'))
STRONG_FOCUS = getattr(Qt, 'StrongFocus', getattr(getattr(Qt, 'FocusPolicy', Qt), 'StrongFocus'))
NO_CONTEXT_MENU = getattr(Qt, 'NoContextMenu', getattr(getattr(Qt, 'ContextMenuPolicy', Qt), 'NoContextMenu'))
VERTICAL_ORIENTATION = getattr(Qt, 'Vertical', getattr(getattr(Qt, 'Orientation', Qt), 'Vertical'))
FLAT_CAP_STYLE = getattr(Qt, 'FlatCap', getattr(getattr(Qt, 'PenCapStyle', Qt), 'FlatCap'))

KEY_UP = getattr(Qt, 'Key_Up', getattr(getattr(Qt, 'Key', Qt), 'Key_Up'))
KEY_DOWN = getattr(Qt, 'Key_Down', getattr(getattr(Qt, 'Key', Qt), 'Key_Down'))
KEY_RIGHT = getattr(Qt, 'Key_Right', getattr(getattr(Qt, 'Key', Qt), 'Key_Right'))
KEY_LEFT = getattr(Qt, 'Key_Left', getattr(getattr(Qt, 'Key', Qt), 'Key_Left'))
KEY_W = getattr(Qt, 'Key_W', getattr(getattr(Qt, 'Key', Qt), 'Key_W'))
KEY_S = getattr(Qt, 'Key_S', getattr(getattr(Qt, 'Key', Qt), 'Key_S'))
KEY_E = getattr(Qt, 'Key_E', getattr(getattr(Qt, 'Key', Qt), 'Key_E'))
KEY_D = getattr(Qt, 'Key_D', getattr(getattr(Qt, 'Key', Qt), 'Key_D'))
KEY_R = getattr(Qt, 'Key_R', getattr(getattr(Qt, 'Key', Qt), 'Key_R'))
KEY_F = getattr(Qt, 'Key_F', getattr(getattr(Qt, 'Key', Qt), 'Key_F'))
KEY_T = getattr(Qt, 'Key_T', getattr(getattr(Qt, 'Key', Qt), 'Key_T'))
KEY_G = getattr(Qt, 'Key_G', getattr(getattr(Qt, 'Key', Qt), 'Key_G'))
KEY_I = getattr(Qt, 'Key_I', getattr(getattr(Qt, 'Key', Qt), 'Key_I'))
KEY_K = getattr(Qt, 'Key_K', getattr(getattr(Qt, 'Key', Qt), 'Key_K'))
KEY_Y = getattr(Qt, 'Key_Y', getattr(getattr(Qt, 'Key', Qt), 'Key_Y'))
KEY_H = getattr(Qt, 'Key_H', getattr(getattr(Qt, 'Key', Qt), 'Key_H'))
KEY_U = getattr(Qt, 'Key_U', getattr(getattr(Qt, 'Key', Qt), 'Key_U'))
KEY_J = getattr(Qt, 'Key_J', getattr(getattr(Qt, 'Key', Qt), 'Key_J'))
KEY_O = getattr(Qt, 'Key_O', getattr(getattr(Qt, 'Key', Qt), 'Key_O'))
KEY_A = getattr(Qt, 'Key_A', getattr(getattr(Qt, 'Key', Qt), 'Key_A'))
KEY_Z = getattr(Qt, 'Key_Z', getattr(getattr(Qt, 'Key', Qt), 'Key_Z'))
KEY_X = getattr(Qt, 'Key_X', getattr(getattr(Qt, 'Key', Qt), 'Key_X'))
KEY_C = getattr(Qt, 'Key_C', getattr(getattr(Qt, 'Key', Qt), 'Key_C'))
KEY_V = getattr(Qt, 'Key_V', getattr(getattr(Qt, 'Key', Qt), 'Key_V'))
KEY_L = getattr(Qt, 'Key_L', getattr(getattr(Qt, 'Key', Qt), 'Key_L'))
KEY_PAGE_UP = getattr(Qt, 'Key_PageUp', getattr(getattr(Qt, 'Key', Qt), 'Key_PageUp'))
KEY_PAGE_DOWN = getattr(Qt, 'Key_PageDown', getattr(getattr(Qt, 'Key', Qt), 'Key_PageDown'))
KEY_M = getattr(Qt, 'Key_M', getattr(getattr(Qt, 'Key', Qt), 'Key_M'))
KEY_N = getattr(Qt, 'Key_N', getattr(getattr(Qt, 'Key', Qt), 'Key_N'))


MODE_JOYSTICK = 1
MODE_XPLANE = 2
MODE_MSP = 3

MODE_MANUAL = MODE_JOYSTICK
MODE_CRUISE = MODE_XPLANE
MODE_STRESS = MODE_MSP


def _clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def _normalize_heading(value):
    return value % 360


@dataclass
class WaypointInfo:
    name: str
    distance_nm: float = 0.0
    ete_min: float = 0.0
    altitude_constraint: str = ''
    is_active: bool = False


@dataclass
class EngineTelemetry:
    rpm: float = 0.0
    load: float = 0.0
    fflow: float = 0.0
    oil_psi: float = 0.0
    oil_temp: float = 50.0
    egt: float = 1000.0
    fuel_temp_left: float = -40.0
    fuel_temp_right: float = -40.0
    fuel_qty_L: float = 0.0
    fuel_qty_R: float = 0.0
    heading: float = 0.0
    track: float = 0.0
    ground_speed: float = 0.0
    true_airspeed: float = 0.0
    lat: float = 38.0
    lon: float = 25.0

    def as_dict(self):
        return {
            'rpm': self.rpm,
            'load': self.load,
            'fflow': self.fflow,
            'oil_psi': self.oil_psi,
            'oil_temp': self.oil_temp,
            'egt': self.egt,
            'fuel_temp_left': self.fuel_temp_left,
            'fuel_temp_right': self.fuel_temp_right,
            'fuel_qty_L': self.fuel_qty_L,
            'fuel_qty_R': self.fuel_qty_R,
            'heading': self.heading,
            'track': self.track,
            'ground_speed': self.ground_speed,
            'true_airspeed': self.true_airspeed,
            'lat': self.lat,
            'lon': self.lon,
        }


class ManualEngineSource:

    def __init__(self, display):
        self.display = display

    def poll(self):
        return EngineTelemetry(
            rpm=self.display.rpm,
            load=self.display.load,
            fflow=self.display.fflow,
            oil_psi=self.display.oil_psi,
            oil_temp=self.display.oil_temp,
            egt=self.display.egt,
            fuel_temp_left=self.display.fuel_temp_left,
            fuel_temp_right=self.display.fuel_temp_right,
            fuel_qty_L=self.display.fuel_qty_L,
            fuel_qty_R=self.display.fuel_qty_R,
            heading=self.display.heading,
            track=self.display.track,
            ground_speed=self.display.ground_speed,
            true_airspeed=self.display.true_airspeed,
            lat=self.display.lat,
            lon=self.display.lon,
        ).as_dict()


class CruiseEngineSource:

    def __init__(self):
        self.t0 = time.monotonic()

    def poll(self):
        t = time.monotonic() - self.t0
        heading = _normalize_heading(110.0 + 35.0 * math.sin(t * 0.10))
        track = _normalize_heading(heading + 3.0 * math.sin(t * 0.17))
        return EngineTelemetry(
            rpm=2100.0 + 180.0 * math.sin(t * 0.20),
            load=62.0 + 10.0 * math.sin(t * 0.27),
            fflow=8.8 + 0.7 * math.sin(t * 0.23),
            oil_psi=58.0 + 6.0 * math.sin(t * 0.21),
            oil_temp=190.0 + 12.0 * math.sin(t * 0.18),
            egt=1310.0 + 40.0 * math.sin(t * 0.24),
            fuel_temp_left=58.0 + 4.0 * math.sin(t * 0.14),
            fuel_temp_right=60.0 + 4.5 * math.sin(t * 0.16),
            fuel_qty_L=58.0 + 6.0 * math.sin(t * 0.03),
            fuel_qty_R=54.0 + 5.0 * math.sin(t * 0.032),
            heading=heading,
            track=track,
            ground_speed=142.0 + 6.0 * math.sin(t * 0.15),
            true_airspeed=138.0 + 5.0 * math.sin(t * 0.13),
            lat=38.0 + 0.08 * math.sin(t * 0.01),
            lon=25.0 + 0.10 * math.cos(t * 0.01),
        ).as_dict()


class StressEngineSource:

    def __init__(self):
        self.t0 = time.monotonic()

    def poll(self):
        t = time.monotonic() - self.t0
        heading = _normalize_heading(240.0 + 90.0 * math.sin(t * 0.22))
        track = _normalize_heading(heading - 10.0 + 8.0 * math.sin(t * 0.41))
        return EngineTelemetry(
            rpm=2680.0 + 240.0 * math.sin(t * 0.65),
            load=84.0 + 12.0 * math.sin(t * 0.55),
            fflow=14.5 + 2.2 * math.sin(t * 0.48),
            oil_psi=26.0 + 10.0 * math.sin(t * 0.92),
            oil_temp=255.0 + 20.0 * math.sin(t * 0.60),
            egt=1580.0 + 120.0 * math.sin(t * 0.72),
            fuel_temp_left=112.0 + 18.0 * math.sin(t * 0.53),
            fuel_temp_right=116.0 + 20.0 * math.sin(t * 0.59),
            fuel_qty_L=22.0 + 8.0 * math.sin(t * 0.08),
            fuel_qty_R=18.0 + 7.0 * math.sin(t * 0.09),
            heading=heading,
            track=track,
            ground_speed=171.0 + 13.0 * math.sin(t * 0.37),
            true_airspeed=167.0 + 12.0 * math.sin(t * 0.33),
            lat=38.0 + 0.22 * math.sin(t * 0.03),
            lon=25.0 + 0.24 * math.cos(t * 0.03),
        ).as_dict()


class RPMGauge(QWidget):
    def __init__(self, min_val=0, max_val=3000, title='RPM', unit='RPM'):
        super().__init__()
        self.min_val = min_val
        self.max_val = max_val
        self.value = min_val
        self.title = title
        self.unit = unit
        self.step_count = 6
        self.red_zone_threshold = None
        if self.title.upper() == 'RPM':
            interval = (self.max_val - self.min_val) / self.step_count
            self.red_zone_threshold = self.max_val - 1.5 * interval
        self.setMinimumSize(198, 162)

    def setValue(self, value):
        self.value = max(self.min_val, min(self.max_val, value))
        self.update()

    def paintEvent(self, a0):
        del a0
        w = self.width()
        h = self.height()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor('black'))

        cx = w / 2.0
        cy = h * 0.65
        radius = min(w, h) * 0.45
        arc_pen = QPen(QColor('green'))
        arc_pen.setWidth(4)
        painter.setPen(arc_pen)
        arc_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        painter.drawArc(arc_rect, 0, 180 * 16)

        if self.red_zone_threshold is not None:
            red_pen = QPen(QColor('red'))
            red_pen.setWidth(arc_pen.width())
            painter.setPen(red_pen)
            span_fraction = (self.max_val - self.red_zone_threshold) / (self.max_val - self.min_val)
            span_degrees = span_fraction * 180
            painter.drawArc(arc_rect, 0, int(span_degrees * 16))
            painter.setPen(arc_pen)

        tick_pen = QPen(QColor('green'))
        tick_pen.setWidth(3)
        red_tick_pen = QPen(QColor('red'))
        red_tick_pen.setWidth(tick_pen.width())
        step_value = (self.max_val - self.min_val) / self.step_count

        for i in range(self.step_count + 1):
            value_at_tick = self.min_val + i * step_value
            use_red = self.red_zone_threshold is not None and value_at_tick >= self.red_zone_threshold
            painter.setPen(red_tick_pen if use_red else tick_pen)

            angle_deg = 180 - i * (180 / self.step_count)
            angle_rad = math.radians(angle_deg)
            outer = QPointF(
                cx + (radius - arc_pen.width() / 2) * math.cos(angle_rad),
                cy - (radius - arc_pen.width() / 2) * math.sin(angle_rad),
            )
            inner = QPointF(
                cx + (radius - arc_pen.width() / 2 - 12) * math.cos(angle_rad),
                cy - (radius - arc_pen.width() / 2 - 12) * math.sin(angle_rad),
            )
            painter.drawLine(outer, inner)

            if i in (0, self.step_count):
                label_font = QFont('Arial', 12, QFont.Bold)
                painter.setFont(label_font)
                text = str(int(value_at_tick))
                fm = painter.fontMetrics()
                text_width = fm.horizontalAdvance(text)
                label_radius = radius - arc_pen.width() / 2
                lx = cx + label_radius * math.cos(angle_rad) - text_width / 2
                ly = cy + fm.height() + 8
                painter.setPen(QPen(QColor('white')))
                painter.drawText(int(lx), int(ly), text)
                painter.setPen(tick_pen)
                painter.setFont(QFont('Arial', 8))

        painter.setPen(QPen(QColor('white'), 3))
        ratio = (self.value - self.min_val) / (self.max_val - self.min_val) if self.max_val != self.min_val else 0
        ratio = max(0.0, min(1.0, ratio))
        angle = math.radians(180 - ratio * 180)
        pointer_radius = radius - arc_pen.width() / 2
        x_tip = cx + pointer_radius * math.cos(angle)
        y_tip = cy - pointer_radius * math.sin(angle)
        painter.drawLine(QPointF(cx, cy), QPointF(x_tip, y_tip))

        dx = x_tip - cx
        dy = y_tip - cy
        length = math.hypot(dx, dy) or 1
        ux = dx / length
        uy = dy / length
        perp_x = -uy
        perp_y = ux
        diamond_length = 14
        diamond_width = 10
        forward = QPointF(x_tip + ux * (diamond_length / 2), y_tip + uy * (diamond_length / 2))
        backward = QPointF(x_tip - ux * (diamond_length / 2), y_tip - uy * (diamond_length / 2))
        left = QPointF(x_tip + perp_x * (diamond_width / 2), y_tip + perp_y * (diamond_width / 2))
        right = QPointF(x_tip - perp_x * (diamond_width / 2), y_tip - perp_y * (diamond_width / 2))
        painter.setBrush(QColor(0, 0, 0, 0))
        painter.setPen(QPen(QColor('white'), 2))
        painter.drawPolygon(QPolygonF([forward, left, backward, right]))

        painter.setPen(QPen(QColor('white')))
        title_font = QFont('Arial', 14, QFont.Bold)
        painter.setFont(title_font)
        painter.drawText(QRectF(0, cy + 12, w, 28), ALIGN_CENTER, self.title)

        value_font = QFont('Arial', 16, QFont.Bold)
        painter.setFont(value_font)
        value_text = f"{int(self.value)} {self.unit}" if self.unit else str(int(self.value))
        painter.drawText(QRectF(0, cy + 38, w, 28), ALIGN_CENTER, value_text)


class BarGauge(QWidget):
    def __init__(self, label, min_val, max_val, unit, orientation='horizontal'):
        super().__init__()
        self.label_text = label
        self.min_val = min_val
        self.max_val = max_val
        self.unit = unit
        self.value = int((min_val + max_val) / 2)

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        self.label = QLabel(label)
        self.label.setFont(QFont('Arial', 8))
        self.label.setStyleSheet('color: white')
        self.label.setAlignment(ALIGN_CENTER)

        self.bar = QProgressBar()
        if orientation == 'vertical':
            self.bar.setOrientation(VERTICAL_ORIENTATION)
            self.bar.setFixedSize(36, 180)
        else:
            self.bar.setFixedSize(198, 22)
        self.bar.setRange(self.min_val, self.max_val)
        self.bar.setValue(self.value)
        self.bar.setTextVisible(False)
        self._set_color(self.value)

        self.value_label = QLabel(f"{self.value} {self.unit}")
        self.value_label.setFont(QFont('Arial', 9))
        self.value_label.setStyleSheet('color: white')
        self.value_label.setAlignment(ALIGN_CENTER)

        layout.addWidget(self.label)
        layout.addWidget(self.bar, alignment=ALIGN_CENTER)
        layout.addWidget(self.value_label)
        self.setLayout(layout)

    def set_value(self, value):
        self.value = int(max(self.min_val, min(self.max_val, value)))
        self.bar.setValue(self.value)
        self.value_label.setText(f"{self.value} {self.unit}")
        self._set_color(self.value)

    def _set_color(self, value):
        color = 'green'
        lab = self.label_text.upper()
        if lab == 'FFLOW':
            color = 'green' if 0 <= value < 10 else 'orange' if value < 15 else 'red'
        elif lab == 'OIL PSI':
            color = 'red' if value < 20 or value > 80 else 'green'
        elif lab == 'OIL TEMP':
            color = 'red' if value < 100 or value > 250 else 'green'
        elif lab == 'EGT':
            color = 'green' if value < 1200 else 'orange' if value < 1500 else 'red'
        elif lab == 'VAC':
            color = 'green' if value > 15 else 'orange' if value > 10 else 'red'
        self.bar.setStyleSheet(
            f"QProgressBar::chunk {{ background-color: {color}; }}"
            " QProgressBar { border: 1px solid #444; background: black; }"
        )


class ValueDisplay(QWidget):
    def __init__(self, label, unit=''):
        super().__init__()
        self.unit = unit
        self.value = 0.0

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 4, 4, 4)
        layout.setSpacing(10)

        self.label = QLabel(label)
        self.label.setFont(QFont('Arial', 12, QFont.Bold))
        self.label.setStyleSheet('color: white')
        self.label.setAlignment(ALIGN_VCENTER | ALIGN_LEFT)

        self.value_label = QLabel('0.0')
        value_font = QFont('Arial', 24, QFont.Bold)
        self.value_label.setFont(value_font)
        self.value_label.setStyleSheet('color: white')
        self.value_label.setAlignment(ALIGN_VCENTER | ALIGN_LEFT)

        layout.addWidget(self.label)
        layout.addWidget(self.value_label)
        layout.addStretch()
        self.setLayout(layout)

    def set_value(self, value):
        self.value = float(value)
        display = f"{self.value:.1f}"
        if self.unit:
            display = f"{display} {self.unit}"
        self.value_label.setText(display)


class SegmentedLinearGauge(QWidget):
    def __init__(
        self,
        label,
        min_val,
        max_val,
        unit,
        zones,
        value_formatter=None,
        min_width=234,
        min_height=81,
        title_font_size=13,
        value_font_size=12,
        base_line_position='bottom',
        draw_base_line=True,
        pointer_orientation='down',
        tick_values=None,
    ):
        super().__init__()
        self.label_text = label
        self.min_val = min_val
        self.max_val = max_val
        self.unit = unit
        self.value = min_val
        self.value_formatter = value_formatter or (lambda v: f"{int(round(v))}")
        self.zones = zones
        self.title_font_size = title_font_size
        self.value_font_size = value_font_size
        self.base_line_position = base_line_position
        self.draw_base_line = draw_base_line
        self.pointer_orientation = pointer_orientation
        self.tick_values = list(tick_values) if tick_values else []
        self.setMinimumSize(min_width, min_height)

    def _clamp(self, value):
        return max(self.min_val, min(self.max_val, value))

    def set_value(self, value):
        self.value = self._clamp(value)
        self.update()

    def get_pointer_infos(self):
        formatted = self.value_formatter(self.value)
        display_text = f"{formatted} {self.unit}".strip()
        return [
            {
                'value': self.value,
                'label': None,
                'orientation': self.pointer_orientation,
                'slot_index': 0,
                'display_text': display_text,
            }
        ]

    def get_bottom_text(self, pointer_infos):
        if not pointer_infos:
            return ''
        return pointer_infos[0].get('display_text', '')

    def paintEvent(self, a0):
        del a0
        w = self.width()
        h = self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor('black'))

        bar_margin = max(24.0, w * 0.07)
        bar_width = max(0.0, w - 2 * bar_margin)
        line_y = h * 0.42
        line_width = max(6.0, h * 0.11)
        tab_height = line_width + max(20.0, h * 0.16)
        base_line_y = line_y if self.base_line_position == 'center' else line_y + line_width / 2

        painter.setPen(QPen(QColor('white')))
        title_font = QFont('Arial', self.title_font_size, QFont.Bold)
        painter.setFont(title_font)
        title_height = max(20.0, h * 0.22)
        gap = 3
        top_of_bar = line_y - tab_height / 2
        title_y = max(0.0, top_of_bar - title_height - gap)
        painter.drawText(QRectF(0, title_y, w, title_height), ALIGN_CENTER, self.label_text)

        span = self.max_val - self.min_val or 1
        for start, end, color in self.zones:
            clamped_start = max(self.min_val, min(self.max_val, start))
            clamped_end = max(self.min_val, min(self.max_val, end))
            if clamped_end <= clamped_start:
                continue
            start_ratio = (clamped_start - self.min_val) / span
            end_ratio = (clamped_end - self.min_val) / span
            start_x = bar_margin + bar_width * start_ratio
            end_x = bar_margin + bar_width * end_ratio
            pen = QPen(color)
            pen.setWidth(int(line_width))
            pen.setCapStyle(FLAT_CAP_STYLE)
            painter.setPen(pen)
            color_center_y = line_y
            painter.drawLine(QPointF(start_x, color_center_y), QPointF(end_x, color_center_y))

        left_x = bar_margin
        right_x = bar_margin + bar_width
        painter.setPen(QPen(QColor('white'), 2))
        painter.drawLine(QPointF(left_x, line_y - tab_height / 2), QPointF(left_x, line_y + tab_height / 2))
        painter.drawLine(QPointF(right_x, line_y - tab_height / 2), QPointF(right_x, line_y + tab_height / 2))

        if self.tick_values:
            tick_pen = QPen(QColor('white'), 1)
            painter.setPen(tick_pen)
            tick_length = max(6.0, h * 0.08)
            tick_top = line_y - line_width / 2 - tick_length
            tick_bottom = line_y + line_width / 2 + tick_length
            for tick in self.tick_values:
                clamped_tick = max(self.min_val, min(self.max_val, tick))
                if span:
                    ratio = (clamped_tick - self.min_val) / span
                else:
                    ratio = 0.0
                tick_x = bar_margin + bar_width * ratio
                painter.drawLine(QPointF(tick_x, tick_top), QPointF(tick_x, tick_bottom))

        if self.draw_base_line:
            base_line_pen = QPen(QColor('white'), 3)
            base_line_pen.setCapStyle(FLAT_CAP_STYLE)
            painter.setPen(base_line_pen)
            painter.drawLine(QPointF(left_x, base_line_y), QPointF(right_x, base_line_y))

        pointer_infos = self.get_pointer_infos()
        pointer_height = tab_height / 2
        pointer_width = max(12.0, w * 0.03)
        max_down_base = base_line_y

        for idx, info in enumerate(pointer_infos):
            value = self._clamp(info.get('value', self.value))
            if span:
                ratio = (value - self.min_val) / span
            else:
                ratio = 0.0
            ratio = max(0.0, min(1.0, ratio))
            pointer_x = bar_margin + bar_width * ratio
            slot_index = info.get('slot_index', idx)
            vertical_offset = slot_index * pointer_height * 0.6
            orientation = info.get('orientation', 'down')

            if orientation == 'up':
                tip_y = base_line_y - vertical_offset
                base_y = tip_y - pointer_height
            else:
                tip_y = base_line_y + vertical_offset
                base_y = tip_y + pointer_height

            pointer = QPolygonF(
                [
                    QPointF(pointer_x - pointer_width / 2, base_y),
                    QPointF(pointer_x + pointer_width / 2, base_y),
                    QPointF(pointer_x, tip_y),
                ]
            )
            painter.setBrush(QColor('white'))
            painter.setPen(QPen(QColor('white')))
            painter.drawPolygon(pointer)

            label_text = info.get('label')
            if label_text:
                label_font = QFont('Arial', max(9, int(pointer_height * 0.6)), QFont.Bold)
                painter.setFont(label_font)
                painter.setPen(QPen(QColor('black')))
                text_rect = pointer.boundingRect().adjusted(0, pointer_height * 0.15, 0, -pointer_height * 0.15)
                shift = pointer_height * 0.1
                if orientation == 'up':
                    text_rect.translate(0, -shift)
                else:
                    text_rect.translate(0, shift)
                painter.drawText(text_rect, ALIGN_CENTER, label_text)
                painter.setPen(QPen(QColor('white')))

            if orientation != 'up':
                max_down_base = max(max_down_base, base_y)

        bottom_text = self.get_bottom_text(pointer_infos)
        if bottom_text:
            value_font = QFont('Arial', self.value_font_size, QFont.Bold)
            painter.setFont(value_font)
            painter.setPen(QPen(QColor('white')))
            painter.drawText(
                QRectF(0, max_down_base + 10, w, max(28.0, pointer_height + 12)),
                ALIGN_CENTER,
                bottom_text,
            )


class OilPressureGauge(SegmentedLinearGauge):

    def __init__(self, min_val=0, max_val=100, unit='PSI'):

        span = max_val - min_val or 1

        pct = lambda fraction: min_val + span * fraction

        zones = [

            (min_val, pct(0.15), QColor(200, 30, 30)),

            (pct(0.15), pct(0.30), QColor(220, 170, 40)),

            (pct(0.30), pct(0.85), QColor(40, 180, 40)),

            (pct(0.85), pct(0.95), QColor(220, 170, 40)),

            (pct(0.95), max_val, QColor(200, 30, 30)),

        ]

        super().__init__('OIL PSI', min_val, max_val, unit, zones, pointer_orientation='up')





class OilTemperatureGauge(SegmentedLinearGauge):

    def __init__(self, min_val=50, max_val=300, unit='F'):

        span = max_val - min_val or 1

        pct = lambda fraction: min_val + span * fraction

        zones = [

            (min_val, pct(0.05), QColor(200, 30, 30)),

            (pct(0.05), pct(0.40), QColor(220, 170, 40)),

            (pct(0.40), pct(0.85), QColor(40, 180, 40)),

            (pct(0.85), pct(0.90), QColor(220, 170, 40)),

            (pct(0.90), max_val, QColor(200, 30, 30)),

        ]

        super().__init__('OIL TEMP', min_val, max_val, unit, zones, pointer_orientation='up')





class EGTGauge(SegmentedLinearGauge):

    def __init__(self, min_val=1000, max_val=1800, unit='F'):

        span = max_val - min_val or 1

        fractions = [0.05, 0.55, 0.20, 0.05, 0.10]

        total = sum(fractions) or 1.0

        normalized = [fraction / total for fraction in fractions]

        colors = [

            QColor(200, 30, 30),

            QColor(220, 170, 40),

            QColor(40, 180, 40),

            QColor(220, 170, 40),

            QColor(200, 30, 30),

        ]

        cumulative = 0.0

        zones = []

        for fraction, color in zip(normalized, colors):

            start_ratio = cumulative

            cumulative += fraction

            end_ratio = min(1.0, cumulative)

            start_val = min_val + span * start_ratio

            end_val = min_val + span * end_ratio

            zones.append((start_val, end_val, color))

        super().__init__('COOLANT TEMP', min_val, max_val, unit, zones, pointer_orientation='up')





class FuelTemperatureGauge(SegmentedLinearGauge):

    def __init__(self, min_val=-40, max_val=160, unit='F'):

        span = max_val - min_val or 1

        pct = lambda fraction: min_val + span * fraction

        zones = [

            (min_val, pct(0.05), QColor(200, 30, 30)),

            (pct(0.05), pct(0.30), QColor(220, 170, 40)),

            (pct(0.30), pct(0.85), QColor(40, 180, 40)),

            (pct(0.85), pct(0.90), QColor(220, 170, 40)),

            (pct(0.90), max_val, QColor(200, 30, 30)),

        ]

        super().__init__(

            'FUEL TEMP',

            min_val,

            max_val,

            unit,

            zones,

            value_formatter=lambda v: f"{int(round(v))}",

            base_line_position='center',

            draw_base_line=False,

        )

        self.right_value = self.value



    def set_values(self, left, right):

        self.value = self._clamp(left)

        self.right_value = self._clamp(right)

        self.update()



    def set_value(self, value):

        self.set_values(value, getattr(self, 'right_value', value))



    def get_pointer_infos(self):

        left_val = self.value

        right_val = getattr(self, 'right_value', self.value)

        left_display = f"L: {self.value_formatter(left_val)} {self.unit}".strip()

        right_display = f"R: {self.value_formatter(right_val)} {self.unit}".strip()

        return [

            {

                'value': left_val,

                'label': 'L',

                'orientation': 'up',

                'slot_index': 0,

                'display_text': left_display,

            },

            {

                'value': right_val,

                'label': 'R',

                'orientation': 'down',

                'slot_index': 0,

                'display_text': right_display,

            },

        ]



    def get_bottom_text(self, pointer_infos):

        texts = [info.get('display_text', '') for info in pointer_infos if info.get('display_text')]

        return '    '.join(texts)



    def paintEvent(self, a0):

        super().paintEvent(a0)

        w = self.width()

        h = self.height()

        bar_margin = max(24.0, w * 0.07)

        line_y = h * 0.42

        line_width = max(6.0, h * 0.11)

        tab_height = line_width + max(20.0, h * 0.16)

        label_y = max(0.0, line_y - tab_height / 2 - 6)



        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing)

        label_font = QFont('Arial', 10, QFont.Bold)

        painter.setFont(label_font)

        painter.setPen(QPen(QColor('white')))

        painter.drawText(QRectF(bar_margin - 18, label_y - 10, 36, 14), ALIGN_CENTER, '0')

        painter.drawText(QRectF(w - bar_margin - 18, label_y - 10, 36, 14), ALIGN_CENTER, '14')





class FuelQuantityGauge(SegmentedLinearGauge):

    def __init__(self, min_val=0, max_val=14, unit='GAL'):

        span = max_val - min_val or 1

        pct = lambda fraction: min_val + span * fraction

        zones = [

            (min_val, pct(0.05), QColor(200, 30, 30)),

            (pct(0.05), max_val, QColor(40, 180, 40)),

        ]

        ticks = [min_val, pct(0.35), pct(0.70), max_val]

        super().__init__(

            'FUEL QTY GAL',

            min_val,

            max_val,

            unit,

            zones,

            value_formatter=lambda v: f"{int(round(v))}",

            base_line_position='center',

            draw_base_line=False,

            pointer_orientation='up',

            tick_values=ticks,

        )

        self.right_value = self.value



    def set_values(self, left, right):

        self.value = self._clamp(left)

        self.right_value = self._clamp(right)

        self.update()



    def set_value(self, value):

        self.set_values(value, getattr(self, 'right_value', value))



    def get_pointer_infos(self):

        left_val = self.value

        right_val = getattr(self, 'right_value', self.value)

        left_display = f"L: {self.value_formatter(left_val)} {self.unit}".strip()

        right_display = f"R: {self.value_formatter(right_val)} {self.unit}".strip()

        return [

            {

                'value': left_val,

                'label': 'L',

                'orientation': 'up',

                'slot_index': 0,

                'display_text': left_display,

            },

            {

                'value': right_val,

                'label': 'R',

                'orientation': 'down',

                'slot_index': 0,

                'display_text': right_display,

            },

        ]



    def get_bottom_text(self, pointer_infos):

        texts = [info.get('display_text', '') for info in pointer_infos if info.get('display_text')]

        return '    '.join(texts)





class FuelTank(QWidget):

    def __init__(self, label):

        super().__init__()

        self.label = label

        self.qty = 50



        layout = QVBoxLayout()

        self.label_widget = QLabel(label)

        self.label_widget.setStyleSheet('color: white')

        self.label_widget.setAlignment(ALIGN_CENTER)



        self.progress = QProgressBar()

        self.progress.setOrientation(VERTICAL_ORIENTATION)

        self.progress.setRange(0, 100)

        self.progress.setValue(self.qty)

        self.progress.setFixedSize(36, 180)

        self.progress.setTextVisible(False)



        self.value_label = QLabel(f"{self.qty}%")

        self.value_label.setStyleSheet('color: white')

        self.value_label.setAlignment(ALIGN_CENTER)



        layout.addWidget(self.label_widget)

        layout.addWidget(self.progress, alignment=ALIGN_CENTER)

        layout.addWidget(self.value_label)

        self.setLayout(layout)



    def set_qty(self, qty):

        self.qty = int(max(0, min(100, qty)))

        self.progress.setValue(self.qty)

        self.value_label.setText(f"{self.qty}%")

        color = 'red' if self.qty < 10 else 'orange' if self.qty < 30 else 'green'

        self.progress.setStyleSheet(

            f"QProgressBar::chunk {{ background-color: {color}; }}"

            " QProgressBar { border: 1px solid #444; background: #222; }"

        )





class GPSWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet('background-color: #202020;')
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        self.web_view = None
        self.current_heading = 0
        self.current_track = 0
        if QWebEngineView is None:
            self._build_placeholder(
                'PyQtWebEngine est introuvable.\nInstallez pyqtwebengine pour afficher la carte GPS.'
            )
            return
        try:
            self.web_view = QWebEngineView()
            self.web_view.setContextMenuPolicy(NO_CONTEXT_MENU)
            layout.addWidget(self.web_view)
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gps_map.html')
            if os.path.exists(html_path):
                self.web_view.load(QUrl.fromLocalFile(html_path))
                self.web_view.loadFinished.connect(self._on_page_loaded)
            else:
                self.web_view.setHtml(
                    '<html><body style="background:black;color:white;">Fichier gps_map.html introuvable.</body></html>'
                )
        except Exception as exc:
            self.web_view = None
            self._build_placeholder(f'Erreur lors du chargement du GPS : {exc}')

    def _on_page_loaded(self, ok):
        if ok and self.web_view:
            # Injecter un timer pour récupérer les données de l'avion
            self._start_data_sync()

    def _start_data_sync(self):
        if not self.web_view:
            return
        # Récupérer les données toutes les 200ms
        self._sync_timer = QTimer(self)
        self._sync_timer.timeout.connect(self._fetch_aircraft_data)
        self._sync_timer.start(200)

    def _fetch_aircraft_data(self):
        if not self.web_view:
            return
        page = self.web_view.page()
        if not page:
            return
        # Exécuter JavaScript pour récupérer heading, track et position
        page.runJavaScript(
            'JSON.stringify({heading: aircraftHeading, track: aircraftHeading, speed: aircraftSpeed, lat: aircraftLat, lon: aircraftLon, altitude: aircraftAltitude});',
            self._update_from_js
        )

    def _update_from_js(self, result):
        if result:
            try:
                import json
                data = json.loads(result)
                self.current_heading = data.get('heading', 0)
                self.current_track = data.get('track', 0)
                lat = data.get('lat', None)
                lon = data.get('lon', None)
                # Notifier le parent (EngineDisplay) pour mettre à jour le Cap widget
                parent = self.parent()
                while parent and not isinstance(parent, EngineDisplay):
                    parent = parent.parent()
                if parent and isinstance(parent, EngineDisplay):
                    # Passer lat/lon si disponibles
                    try:
                        parent.update_from_gps(self.current_heading, self.current_track, lat, lon)
                    except TypeError:
                        # Ancienne signature fallback
                        parent.update_from_gps(self.current_heading, self.current_track)
            except:
                pass

    def get_heading(self):
        return self.current_heading

    def get_track(self):
        return self.current_track

    def _build_placeholder(self, message):
        layout = self.layout()
        if layout is None:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        placeholder = QLabel(message)
        placeholder.setWordWrap(True)
        placeholder.setStyleSheet('color: white')
        placeholder.setAlignment(ALIGN_CENTER)
        layout.addStretch()
        layout.addWidget(placeholder)
        layout.addStretch()


class GreeceMapWidget(QWidget):

    REMOTE_URL = (
        'https://geo-gishpc1.aegean.gr:446/AWG/?VER=4.10.1&BL=5&LAT=38&LON=25&ZL=7&OL=1'
        '&WX_DTG=2025112115&LVL=SFC&TRV=comp&NOTAM_FROM_DTG=202511211305&NOTAM_TO_DTG=202511211305'
    )

    def __init__(self):

        super().__init__()

        self.setStyleSheet('background-color: #1a1d24;')

        layout = QVBoxLayout()

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(0)

        self.setLayout(layout)

        self.web_view = None
        self._waiting_for_remote = False
        self._local_html = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'greece_map.html')

        if QWebEngineView is None:

            self._build_placeholder(

                'PyQtWebEngine est requis pour afficher la Greece Map.\nInstallez pyqtwebengine ou ajoutez greece_map.html.'

            )

            return

        try:

            self.web_view = QWebEngineView()

            self.web_view.setContextMenuPolicy(NO_CONTEXT_MENU)

            layout.addWidget(self.web_view)

            self._waiting_for_remote = True
            self.web_view.loadFinished.connect(self._on_first_load_finished)
            self.web_view.load(QUrl(self.REMOTE_URL))

        except Exception as exc:

            self.web_view = None

            self._build_placeholder(f'Erreur lors du chargement de la Greece Map : {exc}')


    def _on_first_load_finished(self, ok):

        if not self._waiting_for_remote:

            return

        self._waiting_for_remote = False

        if ok:

            return

        if self._load_local_map():

            return

        self._build_placeholder(

            "Impossible de contacter le service AWG.\nVérifiez votre connexion ou placez greece_map.html à côté du script."

        )


    def _load_local_map(self):

        if not self.web_view:

            return False

        if os.path.exists(self._local_html):

            self.web_view.load(QUrl.fromLocalFile(self._local_html))

            return True

        return False


    def _build_placeholder(self, message):

        layout = self.layout()

        if layout is None:

            layout = QVBoxLayout(self)

            layout.setContentsMargins(0, 0, 0, 0)

            layout.setSpacing(0)

        while layout.count():

            item = layout.takeAt(0)

            widget = item.widget()

            if widget is not None:

                widget.deleteLater()

        layout.setContentsMargins(40, 40, 40, 40)

        layout.setSpacing(12)

        title = QLabel('GREECE MAP')

        title.setAlignment(ALIGN_CENTER)

        title.setStyleSheet('color: #7cfaff; font: bold 20px Arial;')

        content = QLabel(message)

        content.setWordWrap(True)

        content.setAlignment(ALIGN_CENTER)

        content.setStyleSheet('color: white; font: 14px Arial;')

        layout.addStretch()

        layout.addWidget(title)

        layout.addSpacing(12)

        layout.addWidget(content)

        layout.addStretch()

class Tar1090Widget(QWidget):
    """Widget affichant la carte tar1090 (ADS-B) servie localement."""

    TAR1090_URL = 'http://localhost:8081'

    def __init__(self):
        super().__init__()
        self.setStyleSheet('background-color: #1a1d24;')
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        self.web_view = None

        if QWebEngineView is None:
            self._build_placeholder(
                'PyQtWebEngine est requis pour afficher la carte tar1090.\n'
                'Installez pyqtwebengine.'
            )
            return

        try:
            self.web_view = QWebEngineView()
            self.web_view.setContextMenuPolicy(NO_CONTEXT_MENU)
            layout.addWidget(self.web_view)
            self.web_view.load(QUrl(self.TAR1090_URL))
        except Exception as exc:
            self.web_view = None
            self._build_placeholder(f'Erreur lors du chargement de tar1090 : {exc}')

    def reload_page(self):
        if self.web_view:
            self.web_view.reload()

    def _build_placeholder(self, message):
        layout = self.layout()
        if layout is None:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(12)
        title = QLabel('TAR1090 – ADS-B')
        title.setAlignment(ALIGN_CENTER)
        title.setStyleSheet('color: #7cfaff; font: bold 20px Arial;')
        content = QLabel(message)
        content.setWordWrap(True)
        content.setAlignment(ALIGN_CENTER)
        content.setStyleSheet('color: white; font: 14px Arial;')
        hint = QLabel(
            'Lancez les commandes suivantes dans un terminal :\n\n'
            'readsb --net --device-type rtlsdr --gain auto '
            '--write-json-every 0.5 --write-json ~/tar1090/html/data\n\n'
            'cd ~/tar1090/html && python3 -m http.server 8081'
        )
        hint.setWordWrap(True)
        hint.setAlignment(ALIGN_CENTER)
        hint.setStyleSheet('color: #aaa; font: 12px monospace;')
        layout.addStretch()
        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(content)
        layout.addSpacing(8)
        layout.addWidget(hint)
        layout.addStretch()


class Tar1090Widget(QWidget):
    """Widget affichant la carte tar1090 (ADS-B) servie localement."""

    TAR1090_URL = 'http://localhost:8081'

    def __init__(self):
        super().__init__()
        self.setStyleSheet('background-color: #1a1d24;')
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        self.web_view = None

        if QWebEngineView is None:
            self._build_placeholder(
                'PyQtWebEngine est requis pour afficher la carte tar1090.\n'
                'Installez pyqtwebengine.'
            )
            return

        try:
            self.web_view = QWebEngineView()
            self.web_view.setContextMenuPolicy(NO_CONTEXT_MENU)
            layout.addWidget(self.web_view)
            self.web_view.load(QUrl(self.TAR1090_URL))
        except Exception as exc:
            self.web_view = None
            self._build_placeholder(f'Erreur lors du chargement de tar1090 : {exc}')

    def reload_page(self):
        if self.web_view:
            self.web_view.reload()

    def _build_placeholder(self, message):
        layout = self.layout()
        if layout is None:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(12)
        title = QLabel('TAR1090 \u2013 ADS-B')
        title.setAlignment(ALIGN_CENTER)
        title.setStyleSheet('color: #7cfaff; font: bold 20px Arial;')
        content = QLabel(message)
        content.setWordWrap(True)
        content.setAlignment(ALIGN_CENTER)
        content.setStyleSheet('color: white; font: 14px Arial;')
        hint = QLabel(
            'Lancez les commandes suivantes dans un terminal :\n\n'
            'readsb --net --device-type rtlsdr --gain auto '
            '--write-json-every 0.5 --write-json ~/tar1090/html/data\n\n'
            'cd ~/tar1090/html && python3 -m http.server 8081'
        )
        hint.setWordWrap(True)
        hint.setAlignment(ALIGN_CENTER)
        hint.setStyleSheet('color: #aaa; font: 12px monospace;')
        layout.addStretch()
        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(content)
        layout.addSpacing(8)
        layout.addWidget(hint)
        layout.addStretch()


class NavigationDisplayWidget(QWidget):

    MODES = ('ROSE', 'ARC', 'MAP', 'PLAN')
    ARC_RADIUS_FACTOR = 0.48

    def __init__(self):

        super().__init__()

        self.setFocusPolicy(STRONG_FOCUS)

        self.setMinimumSize(560, 520)

        self.mode_index = 1

        self.mode = self.MODES[self.mode_index]

        self.heading = 0

        self.track = 0

        self.desired_track = 0

        self.ground_speed = 0

        self.true_airspeed = 0

        self.gps_source = 'GPS1'

        self.gps_integrity = 'WAAS'

        self.approach_mode = 'LNAV'

        self.com1_active = '119.750'

        self.com1_standby = '123.975'

        self.com2_active = '126.700'

        self.com2_standby = '118.500'

        self.active_waypoint = WaypointInfo('----', is_active=True)

        self.next_waypoints: List[WaypointInfo] = []

        self.distance_to_active = 0.0

        self.ete_minutes = 0.0

        self.altitude_target = ''

        self.deviation_nm = 0.0

        self.deviation_limit_nm = 0.3

        self.range_nm = 20

        self.route_points = [

            (-0.9, -0.3),

            (-0.4, -0.1),

            (0.0, 0.15),

            (0.35, 0.45),

            (0.75, 0.7),

        ]


    def set_mode(self, mode):

        if mode not in self.MODES:

            return

        self.mode = mode

        self.mode_index = self.MODES.index(mode)

        self.update()


    def cycle_mode(self, step=1):

        total = len(self.MODES)

        if not total:

            return self.mode

        self.mode_index = (self.mode_index + step) % total

        self.mode = self.MODES[self.mode_index]

        self.update()

        return self.mode


    def update_state(self, state):

        if not state:

            return

        for key, value in state.items():

            if key == 'active_waypoint' and isinstance(value, WaypointInfo):

                self.active_waypoint = value

            elif key == 'next_waypoints' and isinstance(value, (list, tuple)):

                self.next_waypoints = [cast(WaypointInfo, wp) for wp in value]

            elif key == 'mode':

                self.set_mode(value)

            elif hasattr(self, key):

                setattr(self, key, value)

        self.update()


    def keyPressEvent(self, event):
        if event is None:
            return
        key = event.key()
        if key in (KEY_A, KEY_D):
            parent = self.parent()
            while parent and not isinstance(parent, EngineDisplay):
                parent = parent.parent()
            if parent and isinstance(parent, EngineDisplay):
                if key == KEY_A:
                    parent.heading = (parent.heading - 1) % 360
                else:
                    parent.heading = (parent.heading + 1) % 360
                parent.update_display()
                # Mettre à jour la carte GPS (webview) si disponible
                try:
                    gps = getattr(parent, 'gps', None)
                    if gps and getattr(gps, 'web_view', None):
                        js = (
                            f"(function(){{"
                            f" if (typeof setAircraftHeading === 'function') {{ setAircraftHeading({parent.heading}); }}"
                            f" else {{ aircraftHeading = {parent.heading}; if(typeof updateAircraft === 'function') updateAircraft(); }}"
                            f"}})();"
                        )
                        try:
                            gps.web_view.page().runJavaScript(js)
                        except Exception:
                            # Ignore si la page n'est pas prête
                            pass
                except Exception:
                    pass
                event.accept()
                return
        super().keyPressEvent(event)


    def _format_time(self, minutes):

        total_seconds = max(0, int(minutes * 60))

        mins = total_seconds // 60

        secs = total_seconds % 60

        return f"{mins:02d}:{secs:02d}"


    def paintEvent(self, a0):

        del a0

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(self.rect(), QColor('#050a11'))

        center, radius = self._compute_geometry()

        self._draw_banner(painter)

        self._draw_range_rings(painter, center, radius)

        self._draw_heading_marks(painter, center, radius)

        # self._draw_route(painter, center, radius)  # Route désactivée

        self._draw_aircraft_symbol(painter, center)

        # self._draw_waypoint_stack(painter)  # Waypoints désactivés

        # self._draw_distance_box(painter)  # Distance box désactivée


    def _compute_geometry(self):

        w = self.width()

        h = self.height()

        if self.mode == 'ARC':

            center = QPointF(w / 2, h * 0.82)

            radius = min(w, h * 1.2) * self.ARC_RADIUS_FACTOR

        elif self.mode == 'ROSE':

            center = QPointF(w / 2, h * 0.58)

            radius = min(w, h) * 0.42

        elif self.mode == 'MAP':

            center = QPointF(w / 2, h * 0.6)

            radius = min(w, h) * 0.5

        else:  # PLAN

            center = QPointF(w / 2, h * 0.6)

            radius = min(w, h) * 0.48

        return center, radius


    def _draw_banner(self, painter):

        banner_rect = QRectF(18, 12, self.width() - 36, 64)

        painter.setPen(QPen(QColor('#1f8dd6')))

        painter.setBrush(QColor(0, 0, 0, 200))

        painter.drawRoundedRect(banner_rect, 8, 8)

        painter.setPen(QColor('white'))

        font = QFont('Arial', 12, QFont.Bold)

        painter.setFont(font)

        com_block_width = 330

        text = (

            f"DTK {int(round(self.desired_track)) % 360:03d}  "

            f"TRK {int(round(self.track)) % 360:03d}  "

            f"HDG {int(round(self.heading)) % 360:03d}"

        )

        painter.drawText(banner_rect.adjusted(14, 8, -com_block_width, -32), ALIGN_LEFT | ALIGN_VCENTER, text)

        speed_text = f"GS {int(self.ground_speed):3d} KT    TAS {int(self.true_airspeed):3d} KT"

        painter.drawText(banner_rect.adjusted(14, 32, -com_block_width, -4), ALIGN_LEFT | ALIGN_VCENTER, speed_text)

        com_font = QFont('Consolas', 11, QFont.Bold)
        painter.setFont(com_font)
        com1_text = f"COM1  {self.com1_active}  <->  {self.com1_standby}"
        com2_text = f"COM2  {self.com2_active}  <->  {self.com2_standby}"
        painter.drawText(banner_rect.adjusted(0, 8, -18, -32), ALIGN_RIGHT | ALIGN_VCENTER, com1_text)
        painter.drawText(banner_rect.adjusted(0, 32, -18, -6), ALIGN_RIGHT | ALIGN_VCENTER, com2_text)


    def _draw_range_rings(self, painter, center, radius):

        painter.setPen(QPen(QColor('#1f8dd6'), 2))

        max_rings = 3

        for ring in range(1, max_rings + 1):

            r = radius * ring / max_rings

            rect = QRectF(center.x() - r, center.y() - r, 2 * r, 2 * r)

            if self.mode == 'ARC':

                painter.drawArc(rect, 0, 180 * 16)

            else:

                painter.drawEllipse(rect)

            painter.setFont(QFont('Arial', 9))

            label = f"{int(self.range_nm * ring / max_rings)} NM"

            painter.drawText(QPointF(center.x() + r + 4, center.y()), label)


    def _draw_heading_marks(self, painter, center, radius):

        rose_radius = radius + (28 if self.mode != 'ARC' else 18)
        ring_rect = QRectF(center.x() - rose_radius, center.y() - rose_radius, rose_radius * 2, rose_radius * 2)

        ring_pen = QPen(QColor('#5a6a88'), 2)
        ring_pen.setCapStyle(Qt.FlatCap)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.NoBrush)

        if self.mode == 'ARC':
            painter.drawArc(ring_rect, 0, 180 * 16)
        else:
            painter.drawEllipse(ring_rect)

        tick_pen = QPen(QColor('#d7dbe4'), 2)
        painter.setPen(tick_pen)

        def _bearing_visible(bearing):
            if self.mode != 'ARC':
                return True
            # Calculer le bearing relatif par rapport au heading
            relative_bearing = (bearing - self.heading + 360) % 360
            return relative_bearing <= 90 or relative_bearing >= 270

        def _bearing_to_angle(bearing):
            # La rose tourne en fonction du heading (comme une boussole)
            relative_bearing = bearing - self.heading
            return math.radians(relative_bearing - 90)

        for bearing in range(0, 360, 5):
            if not _bearing_visible(bearing):
                continue
            angle = _bearing_to_angle(bearing)
            outer = QPointF(
                center.x() + rose_radius * math.cos(angle),
                center.y() + rose_radius * math.sin(angle),
            )
            length = 6
            if bearing % 30 == 0:
                length = 14
            elif bearing % 10 == 0:
                length = 10
            inner = QPointF(
                center.x() + (rose_radius - length) * math.cos(angle),
                center.y() + (rose_radius - length) * math.sin(angle),
            )
            painter.drawLine(inner, outer)

            if bearing % 30 == 0:
                label_offset = rose_radius + 16
                label_point = QPointF(
                    center.x() + label_offset * math.cos(angle),
                    center.y() + label_offset * math.sin(angle),
                )
                if bearing % 90 == 0:
                    text = {0: 'N', 90: 'E', 180: 'S', 270: 'W'}[bearing]
                    font = QFont('Arial', 12, QFont.Bold)
                else:
                    text = f"{bearing:03d}"
                    font = QFont('Arial', 9)
                painter.setFont(font)
                rect = QRectF(label_point.x() - 24, label_point.y() - 12, 48, 24)
                painter.drawText(rect, ALIGN_CENTER, text)

        # Indicateur de heading fixe (toujours vers le haut) - triangle plus petit
        heading_angle = math.radians(-90)  # Toujours vers le haut
        bug_radius = rose_radius - 4
        bug_tip = QPointF(
            center.x() + bug_radius * math.cos(heading_angle),
            center.y() + bug_radius * math.sin(heading_angle),
        )
        side_radius = bug_radius - 8  # Réduit de 18 à 8 pour un triangle plus petit
        left_angle = heading_angle + math.radians(6)  # Réduit de 10 à 6 degrés
        right_angle = heading_angle - math.radians(6)
        left_point = QPointF(
            center.x() + side_radius * math.cos(left_angle),
            center.y() + side_radius * math.sin(left_angle),
        )
        right_point = QPointF(
            center.x() + side_radius * math.cos(right_angle),
            center.y() + side_radius * math.sin(right_angle),
        )
        painter.setBrush(QColor('#ffca4f'))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(QPolygonF([bug_tip, left_point, right_point]))


    def _map_route_point(self, normalized, center, radius):

        scale_x = radius * (1.15 if self.mode == 'PLAN' else 0.9)

        scale_y = scale_x * (1.0 if self.mode != 'ARC' else 0.7)

        x = center.x() + normalized[0] * scale_x

        y = center.y() - normalized[1] * scale_y

        return QPointF(x, y)


    def _draw_route(self, painter, center, radius):

        if not self.route_points:

            return

        magenta = QColor('#ff00c4')

        cyan = QColor('#4bd4ff')

        painter.setPen(QPen(cyan, 2, Qt.DashLine))

        points = [self._map_route_point(pt, center, radius) for pt in self.route_points]

        for i in range(len(points) - 1):

            painter.drawLine(points[i], points[i + 1])

        painter.setPen(QPen(magenta, 4))

        if len(points) >= 2:

            painter.drawLine(points[-2], points[-1])

        painter.setBrush(magenta)

        painter.setPen(Qt.NoPen)

        painter.drawEllipse(points[-1], 6, 6)


    def _draw_aircraft_symbol(self, painter, center):

        painter.setBrush(QColor('white'))

        painter.setPen(Qt.NoPen)

        size = 16

        if self.mode == 'ARC':

            y_offset = 28

        elif self.mode == 'ROSE':

            y_offset = 0

        else:

            y_offset = -8

        nose = QPointF(center.x(), center.y() - size + y_offset)

        left = QPointF(center.x() - size / 2, center.y() + y_offset)

        right = QPointF(center.x() + size / 2, center.y() + y_offset)

        painter.drawPolygon(QPolygonF([nose, right, left]))

        # Dessiner la ligne de trajectoire (trait pointillé jusqu'au triangle jaune)
        trajectory_pen = QPen(QColor('#ffca4f'), 2, Qt.DashLine)
        painter.setPen(trajectory_pen)
        
        # Calculer la position du triangle jaune
        w = self.width()
        h = self.height()
        if self.mode == 'ARC':
            center_compass = QPointF(w / 2, h * 0.82)
            radius_compass = min(w, h * 1.2) * self.ARC_RADIUS_FACTOR
        elif self.mode == 'ROSE':
            center_compass = QPointF(w / 2, h * 0.58)
            radius_compass = min(w, h) * 0.42
        elif self.mode == 'MAP':
            center_compass = QPointF(w / 2, h * 0.6)
            radius_compass = min(w, h) * 0.5
        else:  # PLAN
            center_compass = QPointF(w / 2, h * 0.6)
            radius_compass = min(w, h) * 0.48
        
        rose_radius = radius_compass + (28 if self.mode != 'ARC' else 18)
        heading_angle = math.radians(-90)
        bug_radius = rose_radius - 4
        triangle_tip_y = center_compass.y() + bug_radius * math.sin(heading_angle)
        
        # Ligne de trajectoire du nez de l'avion jusqu'au triangle jaune
        trajectory_start = QPointF(center.x(), center.y() - size + y_offset)
        trajectory_end = QPointF(center.x(), triangle_tip_y)
        
        painter.drawLine(trajectory_start, trajectory_end)


    def _draw_deviation_scale(self, painter):

        width = self.width() * 0.5

        center_x = self.width() / 2

        y = self.height() - 60

        painter.setPen(QPen(QColor('white'), 2))

        painter.drawLine(QPointF(center_x - width / 2, y), QPointF(center_x + width / 2, y))

        painter.setFont(QFont('Arial', 9))

        painter.drawText(QPointF(center_x - width / 2 - 40, y + 4), 'CDI')

        ticks = 4

        for i in range(-ticks, ticks + 1):

            x = center_x + (width / (ticks * 2)) * i

            painter.drawLine(QPointF(x, y - 8), QPointF(x, y + 8))

        painter.setPen(QPen(QColor('#ff00c4'), 4))

        deviation_ratio = 0.0

        if self.deviation_limit_nm:

            deviation_ratio = max(-1.0, min(1.0, self.deviation_nm / self.deviation_limit_nm))

        pointer_x = center_x + (width / 2) * deviation_ratio

        painter.drawLine(QPointF(pointer_x, y - 14), QPointF(pointer_x, y + 14))


    def _draw_waypoint_stack(self, painter):

        stack = [self.active_waypoint] + self.next_waypoints[:3]

        base_x = self.width() - 210

        base_y = 140

        painter.setFont(QFont('Arial', 11, QFont.Bold))

        for idx, wp in enumerate(stack):

            color = '#ff00c4' if wp.is_active else '#ffffff'

            rect = QRectF(base_x, base_y + idx * 72, 180, 60)

            painter.setPen(QPen(QColor(color)))

            painter.setBrush(QColor(0, 0, 0, 160))

            painter.drawRoundedRect(rect, 6, 6)

            painter.setPen(QColor(color))

            painter.drawText(rect.adjusted(8, 4, -8, -30), ALIGN_LEFT | ALIGN_TOP, wp.name)

            painter.setPen(QColor('white'))

            info = f"{wp.distance_nm:4.1f} NM  {self._format_time(wp.ete_min)}"

            painter.drawText(rect.adjusted(8, 20, -8, -8), ALIGN_LEFT | ALIGN_TOP, info)

            if wp.altitude_constraint:

                painter.drawText(

                    rect.adjusted(8, 36, -8, -4),

                    ALIGN_LEFT | ALIGN_TOP,

                    f"ALT {wp.altitude_constraint}",

                )


    def _draw_distance_box(self, painter):

        rect = QRectF(18, self.height() - 140, 220, 110)

        painter.setPen(QPen(QColor('#1f8dd6')))

        painter.setBrush(QColor(0, 0, 0, 200))

        painter.drawRoundedRect(rect, 8, 8)

        painter.setPen(QColor('white'))

        painter.setFont(QFont('Arial', 11))

        painter.drawText(rect.adjusted(12, 8, -12, -70), ALIGN_LEFT | ALIGN_TOP, 'DIST / ETA / ALT')

        painter.setFont(QFont('Arial', 18, QFont.Bold))

        painter.setPen(QColor('#ff00c4'))

        painter.drawText(

            rect.adjusted(12, 26, -12, -40), ALIGN_LEFT | ALIGN_TOP, f"{self.distance_to_active:4.1f} NM"

        )

        painter.setPen(QColor('#7cfaff'))

        painter.setFont(QFont('Arial', 14))

        painter.drawText(

            rect.adjusted(12, 54, -12, -12),

            ALIGN_LEFT | ALIGN_TOP,

            f"ETE {self._format_time(self.ete_minutes)}  ALT {self.altitude_target}",

        )


class CapWidget(QWidget):

    def __init__(self):

        super().__init__()

        self.setStyleSheet('background-color: #050505; border: none;')

        layout = QVBoxLayout()

        layout.setContentsMargins(18, 18, 18, 18)

        layout.setSpacing(12)

        self.nav_display = NavigationDisplayWidget()

        layout.addWidget(self.nav_display, stretch=1)

        self.setLayout(layout)


    def _on_mode_changed(self, mode):

        self.nav_display.set_mode(mode)


    def set_heading(self, heading):

        self.nav_display.update_state({'heading': heading})


    def update_navigation_state(self, state):

        if not state:

            return

        self.nav_display.update_state(state)


    def cycle_mode(self):

        current = self.nav_display.cycle_mode(1)
        return current





class EngineDisplay(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle('DA40 Engine Display (PyQt5)')

        self.setGeometry(50, 50, 1400, 700)

        self.setStyleSheet('background-color: black')

        self._local_service_processes = []



        self.rpm = 0

        self.load = 0

        self.fflow = 0.0

        self.oil_psi = 0.0

        self.oil_temp = 100

        self.egt = 1200

        self.fuel_temp_left = 60

        self.fuel_temp_right = 65

        self.fuel_qty_L = 60

        self.fuel_qty_R = 45

        self.heading = 0

        self.track = 132

        self.desired_track = 135

        self.ground_speed = 148

        self.true_airspeed = 142
        # Position de l'avion (synchronisée avec la WebView)
        self.lat = 38.0
        self.lon = 25.0

        self.gps_source = 'GPS1'

        self.gps_integrity = 'WAAS'

        self.approach_mode = 'LPV'

        self.com1_active = '119.750'

        self.com1_standby = '123.975'

        self.com2_active = '126.700'

        self.com2_standby = '118.500'

        self.distance_to_waypoint = 4.2

        self.ete_minutes = 3.6

        self.altitude_target = '2500 FT'

        self.deviation_nm = 0.05

        self.deviation_limit_nm = 0.3

        self.range_nm = 20

        self.active_waypoint = WaypointInfo('OKIPA', self.distance_to_waypoint, self.ete_minutes, self.altitude_target, True)

        self.next_waypoints: List[WaypointInfo] = [

            WaypointInfo('SABEX', 18.4, 9.7, '3000 FT'),

            WaypointInfo('ANEBI', 42.0, 25.0, '4000 FT'),

            WaypointInfo('LGL', 78.0, 42.0, ''),

        ]

        self.route_points = [

            (-0.9, -0.3),

            (-0.4, -0.1),

            (0.0, 0.15),

            (0.35, 0.45),

            (0.75, 0.7),

        ]

        self.nav_mode = 'ARC'
        self.engine_mode = MODE_MANUAL
        self.engine_mode_names = {
            MODE_MANUAL: 'MODE 1 - MANUAL',
            MODE_CRUISE: 'MODE 2 - CRUISE',
            MODE_STRESS: 'MODE 3 - STRESS',
        }
        self.engine_sources = {
            MODE_MANUAL: ManualEngineSource(self),
            MODE_CRUISE: CruiseEngineSource(),
            MODE_STRESS: StressEngineSource(),
        }
        self.engine_source = self.engine_sources[self.engine_mode]
        self.engine_control_keys = {
            KEY_UP,
            KEY_DOWN,
            KEY_RIGHT,
            KEY_LEFT,
            KEY_W,
            KEY_S,
            KEY_E,
            KEY_D,
            KEY_R,
            KEY_F,
            KEY_T,
            KEY_G,
            KEY_Y,
            KEY_H,
            KEY_I,
            KEY_K,
            KEY_Z,
            KEY_X,
            KEY_C,
            KEY_V,
            KEY_U,
            KEY_J,
            KEY_O,
            KEY_L,
            KEY_PAGE_UP,
            KEY_PAGE_DOWN,
        }



        main_layout = QHBoxLayout()

        main_layout.setContentsMargins(18, 10, 18, 18)



        left_col = QVBoxLayout()

        left_col.setSpacing(6)

        self.rpm_widget = RPMGauge()

        left_col.addWidget(self.rpm_widget, alignment=ALIGN_LEFT)

        self.load_widget = RPMGauge(0, 100, title='LOAD', unit='%')

        left_col.addWidget(self.load_widget, alignment=ALIGN_LEFT)

        self.fflow_widget = ValueDisplay('FFLOW GPH')

        self.oil_psi_widget = OilPressureGauge(0, 100, 'PSI')

        self.oil_temp_widget = OilTemperatureGauge()

        self.egt_widget = EGTGauge()

        self.fuel_temp_widget = FuelTemperatureGauge()

        self.fuel_qty_gal_widget = FuelQuantityGauge()

        self.mode_label = QLabel('')

        self.mode_label.setAlignment(ALIGN_CENTER)

        self.mode_label.setStyleSheet('color: #7cfaff; font: bold 12px Consolas;')

        left_col.addWidget(self.fflow_widget)

        left_col.addWidget(self.oil_psi_widget)

        left_col.addWidget(self.oil_temp_widget)

        left_col.addWidget(self.egt_widget)

        left_col.addWidget(self.fuel_temp_widget)

        left_col.addWidget(self.fuel_qty_gal_widget)

        left_col.addWidget(self.mode_label)

        left_col.addStretch()



        self.gps = GPSWidget()

        self.cap_widget = CapWidget()

        self.greece_widget = GreeceMapWidget()

        self.tar1090_widget = Tar1090Widget()

        for widget in (self.gps, self.cap_widget, self.greece_widget, self.tar1090_widget):

            widget.setMinimumSize(600, 600)

        self.display_tabs = QTabWidget()

        self.display_tabs.addTab(self.gps, 'GPS')

        self.display_tabs.addTab(self.cap_widget, 'Cap')

        self.display_tabs.addTab(self.greece_widget, 'Greece Map')

        self.display_tabs.addTab(self.tar1090_widget, 'ADS-B Radar')


        gps_container = QWidget()

        gps_container.setStyleSheet('border: 3px solid white;')

        gps_layout = QVBoxLayout()

        gps_layout.setContentsMargins(0, 0, 0, 0)

        gps_layout.addWidget(self.display_tabs)

        gps_container.setLayout(gps_layout)



        main_layout.addLayout(left_col)

        main_layout.addWidget(gps_container, stretch=1)

        self.setLayout(main_layout)



        self.setFocusPolicy(STRONG_FOCUS)

        self.timer = QTimer(self)

        self.timer.timeout.connect(self.update_display)

        self.timer.start(100)

        self._set_engine_mode(self.engine_mode)

        self._start_local_services()

        self.update_display()


    def _start_local_services(self):

        data_dir = os.path.expanduser('~/tar1090/html/data')
        http_dir = os.path.expanduser('~/tar1090/html')

        try:
            os.makedirs(http_dir, exist_ok=True)
            os.makedirs(data_dir, exist_ok=True)
        except Exception:
            pass

        commands = [
            (
                [
                    'readsb',
                    '--net',
                    '--device-type',
                    'rtlsdr',
                    '--gain',
                    'auto',
                    '--write-json-every',
                    '0.5',
                    '--write-json',
                    data_dir,
                ],
                None,
            ),
            ([sys.executable, '-m', 'http.server', '8081'], http_dir),
        ]

        for command, working_directory in commands:
            try:
                process = subprocess.Popen(
                    command,
                    cwd=working_directory,
                    stdout=None,
                    stderr=None,
                    start_new_session=True,
                )
            except FileNotFoundError:
                print(f'Commande introuvable au démarrage: {command[0]}')
                continue
            except Exception:
                print(f'Impossible de démarrer: {command}')
                continue
            self._local_service_processes.append(process)


    def _stop_local_services(self):

        while self._local_service_processes:
            process = self._local_service_processes.pop()
            try:
                process.terminate()
            except Exception:
                pass


    def closeEvent(self, a0):

        self._stop_local_services()
        super().closeEvent(a0)


    def _set_engine_mode(self, mode):

        if mode not in self.engine_sources:
            return

        self.engine_mode = mode
        self.engine_source = self.engine_sources[mode]
        mode_name = self.engine_mode_names.get(mode, f'MODE {mode}')
        self.mode_label.setText(f'{mode_name}  (N: cycle)')
        self.setWindowTitle(f'DA40 Engine Display (PyQt5) - {mode_name}')


    def _cycle_engine_mode(self):

        order = [MODE_MANUAL, MODE_CRUISE, MODE_STRESS]
        try:
            idx = order.index(self.engine_mode)
        except ValueError:
            idx = 0
        self._set_engine_mode(order[(idx + 1) % len(order)])


    def _apply_engine_mode(self):

        if self.engine_source is None:
            return
        data = self.engine_source.poll()
        if not data:
            return
        self.rpm = _clamp(float(data.get('rpm', self.rpm)), 0, 3000)
        self.load = _clamp(float(data.get('load', self.load)), 0, 100)
        self.fflow = _clamp(float(data.get('fflow', self.fflow)), 0.0, 20.0)
        self.oil_psi = _clamp(float(data.get('oil_psi', self.oil_psi)), 0.0, 100.0)
        self.oil_temp = _clamp(float(data.get('oil_temp', self.oil_temp)), 50.0, 300.0)
        self.egt = _clamp(float(data.get('egt', self.egt)), 1000.0, 1800.0)
        self.fuel_temp_left = _clamp(float(data.get('fuel_temp_left', self.fuel_temp_left)), -40.0, 160.0)
        self.fuel_temp_right = _clamp(float(data.get('fuel_temp_right', self.fuel_temp_right)), -40.0, 160.0)
        self.fuel_qty_L = _clamp(float(data.get('fuel_qty_L', self.fuel_qty_L)), 0.0, 100.0)
        self.fuel_qty_R = _clamp(float(data.get('fuel_qty_R', self.fuel_qty_R)), 0.0, 100.0)
        self.heading = _normalize_heading(float(data.get('heading', self.heading)))
        self.track = _normalize_heading(float(data.get('track', self.track)))
        self.ground_speed = _clamp(float(data.get('ground_speed', self.ground_speed)), 0.0, 300.0)
        self.true_airspeed = _clamp(float(data.get('true_airspeed', self.true_airspeed)), 0.0, 300.0)
        self.lat = _clamp(float(data.get('lat', self.lat)), -90.0, 90.0)
        lon = float(data.get('lon', self.lon))
        self.lon = ((lon + 180.0) % 360.0) - 180.0



    def update_from_gps(self, heading, track, lat=None, lon=None):

        """Mettre à jour les données depuis le GPS (peut inclure lat/lon)."""

        self.heading = heading

        self.track = track

        if lat is not None:
            try:
                self.lat = float(lat)
            except Exception:
                pass
        if lon is not None:
            try:
                self.lon = float(lon)
            except Exception:
                pass

        # Pas besoin d'appeler update_display car le timer le fait déjà



    def update_display(self):

        self._apply_engine_mode()

        self.rpm_widget.setValue(self.rpm)

        self.load_widget.setValue(self.load)

        self.fflow_widget.set_value(self.fflow)

        self.oil_psi_widget.set_value(int(self.oil_psi))

        self.oil_temp_widget.set_value(self.oil_temp)

        self.egt_widget.set_value(self.egt)

        self.fuel_temp_widget.set_values(self.fuel_temp_left, self.fuel_temp_right)

        max_gallons = 14.0

        left_gal = max(0.0, min(max_gallons, self.fuel_qty_L / 100.0 * max_gallons))

        right_gal = max(0.0, min(max_gallons, self.fuel_qty_R / 100.0 * max_gallons))

        self.fuel_qty_gal_widget.set_values(left_gal, right_gal)

        nav_state = {

            'mode': self.nav_mode,

            'heading': self.heading,

            'track': self.track,

            'desired_track': self.desired_track,

            'ground_speed': self.ground_speed,

            'true_airspeed': self.true_airspeed,

            'gps_source': self.gps_source,

            'gps_integrity': self.gps_integrity,

            'approach_mode': self.approach_mode,

            'com1_active': self.com1_active,

            'com1_standby': self.com1_standby,

            'com2_active': self.com2_active,

            'com2_standby': self.com2_standby,

            'distance_to_active': self.distance_to_waypoint,

            'ete_minutes': self.ete_minutes,

            'altitude_target': self.altitude_target,

            'deviation_nm': self.deviation_nm,

            'deviation_limit_nm': self.deviation_limit_nm,

            'range_nm': self.range_nm,

            'active_waypoint': self.active_waypoint,

            'next_waypoints': self.next_waypoints,

            'route_points': self.route_points,

        }

        self.cap_widget.update_navigation_state(nav_state)

        # Synchroniser certaines données vers la WebView GPS si présente
        try:
            gps = getattr(self, 'gps', None)
            if gps and getattr(gps, 'web_view', None):
                heading_val = int(round(self.heading)) % 360
                speed_val = int(round(self.ground_speed))
                lat_val = getattr(self, 'lat', 38.0)
                lon_val = getattr(self, 'lon', 25.0)
                js = (
                    f"(function(){{"
                    f" try {{ aircraftHeading = {heading_val}; aircraftSpeed = {speed_val}; aircraftLat = {lat_val}; aircraftLon = {lon_val}; if(typeof updateDisplay === 'function') updateDisplay(); }} catch(e) {{ /* ignore */ }}"
                    f"}})();"
                )
                try:
                    gps.web_view.page().runJavaScript(js)
                except Exception:
                    pass
        except Exception:
            pass



    def keyPressEvent(self, a0):

        if a0 is None:

            return

        key = a0.key()

        if key == KEY_N:

            self._cycle_engine_mode()

            self.update_display()

            return

        if self.engine_mode != MODE_MANUAL and key in self.engine_control_keys:

            a0.accept()

            return

        if key == KEY_UP:

            self.rpm = min(self.rpm + 100, 3000)

        elif key == KEY_DOWN:

            self.rpm = max(self.rpm - 100, 0)

        elif key == KEY_RIGHT:

            self.fflow = min(self.fflow + 0.5, 20)

        elif key == KEY_LEFT:

            self.fflow = max(self.fflow - 0.5, 0)

        elif key == KEY_W:

            self.oil_psi = min(self.oil_psi + 5, 100)

        elif key == KEY_S:

            self.oil_psi = max(self.oil_psi - 5, 0)

        elif key == KEY_E:

            self.oil_temp = min(self.oil_temp + 10, 300)

        elif key == KEY_D:

            self.oil_temp = max(self.oil_temp - 10, 50)

        elif key == KEY_R:

            self.egt = min(self.egt + 50, 1800)

        elif key == KEY_F:

            self.egt = max(self.egt - 50, 1000)

        elif key == KEY_T:

            self.fuel_temp_left = min(self.fuel_temp_left + 2, 160)

        elif key == KEY_G:

            self.fuel_temp_left = max(self.fuel_temp_left - 2, -40)

        elif key == KEY_Y:

            self.fuel_temp_right = min(self.fuel_temp_right + 2, 160)

        elif key == KEY_H:

            self.fuel_temp_right = max(self.fuel_temp_right - 2, -40)

        elif key == KEY_I:

            self.load = min(self.load + 5, 100)

        elif key == KEY_K:

            self.load = max(self.load - 5, 0)

        # Latitude: Z (north +), X (south -)
        elif key == KEY_Z:
            try:
                self.lat = min(90.0, self.lat + 0.001)
            except Exception:
                self.lat = 38.0

        elif key == KEY_X:
            try:
                self.lat = max(-90.0, self.lat - 0.001)
            except Exception:
                self.lat = 38.0

        # Longitude: C (east +), V (west -)
        elif key == KEY_C:
            try:
                self.lon = ((self.lon + 0.001 + 180.0) % 360.0) - 180.0
            except Exception:
                self.lon = 25.0

        elif key == KEY_V:
            try:
                self.lon = ((self.lon - 0.001 + 180.0) % 360.0) - 180.0
            except Exception:
                self.lon = 25.0

        elif key == KEY_U:

            self.fuel_qty_L = max(0, min(100, self.fuel_qty_L - 5))

        elif key == KEY_J:

            self.fuel_qty_L = max(0, min(100, self.fuel_qty_L + 5))

        elif key == KEY_O:

            self.fuel_qty_R = max(0, min(100, self.fuel_qty_R - 5))

        elif key == KEY_L:

            self.fuel_qty_R = max(0, min(100, self.fuel_qty_R + 5))

        elif key == KEY_PAGE_UP:

            self.heading = (self.heading + 5) % 360

        elif key == KEY_PAGE_DOWN:

            self.heading = (self.heading - 5) % 360

        elif key == KEY_M:

            self.nav_mode = self.cap_widget.cycle_mode()

        self.update_display()





def main():

    app = QApplication(sys.argv)

    window = EngineDisplay()

    window.show()

    sys.exit(app.exec_())





if __name__ == '__main__':

    main()

