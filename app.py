from mocks.colorimeter_mock import ColorimeterMock
from mocks.esp32_mock import Esp32Mock

import serial
import json
import re

from azure.iot.device import IoTHubDeviceClient
from azure.iot.device import Message

from datetime import datetime
from dotenv import load_dotenv
from time import sleep
from os import getenv, path


load_dotenv()


def get_devices() -> tuple[IoTHubDeviceClient | None, serial.Serial | ColorimeterMock, serial.Serial | Esp32Mock]:
    """Initialize and return the Azure IoT Hub client, colorimeter serial connection, and ESP32 serial connection 
        or their mocks based on the DEBUG mode
        
    Args:
        None

    Returns:
        tuple[IoTHubDeviceClient | None, serial.Serial | ColorimeterMock, serial.Serial | Esp32Mock]: 
                Azure client, colorimeter connection, esp32 connection
    """
    if AZURE_ENABLED:
        # == Azure Config ==
        CONNECTION_STRING = getenv("PRIMARY_CONNECTION_STRING")
        client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
        client.connect()
    else:
        client = None

    if not DEBUG:
        
        # == Colorimeter Config ==
        # (x, y)
        colorimeter = serial.Serial(
            port=getenv("COLPORT"),
            baudrate=getenv("COLBAUD_RATE"),
            timeout=2
        )

        # == ESP32 Config ==
        esp = serial.Serial(
            port=getenv("ESPPORT"),
            baudrate=getenv("ESPBAUD_RATE"),
            timeout=2
        )

    else:
        colorimeter = ColorimeterMock()
        esp = Esp32Mock()

    return client, colorimeter, esp



def log(message: str) -> None:
    """Log data to log file in csv format
    
    Args:
        message (str): CSV formatted data
    """
    filename = getenv("LOGFILE")
    ensure_file_exists(filename)
    
    with open(filename, 'a', newline='') as log_file:
        log_file.write(message + "\n")
        print(message)

        if AZURE_ENABLED:
            send_message_to_azure(convert_csv_to_json(message))


def ensure_file_exists(filename):
    if not path.isfile(filename):
        with open(filename, 'w', newline='') as log_file:
            # Write csv headers according to database schema
            log_file.write("lux_intensity,ph,temperature,conductivity,colorimeter_90,colorimeter_180,progby_90,progby_180\n")


def send_message_to_azure(azure_message):
    if type(azure_message) == dict:
        azure_message = json.dumps(azure_message)

    message = Message(azure_message)
    message.content_type = 'application/json'
    message.content_encoding = 'UTF-8'
    
    try:
        client.send_message(message)
        print("Data sent to iot hub")
    except Exception as e:
        pass



def read_from_esp32() -> list[int | float] | None:
    """Read data from the ESP32 serial port, convert from csv to python list with correct data types
    
    Args:
        None

    Returns:
        list[int | float] | None: List of values received from the esp or None if no data recieved/errored
    """
    try:
        esp.reset_input_buffer()
        data = esp.readline().decode("UTF-8").strip()

        if not data:
            return None
        
        return convert_esp_types(data.split(","))
        
    except Exception as e:
        print(e)
        return None


def read_from_colorimeter() -> list[int] | None:
    """Read bytes from colorimeter serial monitor and parse them into integers into a python list
    colorimeter_90 (int, null)
    colorimeter_180 (int, null)
    
    Returns:
        list[int] | None: List of integers received from the colorimeter or None if no data recieved/errored
    """
    try:
        colorimeter.reset_input_buffer()
        data = colorimeter.readline().decode("UTF-8").strip()

        if not data:
            return None
        colorimeter_data_grouped = re.search(serial_regex, data, re.MULTILINE)

        if not colorimeter_data_grouped:
            return None

        return [
            int(colorimeter_data_grouped[1]),
            int(colorimeter_data_grouped[2])
        ]
    
    except Exception as e:
        return None
    

def convert_esp_types(espdata: list[str]) -> list[int | float]:
    """Convert data from the esp to the proper types to be sent to azure
        lux_intensity (float, null)
        ph (float, null)
        temperature (int, null)
        conductivity (float, null)
        progby_90 (int, null)
        progby_180 (int, null)
    
    Args:
        espdata (list[str]): List of strings received from the esp

    Returns:
        list[int | float]: List of converted data to the correct types 
    """
    return [
        float(espdata[0]) if espdata[0] != "null" else None,
        float(espdata[1]) if espdata[1] != "null" else None,
        int(espdata[2]) if espdata[2] != "null" else None,
        float(espdata[3]) if espdata[3] != "null" else None,
        int(espdata[4]) if espdata[4] != "null" else None,
        int(espdata[5]) if espdata[5] != "null" else None
    ]


def convert_csv_to_json(csvdata: str) -> str:
    values = csvdata.split(",")

    data = {
        "lux_intensity": float(values[0]),
        "ph": float(values[1]),
        "temperature": int(values[2]),
        "conductivity": float(values[3]),
        "colorimeter_90": int(values[4]),
        "colorimeter_180": int(values[5]),
        "progby_90": int(values[6]),
        "progby_180": int(values[7]),
        "rasp_timestamp": values[8]
    }

    return json.dumps(data)


def main():
    while True:
        espdata = read_from_esp32()
        coldata = read_from_colorimeter()
        
        try:
            assert espdata is not None
            assert coldata is not None

        except AssertionError:
            print("No data received from one of the devices")
            print(f"ESP32 data: {espdata} | Colorimeter data: {coldata}")

        fulldata = espdata[:4] + coldata + espdata[4:] + [str(datetime.now())]
        fulldatacsv = ",".join([str(i) for i in fulldata])
        log(fulldatacsv)

        sleep(int(MONITORING_DELAY))


if __name__ == "__main__":
    # == General Config ==
    DEBUG = getenv("DEBUG") == "true"
    AZURE_ENABLED = getenv("AZURE_ENABLED") == "true"
    serial_regex = r"\((\d+), (\d+)\)"

    # Device handles
    client, colorimeter, esp = get_devices()

    # Monitoring Delay in seconds
    MONITORING_DELAY = getenv("MONITORING_DELAY")

    main()
