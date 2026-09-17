#!/usr/bin/env python3
"""
Ingesta Mercadona para la nube.

  1) Entra a Gmail por IMAP y descarga los PDF de factura recientes.
  2) Los parsea con parser.py (validado con tickets reales).
  3) Los guarda en Supabase (Postgres), idempotente por nº de factura.

Lo ejecuta GitHub Actions varias veces al día. Variables de entorno
(definidas como GitHub Secrets):

  GMAIL_USER            tu_correo@gmail.com
  GMAIL_APP_PASS        contraseña de aplicación de Google (requiere 2FA)
  SUPABASE_URL          https://xxxx.supabase.co
  SUPABASE_SERVICE_KEY  clave service_role del proyecto Supabase
  MERCADONA_QUERY       (opcional) búsqueda Gmail; por defecto la de abajo
"""

import email
import imaplib
import os
import tempfile

from supabase import create_client

from normalize import normaliza
from parser import parse_ticket

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASS = os.environ["GMAIL_APP_PASS"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
# newer_than:30d mantiene cada ejecución ligera; con varias pasadas al día
# hay solapamiento de sobra para no perder ningún ticket.
QUERY = os.environ.get(
    "MERCADONA_QUERY",
    "from:mercadona.com has:attachment filename:pdf newer_than:30d",
)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)


def ids_existentes():
    rows = sb.table("tickets").select("factura_id").execute().data
    return {r["factura_id"] for r in rows}


def descargar_pdfs():
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(GMAIL_USER, GMAIL_APP_PASS)
    imap.select("INBOX")
    typ, data = imap.search(None, "X-GM-RAW", f'"{QUERY}"')
    pdfs = []
    if typ == "OK":
        for num in data[0].split():
            _, md = imap.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(md[0][1])
            for part in msg.walk():
                fn = part.get_filename()
                if fn and fn.lower().endswith(".pdf"):
                    payload = part.get_payload(decode=True)
                    if payload:
                        pdfs.append((fn, payload))
    imap.logout()
    return pdfs


def main():
    conocidos = ids_existentes()
    vistos = set()
    nuevos = 0

    for fn, payload in descargar_pdfs():
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tf:
            tf.write(payload)
            tf.flush()
            try:
                d = parse_ticket(tf.name)
            except Exception as e:
                print(f"! error parseando {fn}: {e}")
                continue

        fid = d.get("factura_id")
        if not fid or fid in conocidos or fid in vistos:
            continue

        sb.table("tickets").insert({
            "factura_id": fid,
            "fecha": d["fecha"],
            "tienda": d.get("tienda"),
            "direccion": d.get("direccion"),
            "cp": d.get("cp"),
            "ciudad": d.get("ciudad"),
            "total": d.get("total"),
            "forma_pago": d.get("forma_pago"),
            "source_file": fn,
        }).execute()

        rows = [{
            "factura_id": fid,
            "fecha": d["fecha"],
            "descripcion": l["descripcion"],
            "producto_norm": normaliza(l["descripcion"]),
            "cantidad": l["cantidad"],
            "precio_unit": l["precio_unit"],
            "importe": l["importe"],
            "por_peso": bool(l.get("por_peso")),
        } for l in d["lineas"]]
        if rows:
            sb.table("lineas").insert(rows).execute()

        vistos.add(fid)
        nuevos += 1
        print(f"+ {fid}  {d['fecha'][:10]}  {d['total']} €")

    print(f"Cargados {nuevos} tickets nuevos.")


if __name__ == "__main__":
    main()
