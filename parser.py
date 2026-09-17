#!/usr/bin/env python3
"""
Parser de tickets Mercadona (factura simplificada, PDF con texto).

parse_ticket(path) -> dict con:
  factura_id, fecha (ISO), tienda, direccion, cp, total, forma_pago,
  lineas: [ {cantidad, descripcion, precio_unit, importe} ],
  iva: [ {tipo, base, cuota} ]

Diseñado para la modalidad "una factura por compra" (tienda física).
Los productos por peso (fruta/verdura: "0,930 kg  1,99 €/kg") usan otro
formato de línea; se detectan y marcan para revisión (ver LINEA_PESO).
"""

import re
from datetime import datetime
from pathlib import Path

import pdfplumber

# ---- Expresiones regulares --------------------------------------------------

RE_FACTURA = re.compile(r"FACTURA SIMPLIFICADA:\s*([\d\-]+)")
RE_FECHA = re.compile(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})")
RE_CP_CIUDAD = re.compile(r"^(\d{5})\s+(.+)$")
RE_TOTAL = re.compile(r"^TOTAL\s*\(€\)\s+([\d.,]+)")
RE_FORMA_PAGO = re.compile(r"^(TARJETA BANCARIA|EFECTIVO|TARJETA)\s+([\d.,]+)")

# Línea de producto normal:
#   <cant> <descripcion> [<p.unit>] <importe>
RE_LINEA = re.compile(
    r"^(\d+)\s+(.+?)\s+(?:(\d+,\d{2})\s+)?(\d+,\d{2})$"
)
# Fila de IVA: "21% 12,44 2,61"
RE_IVA = re.compile(r"^(\d+)%\s+([\d.,]+)\s+([\d.,]+)$")
# Producto por peso (segunda línea): "0,930 kg 1,99 1,85" o con "€/kg"
RE_LINEA_PESO = re.compile(
    r"^([\d.,]+)\s*kg\s+([\d.,]+)(?:\s*€?/?kg)?\s+([\d.,]+)$", re.IGNORECASE
)

# Líneas que NO son productos aunque casen con algún patrón
STOP_DESCRIPCIONES = {"IVA", "TOTAL", "BASE IMPONIBLE", "CUOTA"}


def _num(s):
    """'1.234,56' -> 1234.56"""
    return float(s.replace(".", "").replace(",", "."))


def parse_ticket(path):
    path = Path(path)
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    out = {
        "factura_id": None,
        "fecha": None,
        "tienda": None,
        "direccion": None,
        "cp": None,
        "ciudad": None,
        "total": None,
        "forma_pago": None,
        "lineas": [],
        "iva": [],
        "source_file": path.name,
    }

    en_productos = False       # entre cabecera "Descripción..." y "TOTAL"
    linea_pendiente = None     # para productos por peso (desc en línea previa)
    prev = None                # línea anterior (para capturar la calle)

    for ln in lines:
        # --- Cabecera / metadatos ---
        if out["factura_id"] is None:
            m = RE_FACTURA.search(ln)
            if m:
                out["factura_id"] = m.group(1)
                continue
        if out["fecha"] is None:
            m = RE_FECHA.search(ln)
            if m:
                dt = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%d/%m/%Y %H:%M")
                out["fecha"] = dt.isoformat()
                continue
        if ln.startswith("MERCADONA") and out["tienda"] is None:
            out["tienda"] = ln
            continue
        if out["cp"] is None:
            m = RE_CP_CIUDAD.match(ln)
            if m:
                out["cp"], out["ciudad"] = m.group(1), m.group(2)
                if prev and out["direccion"] is None:
                    out["direccion"] = prev  # la calle es la línea anterior
                prev = ln
                continue

        # --- Delimitadores de la zona de productos ---
        if ln.startswith("Descripción"):
            en_productos = True
            continue

        m = RE_TOTAL.match(ln)
        if m:
            out["total"] = _num(m.group(1))
            en_productos = False
            continue

        m = RE_FORMA_PAGO.match(ln)
        if m and out["forma_pago"] is None:
            out["forma_pago"] = m.group(1)
            continue

        m = RE_IVA.match(ln)
        if m:
            out["iva"].append(
                {"tipo": int(m.group(1)), "base": _num(m.group(2)), "cuota": _num(m.group(3))}
            )
            continue

        # --- Productos ---
        if en_productos:
            # ¿segunda línea de un producto por peso?
            if linea_pendiente is not None:
                mp = RE_LINEA_PESO.match(ln)
                if mp:
                    peso, punit, importe = map(_num, mp.groups())
                    out["lineas"].append({
                        "cantidad": peso,
                        "descripcion": linea_pendiente,
                        "precio_unit": punit,
                        "importe": importe,
                        "por_peso": True,
                    })
                    linea_pendiente = None
                    continue
                linea_pendiente = None  # no encajó: descartamos el pendiente

            m = RE_LINEA.match(ln)
            if m:
                cant = int(m.group(1))
                desc = m.group(2).strip()
                if desc.upper() in STOP_DESCRIPCIONES:
                    continue
                punit = _num(m.group(3)) if m.group(3) else None
                importe = _num(m.group(4))
                if punit is None:
                    punit = round(importe / cant, 4) if cant else importe
                out["lineas"].append({
                    "cantidad": cant,
                    "descripcion": desc,
                    "precio_unit": punit,
                    "importe": importe,
                    "por_peso": False,
                })
                continue

            # línea sin precio final: cabecera de producto por peso
            # p.ej. "1 MELON PIEL SAPO"  (el kg y el €/kg van en la línea siguiente)
            mh = re.match(r"^\d+\s+(.+)$", ln)
            if mh and not re.search(r"\d+,\d{2}$", ln):
                linea_pendiente = mh.group(1).strip()
            elif re.match(r"^[A-ZÁÉÍÓÚÑ]", ln):
                linea_pendiente = ln

        prev = ln

    return out


if __name__ == "__main__":
    import json
    import sys
    data = parse_ticket(sys.argv[1])
    print(json.dumps(data, indent=2, ensure_ascii=False))
