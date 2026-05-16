#!/usr/bin/env python3
"""Read and set RTC clock on Riden RD60xx power supply via MODBUS."""

import sys
import struct
import argparse
from datetime import datetime
import serial


def modbus_crc(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def read_registers(port, addr, start_reg, count):
    """Read multiple MODBUS holding registers (function 0x03)."""
    msg = struct.pack('>BBHH', addr, 0x03, start_reg, count)
    crc = modbus_crc(msg)
    msg += struct.pack('<H', crc)
    port.write(msg)
    resp_len = 5 + count * 2
    resp = port.read(resp_len)
    if len(resp) < 5:
        print(f'Short response: {resp}')
        return []
    byte_count = resp[2]
    values = []
    for i in range(count):
        val = struct.unpack('>H', resp[3 + i*2 : 5 + i*2])[0]
        values.append(val)
    return values


def write_register(port, addr, reg, value):
    """Write a single MODBUS holding register (function 0x06)."""
    msg = struct.pack('>BBHH', addr, 0x06, reg, value)
    crc = modbus_crc(msg)
    msg += struct.pack('<H', crc)
    port.write(msg)
    return port.read(8)


def main():
    parser = argparse.ArgumentParser(description='Read/Set RTC on Riden RD60xx')
    parser.add_argument('port', help='Serial port')
    parser.add_argument('--read', action='store_true', help='Read current RTC values')
    parser.add_argument('--set', action='store_true', help='Set RTC to current time')
    parser.add_argument('-s', '--speed', type=int, default=115200)
    args = parser.parse_args()

    try:
        ser = serial.Serial(port=args.port, baudrate=args.speed, timeout=2)
    except serial.SerialException as err:
        sys.exit(err)

    if args.read or not args.set:
        # Read registers 48-53 (RTC)
        vals = read_registers(ser, 0x01, 48, 6)
        if vals:
            labels = ['Year', 'Month', 'Day', 'Hour', 'Minute', 'Second']
            print('Current RTC register values (registers 48-53):')
            for i, (label, val) in enumerate(zip(labels, vals)):
                print(f'  Reg {48+i} ({label}): {val}')

    if args.set:
        now = datetime.now()
        print(f'\nSetting RTC to: {now.strftime("%Y-%m-%d %H:%M:%S")}')

        # Try full year value (2026) instead of offset (26)
        clock_values = [
            (48, now.year),
            (49, now.month),
            (50, now.day),
            (51, now.hour),
            (52, now.minute),
            (53, now.second),
        ]

        for reg, val in clock_values:
            print(f'  Writing reg {reg} = {val}')
            write_register(ser, 0x01, reg, val)

        # Read back to verify
        print('\nVerifying...')
        vals = read_registers(ser, 0x01, 48, 6)
        if vals:
            labels = ['Year', 'Month', 'Day', 'Hour', 'Minute', 'Second']
            for label, val in zip(labels, vals):
                print(f'  {label}: {val}')

    ser.close()


if __name__ == '__main__':
    main()
