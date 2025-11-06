# seed_status.py
import os
import oracledb as cx

HOST = "200.13.89.10"
PORT = 1521
SERVICE_NAME = "pdbcib.lci.ulsa.mx"
USER = "cib700_01"

pwd = os.environ.get("ORA_PWD")
if not pwd:
    raise SystemExit("Define ORA_PWD: export ORA_PWD='TU_PASSWORD'")

dsn = f"{HOST}:{PORT}/{SERVICE_NAME}"
with cx.connect(user=USER, password=pwd, dsn=dsn) as con:
    cur = con.cursor()

    # Asegura 1=En proceso, 2=Terminada, 3=Recogida
    cur.execute("""
        MERGE INTO STATUS d
        USING (SELECT 1 cve, 'En proceso' txt FROM dual) s
        ON (d.cve_status = s.cve)
        WHEN MATCHED THEN UPDATE SET d.status = s.txt
        WHEN NOT MATCHED THEN INSERT (cve_status, status) VALUES (s.cve, s.txt)
    """)
    cur.execute("""
        MERGE INTO STATUS d
        USING (SELECT 2 cve, 'Terminada' txt FROM dual UNION ALL SELECT 3, 'Recogida' FROM dual) s
        ON (d.cve_status = s.cve)
        WHEN NOT MATCHED THEN INSERT (cve_status, status) VALUES (s.cve, s.txt)
    """)
    # Si tu UI usa "Alta" y quieres soportarla como 4:
    # cur.execute("""
    #     MERGE INTO STATUS d
    #     USING (SELECT 4 cve, 'Alta' txt FROM dual) s
    #     ON (d.cve_status = s.cve)
    #     WHEN NOT MATCHED THEN INSERT (cve_status, status) VALUES (s.cve, s.txt)
    # """)

    con.commit()
    print("✔ STATUS normalizado.\n")

    print("STATUS actual:")
    for r in cur.execute("SELECT cve_status, status FROM STATUS ORDER BY cve_status"):
        print(" ", r[0], r[1])

    print("\nBuscando órdenes con estatus inexistente...")
    orphans = list(cur.execute("""
        SELECT o.cve_orden, o.cve_status
        FROM ORDEN o
        LEFT JOIN STATUS s ON s.cve_status = o.cve_status
        WHERE s.cve_status IS NULL
    """))
    if not orphans:
        print("✔ No hay órdenes con estatus inexistente.")
    else:
        print("⚠ Hay órdenes con cve_status sin catálogo. Corrigiendo a 1 (En proceso)...")
        cur.execute("""
            UPDATE ORDEN o
            SET o.cve_status = 1
            WHERE NOT EXISTS (SELECT 1 FROM STATUS s WHERE s.cve_status = o.cve_status)
        """)
        print(f"✔ Filas actualizadas: {cur.rowcount}")
        con.commit()
        