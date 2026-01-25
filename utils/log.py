import json
from typing import Any

from azure.iot.device import IoTHubDeviceClient
from azure.iot.device import Message

from utils.database import DatabaseConnection


class Logger:
    def __init__(self, database: DatabaseConnection, azure_client=None):
        self.database: DatabaseConnection = database
        self.azure_client: IoTHubDeviceClient | None = azure_client


    def log(self, values: list[int | float]) -> None:
        """Log data to log file in the sqlite database
        
        Args:
            values (list[int | float]): List of values to log
        """
        self.database.insert_measurement(*values)
        
        if self.azure_client:
            message = self.list_to_json(values)
            self.send_message_to_azure(message)


    def send_message_to_azure(self, azure_message):
        if type(azure_message) == dict:
            azure_message = json.dumps(azure_message)

        message = Message(azure_message)
        message.content_type = 'application/json'
        message.content_encoding = 'UTF-8'
        
        try:
            self.azure_client.send_message(message)
            print("Data sent to iot hub")
        except Exception as e:
            pass


    def list_to_json(self, values: list[int | float]) -> str:
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