import os


def guardar_datos_conexion(filename, hostname=None, port=None, service_name=None,mongodb_url=None):
    with open(filename, 'w') as file:
        if hostname and port and service_name:
            file.write(f"hostname={hostname}\n")
            file.write(f"port={port}\n")
            file.write(f"service_name={service_name}\n")
        if mongodb_url:
            file.write(f"mongodb_url={mongodb_url}\n")


def cargar_datos_conexion(filename):
    if not os.path.exists(filename):
        print("El archivo de configuración no existe.")
        return None

    datos_conexion = {}
    with open(filename, 'r') as file:
        for line in file:
            key, value = line.strip().split('=', 1)
            datos_conexion[key] = value

    return datos_conexion


