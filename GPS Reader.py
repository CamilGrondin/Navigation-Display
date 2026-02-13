import argparse
import struct
import sys
import time
from typing import Optional

import serial
from serial.tools import list_ports

MSP_GPS = 106
HEADER_REQUEST = b"$M<"
HEADER_RESPONSE = b"$M>"


def detect_serial_port(keyword: Optional[str]) -> Optional[str]:
    needle = keyword.lower() if keyword else None
    candidate = None
    for entry in list_ports.comports():
        description = (entry.description or "").lower()
        hwid = (entry.hwid or "").lower()
        if needle and (needle in description or needle in hwid):
            return entry.device
        if candidate is None:
            candidate = entry.device
    return candidate


def build_msp_request(cmd: int, payload: bytes = b"") -> bytes:
    size = len(payload)
    checksum = size ^ cmd
    for byte in payload:
        checksum ^= byte
    return HEADER_REQUEST + bytes((size, cmd, checksum)) + payload


def _read_exact(ser: serial.Serial, count: int, timeout: float) -> Optional[bytes]:
    buffer = bytearray()
    deadline = time.monotonic() + timeout
    while len(buffer) < count and time.monotonic() < deadline:
        chunk = ser.read(count - len(buffer))
        if not chunk:
            continue
        buffer.extend(chunk)
    return bytes(buffer) if len(buffer) == count else None


def read_msp_response(ser: serial.Serial, timeout: float = 1.0) -> Optional[tuple[int, bytes]]:
    start = time.monotonic()
    buffer = bytearray()
    while time.monotonic() - start < timeout:
        byte = ser.read(1)
        if not byte:
            continue
        buffer.extend(byte)
        if buffer.endswith(HEADER_RESPONSE):
            break
    if not buffer.endswith(HEADER_RESPONSE):
        return None
    length_bytes = _read_exact(ser, 1, timeout)
    if length_bytes is None:
        return None
    size = length_bytes[0]
    cmd_bytes = _read_exact(ser, 1, timeout)
    if cmd_bytes is None:
        return None
    cmd = cmd_bytes[0]
    payload = _read_exact(ser, size, timeout) or b""
    checksum_bytes = _read_exact(ser, 1, timeout)
    if checksum_bytes is None:
        return None
    checksum = checksum_bytes[0]
    chk = size ^ cmd
    for pb in payload:
        chk ^= pb
    if chk != checksum:
        return None
    return cmd, payload


def parse_gps_payload(payload: bytes) -> Optional[dict[str, float | int | str]]:
    if len(payload) < 18:
        return None
    try:
        fix, sats, lat_raw, lon_raw, alt_raw, speed_raw, course_raw = struct.unpack("<BBiiiHH", payload[:18])
    except struct.error:
        return None
    return {
        "fix": fix,
        "satellites": sats,
        "latitude": lat_raw / 1e7,
        "longitude": lon_raw / 1e7,
        "altitude_m": alt_raw / 100.0,
        "speed_m_per_s": speed_raw / 100.0,
        "course_deg": course_raw / 10.0,
    }


def format_fix_status(fix: int) -> str:
    if fix == 0:
        return "no fix"
    if fix == 1:
        return "2D"
    if fix == 2:
        return "3D"
    return f"unknown({fix})"


def main() -> None:
    parser = argparse.ArgumentParser(description="Poll Betaflight MSP_GPS telemetry")
    parser.add_argument("--port", help="Serial port communicated with Betaflight")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate")
    parser.add_argument("--interval", type=float, default=0.9, help="Delay between polls (seconds)")
    parser.add_argument("--timeout", type=float, default=1.0, help="Response timeout (seconds)")
    parser.add_argument("--auto", action="store_true", help="Auto-detect the Betaflight port")
    parser.add_argument("--device-id", default="NL 1S", help="Substring to match when auto-detecting")
    parser.add_argument("--once", action="store_true", help="Exit after the first GPS response")
    parser.add_argument("--show-raw", action="store_true", help="Print raw payload when parsing fails")
    args = parser.parse_args()

    port = args.port
    if not port and args.auto:
        port = detect_serial_port(args.device_id)
    if not port:
        print("No port specified and auto-detection failed. Use --port to set the COM port.")
        sys.exit(1)

    print(f"Listening for MSP_GPS on {port} @{args.baud} baud")
    try:
        with serial.Serial(port, args.baud, timeout=0.05) as ser:
            while True:
                ser.write(build_msp_request(MSP_GPS))
                response = read_msp_response(ser, timeout=args.timeout)
                if response and response[0] == MSP_GPS:
                    payload = response[1]
                    data = parse_gps_payload(payload)
                    if data is not None:
                        fix_text = format_fix_status(data["fix"])
                        speed_kmh = data["speed_m_per_s"] * 3.6
                        timestamp = time.strftime("%H:%M:%S")
                        print(
                            f"[{timestamp}] Fix={fix_text} sats={data['satellites']} "
                            f"lat={data['latitude']:.7f} lon={data['longitude']:.7f} "
                            f"alt={data['altitude_m']:.2f}m speed={speed_kmh:.1f}km/h "
                            f"course={data['course_deg']:.1f}°"
                        )
                        if args.once:
                            break
                else:
                    if args.show-raw and response:
                        print(f"[{time.strftime('%H:%M:%S')}] raw payload: {response[1].hex()}")
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Interrupted by user")
    except serial.SerialException as exc:
        print(f"Serial error: {exc}")


if __name__ == "__main__":
    main()
