from model.repositories import OrdenModelo

class OrdenControlador:
    def __init__(self, modelo: OrdenModelo): self.m = modelo
    def listar(self): return self.m.listar()
    def insertar(self, *a, **k): return self.m.insertar(*a, **k)
    def tecnicos_orden(self, cve_orden, horas=False): return self.m.tecnicos_orden(cve_orden, horas)
    def tipos(self): return self.m.tipos()
    def estados(self): return self.m.estados()
    def talleres(self): return self.m.talleres()
