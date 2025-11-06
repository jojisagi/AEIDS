# controller/app_controller.py
from __future__ import annotations
from typing import Tuple, Optional

from controller.db_facade import DBFacade


class AppController:
    """
    Orquesta la creación de DBFacade.
    UI usará: (db_facade, connection) = connect(...)
    """
    def __init__(self) -> None:
        self.db: Optional[DBFacade] = None
        self.connection = None

    def connect(
        self,
        hostname: str,
        port: str | int,
        service_name: str,
        username: str,
        password: str,
    ) -> Tuple[DBFacade, object]:
        self.db = DBFacade(
            hostname=hostname,
            port=port,
            service_name=service_name,
            username=username,
            password=password,
        )
        self.connection = self.db.get_connection()
        return self.db, self.connection

    def is_connected(self) -> bool:
        return self.db is not None and self.connection is not None

    def close(self) -> None:
        if self.db:
            try:
                self.db.close_connection()
            finally:
                self.db = None
                self.connection = None