import oracledb
from datetime import datetime

class Orden:
    def __init__(self, cve_orden, cve_status, eq_marca, eq_modelo, cve_tipo_equipo, notas_cliente, cliente, cve_taller, db_instance):
        self.cve_orden = cve_orden
        self.cve_status = cve_status
        self.eq_marca = eq_marca
        self.eq_modelo = eq_modelo
        self.cve_tipo_equipo = cve_tipo_equipo
        self.notas_cliente = notas_cliente
        self.cliente = cliente  # Cliente es un objeto de la clase Cliente
        self.cve_taller = cve_taller
        self.tecnicos = db_instance.tecnicos_orden(cve_orden)
        self.horas = db_instance.tecnicos_orden(cve_orden, True)

    def __str__(self):
        return (f"Orden(cve_orden={self.cve_orden}, cve_status={self.cve_status}, "
                f"eq_marca='{self.eq_marca}', eq_modelo='{self.eq_modelo}', "
                f"cve_tipo_equipo={self.cve_tipo_equipo}, notas_cliente='{self.notas_cliente}',"
                f"cliente={self.cliente}, cve_taller={self.cve_taller}),"
                f"tecnicos={self.tecnicos}, horas={self.horas}")

    # dentro de la clase Orden
    def guardar(self, db_instance, marca, tipo, modelo, stat):
        """
        Actualiza la orden en Oracle.
        - 'tipo' y 'stat' pueden ser id (int) o texto; aquí se resuelven.
        - Sanitizamos 'marca' y 'modelo' para evitar Ellipsis u otros tipos.
        """
        conn = db_instance._connection
        cur = conn.cursor()

        def _to_int(v):
            try:
                s = "" if v is None else str(v).strip()
                return int(s) if s != "" else None
            except Exception:
                return None

        # --- resolver STATUS ---
        status_id = _to_int(stat)
        if status_id is None:
            cur.execute(
                "SELECT cve_status FROM status_orden WHERE LOWER(descripcion)=:d",
                {"d": str(stat).strip().lower()},
            )
            row = cur.fetchone()
            # si el texto no existe (p.ej. 'Alta'), mapea a 'En proceso' (1)
            status_id = row[0] if row else 1

        # --- resolver TIPO ---
        tipo_id = _to_int(tipo)
        if tipo_id is None:
            cur.execute(
                "SELECT cve_tipo_equipo FROM tipo_equipo WHERE LOWER(descripcion)=:d",
                {"d": str(tipo).strip().lower()},
            )
            row = cur.fetchone()
            tipo_id = row[0] if row else None

        # --- sanitizar campos texto (evita error con Ellipsis u objetos no str) ---
        marca_s  = str(marca  if marca  is not None else "").strip()
        modelo_s = str(modelo if modelo is not None else "").strip()

        # --- UPDATE real ---
        cur.execute(
            """
            UPDATE orden
            SET eq_marca        = :marca,
                eq_modelo       = :modelo,
                cve_tipo_equipo = :tipo,
                cve_status      = :status
            WHERE cve_orden       = :orden
            """,
            {
                "marca":  marca_s,
                "modelo": modelo_s,
                "tipo":   tipo_id,
                "status": status_id,
                "orden":  self.cve_orden,
            },
        )
        cur.close()
        return 1

    def guardar_horas(self, horas, db_instance):
        if not db_instance._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = db_instance._connection.cursor()
        try:
            cursor.execute("""
                        UPDATE cib700_01.orden_tecnicos
                        SET horas = :1
                        WHERE cve_orden = :2
                    """, (
                horas,
                self.cve_orden
            ))
        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            db_instance._connection.rollback()  # Revertir la transacción en caso de error
        finally:
            cursor.close()

    def insertar_tecnico(self, cve_tecnico, db_instance):
        if not db_instance._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = db_instance._connection.cursor()
        try:
            print('aa')
            cursor.execute("SELECT * FROM cib700_01.orden_tecnicos WHERE cve_orden = :1 AND cve_empleado = :2",
                           (self.cve_orden, cve_tecnico))
            if cursor.fetchone():
                print("Ya esta")
                return 0
            else:
                print('hola')
                cursor.execute("INSERT INTO cib700_01.orden_tecnicos (cve_orden, cve_empleado, horas) VALUES (:1, :2, :3) ",
                               (self.cve_orden, cve_tecnico, self.horas))
                self.tecnicos = db_instance.tecnicos_orden(self.cve_orden)
                print(self.tecnicos)
                return 1

        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            db_instance._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()


