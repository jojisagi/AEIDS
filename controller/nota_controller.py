from model.repositories import NotaModelo

class NotaControlador:
    def __init__(self, modelo: NotaModelo):
        self._m = modelo

    def insertar(self, cve_orden, nota):
        return self._m.insertar(cve_orden, nota)

    def listar(self, cve_orden):
        return self._m.listar(cve_orden)