from model.repositories import ParteModelo

class ParteControlador:
    def __init__(self, modelo: ParteModelo):
        self.m = modelo

    # Catálogo
    def catalogo(self):
        return self.m.catalogo()

    # Asociadas a orden
    def listar(self, cve_orden):
        return self.m.listar(cve_orden)

    def insertar(self, cve_orden, parte_id):
        return self.m.insertar(cve_orden, parte_id)

    def eliminar(self, cve_parte_orden):
        return self.m.eliminar(cve_parte_orden)
