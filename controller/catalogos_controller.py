from model.repositories import CatalogosModelo

class CatalogosControlador:
    def __init__(self, modelo: CatalogosModelo):
        self.m = modelo

    def tipos(self):
        return self.m.tipos()

    # ⬇️ Propaga el país a la capa Model
    def estados(self, pais):
        return self.m.estados(pais)

    def paises(self):
        return self.m.paises()

    def talleres(self):
        return self.m.talleres()

    def tecnicos_taller(self, cve_taller):
        return self.m.tecnicos_taller(cve_taller)