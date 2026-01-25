from random import randint, uniform
from typing import Any


class Esp32Mock:
    def __init__(self):
        pass


    def reset_input_buffer(self) -> None:
        """Mocked method to reset the input buffer of the ESP32 serial port

         Returns:
            None: Does nothing, original method only clears buffer, but there is no buffer as the data is mocked
        """
        pass

    
    def readline(self) -> bytes | Any:
        """Return mocked serial data from ESP32
        lux_intensity (float, null)
        ph (float, null)
        temperature (int, null)
        conductivity (float, null)
        progby_90 (int, null)
        progby_180 (int, null)
        
        Returns:
            bytes | Any: Mocked UTF-8 encoded data from ESP32
        """
        return f"{uniform(20.0, 30.0):.2f},{uniform(0.0, 14.0)},{randint(10, 30)},\
                {uniform(0.0, 100.0)},{randint(0, 180)},{randint(0, 180)}\n".encode("UTF-8")

    def close(self) -> None:
        """Close the mock serial connection

        Returns:
            None: Does nothing, mocked connection has nothing to close
        """
        pass