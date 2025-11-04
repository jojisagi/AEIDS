from model.repositories import ClienteModelo

class ClienteControlador:
    def __init__(self, modelo: ClienteModelo):
        self.m = modelo

    def insertar_y_verificar(self, *args, **kwargs):
        # Mantener posicionales/keywords intactos
        return self.m.insertar_y_verificar(*args, **kwargs)