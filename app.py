import RPi.GPIO as GPIO
import time
import atexit # Wichtig für das Aufräumen der GPIO-Pins beim Beenden der Anwendung
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# --- GPIO & Motor Konfiguration ---
# WICHTIG: Diese Pin-Nummern an Ihre tatsächliche Verkabelung anpassen!
# Jeder Motor benötigt ein eigenes Set von STEP-, DIR- und EN-Pins.
MOTOR_PINS = {
    1: {'STEP': 17, 'DIR': 27, 'EN': 23},  # Motor 1: Beispiel-Pins
    2: {'STEP': 24, 'DIR': 25, 'EN': 8},   # Motor 2: Beispiel-Pins
    3: {'STEP': 16, 'DIR': 20, 'EN': 21}    # Motor 3: Beispiel-Pins
}

# Parameter für JEDEN Motor (wie vom Benutzer gewünscht)
# Diese Parameter sind für alle Motoren in dieser Konfiguration gleich.
MOTOR_PARAMS = {
    'STEPS_PER_REV': 200,   # Schritte pro Umdrehung des Motors (z.B. 200 für 1.8 Grad/Schritt)
    'MOVEMENT_DEGREE': 90,  # Grad der Bewegung pro Klick
    'usDelay': 800,         # Mikrosekunden-Verzögerung zwischen Pulsen (Geschwindigkeit)
    'uS': 0.000001          # Eine Mikrosekunde (für Umrechnung von Mikrosekunden zu Sekunden)
}

gpio_initialized = False # Flag, um den Initialisierungsstatus von GPIO zu verfolgen

try:
    GPIO.setmode(GPIO.BCM) # Verwende BCM Pin-Nummerierung
    GPIO.setwarnings(False) # Deaktiviere Warnungen für bereits eingerichtete Pins

    # Richte alle GPIO-Pins für jeden Motor als Ausgänge ein
    for motor_id, pins in MOTOR_PINS.items():
        GPIO.setup(pins['STEP'], GPIO.OUT)
        GPIO.setup(pins['DIR'], GPIO.OUT)
        GPIO.setup(pins['EN'], GPIO.OUT)
        # Deaktiviere Motoren initial, indem der Enable-Pin auf HIGH gesetzt wird (oft HIGH für deaktiviert)
        GPIO.output(pins['EN'], GPIO.HIGH)

    gpio_initialized = True
    print("RPi.GPIO erfolgreich initialisiert. Motoren bereit zur Steuerung.")

except RuntimeError:
    # Dieser Block wird ausgeführt, wenn RPi.GPIO nicht auf einem Raspberry Pi läuft
    print("RPi.GPIO nicht verfügbar. Führe den Code auf einem Raspberry Pi aus, um die Motorsteuerung zu aktivieren.")
    print("Die Anwendung läuft im Simulationsmodus. Motoraktionen werden nur in der Konsole ausgegeben.")
    gpio_initialized = False

# Funktion zur Steuerung eines spezifischen Motors
def move_motor_degrees(motor_id, degrees, direction_clockwise):
    """
    Bewegt den angegebenen Motor um eine bestimmte Gradzahl in die angegebene Richtung.

    Args:
        motor_id (int): Die ID des zu steuernden Motors (1, 2, oder 3).
        degrees (float): Die Anzahl der Grad, um die sich der Motor bewegen soll.
        direction_clockwise (bool): True für Bewegung im Uhrzeigersinn, False für gegen den Uhrzeigersinn.
    """
    if not gpio_initialized:
        # Wenn GPIO nicht initialisiert ist (z.B. auf einem PC ausgeführt), simuliere die Bewegung
        print(f"SIMULATION: Motor {motor_id} bewegt sich {degrees} Grad {'im Uhrzeigersinn' if direction_clockwise else 'gegen den Uhrzeigersinn'}")
        return

    # Überprüfe, ob die Motor-ID in der Konfiguration vorhanden ist
    if motor_id not in MOTOR_PINS:
        print(f"FEHLER: Motor {motor_id} ist nicht in der Konfiguration 'MOTOR_PINS' definiert.")
        return

    pins = MOTOR_PINS[motor_id] # Hole die Pin-Informationen für den spezifischen Motor
    params = MOTOR_PARAMS       # Nutze die globalen Motorparameter

    # Aktiviere den Motor-Treiber (Enable-Pin auf LOW setzen, falls aktiv LOW)
    GPIO.output(pins['EN'], GPIO.LOW)
    time.sleep(0.01) # Kurze Wartezeit für die Stabilisierung des Treibers

    # Berechne die Anzahl der benötigten Schritte
    num_steps = int((degrees / 360.0) * params['STEPS_PER_REV'])

    # Setze die Drehrichtung (DIR Pin)
    # GPIO.HIGH für im Uhrzeigersinn, GPIO.LOW für gegen den Uhrzeigersinn (Anpassung je nach Treiber)
    GPIO.output(pins['DIR'], GPIO.HIGH if direction_clockwise else GPIO.LOW)

    # Erzeuge die Schrittpulse
    for _ in range(num_steps):
        GPIO.output(pins['STEP'], GPIO.HIGH) # STEP-Pin HIGH setzen
        time.sleep(params['uS'] * params['usDelay']) # Kurze Pause für den Puls
        GPIO.output(pins['STEP'], GPIO.LOW)  # STEP-Pin LOW setzen
        time.sleep(params['uS'] * params['usDelay']) # Kurze Pause vor dem nächsten Puls

    # Deaktiviere den Motor-Treiber nach der Bewegung
    GPIO.output(pins['EN'], GPIO.HIGH)
    print(f"Motor {motor_id} hat sich um {degrees} Grad {'im Uhrzeigersinn' if direction_clockwise else 'gegen den Uhrzeigersinn'} bewegt.")

