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

# Motor und Sequenzkonfiguration 
# In diesem Abschnitt werden nun die Rollen der einzelnen Motoren und die Sequenzen definiert.
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

sequence_config = {
    'dispenser1': {
        'wagon_move_degrees': 90,  # Grad, um den Wagen zu bewegen und Spender 1 zu erreichen
        'dispense_rotations': 3,   # Anzahl der vollständigen 360-Grad-Drehungen
    },
    'dispenser2': {
        'wagon_move_degrees': 180, # Grad, um den Wagen zu bewegen und Spender 2 zu erreichen
        'dispense_rotations': 5,   # Anzahl der vollständigen 360-Grad-Drehungen
    }
}


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

def move_motor_degrees(motor_id, degrees, direction_clockwise):
   
    config = motors_config[motor_id]
    direction_str = 'Forward' if direction_clockwise else 'Vorwärts'
    if 'Dispenser' in config['name']:
        direction_str = 'Clockwise' if direction_clockwise else 'Ruckwärts'

    print(f"INFO: Moving {config['name']} by {degrees}° {direction_str}.")
    
    if not gpio_initialized:
        print(f"SIMULATION: Überspringen der tatsächlichen GPIO-Bewegung für {config['name']}.")
        time.sleep(1) # Simulieren Sie die für die Bewegung benötigte Zeit
        return

    pins = config['pins']
    params = config['params']
    STEP_PIN, DIR_PIN, EN_PIN = pins['STEP'], pins['DIR'], pins['EN']
    STEPS_PER_REV = params['STEPS_PER_REV']
    usDelay = params['usDelay']

    GPIO.output(EN_PIN, GPIO.LOW)
    time.sleep(0.01)
    GPIO.output(DIR_PIN, GPIO.HIGH if direction_clockwise else GPIO.LOW)
    num_steps = int((degrees / 360.0) * STEPS_PER_REV)

    for _ in range(num_steps):
        GPIO.output(STEP_PIN, GPIO.HIGH)
        time.sleep(uS * usDelay)
        GPIO.output(STEP_PIN, GPIO.LOW)
        time.sleep(uS * usDelay)

    GPIO.output(EN_PIN, GPIO.HIGH)

def run_dispensing_sequence(dispenser_id, status_label):
   
    def sequence_thread():
        # Schaltflächen während des Betriebs deaktivieren
        for btn in dispenser_buttons.values():
            btn.config(state=tk.DISABLED, bg="#95a5a6")

        try:
            seq_params = sequence_config[dispenser_id]
            wagon_move = seq_params['wagon_move_degrees']
            dispense_rotations = seq_params['dispense_rotations']

            # 1. Wagen zum Spender bewegen
            status_label.config(text=f"Status:Behälter bewegt sich zu  {motors_config[dispenser_id]['name']}...")
            move_motor_degrees('rail_wagon', wagon_move, True) #Vorwärts bewegen

            # 2. Motor 3 gibt die Snack Ausgabe frei
            status_label.config(text=f"Status: Aktivierung {motors_config[dispenser_id]['name']}...")
            dispense_degrees = dispense_rotations * 360
            move_motor_degrees(dispenser_id, dispense_degrees, True) 

            # 3. Behalter zurück auf Position 0 bringen
            status_label.config(text="Status: Wagen wird zur Ausgangsposition zurückgebracht")
            move_motor_degrees('rail_wagon', wagon_move, False) #Rückwärts bewegen

            status_label.config(text="Status: Sequenz abgeschlossen. Bereit.")
        except Exception as e:
            status_label.config(text=f"Error: {e}")
            print(f"Während der Sequenz ist ein Fehler aufgetreten: {e}")
        finally:
            # Schaltflächen wieder aktivieren
            dispenser_buttons['dispenser1'].config(state=tk.NORMAL, bg="#2ecc71")
            dispenser_buttons['dispenser2'].config(state=tk.NORMAL, bg="#3498db")

    # Run the sequence in a separate thread to keep the GUI responsive
    threading.Thread(target=sequence_thread).start()


# GUI 
dispenser_buttons = {}

def launch_main_app():
    "Startet das Tkinter Hauptfenster für das Spendersystem."
    root = tk.Tk()
    root.title("Snackster")
    root.geometry("800x600")
    root.configure(bg="#2c3e50")

    title_font = font.Font(family="Helvetica", size=32, weight="bold")
    button_font = font.Font(family="Helvetica", size=22, weight="bold")
    status_font = font.Font(family="Helvetica", size=16)

    title_label = tk.Label(root, text="🛤️ Snackster", font=title_font, bg="#2c3e50", fg="white")
    title_label.pack(pady=30)
    
    status_label = tk.Label(root, text="Status: Bereit", font=status_font, bg="#2c3e50", fg="#ecf0f1", height=2)
    status_label.pack(pady=20)

    button_frame = tk.Frame(root, bg="#2c3e50")
    button_frame.pack(pady=20)

   #Spendertasten 
    dispenser_buttons['dispenser1'] = tk.Button(
        button_frame,
        text="Spender 1 wird aktiviert",
        font=button_font,
        bg="#2ecc71",
        fg="white",
        activebackground="#27ae60",
        activeforeground="white",
        width=20,
        height=3,
        command=lambda: run_dispensing_sequence('dispenser1', status_label)
    )
    dispenser_buttons['dispenser1'].pack(side=tk.LEFT, padx=20)

    dispenser_buttons['dispenser2'] = tk.Button(
        button_frame,
        text="Activate Dispenser 2",
        font=button_font,
        bg="#3498db",
        fg="white",
        activebackground="#2980b9",
        activeforeground="white",
        width=20,
        height=3,
        command=lambda: run_dispensing_sequence('dispenser2', status_label)
    )
    dispenser_buttons['dispenser2'].pack(side=tk.LEFT, padx=20)
    
    # "Aufräumen" beim Schließen
    def on_closing():
        if gpio_initialized:
            for config in motors_config.values():
                GPIO.output(config['pins']['EN'], GPIO.HIGH)
            GPIO.cleanup()
            print("GPIO cleaned up.")
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

#Anmeldung Fenster 
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
    tk.Label(login_window, text="Gibt deine Matrikelnummer ein und drücke Enter", font=prompt_font, bg="#f0f0f0").pack(pady=20, padx=10)
    entry_field = tk.Entry(login_window, font=prompt_font, width=30)
    entry_field.pack(pady=10)
    entry_field.focus_set()
    entry_field.bind("<Return>", proceed_to_main_app)
    login_window.mainloop()

# Program Starten
if __name__ == "__main__":
    create_login_window()