#!/usr/bin/env python3
import sys
import time
from evdev import InputDevice, list_devices, ecodes, UInput

# === CONFIGURATION ===
DEVICE_NAME_FRAGMENT = "SPEED-LINK"  # Replace with part of your joystick's name
CENTER = 128
DEADZONE = 20  # Adjust for joystick sensitivity

# === Helper: Find device by name ===
def find_device_by_name(name_fragment):
    for path in list_devices():
        dev = InputDevice(path)
        if name_fragment.lower() in dev.name.lower():
            print(f"Found device: '{dev.name}' at {path}")
            return dev

# === State tracking ===
state = {
    'UP': False,
    'DOWN': False,
    'LEFT': False,
    'RIGHT': False
}

# === Helper: Emit key events ===
def update_key(direction, pressed, ui):
    key_map = {
        'UP': ecodes.KEY_UP,
        'DOWN': ecodes.KEY_DOWN,
        'LEFT': ecodes.KEY_LEFT,
        'RIGHT': ecodes.KEY_RIGHT
    }
    if state[direction] != pressed:
        ui.write(ecodes.EV_KEY, key_map[direction], int(pressed))
        ui.syn()
        state[direction] = pressed

# === Main ===
def main():
    joystick = find_device_by_name(DEVICE_NAME_FRAGMENT)
    if not joystick:
        print(f"Device with name containing '{DEVICE_NAME_FRAGMENT}' not found.")
        sys.exit(0)

    ui = UInput()
    print("Listening for joystick input...")

    for event in joystick.read_loop():
        if event.type == ecodes.EV_ABS:
            if event.code == ecodes.ABS_Y:
                if event.value < CENTER - DEADZONE:
                    update_key('UP', True, ui)
                    update_key('DOWN', False, ui)
                elif event.value > CENTER + DEADZONE:
                    update_key('DOWN', True, ui)
                    update_key('UP', False, ui)
                else:
                    update_key('UP', False, ui)
                    update_key('DOWN', False, ui)

            elif event.code == ecodes.ABS_X:
                if event.value < CENTER - DEADZONE:
                    update_key('LEFT', True, ui)
                    update_key('RIGHT', False, ui)
                elif event.value > CENTER + DEADZONE:
                    update_key('RIGHT', True, ui)
                    update_key('LEFT', False, ui)
                else:
                    update_key('LEFT', False, ui)
                    update_key('RIGHT', False, ui)

if __name__ == "__main__":
    main()
