from random import randint, uniform
from typing import Any


class ColorimeterMock:
    def __init__(self):
        pass

    def reset_input_buffer(self) -> None:
        """Mocked method to reset the input buffer of the colorimeter serial port

         Returns:
            None: Does nothing, original method only clears buffer, but there is no buffer as the data is mocked
        """
        pass

    
    def readline(self) -> bytes | Any:
        """Return mocked serial data from colorimeter
        colorimeter_90 (int, null)
        colorimeter_180 (int, null)
        
        Returns:
            bytes | Any: Mocked UTF-8 encoded data from colorimeter, in the form of (colorimeter_90, colorimeter_180)
        """
        return f"({randint(0, 90)}, {randint(0, 180)})\n".encode("UTF-8")

    def close(self) -> None:
        """Close the mock serial connection

        Returns:
            None: Does nothing, mocked connection has nothing to close
        """
        pass