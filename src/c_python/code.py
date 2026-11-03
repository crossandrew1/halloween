# CircuitPython firmware for a Pro Micro nRF52840 (nice!nano compatible).
#
# Reads an AM312 / HC-SR312 mini PIR motion sensor and, whenever new motion
# is detected, sends the string "True" to the connected central (the
# Raspberry Pi) over the Nordic UART Service (NUS) via Bluetooth Low Energy.
#
# Wiring (AM312 -> Pro Micro nRF52840):
#   VCC -> 3.3V (VCC pin)   AM312 works from 2.7 V to 12 V
#   GND -> GND
#   OUT -> P0.17            (change PIR_PIN below to use another pin)
#
# Required library (copy into CIRCUITPY/lib from the Adafruit bundle):
#   adafruit_ble

import time

import board
import digitalio
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

DEVICE_NAME = "PIR-Sensor"       # Name the Pi scans for
PIR_PIN = board.P0_17            # AM312 OUT pin
COOLDOWN_S = 1.0                 # Minimum seconds between "True" messages
POLL_INTERVAL_S = 0.05

# --- Hardware setup -------------------------------------------------------
pir = digitalio.DigitalInOut(PIR_PIN)
pir.direction = digitalio.Direction.INPUT
pir.pull = digitalio.Pull.DOWN   # AM312 drives HIGH on motion, LOW otherwise

led = None
try:
    led = digitalio.DigitalInOut(board.LED)  # Blue LED on P0.15
    led.direction = digitalio.Direction.OUTPUT
except (AttributeError, ValueError):
    pass


def set_led(on):
    if led is not None:
        led.value = on


# --- BLE setup ------------------------------------------------------------
ble = BLERadio()
ble.name = DEVICE_NAME
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)
advertisement.complete_name = DEVICE_NAME

# The AM312 needs a few seconds after power-up to settle.
print("Warming up PIR sensor...")
time.sleep(3)

while True:
    print("Advertising as", DEVICE_NAME)
    ble.start_advertising(advertisement)
    while not ble.connected:
        time.sleep(0.1)
    ble.stop_advertising()
    print("Connected")

    last_state = pir.value
    last_sent = 0.0

    while ble.connected:
        state = pir.value
        set_led(state)

        # Send only on a LOW -> HIGH transition (new motion event).
        if state and not last_state:
            now = time.monotonic()
            if now - last_sent >= COOLDOWN_S:
                try:
                    uart.write(b"True\n")
                    print("Motion detected -> sent True")
                    last_sent = now
                except Exception as e:  # connection dropped mid-write
                    print("Send failed:", e)

        last_state = state
        time.sleep(POLL_INTERVAL_S)

    set_led(False)
    print("Disconnected")

