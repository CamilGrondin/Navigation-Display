import math
import gzip
import os
import queue
import socket
import subprocess
import struct
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, cast

from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer, QUrl
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


def _append_chromium_flag(flag):
    current = os.environ.get('QTWEBENGINE_CHROMIUM_FLAGS', '').strip()
    if flag in current.split():
        return
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = f'{current} {flag}'.strip()


def _configure_qtwebengine_runtime():
    if sys.platform != 'darwin':
        return
    setting = os.environ.get('NAVIGATION_DISPLAY_QTWEBENGINE_JITLESS', '1').strip().lower()
    if setting in ('0', 'false', 'no'):
        return
    # tar1090 can crash the embedded V8 renderer on some macOS QtWebEngine builds.
    _append_chromium_flag('--js-flags=--jitless')


_configure_qtwebengine_runtime()

try:
    from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineSettings, QWebEngineView
except ImportError:  # pragma: no cover - optional dependency
    QWebEnginePage = None
    QWebEngineSettings = None
    QWebEngineView = None

try:
    import serial  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    serial = None

try:
    import pygame  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    pygame = None


ALIGN_CENTER = getattr(Qt, 'AlignCenter', getattr(getattr(Qt, 'AlignmentFlag', Qt), 'AlignCenter'))
ALIGN_LEFT = getattr(Qt, 'AlignLeft', getattr(getattr(Qt, 'AlignmentFlag', Qt), 'AlignLeft'))
ALIGN_RIGHT = getattr(Qt, 'AlignRight', getattr(getattr(Qt, 'AlignmentFlag', Qt), 'AlignRight'))
ALIGN_VCENTER = getattr(Qt, 'AlignVCenter', getattr(getattr(Qt, 'AlignmentFlag', Qt), 'AlignVCenter'))
ALIGN_TOP = getattr(Qt, 'AlignTop', getattr(getattr(Qt, 'AlignmentFlag', Qt), 'AlignTop'))
STRONG_FOCUS = getattr(Qt, 'StrongFocus', getattr(getattr(Qt, 'FocusPolicy', Qt), 'StrongFocus'))
NO_CONTEXT_MENU = getattr(Qt, 'NoContextMenu', getattr(getattr(Qt, 'ContextMenuPolicy', Qt), 'NoContextMenu'))
VERTICAL_ORIENTATION = getattr(Qt, 'Vertical', getattr(getattr(Qt, 'Orientation', Qt), 'Vertical'))
FLAT_CAP_STYLE = getattr(Qt, 'FlatCap', getattr(getattr(Qt, 'PenCapStyle', Qt), 'FlatCap'))
POINTING_HAND_CURSOR = getattr(Qt, 'PointingHandCursor', getattr(getattr(Qt, 'CursorShape', Qt), 'PointingHandCursor'))

if sys.platform == 'darwin':
    MONOSPACE_FAMILY = 'Menlo'
elif sys.platform.startswith('win'):
    MONOSPACE_FAMILY = 'Consolas'
else:
    MONOSPACE_FAMILY = 'DejaVu Sans Mono'

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

MODE_MANUAL = 1
MODE_XPLANE = 2
MODE_MSP = 3


@dataclass
class WaypointInfo:
    name: str
    distance_nm: float = 0.0
    ete_min: float = 0.0
    altitude_constraint: str = ''
    is_active: bool = False


