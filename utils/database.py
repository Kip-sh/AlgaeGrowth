import sqlite3


class DatabaseConnection:
    def __init__(self, db_name: str, table_name: str):
        self.db_name = db_name
        self.table_name = table_name

        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()

        self.create_table()


    def create_table(self) -> None:
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lux_intensity REAL,
            ph_level REAL,
            temperature REAL,
            conductivity REAL,
            colorimeter_90 INTEGER,
            colorimeter_180 INTEGER,
            progby_90 INTEGER,
            progby_180 INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            sent_to_azure BOOLEAN DEFAULT 0
        )
        """)

        self.conn.commit()


    def insert_measurement(self, lux_intensity: float | None, ph_level: float | None,
                           temperature: int | None, conductivity: float | None,
                            colorimeter_90: int | None, colorimeter_180: int | None,
                            progby_90: int | None, progby_180: int | None, rasp_timestamp: str, sent_to_azure: bool=0) -> None:
        
        self.cursor.execute("""INSERT INTO measurements (lux_intensity, ph_level, temperature, conductivity,
                            colorimeter_90, colorimeter_180, progby_90, progby_180, timestamp, sent_to_azure) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                            (lux_intensity, ph_level, temperature, conductivity,
                            colorimeter_90, colorimeter_180, progby_90, progby_180, rasp_timestamp, sent_to_azure))

        self.conn.commit()


    def get_backlog(self) -> list[tuple]:
        self.cursor.execute("SELECT * FROM measurements WHERE sent_to_azure = 0")
        return self.cursor.fetchall()
    

    def mark_as_sent(self, measurement_id: int) -> None:
        self.cursor.execute("UPDATE measurements SET sent_to_azure = 1 WHERE id = ?", (measurement_id,))
        self.conn.commit()


    def close_connection(self) -> None:
        self.cursor.close()
        self.conn.close()