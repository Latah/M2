import tkinter as tk
from tkinter import font
import time
import threading

# GPIO Setup
# Dieser Block wird übersprungen, wenn RPi.GPIO nicht verfügbar ist.
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    gpio_initialized = True
except (ImportError, RuntimeError):
    print("RPi.GPIO nicht verfügbar. Simulationsmodus ist an.")
    gpio_initialized = False

# Motor-Konfiguration
# In diesem Abschnitt werden die Pins und Parameter für jeden Motor definiert.
motors_config = {
    'dispenser1': {
        'name': "Dispenser 1 Motor",
        'pins': {'STEP': 17, 'DIR': 27, 'EN': 23},
        'params': {'STEPS_PER_REV': 200, 'usDelay': 800}
    },
    'dispenser2': {
        'name': "Dispenser 2 Motor",
        'pins': {'STEP': 22, 'DIR': 24, 'EN': 25},
        'params': {'STEPS_PER_REV': 400, 'usDelay': 1000}
    },
    'rail_wagon': {
        'name': "Rail Wagon Motor",
        'pins': {'STEP': 5,  'DIR': 6,  'EN': 13},
        'params': {'STEPS_PER_REV': 200, 'usDelay': 1500}
    }
}

# Globale Variablen für die Steuerung des dritten Motors
rail_motor_moving = False
rail_motor_direction = True # True für Vorwärts, False für Zurück
rail_motor_thread = None

# GPIO Initialisierung
if gpio_initialized:
    for motor_id, config in motors_config.items():
        pins = config['pins']
        GPIO.setup(pins['STEP'], GPIO.OUT)
        GPIO.setup(pins['DIR'], GPIO.OUT)
        GPIO.setup(pins['EN'], GPIO.OUT)
        GPIO.output(pins['EN'], GPIO.HIGH) # Motor zunächst deaktivieren

# Universelle Konstante
uS = 0.000001 # Eine Mikrosekunde

# Kernfunktionen der Motorsteuerung
def move_motor_step(motor_id, direction_clockwise):
    """ Bewegt einen Motor um einen einzigen Schritt. """
    if not gpio_initialized:
        # Im Simulationsmodus wird nichts ausgeführt
        return

    config = motors_config[motor_id]
    pins = config['pins']
    params = config['params']
    
    STEP_PIN, DIR_PIN, EN_PIN = pins['STEP'], pins['DIR'], pins['EN']
    usDelay = params['usDelay']

    GPIO.output(DIR_PIN, GPIO.HIGH if direction_clockwise else GPIO.LOW)
    GPIO.output(STEP_PIN, GPIO.HIGH)
    time.sleep(uS * usDelay)
    GPIO.output(STEP_PIN, GPIO.LOW)
    time.sleep(uS * usDelay)

def move_motor_degrees(motor_id, degrees, direction_clockwise):
    """ Bewegt einen Motor um eine bestimmte Gradzahl. """
    config = motors_config[motor_id]
    direction_str = 'Vorwärts' if direction_clockwise else 'Rückwärts'
    print(f"INFO: Bewege {config['name']} um {degrees}° {direction_str}.")
    
    if not gpio_initialized:
        print(f"SIMULATION: Überspringe tatsächliche Bewegung für {config['name']}.")
        time.sleep(1) # Simuliert die für die Bewegung benötigte Zeit
        return

    pins = config['pins']
    params = config['params']
    EN_PIN = pins['EN']
    STEPS_PER_REV = params['STEPS_PER_REV']
    
    GPIO.output(EN_PIN, GPIO.LOW) # Motor aktivieren
    time.sleep(0.01)
    
    num_steps = int((degrees / 360.0) * STEPS_PER_REV)
    for _ in range(num_steps):
        move_motor_step(motor_id, direction_clockwise)

    GPIO.output(EN_PIN, GPIO.HIGH) # Motor deaktivieren
    print(f"INFO: Bewegung von {config['name']} abgeschlossen.")

# --- Neue Steuerungsfunktionen ---

def activate_dispenser(dispenser_id, status_label):
    """Aktiviert einen Dispenser-Motor für eine volle Umdrehung."""
    def motor_thread():
        status_label.config(text=f"Status: Aktiviere {motors_config[dispenser_id]['name']}...")
        move_motor_degrees(dispenser_id, 360, True) # 360 Grad im Uhrzeigersinn
        status_label.config(text="Status: Bereit")
    
    # Führe die Bewegung in einem separaten Thread aus, um die GUI nicht zu blockieren
    threading.Thread(target=motor_thread).start()

def rail_motor_worker(status_label):
    """Worker-Thread, der den Schienenmotor bewegt, solange die Taste gedrückt wird."""
    global rail_motor_moving, rail_motor_direction
    
    if gpio_initialized:
        GPIO.output(motors_config['rail_wagon']['pins']['EN'], GPIO.LOW) # Motor aktivieren
        time.sleep(0.01)
        
    while rail_motor_moving:
        move_motor_step('rail_wagon', rail_motor_direction)
    
    if gpio_initialized:
        GPIO.output(motors_config['rail_wagon']['pins']['EN'], GPIO.HIGH) # Motor deaktivieren
    
    # Setze den globalen Thread auf None, damit ein neuer gestartet werden kann
    global rail_motor_thread
    rail_motor_thread = None
    status_label.config(text="Status: Bereit")
    print("INFO: Rail-Motor gestoppt.")


