from machine import Pin, PWM, I2C
import utime
from imu import MPU6050
import time

# -- Ρυθμίσεις αισθητήρων και κινητήρων --
trigger = Pin(5, Pin.OUT)
echo = Pin(4, Pin.IN)

M1A = PWM(Pin(8))
M1B = PWM(Pin(9))
M2A = PWM(Pin(10))
M2B = PWM(Pin(11))
M1A.freq(50)
M1B.freq(50)
M2A.freq(50)
M2B.freq(50)

servo_pin = Pin(12)
servo = PWM(servo_pin)
servo.freq(50)

i2c = I2C(1, sda=Pin(2), scl=Pin(3), freq=400000)
imu = MPU6050(i2c)

# -- Matrix Keyboard Setup --
rows = [Pin(27, Pin.OUT), Pin(17, Pin.OUT), Pin(16, Pin.OUT), Pin(26, Pin.OUT)]  # Προσαρμόστε τα GPIO pins
cols = [Pin(0, Pin.IN, Pin.PULL_DOWN), Pin(1, Pin.IN, Pin.PULL_DOWN), Pin(7, Pin.IN, Pin.PULL_DOWN), Pin(28, Pin.IN, Pin.PULL_DOWN)]  # Προσαρμόστε τα GPIO pins


# Χάρτης πληκτρολογίου
keys = [['1', '2', '3', 'A'],
        ['4', '5', '6', 'B'],
        ['7', '8', '9', 'C'],
        ['*', '0', '#', 'D']]

# Ανάγνωση πατήματος πλήκτρου
def read_key():
    pressed_key = None
    for i, row in enumerate(rows):
        row.high()
        for j, col in enumerate(cols):
            if col.value() == 1:
                pressed_key = keys[i][j]
                utime.sleep(0.2)  # Προσθήκη debounce delay για αποφυγή πολλαπλών αναγνώσεων
                row.low()
                return pressed_key
        row.low()
    return None

# -- Υποβοηθητικές συναρτήσεις --
def ultra():
    trigger.low()
    utime.sleep_us(2)
    trigger.high()
    utime.sleep_us(5)
    trigger.low()
    while echo.value() == 0:
        signaloff = utime.ticks_us()
    while echo.value() == 1:
        signalon = utime.ticks_us()
    timepassed = signalon - signaloff
    distance = (timepassed * 0.0343) / 2
    if distance < 2:
        return 100
    return distance

def move_servo(angle):
    duty = int(1802 + (angle / 180) * (7864 - 1802))
    servo.duty_u16(duty)
    time.sleep(0.5)

def set_motor_speed(speed_left, speed_right):
    M1A.duty_u16(0)
    M1B.duty_u16(speed_left)
    M2A.duty_u16(0)
    M2B.duty_u16(speed_right)

def stop():
    M1A.duty_u16(0)
    M1B.duty_u16(0)
    M2A.duty_u16(0)
    M2B.duty_u16(0)

def backward(duration):
    M1A.duty_u16(0)
    M1B.duty_u16(65535)
    M2A.duty_u16(0)
    M2B.duty_u16(65535)
    utime.sleep(duration)
    stop()

def turn_right(duration):
    M1A.duty_u16(0)
    M1B.duty_u16(65535)
    M2A.duty_u16(65535)
    M2B.duty_u16(0)
    utime.sleep(duration)
    stop()

def turn_left(duration):
    M1A.duty_u16(40000)
    M1B.duty_u16(0)
    M2A.duty_u16(0)
    M2B.duty_u16(40000)
    utime.sleep(duration)
    stop()

def print_gyro_angle():
    gyro_data = imu.gyro.xyz
    gyro_z = gyro_data[2]
    print("Γωνία περιστροφής (Ζ-Άξονας): {:.2f}°".format(gyro_z))

def smooth_gyro_data(samples=20):
    gyro_x_total = gyro_y_total = gyro_z_total = 0
    for _ in range(samples):
        gyro_data = imu.gyro.xyz
        gyro_x_total += gyro_data[0]
        gyro_y_total += gyro_data[1]
        gyro_z_total += gyro_data[2]
        time.sleep(0.01)
    return gyro_x_total / samples, gyro_y_total / samples, gyro_z_total / samples

def calibrate_gyro(samples=20):
    gyro_x_total = gyro_y_total = gyro_z_total = 0
    for _ in range(samples):
        gyro_data = imu.gyro.xyz
        gyro_x_total += gyro_data[0]
        gyro_y_total += gyro_data[1]
        gyro_z_total += gyro_data[2]
        time.sleep(0.05)
    return gyro_x_total / samples, gyro_y_total / samples, gyro_z_total / samples

