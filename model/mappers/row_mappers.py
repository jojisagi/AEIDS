# model/mappers/row_mappers.py
from __future__ import annotations
from typing import Any, Sequence
from model.entities.orden import Orden, ClienteLite

def row_to_orden(row: Sequence[Any], cols: list[str]) -> Orden:
    d = {c: row[i] for i, c in enumerate(cols)}
    cliente = d.get("cliente")
    if isinstance(cliente, (tuple, list)) and len(cliente) >= 2:
        cli = ClienteLite(id=int(cliente[0]), nombre=str(cliente[1]))
    else:
        cli = str(cliente) if cliente is not None else ""
    return Orden(
        cve_orden=int(d["cve_orden"]),
        cve_status=int(d["cve_status"]),
        eq_marca=str(d["eq_marca"]),
        eq_modelo=str(d["eq_modelo"]),
        cve_tipo_equipo=int(d["cve_tipo_equipo"]),
        cve_taller=int(d["cve_taller"]),
        horas=int(d.get("horas", 0) or 0),
        tecnicos=[],           # puedes llenarlo aparte
        cliente=cli,
    )