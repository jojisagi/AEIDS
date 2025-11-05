from .oracle_model import OracleDB

class BaseModelo:
    def __init__(self, db: OracleDB):
        self.db = db

class OrdenModelo(BaseModelo):
    def listar(self):
        return self.db.ordenes()

    def insertar(self, cve_status, eq_marca, eq_modelo, cve_tipo_equipo, notas_cliente, cliente, cve_taller, cve_tecnico):
        return self.db.insertar_orden(cve_status, eq_marca, eq_modelo, cve_tipo_equipo, notas_cliente, cliente, cve_taller, cve_tecnico)

    def tecnicos_orden(self, cve_orden, horas=False):
        return self.db.tecnicos_orden(cve_orden, horas)

    def tipos(self):
        return self.db.tipos()

    def estados(self, pais):
        return self.db.estados(pais)

    def talleres(self):
        return self.db.talleres()

class NotaModelo:
    def __init__(self, db):
        self._db = db  # OracleDB

    def insertar(self, cve_orden: int, nota: str):
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ORDEN_NOTA (CVE_ORDEN, NOTA, FECHA)
                VALUES (:ord, :nota, SYSDATE)
                """,
                {"ord": int(cve_orden), "nota": str(nota).strip()},
            )
        # el commit lo haces desde la UI (ya lo tienes)

    def listar(self, cve_orden: int):
        conn = self._db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT NOTA, FECHA
                  FROM ORDEN_NOTA
                 WHERE CVE_ORDEN = :ord
                 ORDER BY FECHA DESC
                """,
                {"ord": int(cve_orden)},
            )
            rows = cur.fetchall()
        return [{"nota": r[0], "fecha": r[1]} for r in rows]

class ParteModelo(BaseModelo):
    # Catálogo (para combos)
    def catalogo(self):
        try:
            return self.db.partes()
        except TypeError:
            return self.db.partes_catalogo()

    # Partes asociadas a una orden
    def listar(self, cve_orden):
        if hasattr(self.db, "partes_orden"):
            return self.db.partes_orden(cve_orden)
        return self.db.partes(cve_orden)

    def insertar(self, cve_orden, parte_id):
        return self.db.parte_orden(cve_orden, parte_id)

    def eliminar(self, cve_parte_orden):
        return self.db.eliminar_parte(cve_parte_orden)

class ServicioModelo(BaseModelo):
    # Catálogo (para combos)
    def catalogo(self):
        try:
            return self.db.servicios()
        except TypeError:
            return self.db.servicios_catalogo()

    # Servicios asociadas a una orden
    def listar(self, cve_orden):
        if hasattr(self.db, "servicios_orden"):
            return self.db.servicios_orden(cve_orden)
        return self.db.servicios(cve_orden)

    def insertar(self, cve_orden, servicio_id):
        return self.db.servicio_orden(cve_orden, servicio_id)

    def eliminar(self, cve_servicio_orden):
        return self.db.eliminar_servicio(cve_servicio_orden)

class ClienteModelo(BaseModelo):
    def insertar_y_verificar(self, *args, **kwargs):
        return self.db.insertar_cliente_y_verificar_datos(*args, **kwargs)

class CatalogosModelo(BaseModelo):
    def tipos(self):
        return self.db.tipos()

    def estados(self, pais):
        return self.db.estados(pais)

    def paises(self):
        return self.db.paises()

    def talleres(self):
        return self.db.talleres()

    def tecnicos_taller(self, cve_taller):
        return self.db.tecnicos_taller(cve_taller)
