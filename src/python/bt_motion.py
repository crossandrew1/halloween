#!/usr/bin/env python3
"""Receive motion events from the Pro Micro nRF52840 PIR sensor over BLE.

The Pro Micro advertises as "PIR-Sensor" and sends "True\\n" over the
Nordic UART Service (NUS) every time the AM312 PIR sensor detects motion.

Install the dependency on the Raspberry Pi:
    pip install bleak

Run:
    python3 motion_receiver.py
"""

import asyncio

from bleak import BleakClient, BleakScanner

DEVICE_NAME = "PIR-Sensor"

# Nordic UART Service TX characteristic: the Pro Micro sends data to us on this.
NUS_TX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

SCAN_TIMEOUT_S = 10.0
RECONNECT_DELAY_S = 5


def on_motion():
    """Called every time "True" is received. Put your Halloween effect here."""
    print("Motion detected!", flush=True)


class MessageReader:
    """Collects notification bytes and splits them into newline-terminated messages."""

    def __init__(self):
        self.buffer = ""

    def __call__(self, _sender, data: bytearray):
        self.buffer += data.decode("utf-8", errors="ignore")
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line.strip() == "True":
                on_motion()


async def connect_and_listen(device):
    disconnected = asyncio.Event()
    async with BleakClient(
        device, disconnected_callback=lambda _client: disconnected.set()
    ) as client:
        print(f"Connected to {device.name} ({device.address})", flush=True)
        await client.start_notify(NUS_TX_CHAR_UUID, MessageReader())
        await disconnected.wait()


async def main():
    while True:
        print(f"Scanning for {DEVICE_NAME}...", flush=True)
        device = await BleakScanner.find_device_by_name(
            DEVICE_NAME, timeout=SCAN_TIMEOUT_S
        )
        if device is None:
            print("Not found, retrying...", flush=True)
            continue

        try:
            await connect_and_listen(device)
        except Exception as e:  # BleakError, timeouts, etc.
            print(f"Connection error: {e}", flush=True)

        print(f"Disconnected, reconnecting in {RECONNECT_DELAY_S}s...", flush=True)
        await asyncio.sleep(RECONNECT_DELAY_S)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")

