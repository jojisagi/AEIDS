from model.repositories import ServicioModelo

class ServicioControlador:
    def __init__(self, modelo: ServicioModelo):
        self.m = modelo

    # Catálogo
    def catalogo(self):
        return self.m.catalogo()

    # Asociados a orden
    def listar(self, cve_orden):
        return self.m.listar(cve_orden)

    def insertar(self, cve_orden, servicio_id):
        return self.m.insertar(cve_orden, servicio_id)

    def eliminar(self, cve_servicio_orden):
        return self.m.eliminar(cve_servicio_orden)
