import mysql.connector
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv(Path(__file__).with_name(".env"))

def conectar():
    conexion = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DATABASE"),
        connection_timeout=5,
    )

    return conexion