# --- Flask Routen ---

@app.route('/')
def index():
    """
    Rendert die Haupt-HTML-Seite.
    Diese Route dient nur dazu, die index.html Datei an den Browser zu senden.
    Da Jinja2 nicht verwendet wird, wird das Template direkt gerendert.
    """
    return render_template('index.html')

@app.route('/control_motor', methods=['POST'])
def control_motor():
    """
    Empfängt POST-Anfragen von der Webseite zur Motorsteuerung.
    Liest die motor_id und direction aus den Formulardaten und ruft die Steuerfunktion auf.
    """
    # Holt die Werte 'motor_id' und 'direction' aus den Formulardaten der POST-Anfrage
    motor_id_str = request.form.get('motor_id')
    direction_str = request.form.get('direction')

    try:
        motor_id = int(motor_id_str) # Konvertiere Motor-ID zu einer Ganzzahl
        # Bestimme die Drehrichtung: True für 'right' (im Uhrzeigersinn), False für 'left' (gegen den Uhrzeigersinn)
        direction_clockwise = (direction_str == 'right')
        
        # Rufe die Funktion zur Motorsteuerung auf mit den Parametern des jeweiligen Motors
        move_motor_degrees(motor_id, MOTOR_PARAMS['MOVEMENT_DEGREE'], direction_clockwise)
        
        # Sende eine einfache Erfolgsbestätigung zurück an den Browser
        return "OK", 200 # HTTP 200 OK
    except Exception as e:
        # Fange potenzielle Fehler ab (z.B. ungültige Daten) und gib eine Fehlermeldung aus
        print(f"Fehler bei der Motorsteuerung für Motor {motor_id_str}, Richtung {direction_str}: {e}")
        return f"Fehler bei der Verarbeitung der Anfrage: {e}", 500 # HTTP 500 Internal Server Error

# --- GPIO Aufräumen beim Beenden der Anwendung ---
def cleanup_gpio():
    """
    Diese Funktion wird aufgerufen, wenn die Flask-Anwendung beendet wird (z.B. bei Strg+C).
    Sie setzt alle GPIO-Pins zurück und deaktiviert die Motoren, um Hardware-Schäden und
    unnötigen Stromverbrauch zu vermeiden.
    """
    if gpio_initialized:
        print("\nStarte GPIO-Cleanup...")
        for motor_id, pins in MOTOR_PINS.items():
            GPIO.output(pins['EN'], GPIO.HIGH) # Alle Motoren deaktivieren
        GPIO.cleanup() # Setzt alle GPIO-Pins auf ihren Standardzustand zurück
        print("GPIO-Pins erfolgreich aufgeräumt und Motorsteuerung deaktiviert.")
    else:
        print("\nGPIO war nicht initialisiert, kein Cleanup notwendig.")

# Registriere die Cleanup-Funktion, die beim Beenden der Anwendung ausgeführt wird
atexit.register(cleanup_gpio)

if __name__ == '__main__':
    # Starte die Flask-Anwendung.
    # host='0.0.0.0' macht die Anwendung von jeder IP im lokalen Netzwerk erreichbar.
    # port=5000 ist der Standard-Port für Flask.
    # debug=True ist nützlich für die Entwicklung (zeigt Fehler an, lädt bei Änderungen neu).
    # Für den produktiven Einsatz sollte debug=False gesetzt werden.
    app.run(host='0.0.0.0', port=5000, debug=True)
