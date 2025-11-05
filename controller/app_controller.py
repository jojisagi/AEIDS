from .db_facade import DBFacade

class AppController:
    def __init__(self):
        self.db_instance = None
        self.connection = None

    def connect(self, hostname: str, port: str, service_name: str,
                username: str = 'cib700_01', password: str = 'Hector701%/01.'):
        self.db_instance = DBFacade(hostname, port, service_name, username, password)
        self.connection = self.db_instance.get_connection()
        return self.db_instance, self.connection

    def close(self):
        if self.db_instance:
            self.db_instance.close_connection()
            self.db_instance = None
            self.connection = None
