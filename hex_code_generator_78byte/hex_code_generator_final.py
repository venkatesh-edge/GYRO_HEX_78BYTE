import time
import serial
import random

def capitalize_alphabets_in_data(data):
    # Convert each byte to a character, capitalize it if it's alphabetic, and convert it back to byte
    return bytes([ord(chr(byte).upper()) if 65 <= byte <= 90 or 97 <= byte <= 122 else byte for byte in data])



def generate_mock_data():
    # Header
    data = b'\x5A\xA5'

    # Number of data bytes (48h or 72 in decimal)
    data += b'\x48'

    # Identifier
    data += b'\x02'

    # Status bytes
    data += random.randint(0, 255).to_bytes(1, byteorder="big")  # Status 1
    data += random.randint(0, 255).to_bytes(1, byteorder="big")  # Status 2

    # BITE Status
    data += random.randint(0, 255).to_bytes(1, byteorder="big")

    # Date (1–366 days)
    data += random.randint(1, 366).to_bytes(2, byteorder="big")

    # Time Reference (0–86400 seconds, scaled by 0.01)
    time_ref = random.randint(0, 86400 * 100)
    data += time_ref.to_bytes(3, byteorder="big")

    # Spare
    data += b'\x00\x00'

    # Attitude (Heading, Roll, Pitch)
    heading = random.randint(0, (2 ** 15) - 1).to_bytes(2, byteorder="big")  # Scaled for 0 to 360
    scale_factor = (2 ** 15 - 1) // 90
    roll = random.randint(-90 * scale_factor, 90 * scale_factor).to_bytes(2, byteorder="big", signed=True)
    pitch = random.randint(-90 * scale_factor, 90 * scale_factor).to_bytes(2, byteorder="big", signed=True)
    data += heading + roll + pitch

    # Attitude Rates
    for _ in range(3):
        rate = random.randint(-(2**15), (2**15) - 1).to_bytes(2, byteorder="big", signed=True)
        data += rate

    # INS Position (Latitude, Longitude, Depth)
    latitude = random.randint(-(2 ** 31), (2 ** 31) - 1).to_bytes(4, byteorder="big", signed=True)
    longitude = random.randint(-(2 ** 31), (2 ** 31) - 1).to_bytes(4, byteorder="big", signed=True)
    depth = random.randint(-(2 ** 15), (2 ** 15) - 1).to_bytes(2, byteorder="big", signed=True)
    data += latitude + longitude + depth

    # INS Position Accuracy
    for i in range(3):
        max_val = (2 ** 32 - 1) if i < 2 else (2 ** 16 - 1)
        accuracy = random.randint(0, max_val).to_bytes(4 if i < 2 else 2, byteorder="big")
        data += accuracy

    # GPS Position
    data += latitude + longitude  # Reuse random values from above

    # INS Velocity (North, East, Down)
    for _ in range(3):
        velocity = random.randint(-(2 ** 15), (2 ** 15) - 1).to_bytes(2, byteorder="big", signed=True)
        data += velocity

    # Log Velocity
    log_velocity = random.randint(-(2 ** 15), (2 ** 15) - 1).to_bytes(2, byteorder="big", signed=True)
    data += log_velocity

    # Navigation Data (Course Made Good, Speed Over Ground, Set, Drift)
    course = random.randint(0, (2 ** 15) - 1).to_bytes(2, byteorder="big")  # Unsigned
    speed = random.randint(0, (2 ** 15) - 1).to_bytes(2, byteorder="big")  # Unsigned
    set_dir = random.randint(0, (2 ** 15) - 1).to_bytes(2, byteorder="big")  # Unsigned
    drift = random.randint(-(2 ** 15), (2 ** 15) - 1).to_bytes(2, byteorder="big", signed=True)  # Signed
    data += course + speed + set_dir + drift

    # Reserved bytes
    data += b'\x00' * 6

    # Check Byte (Mocked with a simple sum of all data bytes mod 256)
    checksum = sum(data) % 256
    data += checksum.to_bytes(1, byteorder="big")

    # Terminator
    data += b'\xAA'

    data = capitalize_alphabets_in_data(data)
    return data


def main():
    port_name = input("Enter the mock serial port name (e.g., COM4 or /dev/pts/4): ")
    try:
        # Configure serial port with the specified settings
        with serial.Serial(
                port=port_name,
                baudrate=19200,          # Baud Rate: 19200
                stopbits=serial.STOPBITS_ONE,  # Stop Bit: 1
                parity=serial.PARITY_EVEN,    # Parity: Even
                timeout=1
        ) as ser:
            while True:
                mock_data = generate_mock_data()
                # print(mock_data)
                ser.write(mock_data)  # Send data to the serial port
                # Convert the data to a hex string and print it in uppercase
                print(f"Sent: {' '.join(format(byte, '02X') for byte in mock_data)}")
                time.sleep(1)  # Simulate 1 Hz data rate
    except serial.SerialException as e:
        print(f"Error: {e}")



if __name__ == "__main__":
    main()
