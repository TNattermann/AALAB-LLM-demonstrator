#!/usr/bin/env python3
import sys
import time
from evdev import InputDevice, list_devices, ecodes, UInput

# === CONFIGURATION ===
DEVICE_NAME_FRAGMENT = "SPEED-LINK"  # Replace with part of your joystick's name
CENTER = 128
DEADZONE = 20  # Adjust for joystick sensitivity

# === Button to Key Sequence Mapping ===
button_map = {
    ecodes.BTN_NORTH: [ecodes.KEY_A, ecodes.KEY_B, ecodes.KEY_C],
    ecodes.BTN_EAST:  [ecodes.KEY_LEFTCTRL, ecodes.KEY_S],  # Example: Save shortcut
    # Add more buttons here
}

# === Track previous state of each button ===
button_state = {btn: False for btn in button_map.keys()}

# === Track axis state ===
axis_state = {
    'UP': False,
    'DOWN': False,
    'LEFT': False,
    'RIGHT': False
}

# === Helper: Find device by name ===
def find_device_by_name(name_fragment):
    for path in list_devices():
        dev = InputDevice(path)
        if name_fragment.lower() in dev.name.lower():
            print(f"Found device: '{dev.name}' at {path}")
            return dev
    return None

# === Helper: Emit key events for axis directions ===
def update_axis_key(direction, pressed, ui):
    key_map = {
        'UP': ecodes.KEY_UP,
        'DOWN': ecodes.KEY_DOWN,
        'LEFT': ecodes.KEY_LEFT,
        'RIGHT': ecodes.KEY_RIGHT
    }
    if axis_state[direction] != pressed:
        ui.write(ecodes.EV_KEY, key_map[direction], int(pressed))
        ui.syn()
        axis_state[direction] = pressed

# === Helper: Emit key sequence for button press ===
def trigger_button_sequence(button_code, ui):
    key_seq = button_map[button_code]
    for key in key_seq:
        ui.write(ecodes.EV_KEY, key, 1)  # key down
        ui.syn()
        time.sleep(0.05)
        ui.write(ecodes.EV_KEY, key, 0)  # key up
        ui.syn()
        time.sleep(0.05)

# === Main loop ===
def main():
    joystick = find_device_by_name(DEVICE_NAME_FRAGMENT)
    if not joystick:
        print(f"Device with name containing '{DEVICE_NAME_FRAGMENT}' not found.")
        sys.exit(1)

    ui = UInput()
    print("Listening for joystick input...")

    for event in joystick.read_loop():
        if event.type == ecodes.EV_ABS:
            if event.code == ecodes.ABS_Y:
                if event.value < CENTER - DEADZONE:
                    update_axis_key('UP', True, ui)
                    update_axis_key('DOWN', False, ui)
                elif event.value > CENTER + DEADZONE:
                    update_axis_key('DOWN', True, ui)
                    update_axis_key('UP', False, ui)
                else:
                    update_axis_key('UP', False, ui)
                    update_axis_key('DOWN', False, ui)

            elif event.code == ecodes.ABS_X:
                if event.value < CENTER - DEADZONE:
                    update_axis_key('LEFT', True, ui)
                    update_axis_key('RIGHT', False, ui)
                elif event.value > CENTER + DEADZONE:
                    update_axis_key('RIGHT', True, ui)
                    update_axis_key('LEFT', False, ui)
                else:
                    update_axis_key('LEFT', False, ui)
                    update_axis_key('RIGHT', False, ui)

        elif event.type == ecodes.EV_KEY and event.code in button_map:
            if event.value == 1 and not button_state[event.code]:
                # Button just pressed
                print(f"Button {event.code} pressed → triggering sequence")
                trigger_button_sequence(event.code, ui)
                button_state[event.code] = True
            elif event.value == 0:
                # Button released
                button_state[event.code] = False

if __name__ == "__main__":
    main()
