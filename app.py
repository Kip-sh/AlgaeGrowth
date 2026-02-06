from mocks.colorimeter_mock import ColorimeterMock
from mocks.esp32_mock import Esp32Mock

from utils.database import DatabaseConnection

import serial
import re

from azure.iot.device import IoTHubDeviceClient

from dotenv import load_dotenv
from time import sleep
from os import getenv

from utils.log import Logger

previous_data = None

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
        attempt = 0
        while True:
            try:
                client = IoTHubDeviceClient.create_from_connection_string(getenv("PRIMARY_CONNECTION_STRING"))
                client.connect()
                print("Connected to Azure IoT Hub")
                break
            except Exception as e:
                attempt += 1
                if attempt >= 10:
                    client=None
                    print("Failed to connect to Azure IoT Hub after 10 attempts, continuing without Azure connection")
                    break
                print(f"Failed to connect to Azure IoT Hub: {e}")
                print("Retrying in 5 seconds...")
                sleep(5)
    else:
        client = None

    colorimeter: serial.Serial | ColorimeterMock = None
    esp: serial.Serial | Esp32Mock = None

    if not DEBUG:
        while colorimeter is None or esp is None:
            try:
                # Try to connect to both devices until successful
                # == Colorimeter Config ==
                # (x, y)
                if colorimeter is None:
                    colorimeter = serial.Serial(
                        port=getenv("COLPORT"),
                        baudrate=getenv("COLBAUD_RATE"),
                        timeout=2
                    )

                # == ESP32 Config ==
                if esp is None:
                    esp = serial.Serial(
                        port=getenv("ESPPORT"),
                        baudrate=getenv("ESPBAUD_RATE"),
                        timeout=2
                    )
            except:
                print("Not all devices connected, retrying in 5 seconds")
                sleep(5)

    else:
        colorimeter = ColorimeterMock()
        esp = Esp32Mock()

    return client, colorimeter, esp


def read_from_esp32() -> list[int | float] | None:
    """Read data from the ESP32 serial port, convert from csv to python list with correct data types

    Args:
        None

    Returns:
        list[int | float] | None: List of values received from the esp or None if no data recieved/errored
    """
    espregex = r"[eE0-9.\+-,]+"

    try:
        esp.reset_input_buffer()
        data = esp.readline().decode("UTF-8").strip()

        if not data:
            data = previous_data
            if data is None:
                return None
            
            previous_data = data

        if not bool(re.fullmatch(espregex, data)):
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
    colregex = r"\((\d+), (\d+)\)"
    try:
        colorimeter.reset_input_buffer()
        data = colorimeter.readline().decode("UTF-8").strip()

        if not data:
            return None
        colorimeter_data_grouped = re.search(colregex, data, re.MULTILINE)

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


def main():
    while True:
        espdata = read_from_esp32()
        coldata = read_from_colorimeter()
        
        try:
            assert espdata is not None
            assert coldata is not None

            fulldata = espdata[:4] + coldata + espdata[4:]
            logger.log(fulldata)
            print(f"Stored data: {fulldata}")

        except AssertionError:
            print("No data received from one of the devices")
            print(f"ESP32 data: {espdata} | Colorimeter data: {coldata}")

        sleep(int(MONITORING_DELAY))


def shutdown() -> None:
    """Shutdown procedure to close device connections gracefully
    """

    if not DEBUG:
        colorimeter.close()
        esp.close()

    if AZURE_ENABLED:
        client.disconnect()

    database.close_connection()
    print("shutdown complete")


def clear_backlog() -> None:
    """"Retrieve all measurements from the database with sent_to_azure=0 and send them to azure, marking them as sent if successful
    """
    if AZURE_ENABLED is False:
        return
    
    print("Clearing backlog...")
    backlog = database.get_backlog()
    for row in backlog:
        try:
            logger.log(row[1:10], backlog_item=True)
            database.mark_as_sent(row[0])

        except Exception as e:
            print(e)

    print("Backlog cleared")


if __name__ == "__main__":
    # == General Config ==
    DEBUG = getenv("DEBUG") == "true"
    AZURE_ENABLED = getenv("AZURE_ENABLED") == "true"

    # Device handles
    client, colorimeter, esp = get_devices()
    database = DatabaseConnection(getenv("DATABASEFILE"), getenv("DATABASETABLE"))
    logger = Logger(database, client)

    clear_backlog()

    # Monitoring Delay in seconds
    MONITORING_DELAY = getenv("MONITORING_DELAY")

    try:
        main()
    
    except KeyboardInterrupt:
        shutdown()
