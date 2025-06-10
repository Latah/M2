import tkinter as tk
from tkinter import font
import time

# --- GPIO Setup ---
# This block will be skipped if RPi.GPIO is not available (e.g., on a PC).
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    gpio_initialized = True
except (ImportError, RuntimeError):
    print("RPi.GPIO not available. Running in simulation mode.")
    gpio_initialized = False

# --- Motor Configuration ---
# All motor-specific data is now in this dictionary.
# You can customize the pins and operating parameters for each motor individually.
motors_config = {
    'motor1': {
        'name': "Motor 1 (Fast)",
        'pins': {'STEP': 17, 'DIR': 27, 'EN': 23},
        'params': {'STEPS_PER_REV': 200, 'MOVEMENT_DEGREE': 90, 'usDelay': 800}
    },
    'motor2': {
        'name': "Motor 2 (Precise)",
        'pins': {'STEP': 22, 'DIR': 24, 'EN': 25},
        'params': {'STEPS_PER_REV': 400, 'MOVEMENT_DEGREE': 45, 'usDelay': 1000} # Double steps for more precision
    },
    'motor3': {
        'name': "Motor 3 (Slow & Wide)",
        'pins': {'STEP': 5,  'DIR': 6,  'EN': 13},
        'params': {'STEPS_PER_REV': 200, 'MOVEMENT_DEGREE': 180, 'usDelay': 1500} # Slower speed, wider angle
    }
}

# --- GPIO Initialization ---
if gpio_initialized:
    for motor_id, config in motors_config.items():
        pins = config['pins']
        GPIO.setup(pins['STEP'], GPIO.OUT)
        GPIO.setup(pins['DIR'], GPIO.OUT)
        GPIO.setup(pins['EN'], GPIO.OUT)
        GPIO.output(pins['EN'], GPIO.HIGH) # Disable motor initially
    print("RPi.GPIO initialized successfully for all motors.")

# Universal constant
uS = 0.000001 # One microsecond

# --- Universal Motor Control Function ---
def move_motor_degrees(motor_id, degrees, direction_clockwise):
    """
    Controls a specific motor using its individual parameters.
    motor_id: The key for the motor in the motors_config dictionary (e.g., 'motor1').
    degrees: The number of degrees to rotate.
    direction_clockwise: True for clockwise, False for counter-clockwise.
    """
    config = motors_config[motor_id]
    direction_str = 'clockwise' if direction_clockwise else 'counter-clockwise'

    if not gpio_initialized:
        print(f"SIMULATION: Moving {config['name']} {degrees}° {direction_str}.")
        return

    # Get the pins and parameters for the specified motor
    pins = config['pins']
    params = config['params']
    STEP_PIN, DIR_PIN, EN_PIN = pins['STEP'], pins['DIR'], pins['EN']
    STEPS_PER_REV = params['STEPS_PER_REV']
    usDelay = params['usDelay']

    # Enable the motor driver
    GPIO.output(EN_PIN, GPIO.LOW)
    time.sleep(0.01)

    # Set the direction
    GPIO.output(DIR_PIN, GPIO.HIGH if direction_clockwise else GPIO.LOW)

    # Calculate the number of steps
    num_steps = int((degrees / 360.0) * STEPS_PER_REV)

    # Execute the steps
    for _ in range(num_steps):
        GPIO.output(STEP_PIN, GPIO.HIGH)
        time.sleep(uS * usDelay)
        GPIO.output(STEP_PIN, GPIO.LOW)
        time.sleep(uS * usDelay)

    # Disable the motor driver
    GPIO.output(EN_PIN, GPIO.HIGH)
    print(f"ACTION: Moved {config['name']} {degrees}° {direction_str}.")

# --- Tkinter GUI Setup ---

root = tk.Tk()
root.title("Individual Multi-Motor Control")
root.geometry("800x650")
root.configure(bg="#f0f0f0")

title_font = font.Font(family="Helvetica", size=36, weight="bold")
button_font = font.Font(family="Helvetica", size=24, weight="bold")
motor_label_font = font.Font(family="Helvetica", size=20)

title_label = tk.Label(root, text="⚙️ Motor Control Panel", font=title_font, bg="#f0f0f0")
title_label.pack(pady=20)

# Function to create a control frame for a single motor
def create_motor_frame(parent, motor_id):
    """Creates a UI frame for a motor using its config."""
    config = motors_config[motor_id]
    motor_name = config['name']
    movement_degree = config['params']['MOVEMENT_DEGREE']

    frame = tk.Frame(parent, bg="#dcdcdc", bd=2, relief=tk.RIDGE)
    frame.pack(pady=12, padx=20, fill="x")

    label = tk.Label(frame, text=motor_name, font=motor_label_font, bg="#dcdcdc")
    label.pack(pady=(10, 5))

    button_frame = tk.Frame(frame, bg="#dcdcdc")
    button_frame.pack(pady=(5, 10))

    # Left button (CCW) - uses lambda to pass the correct motor_id and degree
    btn_left = tk.Button(button_frame, text="◀ Left", font=button_font, fg="#c0392b", width=7, height=1,
                         command=lambda: move_motor_degrees(motor_id, movement_degree, False))
    btn_left.pack(side=tk.LEFT, padx=20)

    # Right button (CW) - uses lambda to pass the correct motor_id and degree
    btn_right = tk.Button(button_frame, text="Right ▶", font=button_font, fg="#27ae60", width=7, height=1,
                          command=lambda: move_motor_degrees(motor_id, movement_degree, True))
    btn_right.pack(side=tk.LEFT, padx=20)

# Create control frames for all configured motors
for motor_id in motors_config:
    create_motor_frame(root, motor_id)

# --- Cleanup on Close ---
def on_closing():
    """Clean up GPIO pins when the window is closed."""
    if gpio_initialized:
        for motor_id, config in motors_config.items():
            GPIO.output(config['pins']['EN'], GPIO.HIGH) # Ensure motor is disabled
        GPIO.cleanup()
        print("GPIO cleaned up successfully.")
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()