class Cliente:
    def __init__(self, cve_cliente, nombre, paterno, correo, telefono, dir_calle, dir_num, cve_colonia, materno = None):
        self.cve_cliente = cve_cliente
        self.nombre = nombre
        self.paterno = paterno
        self.materno = materno
        self.correo = correo
        self.telefono = telefono
        self.dir_calle = dir_calle
        self.dir_num = dir_num
        self.cve_colonia = cve_colonia

    def __str__(self):
        return f"{self.nombre} {self.paterno}"

    def guardar(self, db_instance, nombre, paterno, materno, correo, telefono, dir_calle, dir_num):
        if not db_instance._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = db_instance._connection.cursor()
        try:
            cursor.execute("""
                        UPDATE cib700_01.cliente
                        SET nombre = :1, 
                            paterno = :2, 
                            materno = :3, 
                            correo = :4, 
                            telefono = :5, 
                            dir_calle = :6, 
                            dir_num = :7
                        WHERE cve_cliente = :8
                    """, (
                nombre,
                paterno,
                materno,
                correo,
                telefono,
                dir_calle,
                dir_num,
                self.cve_cliente
            ))
            db_instance._connection.commit()
        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            db_instance._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def __repr__(self):
        return (f"Cliente(cve_cliente={self.cve_cliente}, nombre='{self.nombre}', "
                f"paterno='{self.paterno}', materno='{self.materno}', "
                f"correo='{self.correo}', telefono='{self.telefono}', "
                f"dir_calle='{self.dir_calle}', dir_num='{self.dir_num}', "
                f"cve_colonia={self.cve_colonia})")

