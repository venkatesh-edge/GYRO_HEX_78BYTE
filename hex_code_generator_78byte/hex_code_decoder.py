import sys
import serial
from serial.tools import list_ports
from PyQt5.QtWidgets import (QApplication, QLabel, QVBoxLayout, QGridLayout, QWidget, QLineEdit, QPushButton, QGroupBox, QHBoxLayout, QComboBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal


# Function to parse gyro data based on the provided byte structure
def parse_gyro_data(raw_data):
    if len(raw_data) == 78 and raw_data[:2] == b'\x5A\xA5' and raw_data[-1] == 0xAA:
        raw_time_seconds = int.from_bytes(raw_data[9:12], byteorder="big") * 0.01
        hours = int(raw_time_seconds // 3600)
        minutes = int((raw_time_seconds % 3600) // 60)
        seconds = int(raw_time_seconds % 60)

        data = {
            "Status 1": raw_data[4],
            "Status 2": raw_data[5],
            "BITE Status": raw_data[6],
            "Date (Day)": int.from_bytes(raw_data[7:9], byteorder="big"),
            "Time Ref GPS (HH:MM:SS)": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "Attitude Heading (°)": round(int.from_bytes(raw_data[14:16], byteorder="big") * (180 / 2 ** 15), 3),
            "Attitude Roll (°)": round(int.from_bytes(raw_data[16:18], byteorder="big", signed=True) * (90 / 2 ** 15), 3),
            "Attitude Pitch (°)": round(int.from_bytes(raw_data[18:20], byteorder="big", signed=True) * (90 / 2 ** 15), 3),
            "INS Latitude (°)": round(int.from_bytes(raw_data[26:30], byteorder="big", signed=True) * (90 / 2 ** 31), 3),
            "INS Longitude (°)": round(int.from_bytes(raw_data[30:34], byteorder="big", signed=True) * (180 / 2 ** 31), 3),
            "INS Depth (m)": round(int.from_bytes(raw_data[34:36], byteorder="big", signed=True) * 0.02, 3),
            "GPS Latitude (°)": round(int.from_bytes(raw_data[46:50], byteorder="big", signed=True) * (90 / 2 ** 31), 3),
            "GPS Longitude (°)": round(int.from_bytes(raw_data[50:54], byteorder="big", signed=True) * (180 / 2 ** 31), 3),
            "INS North Velocity (m/s)": round(int.from_bytes(raw_data[54:56], byteorder="big", signed=True) * 0.002, 3),
            "INS East Velocity (m/s)": round(int.from_bytes(raw_data[56:58], byteorder="big", signed=True) * 0.002, 3),
            "INS Down Velocity (m/s)": round(int.from_bytes(raw_data[58:60], byteorder="big", signed=True) * 0.002, 3),
            "Log Velocity (m/s)": round(int.from_bytes(raw_data[60:62], byteorder="big", signed=True) * 0.002, 3),
            "Course Made Good (°)": round(int.from_bytes(raw_data[62:64], byteorder="big") * (180 / 2 ** 15), 3),
            "Speed Over Ground (m/s)": round(int.from_bytes(raw_data[64:66], byteorder="big") * 0.002, 3),
            "Set Direction (°)": round(int.from_bytes(raw_data[66:68], byteorder="big") * (180 / 2 ** 15), 3),
            "Drift Speed (m/s)": round(int.from_bytes(raw_data[68:70], byteorder="big", signed=True) * 0.002, 3),
        }
        return data
    else:
        return {"Error": "Invalid or incomplete data"}



class SerialThread(QThread):
    data_received = pyqtSignal(dict)

    def __init__(self, port_name):
        super().__init__()
        self.port_name = port_name
        self.running = True
        self.serial_port = None
        self.buffer = bytearray()  # Buffer to store incomplete data

    def run(self):
        try:
            self.serial_port = serial.Serial(self.port_name, baudrate=9600, timeout=1, stopbits=serial.STOPBITS_ONE,
                                             parity=serial.PARITY_EVEN)
            while self.running:
                raw_data = self.serial_port.read(78)  # Read up to 78 bytes at once
                if raw_data:
                    self.buffer.extend(raw_data)  # Add the new data to the buffer

                    # Keep processing the buffer until it has fewer than 78 bytes
                    while len(self.buffer) >= 78:
                        packet = self.buffer[:78]  # Extract a potential packet (first 78 bytes)

                        # Check if the packet is valid
                        if self.is_valid_packet(packet):
                            # If valid, parse the data and emit it
                            parsed_data = parse_gyro_data(packet)
                            if "Error" in parsed_data:
                                self.data_received.emit({"Error": parsed_data["Error"]})
                            else:
                                self.data_received.emit(parsed_data)

                            # Remove the processed packet from the buffer
                            self.buffer = self.buffer[78:]
                        else:
                            # If not valid, remove the first byte and continue
                            self.buffer = self.buffer[1:]
        except Exception as e:
            self.data_received.emit({"Error": f"Error reading data: {e}"})

    def stop(self):
        self.running = False
        if self.serial_port:
            self.serial_port.close()

    def is_valid_packet(self, packet):
        # Check for the packet's validity
        return len(packet) == 78 and packet[:2] == b'\x5A\xA5' and packet[-1] == 0xAA



class GyroGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.serial_thread = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Gyro Data Display")
        self.setGeometry(100, 100, 900, 600)

        layout = QVBoxLayout()

        # Port dropdown and refresh button
        port_layout = QHBoxLayout()

        self.port_dropdown = QComboBox(self)
        self.refresh_ports()
        self.port_dropdown.setStyleSheet("""
            QComboBox {
                border: 2px solid #D3D3D3;
                border-radius: 10px;
                padding: 5px 10px;
                font-size: 14px;
            }
        """)
        port_layout.addWidget(self.port_dropdown)

        self.refresh_button = QPushButton("Refresh", self)
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #008CBA;  /* Blue */
                color: white;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #007B9E;
            }
        """)
        self.refresh_button.clicked.connect(self.refresh_ports)
        port_layout.addWidget(self.refresh_button)

        layout.addLayout(port_layout)

        # Connect and Disconnect buttons
        button_layout = QHBoxLayout()

        self.connect_button = QPushButton("Connect", self)
        self.connect_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.connect_button.clicked.connect(self.connect_serial)
        button_layout.addWidget(self.connect_button)

        self.disconnect_button = QPushButton("Disconnect", self)
        self.disconnect_button.setStyleSheet("""
            QPushButton {
                background-color: #FF6347;
                color: white;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #E55343;
            }
        """)
        self.disconnect_button.setEnabled(False)  # Initially disabled
        self.disconnect_button.clicked.connect(self.disconnect_serial)
        button_layout.addWidget(self.disconnect_button)

        layout.addLayout(button_layout)

        # Data display
        self.data_group = QGroupBox("Gyro Data")
        data_layout = QGridLayout()
        self.data_fields = {}
        parameters = [
            "Status 1", "Status 2", "BITE Status", "Date (Day)", "Time Ref GPS (HH:MM:SS)",
            "Attitude Heading (°)", "Attitude Roll (°)", "Attitude Pitch (°)",
            "INS Latitude (°)", "INS Longitude (°)", "INS Depth (m)",
            "GPS Latitude (°)", "GPS Longitude (°)", "INS North Velocity (m/s)",
            "INS East Velocity (m/s)", "INS Down Velocity (m/s)", "Log Velocity (m/s)",
            "Course Made Good (°)", "Speed Over Ground (m/s)", "Set Direction (°)", "Drift Speed (m/s)"
        ]

        for i, param in enumerate(parameters):
            box = QGroupBox(param)
            box.setStyleSheet("""
                QGroupBox{
                    font-family: Verdana;
                    font-size: 10px;
                    font-weight: bold;
                }
            """)
            box_layout = QVBoxLayout()
            value_display = QLabel(self)
            value_display.setAlignment(Qt.AlignCenter)
            value_display.setStyleSheet("""
                QLabel {
                    background-color: #f0f0f0;
                    border: 2px solid #D3D3D3;
                    border-radius: 5px;
                    padding: 5px;
                    font-size: 25px;
                    font-family: Courier New;
                    color: #4682B4;
                    font-weight: bold;
                }
            """)
            self.data_fields[param] = value_display
            box_layout.addWidget(value_display)
            box.setLayout(box_layout)
            row = i // 4
            col = i % 4
            data_layout.addWidget(box, row, col)

        self.data_group.setLayout(data_layout)
        layout.addWidget(self.data_group)

        self.status_label = QLabel("Status: Waiting for connection...", self)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def refresh_ports(self):
        self.port_dropdown.clear()
        ports = list_ports.comports()
        for port in ports:
            self.port_dropdown.addItem(port.device)

    def connect_serial(self):
        port_name = self.port_dropdown.currentText()
        if not port_name:
            self.status_label.setText("Error: No COM port selected.")
            return
        self.serial_thread = SerialThread(port_name)
        self.serial_thread.data_received.connect(self.update_data_fields)
        self.serial_thread.start()
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.status_label.setText(f"Connected to {port_name}")

    def disconnect_serial(self):
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread = None
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.status_label.setText("Disconnected. Select a new port.")

    def update_data_fields(self, data):
        if "Error" in data:
            self.status_label.setText(data["Error"])
        else:
            for key, value in data.items():
                if key in self.data_fields:
                    self.data_fields[key].setText(str(value))

    def closeEvent(self, event):
        if self.serial_thread:
            self.serial_thread.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = GyroGUI()
    gui.show()
    sys.exit(app.exec_())
