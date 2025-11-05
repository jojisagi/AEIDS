import oracledb as cx

HOST="200.13.89.10"; PORT=1521; SERVICE="pdbcib.lci.ulsa.mx"
USER="cib700_01"; PWD="Hector701%/01."
dsn = cx.makedsn(HOST, PORT, service_name=SERVICE)

with cx.connect(user=USER, password=PWD, dsn=dsn) as con:
    cur = con.cursor()
    try:
        cur.execute("SELECT cve_status, descripcion FROM status ORDER BY 1")
    except Exception:
        cur.execute("SELECT cve_status, status FROM status ORDER BY 1")
    for r in cur:
        print(r) 