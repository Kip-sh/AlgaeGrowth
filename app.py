import datetime
import json
import os
from time import sleep

import serial
import re

from azure.iot.device import IoTHubDeviceClient
from azure.iot.device import Message
from dotenv import load_dotenv

load_dotenv()

# == General Config ==

# Monitoring Delay in seconds
MONITORING_DELAY = os.getenv("MONITORING_DELAY")

# == Azure Config ==
CONNECTION_STRING = os.getenv("PRIMARY_CONNECTION_STRING")
client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
client.connect()

# == Colorimeter Config ==
# (x, y)
serial_regex = r"\((\d+), (\d+)\)"

colorimeter = serial.Serial(
    port=os.getenv("COLPORT"),
    baudrate=os.getenv("COLBAUD_RATE"),
    timeout=2
)

# == ESP32 Config ==
esp = serial.Serial(
    port=os.getenv("ESPPORT"),
    baudrate=os.getenv("ESPBAUD_RATE"),
    timeout=2
)


# Log message to log.csv
def log(message):
    filename = os.getenv("LOGFILE")
    ensure_file_exists(filename)
    with open(filename, 'a', newline='') as log_file:
        log_file.write(message + "\n")


def ensure_file_exists(filename):
    if not os.path.isfile(filename):
        with open(filename, 'w', newline='') as log_file:
            log_file.write("lux_intensity,ph,temperature,conductivity,colorimeter_90,colorimeter_180,progby_90,progby_180\n")


def send_message_to_azure(azure_message):
    if type(azure_message) == dict:
        azure_message = json.dumps(azure_message)

    message = Message(azure_message)
    message.content_type = 'application/json'
    message.content_encoding = 'UTF-8'
    try:
        client.send_message(message)
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
    """Read bytes from colorimeter serial monitor and parse them into integers into a python list"""
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


def convert_csv_to_json(csvdata: str) -> dict:
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

        fulldata = espdata[:4] + coldata + espdata[4:] + [str(datetime.datetime.now())]
        fulldatacsv = ",".join([str(i) for i in fulldata])
        log(fulldatacsv)
        send_message_to_azure(convert_csv_to_json(fulldatacsv))
        sleep(int(MONITORING_DELAY))


if __name__ == "__main__":
    main()
