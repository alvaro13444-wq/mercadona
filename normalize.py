#!/usr/bin/env python3
"""
Normalización de nombres de producto.

Objetivo: poder seguir el MISMO producto a lo largo del tiempo aunque
Mercadona varíe ligeramente la descripción del ticket. Sin esto, la
evolución de precios no se puede calcular de forma fiable.

Estrategia:
  1) Limpieza básica (mayúsculas, acentos, espacios, ruido).
  2) Diccionario de alias editable (ALIAS): mapea variantes -> nombre canónico.

Amplía ALIAS a mano conforme veas variantes en tus tickets. Es la única
parte que requiere criterio humano.
"""

import re
import unicodedata

# variante_en_ticket (ya normalizada) -> nombre canónico
ALIAS = {
    "ROLLO COCINA GIGANTE": "PAPEL COCINA",
    "PAPEL COCINA GIGANTE": "PAPEL COCINA",
    "YOG 0%0% LIMON": "YOGUR 0% LIMON",
    "LEJIA NORMAL": "LEJIA",
}


def _sin_acentos(s):
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def normaliza(desc):
    s = _sin_acentos(desc).upper()
    s = re.sub(r"[^\w%\s]", " ", s)   # fuera puntuación (conserva %)
    s = re.sub(r"\s+", " ", s).strip()
    return ALIAS.get(s, s)
