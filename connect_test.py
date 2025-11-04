# connect_test.py
import os
import oracledb as cx

HOST = "200.13.89.10"
PORT = 1521
SERVICE_NAME = "pdbcib.lci.ulsa.mx"
USER = "cib700_01"

pwd = os.environ.get("ORA_PWD")  # export ORA_PWD='Hector701%/01.'
if not pwd:
    raise SystemExit("Define ORA_PWD primero: export ORA_PWD='TU_PASSWORD'")

dsn = f"{HOST}:{PORT}/{SERVICE_NAME}"
print(f"Conectando a {dsn} como {USER} ...")
with cx.connect(user=USER, password=pwd, dsn=dsn) as con:
    with con.cursor() as cur:
        cur.execute("SELECT 'OK' FROM dual")
        print("Conexión OK ->", cur.fetchone()[0])
        print("Versión servidor ->", con.version)