def prompt_text(label: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default is not None else ''
    value = input(f"{label}{suffix}: ").strip()
    if value:
        return value
    if default is not None:
        return default
    raise ValueError(f'{label} est requis')


def prompt_int(label: str, default: Optional[int] = None) -> int:
    while True:
        value = prompt_text(label, str(default) if default is not None else None)
        try:
            return int(value)
        except ValueError:
            print('Veuillez entrer un nombre entier valide.')


def choose_mode() -> int:
    env_mode = os.environ.get('NAVIGATION_DISPLAY_MODE')
    if env_mode is not None:
        try:
            mode = int(env_mode.strip())
            if mode in (MODE_MANUAL, MODE_XPLANE, MODE_MSP):
                print(f'Mode force via NAVIGATION_DISPLAY_MODE={mode}.')
                return mode
            print(f'NAVIGATION_DISPLAY_MODE invalide ({env_mode!r}), retour au choix interactif.')
        except ValueError:
            print(f'NAVIGATION_DISPLAY_MODE invalide ({env_mode!r}), retour au choix interactif.')

    print('Navigation Display')
    print('1 - Controle manuel (clavier)')
    print('2 - Donnees temps reel X-Plane (UDP)')
    print('3 - Donnees GPS MSP (port serie)')
    while True:
        mode = prompt_int('Choisir le mode', 2)
        if mode in (MODE_MANUAL, MODE_XPLANE, MODE_MSP):
            return mode
        print('Le mode doit etre 1, 2 ou 3.')


def choose_screen_layout() -> bool:
    env_layout = os.environ.get('NAVIGATION_DISPLAY_LAYOUT')
    if env_layout is not None:
        token = env_layout.strip().lower()
        if token in ('1', 'full', 'complete', 'panels', 'with-panels', 'avec-panneaux'):
            print(f'Affichage force via NAVIGATION_DISPLAY_LAYOUT={env_layout} (ecran complet).')
            return True
        if token in ('2', 'center', 'minimal', 'no-panels', 'sans-panneaux'):
            print(f'Affichage force via NAVIGATION_DISPLAY_LAYOUT={env_layout} (ecran central).')
            return False
        print(f'NAVIGATION_DISPLAY_LAYOUT invalide ({env_layout!r}), retour au choix interactif.')

    print('Affichage')
    print('1 - Ecran complet (panneaux lateraux + ecran central)')
    print('2 - Ecran central uniquement')
    while True:
        value = prompt_int('Choisir l affichage', 1)
        if value == 1:
            return True
        if value == 2:
            return False
        print('Le choix doit etre 1 ou 2.')


class XPlaneUDPRealtimeSource:

    # id -> dataref
    DATAREFS = {
        1: 'sim/flightmodel/position/true_psi',
        2: 'sim/flightmodel/position/hpath',
        3: 'sim/flightmodel/position/groundspeed',
        4: 'sim/flightmodel/position/latitude',
        5: 'sim/flightmodel/position/longitude',
        6: 'sim/flightmodel/position/elevation',
        10: 'sim/cockpit2/engine/indicators/engine_speed_rpm[0]',
        11: 'sim/cockpit2/engine/indicators/engine_power_hp[0]',
        12: 'sim/cockpit2/engine/indicators/fuel_flow_kg_sec[0]',
        13: 'sim/cockpit2/engine/indicators/oil_pressure_psi[0]',
        14: 'sim/cockpit2/engine/indicators/oil_temperature_deg_C[0]',
        15: 'sim/cockpit2/engine/indicators/EGT_deg_C[0]',
        16: 'sim/cockpit2/fuel/fuel_quantity[0]',
        17: 'sim/cockpit2/fuel/fuel_quantity[1]',
    }

    def __init__(self, ip: str, port: int, local_port: int = 49005, frequency_hz: int = 10):
        self.ip = ip
        self.port = int(port)
        self.local_port = int(local_port)
        self.frequency_hz = int(max(1, frequency_hz))
        self.data_queue: 'queue.Queue[Dict[str, float]]' = queue.Queue(maxsize=200)
        self.error_queue: 'queue.Queue[Exception]' = queue.Queue(maxsize=1)
        self.thread: Optional[threading.Thread] = None
        self._running = threading.Event()

    def _build_subscribe_packet(self, request_id: int, dataref: str) -> bytes:
        payload = struct.pack('<ii400s', self.frequency_hz, request_id, dataref.encode('ascii'))
        return b'RREF\x00' + payload

    def _build_unsubscribe_packet(self, request_id: int, dataref: str) -> bytes:
        payload = struct.pack('<ii400s', 0, request_id, dataref.encode('ascii'))
        return b'RREF\x00' + payload

    def start(self):
        if self.thread is not None:
            return
        self._running.set()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
        print(f'Mode 2 actif: X-Plane UDP {self.ip}:{self.port} (local:{self.local_port})')

    def stop(self):
        self._running.clear()

    def _worker(self):
        sock = None
        fuel_kg_per_gallon = 2.72155
        max_tank_gallons = 14.0
        latest = {
            'heading': 0.0,
            'track': 0.0,
            'ground_speed': 0.0,
            'lat': 38.0,
            'lon': 25.0,
            'altitude_m': 0.0,
            'rpm': 0.0,
            'load': 0.0,
            'fflow': 0.0,
            'oil_psi': 0.0,
            'oil_temp': 100.0,
            'egt': 1200.0,
            'fuel_qty_L': 50.0,
            'fuel_qty_R': 50.0,
        }
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(0.25)
            sock.bind(('', self.local_port))

            for request_id, dataref in self.DATAREFS.items():
                sock.sendto(self._build_subscribe_packet(request_id, dataref), (self.ip, self.port))

            last_refresh = time.monotonic()
            while self._running.is_set():
                try:
                    packet, _ = sock.recvfrom(4096)
                except socket.timeout:
                    packet = b''

                now = time.monotonic()
                if now - last_refresh > 3.0:
                    for request_id, dataref in self.DATAREFS.items():
                        sock.sendto(self._build_subscribe_packet(request_id, dataref), (self.ip, self.port))
                    last_refresh = now

                if not packet or not packet.startswith(b'RREF,'):
                    continue

                updated = False
                payload = packet[5:]
                for offset in range(0, len(payload), 8):
                    chunk = payload[offset:offset + 8]
                    if len(chunk) != 8:
                        continue
                    request_id, value = struct.unpack('<if', chunk)
                    if request_id == 1:
                        latest['heading'] = float(value) % 360.0
                        updated = True
                    elif request_id == 2:
                        latest['track'] = float(value) % 360.0
                        updated = True
                    elif request_id == 3:
                        latest['ground_speed'] = float(value) * 1.943844
                        updated = True
                    elif request_id == 4:
                        latest['lat'] = float(value)
                        updated = True
                    elif request_id == 5:
                        latest['lon'] = float(value)
                        updated = True
                    elif request_id == 6:
                        latest['altitude_m'] = float(value)
                        updated = True
                    elif request_id == 10:
                        latest['rpm'] = max(0.0, float(value))
                        updated = True
                    elif request_id == 11:
                        # DA40 Lycoming IO-360 ~168 HP (utilise pour approx % load)
                        latest['load'] = max(0.0, min(100.0, float(value) / 168.0 * 100.0))
                        updated = True
                    elif request_id == 12:
                        kg_sec = max(0.0, float(value))
                        latest['fflow'] = kg_sec * 3600.0 / fuel_kg_per_gallon
                        updated = True
                    elif request_id == 13:
                        latest['oil_psi'] = max(0.0, float(value))
                        updated = True
                    elif request_id == 14:
                        temp_c = float(value)
                        latest['oil_temp'] = temp_c * 9.0 / 5.0 + 32.0
                        updated = True
                    elif request_id == 15:
                        temp_c = float(value)
                        latest['egt'] = temp_c * 9.0 / 5.0 + 32.0
                        updated = True
                    elif request_id == 16:
                        raw = max(0.0, float(value))
                        gallons = raw if raw <= 20.0 else raw / fuel_kg_per_gallon
                        latest['fuel_qty_L'] = max(0.0, min(100.0, gallons / max_tank_gallons * 100.0))
                        updated = True
                    elif request_id == 17:
                        raw = max(0.0, float(value))
                        gallons = raw if raw <= 20.0 else raw / fuel_kg_per_gallon
                        latest['fuel_qty_R'] = max(0.0, min(100.0, gallons / max_tank_gallons * 100.0))
                        updated = True

                if updated:
                    if self.data_queue.full():
                        try:
                            self.data_queue.get_nowait()
                        except queue.Empty:
                            pass
                    self.data_queue.put(dict(latest))
        except Exception as exc:
            if self.error_queue.empty():
                self.error_queue.put(exc)
        finally:
            if sock is not None:
                try:
                    for request_id, dataref in self.DATAREFS.items():
                        sock.sendto(self._build_unsubscribe_packet(request_id, dataref), (self.ip, self.port))
                except Exception:
                    pass
                try:
                    sock.close()
                except Exception:
                    pass

    def poll(self, timeout: float = 0.05) -> Optional[Dict[str, float]]:
        if not self.error_queue.empty():
            raise RuntimeError(f'Source X-Plane arretee: {self.error_queue.get()}')
        try:
            return self.data_queue.get(timeout=timeout)
        except queue.Empty:
            return None


class MSPGPSRealtimeSource:

    MSP_GPS = 106
    HEADER_REQUEST = b'$M<'
    HEADER_RESPONSE = b'$M>'

    def __init__(self, port: str, baudrate: int, timeout: float = 0.35):
        if serial is None:
            raise RuntimeError('pyserial est requis pour le mode MSP. Installez: pip install pyserial')
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.data_queue: 'queue.Queue[Dict[str, float]]' = queue.Queue(maxsize=120)
        self.error_queue: 'queue.Queue[Exception]' = queue.Queue(maxsize=1)
        self.thread: Optional[threading.Thread] = None
        self._running = threading.Event()

    def start(self):
        if self.thread is not None:
            return
        self._running.set()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
        print(f'Mode MSP actif sur {self.port} @ {self.baudrate} bauds')

    def stop(self):
        self._running.clear()

    def _build_request(self, cmd: int) -> bytes:
        checksum = cmd
        return self.HEADER_REQUEST + bytes((0, cmd, checksum))

    def _read_exact(self, conn, count: int, timeout: float) -> Optional[bytes]:
        buffer = bytearray()
        deadline = time.monotonic() + timeout
        while len(buffer) < count and time.monotonic() < deadline:
            chunk = conn.read(count - len(buffer))
            if not chunk:
                continue
            buffer.extend(chunk)
        if len(buffer) != count:
            return None
        return bytes(buffer)

    def _read_response(self, conn) -> Optional[tuple[int, bytes]]:
        start = time.monotonic()
        marker = bytearray()
        while time.monotonic() - start < self.timeout:
            b = conn.read(1)
            if not b:
                continue
            marker.extend(b)
            if marker.endswith(self.HEADER_RESPONSE):
                break
        if not marker.endswith(self.HEADER_RESPONSE):
            return None

        length_raw = self._read_exact(conn, 1, self.timeout)
        cmd_raw = self._read_exact(conn, 1, self.timeout)
        if length_raw is None or cmd_raw is None:
            return None
        size = length_raw[0]
        cmd = cmd_raw[0]
        payload = self._read_exact(conn, size, self.timeout) or b''
        crc_raw = self._read_exact(conn, 1, self.timeout)
        if crc_raw is None:
            return None

        checksum = size ^ cmd
        for byte in payload:
            checksum ^= byte
        if checksum != crc_raw[0]:
            return None
        return cmd, payload

    def _parse_payload(self, payload: bytes) -> Optional[Dict[str, float]]:
        if len(payload) < 18:
            return None
        try:
            _, _, lat_raw, lon_raw, _, speed_raw, course_raw = struct.unpack('<BBiiiHH', payload[:18])
        except struct.error:
            return None

        speed_m_s = speed_raw / 100.0
        return {
            'lat': lat_raw / 1e7,
            'lon': lon_raw / 1e7,
            'ground_speed': speed_m_s * 1.943844,
            'track': float(course_raw) / 10.0,
            'heading': float(course_raw) / 10.0,
        }

    def _worker(self):
        conn = None
        try:
            conn = serial.Serial(self.port, self.baudrate, timeout=0.05)
            while self._running.is_set():
                conn.write(self._build_request(self.MSP_GPS))
                response = self._read_response(conn)
                if response and response[0] == self.MSP_GPS:
                    parsed = self._parse_payload(response[1])
                    if parsed is not None:
                        if self.data_queue.full():
                            try:
                                self.data_queue.get_nowait()
                            except queue.Empty:
                                pass
                        self.data_queue.put(parsed)
                time.sleep(0.08)
        except Exception as exc:
            if self.error_queue.empty():
                self.error_queue.put(exc)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    def poll(self, timeout: float = 0.05) -> Optional[Dict[str, float]]:
        if not self.error_queue.empty():
            raise RuntimeError(f'Source MSP arretee: {self.error_queue.get()}')
        try:
            return self.data_queue.get(timeout=timeout)
        except queue.Empty:
            return None


class ManualJoystickSource:
    """Source joystick USB pour le mode manuel (combinee avec le clavier)."""

    def __init__(self, joystick_name_hint: str = ''):
        if pygame is None:
            raise RuntimeError('pygame est requis pour le joystick USB. Installez: pip install pygame')

        pygame.init()
        pygame.joystick.init()
        count = pygame.joystick.get_count()
        if count <= 0:
            raise RuntimeError('Aucun joystick USB detecte.')

        hint = (joystick_name_hint or '').strip().lower()
        selected = None
        for idx in range(count):
            candidate = pygame.joystick.Joystick(idx)
            candidate.init()
            name = candidate.get_name()
            if hint and hint in name.lower():
                selected = candidate
                break
            if selected is None:
                selected = candidate

        if selected is None:
            raise RuntimeError('Impossible d initialiser le joystick USB.')

        self.joystick = selected
        self.last_t = time.monotonic()
        self.roll_deadzone = 0.08
        self.max_turn_rate_deg_s = 16.0
        self.load_tau = 1.0
        self.current_load = 35.0
        print(f'Joystick USB detecte: {self.joystick.get_name()}')

    def _axis(self, index: int, default: float = 0.0) -> float:
        if index >= self.joystick.get_numaxes():
            return default
        try:
            return float(self.joystick.get_axis(index))
        except Exception:
            return default

    def poll(self, timeout: float = 0.0) -> Optional[Dict[str, float]]:
        del timeout
        if pygame is None:
            return None

        try:
            pygame.event.pump()
        except Exception as exc:
            raise RuntimeError(f'Lecture joystick interrompue: {exc}') from exc

        now = time.monotonic()
        dt = max(0.001, now - self.last_t)
        self.last_t = now

        roll_axis = self._axis(0, 0.0)
        throttle_axis = self._axis(2, -1.0)
        throttle = max(0.0, min(1.0, (-throttle_axis + 1.0) / 2.0))

        turn_rate = 0.0 if abs(roll_axis) < self.roll_deadzone else roll_axis * self.max_turn_rate_deg_s
        heading_delta = turn_rate * dt

        target_load = 100.0 * throttle
        load_alpha = min(1.0, dt / self.load_tau)
        self.current_load += (target_load - self.current_load) * load_alpha

        return {
            'heading_delta': heading_delta,
            'load': max(0.0, min(100.0, self.current_load)),
        }

    def stop(self):
        try:
            self.joystick.quit()
        except Exception:
            pass
        try:
            pygame.joystick.quit()
        except Exception:
            pass


def build_navigation_source(mode: int):
    if mode == MODE_MANUAL:
        print('Mode 1 actif: controle manuel clavier')
        joystick_setting = os.environ.get('NAVIGATION_DISPLAY_MANUAL_JOYSTICK', '1').strip().lower()
        if joystick_setting in ('0', 'false', 'no'):
            print('Joystick USB desactive via NAVIGATION_DISPLAY_MANUAL_JOYSTICK.')
            return None

        if pygame is None:
            print('pygame non installe: mode manuel clavier uniquement.')
            return None

        joystick_hint = os.environ.get('NAVIGATION_DISPLAY_JOYSTICK_NAME', '').strip()
        try:
            source = ManualJoystickSource(joystick_name_hint=joystick_hint)
            print('Mode manuel combine: clavier + joystick USB.')
            return source
        except Exception as exc:
            print(f'Joystick USB indisponible ({exc}). Fallback clavier uniquement.')
        return None

    if mode == MODE_XPLANE:
        ip_env = os.environ.get('NAVIGATION_DISPLAY_XPLANE_IP', '').strip()
        port_env = os.environ.get('NAVIGATION_DISPLAY_XPLANE_PORT', '').strip()
        local_port_env = os.environ.get('NAVIGATION_DISPLAY_XPLANE_LOCAL_PORT', '').strip()

        ip = ip_env or prompt_text('Adresse IP X-Plane', '127.0.0.1')
        if ip_env:
            print(f'Adresse X-Plane forcee via NAVIGATION_DISPLAY_XPLANE_IP={ip}.')

        if port_env:
            try:
                port = int(port_env)
                print(f'Port X-Plane force via NAVIGATION_DISPLAY_XPLANE_PORT={port}.')
            except ValueError:
                print(f'NAVIGATION_DISPLAY_XPLANE_PORT invalide ({port_env!r}), retour au prompt.')
                port = prompt_int('Port UDP X-Plane', 49000)
        else:
            port = prompt_int('Port UDP X-Plane', 49000)

        if local_port_env:
            try:
                local_port = int(local_port_env)
                print(
                    'Port local force via '
                    f'NAVIGATION_DISPLAY_XPLANE_LOCAL_PORT={local_port}.'
                )
            except ValueError:
                print(
                    f'NAVIGATION_DISPLAY_XPLANE_LOCAL_PORT invalide ({local_port_env!r}), '
                    'retour au prompt.'
                )
                local_port = prompt_int('Port UDP local ecoute', 49005)
        else:
            local_port = prompt_int('Port UDP local ecoute', 49005)

        try:
            source = XPlaneUDPRealtimeSource(ip=ip, port=port, local_port=local_port)
            source.start()
            return source
        except Exception as exc:
            print(f'Impossible de demarrer le mode X-Plane: {exc}')
            print('Demarrage sans source X-Plane.')
            return None

    msp_port_env = os.environ.get('NAVIGATION_DISPLAY_MSP_PORT', '').strip()
    msp_baud_env = os.environ.get('NAVIGATION_DISPLAY_MSP_BAUDRATE', '').strip()

    port = msp_port_env or prompt_text('Port serie MSP', 'COM3')
    if msp_port_env:
        print(f'Port MSP force via NAVIGATION_DISPLAY_MSP_PORT={port}.')

    if msp_baud_env:
        try:
            baudrate = int(msp_baud_env)
            print(f'Baudrate MSP force via NAVIGATION_DISPLAY_MSP_BAUDRATE={baudrate}.')
        except ValueError:
            print(f'NAVIGATION_DISPLAY_MSP_BAUDRATE invalide ({msp_baud_env!r}), retour au prompt.')
            baudrate = prompt_int('Baud rate MSP', 115200)
    else:
        baudrate = prompt_int('Baud rate MSP', 115200)

    try:
        source = MSPGPSRealtimeSource(port=port, baudrate=baudrate)
        source.start()
        print('Mode 3 actif: donnees GPS MSP temps reel')
        return source
    except Exception as exc:
        print(f'Impossible de demarrer le mode MSP: {exc}')
        print('Demarrage sans source MSP.')
        return None


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
        self.setMinimumSize(168, 118)

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
        min_height=62,
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


class BezelSidePanel(QWidget):

    def __init__(
        self,
        title: str,
        button_labels: List[str],
        handlers: Optional[Dict[str, Callable[[], None]]] = None,
    ):
        super().__init__()
        self.handlers = handlers or {}
        self.buttons: Dict[str, QPushButton] = {}
        self.setFixedWidth(116)
        self.setStyleSheet('background-color: #1f232a; border: 1px solid #4a5059; border-radius: 8px;')

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setAlignment(ALIGN_CENTER)
        title_label.setStyleSheet('color: #d7dbe4; font: bold 18px Arial; border: none;')
        layout.addWidget(title_label)

        for label_text in button_labels:
            button = QPushButton(label_text)
            button.setMinimumHeight(40)
            button.setStyleSheet(
                'QPushButton { color: #eceff4; font: bold 10px Arial; background-color: #2b3038; '
                'border: 1px solid #626a75; border-radius: 5px; }'
                'QPushButton:pressed { background-color: #3c4350; }'
            )
            callback = self.handlers.get(label_text)
            if callback is not None:
                button.clicked.connect(callback)
            self.buttons[label_text] = button
            layout.addWidget(button)

        layout.addStretch()
        knob = QLabel('O')
        knob.setAlignment(ALIGN_CENTER)
        knob.setStyleSheet(
            'color: #aeb6c3; font: bold 28px Arial; background-color: #171a1f; '
            'border: 2px solid #606875; border-radius: 28px; min-height: 56px;'
        )
        layout.addWidget(knob)
        self.setLayout(layout)


class SoftKeyStrip(QWidget):

    def __init__(self, labels: List[str], handlers: Optional[Dict[str, Callable[[], None]]] = None):
        super().__init__()
        self.handlers = handlers or {}
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        for label_text in labels:
            key = QPushButton(label_text or ' ')
            key.setMinimumHeight(34)
            key.setStyleSheet(
                'QPushButton { color: #f3f5f7; font: bold 11px Arial; background-color: #2a2f37; '
                'border: 1px solid #5f6672; border-radius: 5px; min-width: 60px; }'
                'QPushButton:pressed { background-color: #3d4552; }'
            )
            callback = self.handlers.get(label_text)
            if callback is not None:
                key.clicked.connect(callback)
            layout.addWidget(key)

        self.setLayout(layout)





class GPSWidget(QWidget):
    def __init__(self, enable_sync=True):
        super().__init__()
        self.setStyleSheet('background-color: #202020;')
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        self.web_view = None
        self.enable_sync = enable_sync
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
        if ok and self.web_view and self.enable_sync:
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


class VolantaWidget(QWidget):

    FLIGHTRADAR_URL = 'https://www.flightradar24.com/'
    VOLANTA_URL = 'https://fly.volanta.app/'
    ADSB_EXCHANGE_URL = 'https://globe.adsbexchange.com/'
    ADSB_EXCHANGE_FALLBACK_URL = 'https://globe.adsb.fi/'
    DESKTOP_UA = (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/123.0.0.0 Safari/537.36'
    )
    MODAL_AUTO_CLOSE_JS = """
        (function() {
            function isVisible(el) {
                if (!el || !el.getBoundingClientRect) return false;
                var style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
                var rect = el.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0;
            }

            function isLikelyModal(el) {
                if (!isVisible(el)) return false;
                var style = window.getComputedStyle(el);
                var rect = el.getBoundingClientRect();
                var fixedish = style.position === 'fixed' || style.position === 'sticky' || style.position === 'absolute';
                var z = parseInt(style.zIndex || '0', 10);
                var className = (el.className || '').toString().toLowerCase();
                var role = (el.getAttribute('role') || '').toLowerCase();
                var hinted = (
                    role === 'dialog' ||
                    className.indexOf('modal') >= 0 ||
                    className.indexOf('popup') >= 0 ||
                    className.indexOf('dialog') >= 0 ||
                    className.indexOf('tour') >= 0
                );
                var largeEnough = rect.width >= Math.min(280, window.innerWidth * 0.35) && rect.height >= Math.min(180, window.innerHeight * 0.22);
                return largeEnough && (hinted || (fixedish && z >= 10));
            }

            function closeWithinModal(modal) {
                var modalRect = modal.getBoundingClientRect();
                var nodes = Array.from(modal.querySelectorAll('button, [role="button"], a, div, span'));
                for (var i = 0; i < nodes.length; i += 1) {
                    var el = nodes[i];
                    if (!isVisible(el)) continue;
                    var rect = el.getBoundingClientRect();
                    if (rect.width > 64 || rect.height > 64) continue;
                    var nearTopRight = rect.right >= modalRect.right - 130 && rect.top <= modalRect.top + 130;
                    if (!nearTopRight) continue;
                    var text = (el.innerText || el.textContent || '').trim().toLowerCase();
                    var aria = (el.getAttribute('aria-label') || '').trim().toLowerCase();
                    var title = (el.getAttribute('title') || '').trim().toLowerCase();
                    var cls = (el.className || '').toString().toLowerCase();
                    var hasCloseHint = (
                        text === 'x' || text === '×' || text === 'close' || text === 'fermer' ||
                        aria.indexOf('close') >= 0 || aria.indexOf('fermer') >= 0 ||
                        title.indexOf('close') >= 0 || cls.indexOf('close') >= 0 || cls.indexOf('dismiss') >= 0
                    );
                    if (!hasCloseHint && !(rect.width <= 40 && rect.height <= 40)) continue;
                    try {
                        el.click();
                        return true;
                    } catch (err) {
                    }
                }
                return false;
            }

            var blocks = Array.from(document.querySelectorAll('[role="dialog"], .modal, .popup, .dialog, div, section, article'));
            for (var i = 0; i < blocks.length; i += 1) {
                var block = blocks[i];
                if (!isLikelyModal(block)) continue;
                if (closeWithinModal(block)) {
                    break;
                }
            }
        })();
    """
    VOLANTA_UI_CLEANUP_JS = """
        (function() {
            function hideNode(node) {
                if (!node) return;
                node.style.setProperty('display', 'none', 'important');
                node.style.setProperty('visibility', 'hidden', 'important');
                node.style.setProperty('opacity', '0', 'important');
                node.style.setProperty('pointer-events', 'none', 'important');
            }

            function hideByText(targetText) {
                var target = targetText.toLowerCase();
                var nodes = Array.from(document.querySelectorAll('button, a, div, span'));
                for (var i = 0; i < nodes.length; i += 1) {
                    var el = nodes[i];
                    if (!el || !el.getBoundingClientRect) continue;
                    var text = (el.innerText || el.textContent || '').trim().toLowerCase();
                    if (!text || text.indexOf(target) < 0) continue;
                    var rect = el.getBoundingClientRect();
                    if (rect.top > 180 || rect.height > 90 || rect.width > 300) continue;
                    hideNode(el);
                }
            }

            hideByText('download app');

            var logoNodes = document.querySelectorAll('img[alt*="volanta" i], img[src*="volanta" i], [data-testid*="logo" i]');
            for (var i = 0; i < logoNodes.length; i += 1) {
                var logo = logoNodes[i];
                if (!logo || !logo.getBoundingClientRect) continue;
                var rect = logo.getBoundingClientRect();
                if (rect.top <= 170 && rect.left <= 260 && rect.height <= 100) {
                    hideNode(logo);
                }
            }

            var brandLabels = Array.from(document.querySelectorAll('span, div, a'));
            for (var i = 0; i < brandLabels.length; i += 1) {
                var label = brandLabels[i];
                if (!label || !label.getBoundingClientRect) continue;
                var txt = (label.innerText || label.textContent || '').trim().toLowerCase();
                if (txt !== 'volanta') continue;
                var r = label.getBoundingClientRect();
                if (r.top <= 170 && r.left <= 260 && r.height <= 80) {
                    hideNode(label);
                }
            }
        })();
    """
    ADSB_403_CHECK_JS = """
        (function() {
            var text = '';
            try {
                text = ((document.body && document.body.innerText) || '').toLowerCase();
            } catch (err) {
                return false;
            }
            return (
                text.indexOf('problem fetching data from the server: 403') >= 0 ||
                text.indexOf('problem fetching data from the server') >= 0 ||
                text.indexOf('error 403') >= 0 ||
                text.indexOf('forbidden') >= 0
            );
        })();
    """
    EMBED_MODE_JS = """
        (function() {
            if (!window.__ndVolanta) {
                window.__ndVolanta = {};
            }

            function looksLikeMapObject(value) {
                return value && typeof value.getZoom === 'function'
                    && (typeof value.zoomIn === 'function' || typeof value.zoomOut === 'function' || typeof value.zoomTo === 'function');
            }

            function findMap() {
                if (looksLikeMapObject(window.__ndVolanta.map)) {
                    return window.__ndVolanta.map;
                }
                if (looksLikeMapObject(window.map)) {
                    window.__ndVolanta.map = window.map;
                    return window.map;
                }
                try {
                    var keys = Object.keys(window);
                    for (var i = 0; i < keys.length; i += 1) {
                        var candidate = window[keys[i]];
                        if (looksLikeMapObject(candidate)) {
                            window.__ndVolanta.map = candidate;
                            return candidate;
                        }
                    }
                } catch (err) {
                }
                return null;
            }

            function zoomMap(step) {
                var map = findMap();
                if (!map) {
                    return false;
                }
                try {
                    if (step > 0 && typeof map.zoomIn === 'function') {
                        map.zoomIn({ duration: 80 });
                        return true;
                    }
                    if (step < 0 && typeof map.zoomOut === 'function') {
                        map.zoomOut({ duration: 80 });
                        return true;
                    }
                    if (typeof map.getZoom === 'function' && typeof map.zoomTo === 'function') {
                        var current = map.getZoom();
                        map.zoomTo(current + (step > 0 ? 0.6 : -0.6), { duration: 80 });
                        return true;
                    }
                } catch (err) {
                }
                return false;
            }

            function hideChrome() {
                var viewportW = window.innerWidth || 0;
                var viewportH = window.innerHeight || 0;
                var nodes = Array.from(document.querySelectorAll('header, nav, aside, [role="navigation"], [class*="side"], [class*="Side"], [class*="top"], [class*="Top"]'));
                for (var i = 0; i < nodes.length; i += 1) {
                    var el = nodes[i];
                    if (!el || !el.getBoundingClientRect) {
                        continue;
                    }
                    var style = window.getComputedStyle(el);
                    var rect = el.getBoundingClientRect();
                    var fixedish = style.position === 'fixed' || style.position === 'sticky';
                    if (!fixedish) {
                        continue;
                    }
                    var topBanner = rect.top <= 6 && rect.height <= 130 && rect.width >= viewportW * 0.35;
                    var leftRail = rect.left <= 6 && rect.width <= 130 && rect.height >= viewportH * 0.3;
                    if (topBanner || leftRail) {
                        el.style.setProperty('display', 'none', 'important');
                        el.style.setProperty('visibility', 'hidden', 'important');
                        el.style.setProperty('opacity', '0', 'important');
                        el.style.setProperty('pointer-events', 'none', 'important');
                    }
                }

                var mapRoots = Array.from(document.querySelectorAll('.mapboxgl-map, .leaflet-container, .mapboxgl-canvas-container'));
                for (var i = 0; i < mapRoots.length; i += 1) {
                    var mapRoot = mapRoots[i];
                    if (!mapRoot) continue;
                    mapRoot.style.setProperty('display', 'block', 'important');
                    mapRoot.style.setProperty('visibility', 'visible', 'important');
                    mapRoot.style.setProperty('opacity', '1', 'important');
                }

                document.body.style.setProperty('margin', '0', 'important');
                document.body.style.setProperty('padding', '0', 'important');
            }

            if (!window.__ndVolanta.zoomHookInstalled) {
                window.__ndVolanta.zoomHookInstalled = true;

                window.addEventListener('wheel', function(event) {
                    if (!(event.ctrlKey || event.metaKey)) {
                        return;
                    }
                    var step = event.deltaY < 0 ? 1 : -1;
                    if (zoomMap(step)) {
                        event.preventDefault();
                        event.stopPropagation();
                    }
                }, { capture: true, passive: false });

                window.addEventListener('keydown', function(event) {
                    if (!(event.ctrlKey || event.metaKey)) {
                        return;
                    }
                    var key = event.key;
                    if (key === '+' || key === '=' || key === '-') {
                        if (zoomMap(key === '-' ? -1 : 1)) {
                            event.preventDefault();
                            event.stopPropagation();
                        }
                    } else if (key === '0') {
                        event.preventDefault();
                        event.stopPropagation();
                    }
                }, true);
            }

            hideChrome();
            setTimeout(hideChrome, 180);
            setTimeout(hideChrome, 900);
        })();
        """

    @classmethod
    def mode_config(cls, mode):
        if mode == MODE_MANUAL:
            return ('Flight Radar', cls.FLIGHTRADAR_URL, False)
        if mode == MODE_MSP:
            return ('ADS-B Exchange', cls.ADSB_EXCHANGE_FALLBACK_URL, False)
        return ('Volanta', cls.VOLANTA_URL, True)

    @classmethod
    def tab_title_for_mode(cls, mode):
        title, _, _ = cls.mode_config(mode)
        return title

    def __init__(self, mode=MODE_XPLANE):

        super().__init__()

        self.site_title, self.site_url, self._use_embed_mode = self.mode_config(mode)
        self._adsb_fallback_used = False

        self.setStyleSheet('background-color: #1a1d24;')

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        self.web_view = None
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(900)
        self._sync_timer.timeout.connect(self._sync_embed_mode)

        if QWebEngineView is None:
            self._build_placeholder(
                f'PyQtWebEngine est requis pour afficher {self.site_title}.\nInstallez pyqtwebengine.',
                open_url=self.site_url,
            )
            return

        try:
            self.web_view = QWebEngineView()
            self.web_view.setContextMenuPolicy(NO_CONTEXT_MENU)
            page = self.web_view.page()
            if page is not None:
                profile = page.profile()
                if profile is not None:
                    profile.setHttpUserAgent(self.DESKTOP_UA)
            layout.addWidget(self.web_view)
            self.web_view.loadFinished.connect(self._on_page_loaded)
            self.web_view.load(QUrl(self.site_url))
        except Exception as exc:
            self.web_view = None
            self._build_placeholder(
                f'Erreur lors du chargement de {self.site_title} : {exc}',
                open_url=self.site_url,
            )

    def _on_page_loaded(self, ok):
        if not ok:
            return
        self._sync_embed_mode()
        if not self._sync_timer.isActive():
            self._sync_timer.start()

    def _sync_embed_mode(self):
        if not self.web_view:
            return
        try:
            if abs(float(self.web_view.zoomFactor()) - 1.0) > 0.0001:
                self.web_view.setZoomFactor(1.0)
        except Exception:
            pass
        page = self.web_view.page()
        if page is None:
            return
        page.runJavaScript(self.MODAL_AUTO_CLOSE_JS)
        if self._use_embed_mode:
            page.runJavaScript(self.EMBED_MODE_JS)
            page.runJavaScript(self.VOLANTA_UI_CLEANUP_JS)
        if self.site_title == 'ADS-B Exchange':
            page.runJavaScript(self.ADSB_403_CHECK_JS, self._on_adsb_403_check)

    def _on_adsb_403_check(self, has_403):
        if not has_403 or self._adsb_fallback_used or not self.web_view:
            return
        self._adsb_fallback_used = True
        print('ADS-B Exchange: erreur 403 detectee, bascule automatique vers le fallback ADS-B.')
        self.web_view.load(QUrl(self.ADSB_EXCHANGE_FALLBACK_URL))

    def _open_external_url(self, url):
        try:
            webbrowser.open(url)
        except Exception as exc:
            print(f'Impossible d ouvrir le navigateur: {exc}')

    def _build_placeholder(self, message, open_url=None):
        self._sync_timer.stop()
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

        title = QLabel(self.site_title.upper())
        title.setAlignment(ALIGN_CENTER)
        title.setStyleSheet('color: #7cfaff; font: bold 20px Arial;')

        content = QLabel(message)
        content.setWordWrap(True)
        content.setAlignment(ALIGN_CENTER)
        content.setStyleSheet('color: white; font: 14px Arial;')

        open_button = None
        if open_url:
            open_button = QPushButton(f'Ouvrir {self.site_title} dans le navigateur')
            open_button.setCursor(POINTING_HAND_CURSOR)
            open_button.setStyleSheet(
                'QPushButton { background: #0b7285; color: white; border: none; '
                'padding: 10px 16px; border-radius: 6px; font: bold 13px Arial; } '
                'QPushButton:hover { background: #1098ad; }'
            )
            open_button.clicked.connect(
                lambda _checked=False, target=open_url: self._open_external_url(target)
            )

        layout.addStretch()
        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(content)
        if open_button is not None:
            layout.addWidget(open_button)
        layout.addStretch()

class Tar1090Widget(QWidget):
    """Widget affichant la carte tar1090 (ADS-B) servie localement."""

    TAR1090_URL = 'http://127.0.0.1:8081/?noglobe'
    TAR1090_URL_SAFE = 'http://127.0.0.1:8081/?noglobe&pTracks'

    def __init__(self):
        super().__init__()
        self.setStyleSheet('background-color: #1a1d24;')
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        self.web_view = None
        self._initial_load_pending = True
        self._load_retry_count = 0
        self._max_load_retries = 8
        self._render_crash_count = 0
        self._max_render_crashes = 2
        self._safe_mode_enabled = False
        self._stability_timer = QTimer(self)
        self._stability_timer.setSingleShot(True)
        self._stability_timer.timeout.connect(self._reset_render_crash_counter)
        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.timeout.connect(self.reload_page)

        autostart_setting = os.environ.get('NAVIGATION_DISPLAY_AUTOSTART_ADSB', '1').strip().lower()
        if autostart_setting in ('0', 'false', 'no'):
            self._build_placeholder(
                'Les services ADS-B ne sont pas démarrés automatiquement.\n\n'
                'Pour activer tar1090, lancez readsb et le serveur HTTP manuellement, '
                'ou supprimez NAVIGATION_DISPLAY_AUTOSTART_ADSB=0 (ou false/no) avant de démarrer '
                'l’application.'
            )
            return

        if QWebEngineView is None or QWebEngineSettings is None or QWebEnginePage is None:
            self._build_placeholder(
                'PyQtWebEngine est requis pour afficher la carte tar1090.\n'
                'Installez pyqtwebengine.'
            )
            return

        self._create_web_view()

    def _clear_layout(self):
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
        return layout

    def _create_web_view(self):
        layout = self._clear_layout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        try:
            self.web_view = QWebEngineView()
            self.web_view.setContextMenuPolicy(NO_CONTEXT_MENU)
            layout.addWidget(self.web_view)

            # Configure WebEngine explicitly for complex map rendering in tar1090.
            settings = self.web_view.settings()
            if settings is not None:
                settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)
                settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
                settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
                settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
                settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
                settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)

            class WebPage(QWebEnginePage):
                def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
                    # Use numeric levels for compatibility across PyQt5 variants.
                    prefix = {0: "js [INFO]:", 1: "js [WARN]:", 2: "js [ERROR]:"}.get(int(level), "js:")
                    print(f"{prefix} {message} (Line: {lineNumber} in {sourceID})")

            current_page = self.web_view.page()
            profile = current_page.profile() if current_page is not None else None
            if profile is not None:
                self.web_page = WebPage(profile, self.web_view)
            else:
                self.web_page = WebPage(self.web_view)
            self.web_view.setPage(self.web_page)

            if hasattr(self.web_view, 'renderProcessTerminated'):
                self.web_view.renderProcessTerminated.connect(self._on_render_process_terminated)

            # Load lazily when the tab is visible; loading while hidden can leave map size at 0x0.
            self.web_view.loadFinished.connect(self._on_load_finished)
            self._initial_load_pending = True
            self._load_retry_count = 0
        except Exception as exc:
            self.web_view = None
            self._build_placeholder(
                f'Erreur lors du chargement de tar1090 : {exc}',
                open_url=self._target_url(),
                allow_retry=True,
            )

    def ensure_loaded(self):
        if not self.web_view:
            return
        if self._initial_load_pending:
            self._initial_load_pending = False
            self._load_retry_count = 0
            self.web_view.load(QUrl(self._target_url()))
            return
        self._nudge_map_render()

    def _target_url(self):
        return self.TAR1090_URL_SAFE if self._safe_mode_enabled else self.TAR1090_URL

    def _enable_safe_mode(self):
        if self._safe_mode_enabled or not self.web_view:
            return
        self._safe_mode_enabled = True
        settings = self.web_view.settings()
        if settings is None:
            return
        try:
            settings.setAttribute(QWebEngineSettings.WebGLEnabled, False)
        except Exception:
            pass
        accelerated_canvas_attr = getattr(QWebEngineSettings, 'Accelerated2dCanvasEnabled', None)
        if accelerated_canvas_attr is not None:
            try:
                settings.setAttribute(accelerated_canvas_attr, False)
            except Exception:
                pass

    def _nudge_map_render(self):
        if not self.web_view:
            return
        page = self.web_view.page()
        if page is None:
            return
        fix_render_js = """
        setTimeout(function() {
            if (typeof map !== 'undefined' && map) {
                map.updateSize();
            }
            window.dispatchEvent(new Event('resize'));
            document.body.style.backgroundColor = '#1a1d24';
        }, 120);
        """
        page.runJavaScript(fix_render_js)

    def _schedule_reload(self, delay_ms):
        if not self.web_view:
            return
        if self._reload_timer.isActive():
            return
        self._reload_timer.start(max(80, int(delay_ms)))

    def _reset_render_crash_counter(self):
        if self._render_crash_count:
            print('Tar1090: rendu stabilise, compteur de crash remis a zero.')
        self._render_crash_count = 0

    def _on_load_finished(self, ok):
        if not ok:
            # Connection can fail briefly if the local HTTP service is still starting.
            if self.web_view and self._load_retry_count < self._max_load_retries:
                self._load_retry_count += 1
                retry_ms = min(2200, 350 * self._load_retry_count)
                self._schedule_reload(retry_ms)
                return
            if not self._safe_mode_enabled:
                print('Tar1090: activation du mode de compatibilite (sans WebGL).')
                self._enable_safe_mode()
                self._load_retry_count = 0
                self._schedule_reload(220)
                return
            self._build_placeholder(
                'Impossible de charger la carte ADS-B apres plusieurs tentatives.\n\n'
                'Verifiez que readsb et le serveur HTTP local sont demarres puis reessayez.',
                open_url=self._target_url(),
                allow_retry=True,
            )
            return

        self._load_retry_count = 0
        # Keep crash count until rendering remains stable for a short period.
        self._stability_timer.start(7000)

        # Multiple nudges handle delayed layout computation in embedded tabs.
        QTimer.singleShot(120, self._nudge_map_render)
        QTimer.singleShot(1200, self._nudge_map_render)

    def _on_render_process_terminated(self, termination_status, exit_code):
        status_value = int(termination_status) if termination_status is not None else -1
        self._stability_timer.stop()
        self._render_crash_count += 1
        print(
            f'Tar1090: moteur Web termine (status={status_value}, exit={exit_code}), '
            f'tentative {self._render_crash_count}.'
        )

        if self._render_crash_count == 1:
            self._enable_safe_mode()

        if self.web_view and self._render_crash_count <= self._max_render_crashes:
            self._load_retry_count = 0
            self._schedule_reload(420)
            return

        self._build_placeholder(
            'Le moteur de rendu ADS-B a cesse de repondre.\n\n'
            'Le service ADS-B est actif, mais QtWebEngine plante sur cette page.\n'
            'Ouvrez tar1090 dans le navigateur avec le bouton ci-dessous.',
            open_url=self._target_url(),
            allow_retry=True,
        )

    def reload_page(self):
        if self.web_view:
            if self._initial_load_pending:
                self.ensure_loaded()
            else:
                self.web_view.load(QUrl(self._target_url()))

    def _open_external_url(self, url):
        try:
            webbrowser.open(url)
        except Exception as exc:
            print(f'Impossible d ouvrir le navigateur: {exc}')

    def _retry_embedded_view(self):
        if QWebEngineView is None or QWebEngineSettings is None or QWebEnginePage is None:
            self._build_placeholder(
                'PyQtWebEngine est requis pour afficher la carte tar1090.\n'
                'Installez pyqtwebengine.',
            )
            return
        self._stability_timer.stop()
        self._reload_timer.stop()
        self._render_crash_count = 0
        self._load_retry_count = 0
        self._initial_load_pending = True
        self._create_web_view()
        self.ensure_loaded()

    def _build_placeholder(self, message, open_url=None, allow_retry=False):
        self._stability_timer.stop()
        self._reload_timer.stop()
        layout = self._clear_layout()
        self.web_view = None
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
            'cd ~/tar1090/html && python3 -m http.server 8081\n\n'
            "Si readsb affiche usb_claim_interface error -3, arrêtez toute autre instance "
            'ou détachez le pilote kernel dvb_usb_rtl28xxu.\n\n'
            'Astuce: NAVIGATION_DISPLAY_AUTOSTART_ADSB=1 réactive le démarrage '
            'automatique.'
        )
        hint.setWordWrap(True)
        hint.setAlignment(ALIGN_CENTER)
        hint.setStyleSheet(f'color: #aaa; font: 12px "{MONOSPACE_FAMILY}";')

        open_button = None
        if open_url:
            open_button = QPushButton('Ouvrir tar1090 dans le navigateur')
            open_button.setCursor(POINTING_HAND_CURSOR)
            open_button.setStyleSheet(
                'QPushButton { background: #0b7285; color: white; border: none; '
                'padding: 10px 16px; border-radius: 6px; font: bold 13px Arial; } '
                'QPushButton:hover { background: #1098ad; }'
            )
            open_button.clicked.connect(
                lambda _checked=False, target=open_url: self._open_external_url(target)
            )

        retry_button = None
        if allow_retry:
            retry_button = QPushButton('Reessayer dans l application')
            retry_button.setCursor(POINTING_HAND_CURSOR)
            retry_button.setStyleSheet(
                'QPushButton { background: #2f3f57; color: white; border: none; '
                'padding: 10px 16px; border-radius: 6px; font: bold 13px Arial; } '
                'QPushButton:hover { background: #3e5678; }'
            )
            retry_button.clicked.connect(self._retry_embedded_view)

        layout.addStretch()
        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(content)
        if retry_button is not None:
            layout.addWidget(retry_button)
        if open_button is not None:
            layout.addWidget(open_button)
        layout.addSpacing(8)
        layout.addWidget(hint)
        layout.addStretch()