def correct_alignment(gyro_zero):
    gyro_x, gyro_y, gyro_z = smooth_gyro_data(samples=20)
    gyro_z_diff = gyro_z - gyro_zero[2]
    alignment_threshold = 1.5
    if gyro_z_diff > alignment_threshold:
        print("Δεξιά", gyro_z_diff)
        set_motor_speed(55000, 65535)
    elif gyro_z_diff < -alignment_threshold:
        print("Αριστερά", gyro_z_diff)
        set_motor_speed(65535, 55000)
    else:
        set_motor_speed(65535, 65535)

def avoid_obstacle():
    stop()
    backward(0.2)
    move_servo(0)
    distance_right = ultra()
    move_servo(120)
    distance_left = ultra()
    move_servo(60)
    if distance_right > distance_left and distance_right > 10:
            print("Στροφή δεξιά για αποφυγή!")
            turn_right(0.5)  # Στροφή δεξιά
            # Κίνηση γύρω από το εμπόδιο
            set_motor_speed(30000,30000)  # Προχωράμε μπροστά για λίγο για να περάσουμε γύρω από το εμπόδιο
            turn_left(0.5)  # Στροφή αριστερά για να επιστρέψουμε στην πορεία
    elif distance_left > 10:
            print("Στροφή αριστερά για αποφυγή!")
            turn_left(0.5)  # Στροφή αριστερά
            # Κίνηση γύρω από το εμπόδιο
            set_motor_speed(10000,10000)  # Προχωράμε μπροστά για λίγο για να περάσουμε γύρω από το εμπόδιο
            turn_right(0.5)  # Στροφή δεξιά για να επιστρέψουμε στην πορεία
    else:
            print("Δεν υπάρχει χώρος για στροφή, κάνουμε πίσω!")
            backward(0.5)  # Οπισθοχώρηση για αποφυγή

def draw_triangle(side_time, turn_time, gyro_zero):
    for _ in range(3):
        # Κίνηση ευθεία για την πλευρά του τριγώνου
        start_time = utime.ticks_ms()
        print(start_time)
        while utime.ticks_ms() - start_time < side_time * 1000:
            correct_alignment(gyro_zero)  # Συνεχής διόρθωση ευθυγράμμισης
            if ultra() < 5:
                stop()
                avoid_obstacle()
                continue
            
            time.sleep(0.05)

        stop()
        time.sleep(0.5)

        # Στροφή για τη γωνία του τριγώνου (60 μοίρες)
        print("Ξεκινάει στροφή 60°...")
        turn_right(turn_time)  # Στροφή για 60 μοίρες με τον χρόνο προσαρμοσμένο
        stop()
        time.sleep(0.7)

        # Εκτύπωση της γωνίας περιστροφής για ενημέρωση
        print_gyro_angle()

# -- Παράμετροι σχεδίασης --
side_time = 1.6
turn_time = 0.4

def modify_parameter(param_name):
    global side_time, turn_time
    input_value = ""
    print(f"Εισάγετε νέα τιμή για το {param_name}. Πατήστε 'C' για καταχώρηση.")
    while True:
        key = read_key()
        if key:
            if key.isdigit():
                input_value += key
                print(f"Εισάγεται: {input_value}")
            elif key == '#':  # Αν το πλήκτρο # πατηθεί, να προσθέσει μια τελεία
                input_value += "."
                print(f"Εισάγεται: {input_value}")
            elif key == 'C':
                try:
                    new_value = float(input_value)
                    if param_name == "side_time":
                        side_time = new_value
                    elif param_name == "turn_time":
                        turn_time = new_value
                    print(f"Η νέα τιμή για το {param_name} είναι: {new_value}")
                except ValueError:
                    print("Λάθος εισαγωγή. Δοκιμάστε ξανά.")
                break
            elif key == '*':
                print("Εισαγωγή ακυρώθηκε.")
                break
            
def main():
    try:
        print("Καλιμπράρισμα...")
        gyro_zero = calibrate_gyro()
        print("Πατήστε 'A', 'B', ή 'D'.")
        while True:
            key = read_key()
            if key == 'A':
                modify_parameter("side_time")
            elif key == 'B':
                modify_parameter("turn_time")
            elif key == 'D':
                draw_triangle(side_time, turn_time, gyro_zero)
    except KeyboardInterrupt:
        stop()
        print("Ρομπότ σταμάτησε.")

if __name__ == "__main__":
    main()