class OracleDB:
    # Variable de clase que almacenará la única instancia de conexión
    _instance = None

    def __new__(cls, *args, **kwargs):
        # Verifica si la instancia ya existe; si no, la crea
        if cls._instance is None:
            cls._instance = super(OracleDB, cls).__new__(cls)
            cls._instance._initialize_connection(*args, **kwargs)
        return cls._instance

    def _initialize_connection(self, hostname, port, service_name, username, password):
        # Si ya hay una conexión establecida, no intenta crear otra
        if not hasattr(self, "_connection"):
            dsn = f"{hostname}:{port}/{service_name}"
            try:
                # Conectar en modo Thin sin necesidad de cliente de Oracle
                self._connection = oracledb.connect(user=username, password=password, dsn=dsn)
            except oracledb.DatabaseError as e:
                print("Error en la conexión:", e)
                self._connection = None

    def get_connection(self):
        """Devuelve la conexión activa"""
        return self._connection

    def close_connection(self):
        """Cierra la conexión si está activa y borra la instancia"""
        if self._connection:
            self._connection.close()
        OracleDB._instance = None  # Restablece la instancia para permitir una nueva conexión

    def insertar_cliente_y_verificar_datos(self, nombre, apellido_p, apellido_m, correo, telefono,
                                           calle, num_calle, cp, colonia, municipio,
                                           cve_estado, cve_pais):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:

            if not isinstance(cve_estado, int):
                cursor.execute("SELECT cve_estado FROM cib700_01.estado WHERE estado = :1", (cve_estado,))
                estado_id = cursor.fetchone()
                if not estado_id:
                    estado_id = cursor.var(int)
                    cursor.execute(
                        "INSERT INTO cib700_01.estado (estado, cve_pais) VALUES (:1, :2) RETURNING cve_estado INTO :est_id",
                        (cve_estado, cve_pais, estado_id))
                    estado_id = estado_id.getvalue()
                    cve_estado = estado_id[0]
            cursor.execute("SELECT cve_municipio FROM cib700_01.municipio WHERE municipio = :1", (municipio,))
            municipio_id = cursor.fetchone()
            if not municipio_id:
                municipio_id = cursor.var(int)
                cursor.execute(
                    "INSERT INTO cib700_01.municipio (municipio, cve_estado) VALUES (:1, :2) RETURNING cve_municipio INTO :mun_id",
                    (municipio, cve_estado, municipio_id))
                municipio_id = municipio_id.getvalue()
                print(municipio_id)
            cursor.execute("SELECT cve_cp FROM cib700_01.cp WHERE cp = :1", (cp,))
            cp_id = cursor.fetchone()
            if not cp_id:
                cp_id = cursor.var(int)
                cursor.execute(
                    "INSERT INTO cib700_01.cp (cp, cve_municipio) VALUES (:1, :2) RETURNING cve_cp INTO :cp_id",
                    (cp, municipio_id[0], cp_id))
                cp_id = cp_id.getvalue()

            cursor.execute("SELECT cve_colonia FROM cib700_01.colonia WHERE colonia = :1", (colonia,))
            colonia_id = cursor.fetchone()
            if not colonia_id:
                colonia_id = cursor.var(int)
                cursor.execute("INSERT INTO cib700_01.colonia (colonia, cve_cp) VALUES (:1, :2) RETURNING cve_colonia INTO :col_id",
                               (colonia, cp_id[0], colonia_id))
                colonia_id = colonia_id.getvalue()

            cve_cliente = cursor.var(int)
            cursor.execute("""SELECT cve_cliente FROM cib700_01.cliente WHERE nombre = :1 AND paterno = :2 AND materno = :3 AND
            correo = :4 AND telefono = :5 AND dir_calle = :6 AND dir_num = :7 AND cve_colonia = :8""", (nombre, apellido_p, apellido_m,
                                                        correo, telefono, calle, num_calle, colonia_id[0]))
            cve_cliente = cursor.fetchone()
            if not cve_cliente:
                cve_cliente = cursor.var(int)
                cursor.execute("""
                    INSERT INTO cib700_01.cliente (
                        nombre, paterno, materno, correo, telefono, dir_calle, dir_num, cve_colonia
                    ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8) RETURNING cve_cliente INTO :9""", (nombre, apellido_p, apellido_m, correo,
                                                                                                 telefono, calle, num_calle, colonia_id[0], cve_cliente))
                return Cliente(cve_cliente=cve_cliente.getvalue()[0], nombre=nombre, paterno=apellido_p, materno=apellido_m,
                        correo=correo, telefono=telefono,
                        dir_calle=calle, dir_num=num_calle, cve_colonia=colonia_id[0])
            else:
                return Cliente(cve_cliente=cve_cliente[0], nombre=nombre, paterno=apellido_p, materno=apellido_m,
                        correo=correo, telefono=telefono,
                        dir_calle=calle, dir_num=num_calle, cve_colonia=colonia_id[0])
        except oracledb.DatabaseError as e:
            print("Error en la inserción:", e)
            self._connection.rollback()
            return None
        finally:
            cursor.close()

    def insertar_orden(self, cve_status, eq_marca, eq_modelo, cve_tipo_equipo, notas_cliente, cliente, cve_taller, cve_tecnico):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            cve_orden = cursor.var(int)
            # Preparar la consulta de inserción
            cursor.execute("""
                INSERT INTO cib700_01.orden (cve_status, eq_marca, eq_modelo, cve_tipo_equipo, notas_cliente, cve_cliente, cve_taller)
                VALUES (:1, :2, :3, :4, :5, :6, :7) RETURNING cve_orden INTO :8
            """, (cve_status, eq_marca, eq_modelo, cve_tipo_equipo, notas_cliente, cliente.cve_cliente, cve_taller, cve_orden))
            cve_orden = cve_orden.getvalue()[0]
            cursor.execute("INSERT INTO cib700_01.orden_tecnicos (cve_empleado, cve_orden, horas) VALUES (:1, :2, 0)", (cve_tecnico, cve_orden))
            orden = Orden(cve_orden=cve_orden, cve_status=cve_status, eq_marca=eq_marca, eq_modelo=eq_modelo, cve_tipo_equipo=cve_tipo_equipo,
                            notas_cliente=notas_cliente, cliente=cliente, cve_taller=cve_taller, db_instance=self)
            return orden
        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def tecnicos_taller(self, cve_taller):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            columnas = ['cve_empleado','nombre', 'paterno', 'materno', 'cve_rol', 'dir_calle', 'dir_num']
            cursor.execute("""SELECT empleado.cve_empleado, empleado.nombre, empleado.paterno, 
            empleado.materno, empleado.cve_rol, empleado.dir_calle, empleado.dir_num
            FROM cib700_01.empleado empleado, (SELECT cve_empleado FROM cib700_01.empleado_taller WHERE
            cve_taller = :1) aux WHERE aux.cve_empleado = empleado.cve_empleado""", (cve_taller,))
            cursor2 = self._connection.cursor()
            empleados = []
            for row in cursor:
                empleado = dict(zip(columnas, row))
                cursor2.execute("SELECT rol FROM cib700_01.rol WHERE cve_rol = :1", (empleado['cve_rol'],))
                rol = cursor2.fetchone()
                if rol:
                    empleado['cve_rol'] = rol[0]
                empleados.append(empleado)
            # Confirmar la transacción
            cursor2.close()
            return empleados

        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def talleres(self):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            cursor.execute("""SELECT cve_taller, apodo FROM cib700_01.taller""")
            talleres = {row[0]:row[1] for row in cursor}
            return talleres
        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def cliente(self, cve_cliente):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            columnas = ['nombre','paterno', 'materno', 'correo', 'telefono', 'calle', 'num', 'cve_colonia']
            cursor.execute("""SELECT nombre, paterno, materno, correo, telefono, dir_calle, dir_num, cve_colonia
            FROM cib700_01.cliente WHERE cve_cliente = :1""", (cve_cliente,))
            aux = cursor.fetchone()
            if not aux:
                return None
            cliente = dict(zip(columnas, aux))
            cliente2 = Cliente(cve_cliente=cve_cliente, nombre=cliente['nombre'], paterno=cliente['paterno'],
                               correo=cliente['correo'], telefono=cliente['telefono'], dir_calle=cliente['calle'],
                               dir_num=cliente['num'], cve_colonia=cliente['cve_colonia'], materno=cliente['materno'])

            return cliente2

        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def ordenes(self):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            columnas = ['cve_orden','status', 'marca', 'modelo', 'tipo', 'nota', 'cliente', 'taller']
            cursor.execute("""SELECT cve_orden, cve_status, eq_marca, eq_modelo, cve_tipo_equipo, notas_cliente, cve_cliente,
            cve_taller FROM cib700_01.orden""")
            ordenes = []
            for row in cursor:
                orden = dict(zip(columnas, row))
                aux = Orden(cve_orden=orden['cve_orden'], cve_status=orden['status'], eq_marca=orden['marca'], eq_modelo=orden['modelo'],
                            cve_tipo_equipo=orden['tipo'], notas_cliente=orden['nota'],
                            cliente=self.cliente(cve_cliente=orden['cliente']), cve_taller=orden['taller'], db_instance=self)
                ordenes.append(aux)
            ordenes.sort(key=lambda a: a.cve_orden)
            return ordenes

        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def tecnicos_orden(self, cve_orden, horas = False):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            cursor.execute("""SELECT empleado.nombre, empleado.paterno, aux.horas
            FROM cib700_01.empleado empleado, (SELECT cve_empleado, horas FROM cib700_01.orden_tecnicos WHERE
            cve_orden = :1) aux WHERE aux.cve_empleado = empleado.cve_empleado""", (cve_orden,))
            if horas:
                return cursor.fetchone()[2]
            empleados = []
            for row in cursor:
                empleado = row[0] + ' ' + row[1]
                empleados.append(empleado)
            return empleados

        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def paises(self):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            cursor.execute("""SELECT pais, cve_pais FROM cib700_01.pais""")
            pais_dict = {row[0]: row[1] for row in cursor}
            pais_dict = {clave: pais_dict[clave] for clave in sorted(pais_dict)}
            return pais_dict

        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def tipos(self):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            cursor.execute("""SELECT tipo, tarifa_h, cve_tipo_equipo FROM cib700_01.tipo_equipo""")
            pais_dict = {row[2]: [row[1], row[0]] for row in cursor}
            return pais_dict

        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def estados(self, pais):
        if pais is None:
            return {}

        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            cursor.execute("""SELECT estado, cve_estado FROM cib700_01.estado WHERE cve_pais = :1""", (pais,))
            pais_dict = {row[0]: row[1] for row in cursor}
            pais_dict = {clave: pais_dict[clave] for clave in sorted(pais_dict)}
            return pais_dict
        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def partes(self):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            columnas = ['cve_parte', 'descripcion', 'part_no', 'precio']
            cursor.execute("""SELECT cve_parte, descripcion, part_no, precio FROM cib700_01.parte""")
            partes = []
            for row in cursor:
                parte = dict(zip(columnas, row))
                partes.append(parte)
            return partes

        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def servicios(self):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            columnas = ['cve_servicio', 'descripcion', 'precio']
            cursor.execute("""SELECT cve_servicio, descripcion, precio FROM cib700_01.servicio""")
            servicios = []
            for row in cursor:
                servicio = dict(zip(columnas, row))
                servicios.append(servicio)
            return servicios

        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def servicio_orden(self, orden, servicio):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            cursor.execute("""INSERT INTO cib700_01.orden_servicio (cve_orden, cve_servicio)
            VALUES (:1, :2)""", (orden, servicio))
            return

        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def parte_orden(self, orden, parte):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            cursor.execute("""INSERT INTO cib700_01.orden_parte (cve_orden, cve_parte)
            VALUES (:1, :2)""", (orden, parte))
            return

        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def insertar_nota(self, nota, cve_orden):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            cursor.execute("""INSERT INTO cib700_01.orden_nota (cve_orden, nota, fecha)
            VALUES (:1, :2, :3)""", (cve_orden, nota, datetime.now()))
            return
        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error
        finally:
            cursor.close()

    def eliminar_parte(self, cve):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            cursor.execute("""DELETE FROM cib700_01.orden_parte WHERE cve_orden_parte = :2""", (cve,))

        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def eliminar_servicio(self, cve):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            cursor.execute("""DELETE FROM cib700_01.orden_servicio WHERE cve_orden_servicio = :2""", (cve,))
        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def eliminar_nota(self, nota):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            cursor.execute("""DELETE FROM cib700_01.orden_nota WHERE cve_orden_nota = :2""", (nota,))

        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def notas(self, cve_orden):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            columnas = ['cve_orden_nota','nota', 'fecha']
            cursor.execute("""SELECT cve_orden_nota, nota, fecha
            FROM cib700_01.orden_nota WHERE cve_orden = :1""", (cve_orden,))
            aux = []
            for row in cursor:
                nota = dict(zip(columnas, row))
                aux.append(nota)
                aux.sort(key=lambda a: a['cve_orden_nota'])
            return aux
        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def partes_orden(self, cve_orden):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            columnas = ['cve_orden_parte','descripcion', 'part_no', 'precio']
            cursor.execute("""SELECT aux.cve_orden_parte, parte.descripcion, parte.part_no, parte.precio
            FROM cib700_01.parte parte, (SELECT cve_parte, cve_orden_parte FROM cib700_01.orden_parte WHERE cve_orden = :1) aux 
            WHERE aux.cve_parte = parte.cve_parte""", (cve_orden,))
            aux = []
            for row in cursor:
                nota = dict(zip(columnas, row))
                aux.append(nota)
                aux.sort(key=lambda a: a['cve_orden_parte'])
            return aux

        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()

    def servicios_orden(self, cve_orden):
        if not self._connection:
            print("No hay conexión activa con la base de datos.")
            return

        cursor = self._connection.cursor()
        try:
            columnas = ['cve_orden_servicio','descripcion', 'precio']
            cursor.execute("""SELECT aux.cve_orden_servicio, parte.descripcion, parte.precio
            FROM cib700_01.servicio parte, (SELECT cve_servicio, cve_orden_servicio FROM cib700_01.orden_servicio WHERE cve_orden = :1) aux 
            WHERE aux.cve_servicio = parte.cve_servicio""", (cve_orden,))
            aux = []
            for row in cursor:
                nota = dict(zip(columnas, row))
                aux.append(nota)
                aux.sort(key=lambda a: a['cve_orden_servicio'])
            return aux

        except oracledb.DatabaseError as e:
            print("Error al insertar la orden:", e)
            self._connection.rollback()  # Revertir la transacción en caso de error

        finally:
            cursor.close()