class NavigationDisplayWidget(QWidget):

    MODES = ('ROSE', 'ARC', 'MAP', 'PLAN')
    ARC_RADIUS_FACTOR = 0.48

    def __init__(self):

        super().__init__()

        self.setFocusPolicy(STRONG_FOCUS)

        self.setMinimumSize(360, 300)

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

        self.source_status = 'SRC MANUAL'

        self.source_color = '#a9b4c6'

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

        if self.mode == 'ARC':
            painter.fillRect(self.rect(), QColor('#d09a2b'))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(172, 124, 24, 120))
            painter.drawEllipse(QRectF(self.width() * 0.02, self.height() * 0.18, self.width() * 0.22, self.height() * 0.12))
            painter.drawEllipse(QRectF(self.width() * 0.74, self.height() * 0.72, self.width() * 0.24, self.height() * 0.16))
            painter.setBrush(QColor(126, 92, 18, 90))
            painter.drawEllipse(QRectF(self.width() * 0.08, self.height() * 0.54, self.width() * 0.30, self.height() * 0.20))
            painter.drawEllipse(QRectF(self.width() * 0.62, self.height() * 0.28, self.width() * 0.20, self.height() * 0.13))
            painter.setPen(QPen(QColor('#ff00c4'), 3))
            painter.drawLine(
                QPointF(self.width() * 0.50, self.height() * 0.14),
                QPointF(self.width() * 0.50, self.height() * 0.88),
            )
            painter.setPen(QPen(QColor('#1f1f1f'), 2))
            painter.drawLine(
                QPointF(self.width() * 0.57, self.height() * 0.14),
                QPointF(self.width() * 0.57, self.height() * 0.88),
            )
        else:
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

        com_font = QFont(MONOSPACE_FAMILY, 11, QFont.Bold)
        painter.setFont(com_font)
        com1_text = f"COM1  {self.com1_active}  <->  {self.com1_standby}"
        com2_text = f"COM2  {self.com2_active}  <->  {self.com2_standby}"
        painter.drawText(banner_rect.adjusted(0, 8, -18, -32), ALIGN_RIGHT | ALIGN_VCENTER, com1_text)
        painter.drawText(banner_rect.adjusted(0, 32, -18, -6), ALIGN_RIGHT | ALIGN_VCENTER, com2_text)

        status_font = QFont(MONOSPACE_FAMILY, 9, QFont.Bold)
        painter.setFont(status_font)
        painter.setPen(QColor(self.source_color))
        painter.drawText(banner_rect.adjusted(16, 0, -18, -48), ALIGN_RIGHT | ALIGN_VCENTER, self.source_status)


    def _draw_range_rings(self, painter, center, radius):


        if self.mode == 'ARC':
            painter.setPen(QPen(QColor('#eceef0'), 2))
            max_rings = 1
        else:
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

        ring_color = '#eceef0' if self.mode == 'ARC' else '#5a6a88'
        ring_pen = QPen(QColor(ring_color), 2)
        ring_pen.setCapStyle(Qt.FlatCap)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.NoBrush)

        if self.mode == 'ARC':
            painter.drawArc(ring_rect, 0, 180 * 16)
        else:
            painter.drawEllipse(ring_rect)

        tick_pen = QPen(QColor('#f2f4f5' if self.mode == 'ARC' else '#d7dbe4'), 2)
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

    def __init__(self, startup_mode=MODE_XPLANE, data_source=None, show_side_panels: bool = True):

        super().__init__()

        self.setWindowTitle('X-Plane 1000 Navigation Display')

        self.setGeometry(50, 40, 980, 660)

        self.setStyleSheet('background-color: #050505;')

        self._local_service_processes = []
        self.startup_mode = startup_mode
        self.data_source = data_source
        self.show_side_panels = bool(show_side_panels)
        self._xplane_cmd_target: Optional[tuple[str, int]] = None
        self._xplane_cmd_socket: Optional[socket.socket] = None
        self._source_error_reported = False
        self._last_source_rx_time: Optional[float] = None



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
        self._ranges = [5, 10, 20, 40, 80]

        if self.startup_mode in (MODE_XPLANE, MODE_MANUAL):
            xplane_ip = os.environ.get('NAV_DISPLAY_XPLANE_IP', '127.0.0.1').strip() or '127.0.0.1'
            xplane_port_raw = os.environ.get('NAV_DISPLAY_XPLANE_PORT', '49000').strip() or '49000'
            try:
                xplane_port = int(xplane_port_raw)
            except Exception:
                xplane_port = 49000
            default_target = (xplane_ip, xplane_port)
            if self.data_source is not None and hasattr(self.data_source, 'ip') and hasattr(self.data_source, 'port'):
                try:
                    default_target = (str(self.data_source.ip), int(self.data_source.port))
                except Exception:
                    pass
            self._xplane_cmd_target = default_target
            try:
                self._xplane_cmd_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            except Exception:
                self._xplane_cmd_socket = None

        if self.startup_mode == MODE_XPLANE:
            self.source_status = 'SRC XPLANE CONNECTING'
            self.source_color = '#ffd166'
        elif self.startup_mode == MODE_MSP:
            self.source_status = 'SRC MSP CONNECTING'
            self.source_color = '#ffd166'
        else:
            if self.data_source is not None:
                self.source_status = 'SRC JOYSTICK USB'
                self.source_color = '#69f0ae'
            else:
                self.source_status = 'SRC MANUAL'
                self.source_color = '#a9b4c6'



        main_layout = QVBoxLayout()

        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(0)



        left_col = QVBoxLayout()

        left_col.setSpacing(3)

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

        # Keep the engine strip compact to avoid forcing a near full-screen window height.
        self.rpm_widget.setMinimumHeight(108)
        self.rpm_widget.setMaximumHeight(108)
        self.load_widget.setMinimumHeight(108)
        self.load_widget.setMaximumHeight(108)
        self.fflow_widget.setMinimumHeight(42)
        self.fflow_widget.setMaximumHeight(42)
        for gauge in (
            self.oil_psi_widget,
            self.oil_temp_widget,
            self.egt_widget,
            self.fuel_temp_widget,
            self.fuel_qty_gal_widget,
        ):
            gauge.setMinimumHeight(58)
            gauge.setMaximumHeight(58)

        left_col.addWidget(self.fflow_widget)

        left_col.addWidget(self.oil_psi_widget)

        left_col.addWidget(self.oil_temp_widget)

        left_col.addWidget(self.egt_widget)

        left_col.addWidget(self.fuel_temp_widget)

        left_col.addWidget(self.fuel_qty_gal_widget)

        left_col.addStretch()



        self.gps = GPSWidget(enable_sync=False)

        self.cap_widget = CapWidget()

        self.greece_widget = GreeceMapWidget()

        self._mode_map_tab_title = VolantaWidget.tab_title_for_mode(self.startup_mode)
        self.volanta_widget = VolantaWidget(mode=self.startup_mode)

        # Start local ADS-B services before creating the embedded radar web view.
        self._start_local_services()

        self.tar1090_widget = Tar1090Widget()

        for widget in (self.gps, self.cap_widget, self.greece_widget, self.volanta_widget, self.tar1090_widget):

            widget.setMinimumSize(380, 320)

        self.display_tabs = QTabWidget()

        self.display_tabs.addTab(self.gps, 'GPS')

        self.display_tabs.addTab(self.cap_widget, 'Cap')

        self.display_tabs.addTab(self.greece_widget, 'Greece Map')

        self.display_tabs.addTab(self.volanta_widget, self._mode_map_tab_title)

        self.display_tabs.addTab(self.tar1090_widget, 'ADS-B Radar')

        self.display_tabs.setCurrentWidget(self.cap_widget)
        self.display_tabs.currentChanged.connect(self._on_display_tab_changed)
        self.display_tabs.setStyleSheet(
            'QTabWidget::pane { border: 1px solid #5b636f; background: #0a0e15; }'
            'QTabBar::tab { background: #1a1f26; color: #c5cedb; padding: 6px 12px; border: 1px solid #4f5763; }'
            'QTabBar::tab:selected { background: #2a6fc7; color: white; }'
        )

        bezel_frame = QFrame()
        bezel_frame.setObjectName('bezelFrame')
        bezel_frame.setStyleSheet(
            'QFrame#bezelFrame {'
            'background-color: #20252d; border: 2px solid #565d68; border-radius: 14px;'
            '}'
        )

        bezel_layout = QVBoxLayout()
        bezel_layout.setContentsMargins(12, 12, 12, 12)
        bezel_layout.setSpacing(10)

        top_header = QLabel('X-PLANE 1000')
        top_header.setAlignment(ALIGN_CENTER)
        top_header.setFixedHeight(34)
        top_header.setStyleSheet(
            'color: #d7dbe4; font: bold 17px Arial; '
            'background-color: #161a20; border: 1px solid #4f5762; border-radius: 6px;'
        )
        bezel_layout.addWidget(top_header)

        center_row = QHBoxLayout()
        center_row.setSpacing(10)

        left_handlers = {
            'PUSH\nVOL ID': self._action_ap_master_toggle,
            'HDG': self._action_heading_plus,
            'AP': self._action_sync_ap_heading,
            'NAV': self._action_ap_nav,
            'APR': self._action_ap_apr,
            'ALT': self._action_ap_alt,
        }
        right_handlers = {
            'PUSH\nVOL SQ': self._action_radio_swap_com1,
            'CRS-BARO': self._action_radio_com1_coarse_up,
            'RANGE': self._action_radio_com1_fine_up,
            'PAN': self._action_radio_swap_com2,
            'FPL': self._action_radio_com2_coarse_up,
            'PROC': self._action_radio_com2_fine_up,
        }
        if self.show_side_panels:
            left_bezel = BezelSidePanel('NAV', ['PUSH\nVOL ID', 'HDG', 'AP', 'NAV', 'APR', 'ALT'], left_handlers)
            center_row.addWidget(left_bezel)

        screen_container = QFrame()
        screen_container.setStyleSheet('background-color: #05070a; border: 1px solid #707887;')
        screen_layout = QHBoxLayout()
        screen_layout.setContentsMargins(8, 8, 8, 8)
        screen_layout.setSpacing(8)

        engine_strip = QFrame()
        engine_strip.setFixedWidth(220)
        engine_strip.setStyleSheet('background-color: #090d12; border: 1px solid #3f4751;')
        engine_strip.setLayout(left_col)
        screen_layout.addWidget(engine_strip)

        center_display = QFrame()
        center_display.setStyleSheet('background-color: #020406; border: 2px solid #aeb6c3;')
        center_display_layout = QVBoxLayout()
        center_display_layout.setContentsMargins(0, 0, 0, 0)
        center_display_layout.setSpacing(0)
        center_display_layout.addWidget(self.display_tabs)
        center_display.setLayout(center_display_layout)

        screen_layout.addWidget(center_display, stretch=1)
        screen_container.setLayout(screen_layout)

        center_row.addWidget(screen_container, stretch=1)
        if self.show_side_panels:
            right_bezel = BezelSidePanel('COM', ['PUSH\nVOL SQ', 'CRS-BARO', 'RANGE', 'PAN', 'FPL', 'PROC'], right_handlers)
            center_row.addWidget(right_bezel)
        bezel_layout.addLayout(center_row, stretch=1)

        softkey_handlers = {
            'SYSTEM': self._action_tab_gps,
            'MAP': self._action_tab_greece,
            'VOL': self._action_tab_volanta,
            'NAV': self._action_tab_cap,
            'DCLTR': self._action_mode_cycle,
        }
        softkeys = SoftKeyStrip(['SYSTEM', '', 'MAP', '', 'VOL', '', '', '', 'NAV', '', 'DCLTR', ''], softkey_handlers)
        bezel_layout.addWidget(softkeys)

        bezel_frame.setLayout(bezel_layout)
        main_layout.addWidget(bezel_frame)
        self.setLayout(main_layout)



        self.setFocusPolicy(STRONG_FOCUS)

        self.timer = QTimer(self)

        self.timer.timeout.connect(self.update_display)

        self.timer.start(100)

        self.update_display()

    def _send_xplane_dref(self, dataref: str, value: float):
        if self._xplane_cmd_socket is None or self._xplane_cmd_target is None:
            return
        try:
            payload = struct.pack('<f500s', float(value), dataref.encode('ascii'))
            packet = b'DREF\x00' + payload
            self._xplane_cmd_socket.sendto(packet, self._xplane_cmd_target)
        except Exception:
            pass

    def _send_xplane_command(self, command: str):
        if self._xplane_cmd_socket is None or self._xplane_cmd_target is None:
            return
        try:
            packet = b'CMND\x00' + command.encode('ascii')
            self._xplane_cmd_socket.sendto(packet, self._xplane_cmd_target)
        except Exception:
            pass

    def _push_navigation_to_xplane(self):
        try:
            selected_alt = float(str(self.altitude_target).split()[0])
        except Exception:
            selected_alt = 2500.0
        self._send_xplane_dref('sim/cockpit/autopilot/heading_mag', self.desired_track)
        self._send_xplane_dref('sim/cockpit2/autopilot/heading_dial_deg_mag_pilot', self.desired_track)
        self._send_xplane_dref('sim/cockpit/radios/nav1_obs_degm', self.desired_track)
        self._send_xplane_dref('sim/cockpit2/autopilot/altitude_dial_ft', selected_alt)

    def _format_freq(self, value: float) -> str:
        return f'{value:.3f}'

    def _send_com_standby(self, index: int, freq_mhz: float):
        freq_mhz = max(118.000, min(136.975, freq_mhz))
        hz833 = int(round(freq_mhz * 1000.0))
        hz25 = int(round(freq_mhz * 100.0))
        if index == 1:
            self._send_xplane_dref('sim/cockpit/radios/com1_stdby_freq_hz_833', hz833)
            self._send_xplane_dref('sim/cockpit/radios/com1_stdby_freq_hz', hz25)
        else:
            self._send_xplane_dref('sim/cockpit/radios/com2_stdby_freq_hz_833', hz833)
            self._send_xplane_dref('sim/cockpit/radios/com2_stdby_freq_hz', hz25)

    def _action_ap_master_toggle(self):
        self._send_xplane_command('sim/autopilot/servos_toggle')

    def _action_ap_nav(self):
        self._send_xplane_command('sim/autopilot/NAV')

    def _action_ap_apr(self):
        self._send_xplane_command('sim/autopilot/approach')

    def _action_ap_alt(self):
        self._send_xplane_command('sim/autopilot/altitude_hold')

    def _action_source_cycle(self):
        self.gps_source = 'GPS2' if self.gps_source == 'GPS1' else 'GPS1'
        self.update_display()

    def _action_heading_plus(self):
        self.desired_track = (self.desired_track + 1) % 360
        self._push_navigation_to_xplane()
        self.update_display()

    def _action_sync_ap_heading(self):
        self.desired_track = self.heading
        self._send_xplane_dref('sim/cockpit/autopilot/heading_mag', self.desired_track)
        self._send_xplane_dref('sim/cockpit2/autopilot/heading_dial_deg_mag_pilot', self.desired_track)
        self._send_xplane_command('sim/autopilot/heading')
        self.update_display()

    def _action_tab_cap(self):
        self.display_tabs.setCurrentWidget(self.cap_widget)

    def _action_mode_arc(self):
        self.nav_mode = 'ARC'
        self.update_display()

    def _action_altitude_plus(self):
        try:
            current = int(str(self.altitude_target).split()[0])
        except Exception:
            current = 2500
        current = min(12000, current + 100)
        self.altitude_target = f'{current} FT'
        self._send_xplane_dref('sim/cockpit2/autopilot/altitude_dial_ft', float(current))
        self.update_display()

    def _action_tab_gps(self):
        self.display_tabs.setCurrentWidget(self.gps)

    def _action_course_plus(self):
        self.desired_track = (self.desired_track + 5) % 360
        self._send_xplane_dref('sim/cockpit/radios/nav1_obs_degm', self.desired_track)
        self._send_xplane_dref('sim/cockpit/radios/nav2_obs_degm', self.desired_track)
        self.update_display()

    def _action_radio_swap_com1(self):
        self.com1_active, self.com1_standby = self.com1_standby, self.com1_active
        self._send_xplane_command('sim/radios/com1_standy_flip')
        self.update_display()

    def _action_radio_com1_coarse_up(self):
        freq = float(self.com1_standby)
        freq = min(136.975, freq + 1.0)
        self.com1_standby = self._format_freq(freq)
        self._send_com_standby(1, freq)
        self._send_xplane_command('sim/radios/stby_com1_coarse_up')
        self.update_display()

    def _action_radio_com1_fine_up(self):
        freq = float(self.com1_standby)
        freq += 0.005
        if freq > 136.975:
            freq = 118.000
        self.com1_standby = self._format_freq(freq)
        self._send_com_standby(1, freq)
        self._send_xplane_command('sim/radios/stby_com1_fine_up')
        self._send_xplane_command('sim/radios/stby_com1_fine_up_833')
        self.update_display()

    def _action_radio_swap_com2(self):
        self.com2_active, self.com2_standby = self.com2_standby, self.com2_active
        self._send_xplane_command('sim/radios/com2_standy_flip')
        self.update_display()

    def _action_radio_com2_coarse_up(self):
        freq = float(self.com2_standby)
        freq = min(136.975, freq + 1.0)
        self.com2_standby = self._format_freq(freq)
        self._send_com_standby(2, freq)
        self._send_xplane_command('sim/radios/stby_com2_coarse_up')
        self.update_display()

    def _action_radio_com2_fine_up(self):
        freq = float(self.com2_standby)
        freq += 0.005
        if freq > 136.975:
            freq = 118.000
        self.com2_standby = self._format_freq(freq)
        self._send_com_standby(2, freq)
        self._send_xplane_command('sim/radios/stby_com2_fine_up')
        self._send_xplane_command('sim/radios/stby_com2_fine_up_833')
        self.update_display()

    def _action_range_cycle(self):
        try:
            idx = self._ranges.index(int(self.range_nm))
            self.range_nm = self._ranges[(idx + 1) % len(self._ranges)]
        except Exception:
            self.range_nm = self._ranges[0]
        self.update_display()

    def _action_mode_cycle(self):
        self.nav_mode = self.cap_widget.cycle_mode()
        self.update_display()

    def _action_tab_greece(self):
        self.display_tabs.setCurrentWidget(self.greece_widget)

    def _action_tab_volanta(self):
        self.display_tabs.setCurrentWidget(self.volanta_widget)

    def _ensure_adsb_backend_running(self):
        if not self._is_http_service_healthy('127.0.0.1', 8081):
            self._start_local_services()

    def _action_tab_adsb(self):
        self._ensure_adsb_backend_running()
        self.display_tabs.setCurrentWidget(self.tar1090_widget)
        self.tar1090_widget.ensure_loaded()

    def _on_display_tab_changed(self, index):
        if self.display_tabs.widget(index) is self.tar1090_widget:
            self._ensure_adsb_backend_running()
            self.tar1090_widget.ensure_loaded()

    def _is_http_service_healthy(self, host='127.0.0.1', port=8081) -> bool:
        try:
            with socket.create_connection((host, int(port)), timeout=0.6) as conn:
                conn.settimeout(0.8)
                conn.sendall(b'GET / HTTP/1.0\r\nHost: localhost\r\n\r\n')
                response_head = conn.recv(64)
                return response_head.startswith(b'HTTP/')
        except Exception:
            return False

    def _restart_stale_http_server(self, port=8081):
        port = int(port)
        # Old detached instances can keep the port but answer with empty replies.
        subprocess.run(
            ['pkill', '-f', f'http.server {port}'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        time.sleep(0.2)

    def _repair_tar1090_db_assets(self, http_dir):
        db_dir = os.path.join(http_dir, 'db2')
        if not os.path.isdir(db_dir):
            return

        repaired = 0
        try:
            entries = list(os.scandir(db_dir))
        except Exception:
            return

        for entry in entries:
            if not entry.is_file() or not entry.name.endswith('.js'):
                continue
            try:
                with open(entry.path, 'rb') as handle:
                    raw = handle.read()
                if len(raw) < 2 or raw[:2] != b'\x1f\x8b':
                    continue
                decoded = gzip.decompress(raw)
                with open(entry.path, 'wb') as handle:
                    handle.write(decoded)
                repaired += 1
            except Exception:
                continue

        if repaired:
            print(f'Reparation tar1090: {repaired} fichier(s) db2 decompresse(s).')


    def _start_local_services(self):

        autostart_setting = os.environ.get('NAVIGATION_DISPLAY_AUTOSTART_ADSB', '1').strip().lower()
        if autostart_setting in ('0', 'false', 'no'):
            print('Démarrage ADS-B automatique désactivé via NAVIGATION_DISPLAY_AUTOSTART_ADSB. '
                  'Supprimez la variable (ou mettez 1) pour lancer readsb et le serveur HTTP au démarrage.')
            return

        data_dir = os.path.expanduser('~/tar1090/html/data')
        http_dir = os.path.expanduser('~/tar1090/html')

        try:
            os.makedirs(http_dir, exist_ok=True)
            os.makedirs(data_dir, exist_ok=True)
        except Exception:
            pass

        self._repair_tar1090_db_assets(http_dir)

        readsb_running = subprocess.run(
            ['pgrep', '-x', 'readsb'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0
        port_open = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.settimeout(0.2)
                port_open = probe.connect_ex(('127.0.0.1', 8081)) == 0
        except Exception:
            port_open = False

        http_running = self._is_http_service_healthy('127.0.0.1', 8081)
        if port_open and not http_running:
            print('Port 8081 répond, mais le service HTTP semble invalide (réponse vide/incomplète).')
            print('Tentative de redémarrage d\'une ancienne instance python -m http.server 8081.')
            self._restart_stale_http_server(8081)
            http_running = self._is_http_service_healthy('127.0.0.1', 8081)

        commands = []
        if not readsb_running:
            commands.append(
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
                )
            )
        else:
            print('readsb déjà actif, démarrage ignoré.')

        if not http_running:
            commands.append(([sys.executable, '-m', 'http.server', '8081'], http_dir))
        else:
            print('Serveur HTTP port 8081 déjà actif, démarrage ignoré.')

        for command, working_directory in commands:
            try:
                process = subprocess.Popen(
                    command,
                    cwd=working_directory,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except FileNotFoundError:
                print(f'Commande introuvable au démarrage: {command[0]}')
                continue
            except Exception:
                print(f'Impossible de démarrer: {command}')
                continue
            self._local_service_processes.append(process)
            if command and command[0] == 'readsb':
                self._monitor_service_startup(
                    process,
                    'readsb',
                    'Le récepteur RTL-SDR est probablement déjà revendiqué par le pilote kernel '
                    'ou une autre instance readsb. Fermez l’autre instance, puis détachez ou '
                    'blacklistez dvb_usb_rtl28xxu si nécessaire.',
                )


    def _monitor_service_startup(self, process, label, failure_hint):
        def _watch():
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    break
                time.sleep(0.1)

            return_code = process.poll()
            if return_code not in (None, 0):
                print(f'{label} a quitté immédiatement avec le code {return_code}.')
                print(failure_hint)
                # Keep other local services (like HTTP) alive even if readsb fails to start.
                try:
                    self._local_service_processes = [p for p in self._local_service_processes if p is not process]
                except Exception:
                    pass

        watcher = threading.Thread(target=_watch, daemon=True)
        watcher.start()


    def _stop_local_services(self):

        while self._local_service_processes:
            process = self._local_service_processes.pop()
            try:
                process.terminate()
            except Exception:
                pass


    def closeEvent(self, a0):

        self._stop_local_services()
        if self._xplane_cmd_socket is not None:
            try:
                self._xplane_cmd_socket.close()
            except Exception:
                pass
            self._xplane_cmd_socket = None
        if self.data_source and hasattr(self.data_source, 'stop'):
            try:
                self.data_source.stop()
            except Exception:
                pass
        super().closeEvent(a0)



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

        if self.startup_mode in (MODE_XPLANE, MODE_MSP, MODE_MANUAL) and self.data_source is not None:
            try:
                data = self.data_source.poll(timeout=0.0)
                if data:
                    self._last_source_rx_time = time.monotonic()
                    if self.startup_mode == MODE_MANUAL:
                        heading_delta = float(data.get('heading_delta', 0.0))
                        self.heading = (self.heading + heading_delta) % 360
                        self.track = self.heading
                        self.load = int(max(0, min(100, float(data.get('load', self.load)))))
                        self.source_status = 'SRC JOYSTICK USB OK'
                        self.source_color = '#69f0ae'
                    else:
                        self.heading = float(data.get('heading', self.heading)) % 360
                        self.track = float(data.get('track', self.track)) % 360
                        self.ground_speed = float(data.get('ground_speed', self.ground_speed))
                        self.lat = float(data.get('lat', self.lat))
                        self.lon = float(data.get('lon', self.lon))
                        self.rpm = int(max(0, min(3000, float(data.get('rpm', self.rpm)))))
                        self.load = int(max(0, min(100, float(data.get('load', self.load)))))
                        self.fflow = max(0.0, min(20.0, float(data.get('fflow', self.fflow))))
                        self.oil_psi = max(0.0, min(100.0, float(data.get('oil_psi', self.oil_psi))) )
                        self.oil_temp = int(max(50, min(300, float(data.get('oil_temp', self.oil_temp)))))
                        self.egt = int(max(1000, min(1800, float(data.get('egt', self.egt)))))
                        self.fuel_qty_L = int(max(0, min(100, float(data.get('fuel_qty_L', self.fuel_qty_L)))))
                        self.fuel_qty_R = int(max(0, min(100, float(data.get('fuel_qty_R', self.fuel_qty_R)))))

                        if self.startup_mode == MODE_XPLANE:
                            self.source_status = 'SRC XPLANE UDP OK'
                            self.source_color = '#69f0ae'
                        elif self.startup_mode == MODE_MSP:
                            self.source_status = 'SRC MSP OK'
                            self.source_color = '#69f0ae'
            except RuntimeError as exc:
                if not self._source_error_reported:
                    print(exc)
                    self._source_error_reported = True
                if self.startup_mode == MODE_XPLANE:
                    self.source_status = 'SRC XPLANE ERROR'
                    self.source_color = '#ff6b6b'
                elif self.startup_mode == MODE_MSP:
                    self.source_status = 'SRC MSP ERROR'
                    self.source_color = '#ff6b6b'
                elif self.startup_mode == MODE_MANUAL:
                    self.source_status = 'SRC MANUAL (CLAVIER)'
                    self.source_color = '#a9b4c6'
                self.data_source = None
            except Exception:
                pass

        if self._last_source_rx_time is not None and self.startup_mode in (MODE_XPLANE, MODE_MSP, MODE_MANUAL):
            age = time.monotonic() - self._last_source_rx_time
            if age > 1.0:
                if self.startup_mode == MODE_XPLANE:
                    self.source_status = f'SRC XPLANE STALE {age:0.1f}s'
                elif self.startup_mode == MODE_MANUAL:
                    self.source_status = f'SRC JOYSTICK STALE {age:0.1f}s'
                else:
                    self.source_status = f'SRC MSP STALE {age:0.1f}s'
                self.source_color = '#ffd166'

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

            'source_status': self.source_status,

            'source_color': self.source_color,

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

        self._push_navigation_to_xplane()
        self.update_display()





def main():

    mode = choose_mode()
    show_side_panels = choose_screen_layout()
    data_source = build_navigation_source(mode)

    app = QApplication(sys.argv)

    window = EngineDisplay(startup_mode=mode, data_source=data_source, show_side_panels=show_side_panels)

    window.show()

    sys.exit(app.exec_())





if __name__ == '__main__':

    main()