def start_rail_motor(direction_is_forward, status_label):
    """Startet die Bewegung des Schienenmotors, wenn eine Taste gedrückt wird."""
    global rail_motor_moving, rail_motor_direction, rail_motor_thread
    
    # Verhindert das Starten mehrerer Threads
    if rail_motor_thread is not None and rail_motor_thread.is_alive():
        return
        
    rail_motor_moving = True
    rail_motor_direction = direction_is_forward
    direction_str = "vorwärts" if direction_is_forward else "zurück"
    status_label.config(text=f"Status: Bewege Schiene {direction_str}...")
    print(f"INFO: Starte Rail-Motor {direction_str}.")
    
    rail_motor_thread = threading.Thread(target=rail_motor_worker, args=(status_label,))
    rail_motor_thread.start()

def stop_rail_motor():
    """Stoppt die Bewegung des Schienenmotors, wenn die Taste losgelassen wird."""
    global rail_motor_moving
    rail_motor_moving = False


# --- GUI ---
def launch_main_app():
    """Startet das Tkinter Hauptfenster für die manuelle Steuerung."""
    root = tk.Tk()
    root.title("Snackster - Manuelle Steuerung")
    root.geometry("800x600")
    root.configure(bg="#2c3e50")

    title_font = font.Font(family="Helvetica", size=32, weight="bold")
    button_font = font.Font(family="Helvetica", size=18, weight="bold")
    status_font = font.Font(family="Helvetica", size=16)

    title_label = tk.Label(root, text="🛤️ Snackster Steuerung", font=title_font, bg="#2c3e50", fg="white")
    title_label.pack(pady=30)
    
    status_label = tk.Label(root, text="Status: Bereit", font=status_font, bg="#2c3e50", fg="#ecf0f1", height=2)
    status_label.pack(pady=20)

    # Frame für die Dispenser-Motoren
    dispenser_frame = tk.Frame(root, bg="#2c3e50")
    dispenser_frame.pack(pady=10)

    # Frame für den Schienen-Motor
    rail_frame = tk.Frame(root, bg="#2c3e50")
    rail_frame.pack(pady=20)

    # --- Tasten erstellen ---

    # Taste für Dispenser 1
    btn_dispenser1 = tk.Button(
        dispenser_frame,
        text="Motor 1 Aktivieren",
        font=button_font, bg="#2ecc71", fg="white",
        activebackground="#27ae60", activeforeground="white",
        width=20, height=3,
        command=lambda: activate_dispenser('dispenser1', status_label)
    )
    btn_dispenser1.pack(side=tk.LEFT, padx=20)

    # Taste für Dispenser 2
    btn_dispenser2 = tk.Button(
        dispenser_frame,
        text="Motor 2 Aktivieren",
        font=button_font, bg="#3498db", fg="white",
        activebackground="#2980b9", activeforeground="white",
        width=20, height=3,
        command=lambda: activate_dispenser('dispenser2', status_label)
    )
    btn_dispenser2.pack(side=tk.LEFT, padx=20)
    
    # Tasten für den dritten Motor (Schiene)
    btn_rail_forward = tk.Button(
        rail_frame,
        text="Motor 3 Vorwärts",
        font=button_font, bg="#f1c40f", fg="white",
        activebackground="#f39c12", activeforeground="white",
        width=20, height=3
    )
    btn_rail_forward.pack(side=tk.LEFT, padx=20)
    
    btn_rail_backward = tk.Button(
        rail_frame,
        text="Motor 3 Zurück",
        font=button_font, bg="#e74c3c", fg="white",
        activebackground="#c0392b", activeforeground="white",
        width=20, height=3
    )
    btn_rail_backward.pack(side=tk.LEFT, padx=20)
    
    # Events für Drücken und Loslassen binden
    btn_rail_forward.bind('<ButtonPress-1>', lambda event: start_rail_motor(True, status_label))
    btn_rail_forward.bind('<ButtonRelease-1>', lambda event: stop_rail_motor())
    
    btn_rail_backward.bind('<ButtonPress-1>', lambda event: start_rail_motor(False, status_label))
    btn_rail_backward.bind('<ButtonRelease-1>', lambda event: stop_rail_motor())

    # "Aufräumen" beim Schließen
    def on_closing():
        global rail_motor_moving
        rail_motor_moving = False # Stellt sicher, dass der Thread stoppt
        if gpio_initialized:
            # Gib den Motoren kurz Zeit zum Stoppen, bevor die Pins freigegeben werden
            time.sleep(0.1)
            for config in motors_config.values():
                GPIO.output(config['pins']['EN'], GPIO.HIGH)
            GPIO.cleanup()
            print("GPIO cleaned up.")
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

# Anmeldefenster
def create_login_window():
    login_window = tk.Tk()
    login_window.title("Anmeldung")
    window_width, window_height = 450, 150
    screen_width, screen_height = login_window.winfo_screenwidth(), login_window.winfo_screenheight()
    position_top = int(screen_height / 2 - window_height / 2)
    position_right = int(screen_width / 2 - window_width / 2)
    login_window.geometry(f"{window_width}x{window_height}+{position_right}+{position_top}")
    login_window.configure(bg="#f0f0f0")
    login_window.resizable(False, False)

    def proceed_to_main_app(event=None):
        login_window.destroy()
        launch_main_app()

    prompt_font = font.Font(family="Helvetica", size=12)
    tk.Label(login_window, text="Gib deine Matrikelnummer ein und drücke Enter", font=prompt_font, bg="#f0f0f0").pack(pady=20, padx=10)
    entry_field = tk.Entry(login_window, font=prompt_font, width=30)
    entry_field.pack(pady=10)
    entry_field.focus_set()
    entry_field.bind("<Return>", proceed_to_main_app)
    login_window.mainloop()

# Programmstart
if __name__ == "__main__":
    create_login_window()