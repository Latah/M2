import tkinter as tk
from tkinter import font
import time

# --- GPIO Setup ---
# This block will be skipped if RPi.GPIO is not available (e.g., on a PC).
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Define GPIO pins for three motors
    motor_pins = {
        'motor1': {'STEP': 17, 'DIR': 27, 'EN': 23},
        'motor2': {'STEP': 22, 'DIR': 24, 'EN': 25}, # Example pins for motor 2
        'motor3': {'STEP': 5,  'DIR': 6,  'EN': 13}  # Example pins for motor 3
    }

    # Setup all GPIO pins
    for motor, pins in motor_pins.items():
        GPIO.setup(pins['STEP'], GPIO.OUT)
        GPIO.setup(pins['DIR'], GPIO.OUT)
        GPIO.setup(pins['EN'], GPIO.OUT)
        GPIO.output(pins['EN'], GPIO.HIGH) # Disable motor initially

    gpio_initialized = True
    print("RPi.GPIO initialized successfully for 3 motors.")

except (ImportError, RuntimeError):
    print("RPi.GPIO not available. Running in simulation mode.")
    gpio_initialized = False

# --- Motor Parameters ---
STEPS_PER_REV = 200     # Steps per revolution of your motor (e.g., 200 for 1.8 deg/step)
MOVEMENT_DEGREE = 90    # Degrees of movement per click
usDelay = 950           # Microseconds delay between pulses (controls speed)
uS = 0.000001           # One microsecond

# --- Universal Motor Control Function ---
def move_motor_degrees(motor_id, degrees, direction_clockwise):
    """
    Controls a specific motor.
    motor_id: The key for the motor in the motor_pins dictionary (e.g., 'motor1').
    degrees: The number of degrees to rotate.
    direction_clockwise: True for clockwise, False for counter-clockwise.
    """
    if not gpio_initialized:
        direction_str = 'clockwise' if direction_clockwise else 'counter-clockwise'
        print(f"SIMULATION: Moving {motor_id} {degrees}° {direction_str}.")
        return

    # Get the pins for the specified motor
    pins = motor_pins[motor_id]
    STEP_PIN, DIR_PIN, EN_PIN = pins['STEP'], pins['DIR'], pins['EN']

    # Enable the motor driver
    GPIO.output(EN_PIN, GPIO.LOW)
    time.sleep(0.01) # Short delay for the driver to stabilize

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

    # Disable the motor driver to save power and reduce heat
    GPIO.output(EN_PIN, GPIO.HIGH)
    direction_str = 'clockwise' if direction_clockwise else 'counter-clockwise'
    print(f"ACTION: Moved {motor_id} {degrees}° {direction_str}.")

# --- Tkinter GUI Setup ---

# Main window setup
root = tk.Tk()
root.title("Multi-Motor Control")
root.geometry("800x600")
root.configure(bg="#f0f0f0")

# Define fonts
title_font = font.Font(family="Helvetica", size=36, weight="bold")
button_font = font.Font(family="Helvetica", size=24, weight="bold")
motor_label_font = font.Font(family="Helvetica", size=20)

# Main title
title_label = tk.Label(root, text="⚙️ 3-Motor Control Panel", font=title_font, bg="#f0f0f0")
title_label.pack(pady=20)

# Function to create a control frame for a single motor
def create_motor_frame(parent, motor_id, motor_name):
    """Creates a frame with a label and two buttons for a motor."""
    frame = tk.Frame(parent, bg="#dcdcdc", bd=2, relief=tk.RIDGE)
    frame.pack(pady=10, padx=20, fill="x")

    label = tk.Label(frame, text=motor_name, font=motor_label_font, bg="#dcdcdc")
    label.pack(pady=(10, 5))

    button_frame = tk.Frame(frame, bg="#dcdcdc")
    button_frame.pack(pady=(5, 10))

    # Left button (counter-clockwise)
    btn_left = tk.Button(button_frame, text="◀ Left", font=button_font, fg="#c0392b", width=7, height=1,
                         command=lambda: move_motor_degrees(motor_id, MOVEMENT_DEGREE, False))
    btn_left.pack(side=tk.LEFT, padx=20)

    # Right button (clockwise)
    btn_right = tk.Button(button_frame, text="Right ▶", font=button_font, fg="#27ae60", width=7, height=1,
                          command=lambda: move_motor_degrees(motor_id, MOVEMENT_DEGREE, True))
    btn_right.pack(side=tk.LEFT, padx=20)

# Create control frames for all three motors
create_motor_frame(root, 'motor1', "Motor 1")
create_motor_frame(root, 'motor2', "Motor 2")
create_motor_frame(root, 'motor3', "Motor 3")

# --- Cleanup on Close ---
def on_closing():
    """Clean up GPIO pins when the window is closed."""
    if gpio_initialized:
        for motor, pins in motor_pins.items():
            GPIO.output(pins['EN'], GPIO.HIGH) # Ensure motor is disabled
        GPIO.cleanup()
        print("GPIO cleaned up successfully.")
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

# Start the GUI event loop
root.mainloop()