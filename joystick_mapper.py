#!/usr/bin/env python3
import sys
import os
import subprocess
import time
from evdev import InputDevice, list_devices, ecodes, UInput

# === CONFIGURATION ===
DEVICE_NAME_FRAGMENT = ["SPEEDLINK", "SPEED-LINK"] # Replace with part of your joystick's name
CENTER = 128
DEADZONE = 20  # Adjust for joystick sensitivity

# === Button to Key Sequence Mapping for New Joysticks (SPEEDLINK) ===
button_map = {
    ecodes.BTN_NORTH: [ecodes.KEY_W, ecodes.KEY_D], # Deutsch - Links Oben
    #ecodes.BTN_EAST:  "RESTART_MODE", # wechselt LLMTimes & fAIrytale
    ecodes.BTN_WEST: [ecodes.KEY_X], # Save - Links Unten
    ecodes.BTN_SOUTH: [ecodes.KEY_W, ecodes.KEY_W, ecodes.KEY_D] # Rechts Oben - english
}

# === Recognize device and dynamically change button mapping ===
for path in list_devices():
    dev = InputDevice(path)
    if 'SPEED-LINK' in dev.name:
        print('Using setup for old Joystick')
        button_map = {
            ecodes.BTN_TRIGGER: [ecodes.KEY_W, ecodes.KEY_D],  # Deutsch - Links Oben
            #ecodes.BTN_EAST:  "RESTART_MODE", # wechselt LLMTimes & fAIrytale
            ecodes.BTN_THUMB2: [ecodes.KEY_X],  # Save - Links Unten
            ecodes.BTN_THUMB: [ecodes.KEY_W, ecodes.KEY_W, ecodes.KEY_D]  # Rechts Oben - english
        }

last_execution_time = {}

# === Track previous state of each button ===
button_state = {btn: False for btn in button_map.keys()}

# === Track axis state ===
axis_state = {
    'UP': False,
    'DOWN': False,
    'LEFT': False,
    'RIGHT': False
}

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

# === Helper: Find device by name ===
def find_device_by_name(fragment_list):
    for path in list_devices():
        dev = InputDevice(path)
        for fragment in fragment_list:
            if fragment.lower() in dev.name.lower():
                print(f"Found device: '{dev.name}' at {path}")
                return dev

# === Helper: Emit key sequence for button press ===
def trigger_button_sequence(button_code, ui):
    global last_execution_time
    action = button_map.get(button_code)
    # ===============================
    # SPECIAL ACTION: RESTART MODE
    # ===============================
    if action == "RESTART_MODE":
        print("Restarting with opposite mode...")
        restart_with_other_mode()
        return

    cooldown_period = 10 if action and isinstance(action, list) and action[0] == ecodes.KEY_X else 2 # dynamic cooldown setting
 # Check if enough time has passed since last execution
    current_time = time.time()
    if button_code in last_execution_time and (current_time - last_execution_time[button_code]) < cooldown_period:
        print(f"{button_code} is on cooldown. Ignoring repeated press.")
        return  # Prevent execution if still on cooldown
    last_execution_time[button_code] = current_time  # Update last execution time
    key_seq = button_map[button_code]
    for key in key_seq:
        ui.write(ecodes.EV_KEY, key, 1)  # Key down
        ui.syn()
        time.sleep(0.05)
        ui.write(ecodes.EV_KEY, key, 0)  # Key up
        ui.syn()
        time.sleep(0.05)

# === Helper: Restart with other mode ===
def restart_with_other_mode():
    args = sys.argv.copy()
    if "--mode" in args:
        idx = args.index("--mode") + 1
        if idx < len(args):
            current = args[idx]
            args[idx] = "fAIrytale" if current == "LLMTimes" else "LLMTimes"
    else:
        args += ["--mode", "LLMTimes"]
    subprocess.Popen([sys.executable] + args)
    os._exit(0)

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
                trigger_button_sequence(event.code, ui)
                button_state[event.code] = True
            elif event.value == 0:
                # Button released
                button_state[event.code] = False

if __name__ == "__main__":
    main()
