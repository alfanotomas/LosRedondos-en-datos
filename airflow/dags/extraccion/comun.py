"""Funciones compartidas por los extractores: rutas, fecha, pedidos y guardado."""

import json
import os
import time
from datetime import date
from pathlib import Path

import requests

RAIZ_PROYECTO = Path(__file__).resolve().parents[3]

try:
    from dotenv import load_dotenv
except ImportError:  # En el contenedor las variables llegan por docker-compose.
    pass
else:
    load_dotenv(RAIZ_PROYECTO / ".env")

# En el contenedor RUTA_DATOS viene de docker-compose; en Windows, data/ del repo.
RUTA_DATOS = Path(os.environ.get("RUTA_DATOS", RAIZ_PROYECTO / "data"))
CARPETA_RAW = RUTA_DATOS / "raw"
CARPETA_CACHE = CARPETA_RAW / "_cache"
ESPERAS_REINTENTO = (5, 15, 45)  # segundos de espera ante 429 o 5xx


def hoy():
    """Fecha de extracción en formato AAAA-MM-DD."""
    return date.today().isoformat()


def pedir_json(url, params, headers=None, pausa=1.0):
    """GET que reintenta si el servidor está saturado (429 o 5xx).

    Tras cada respuesta buena espera `pausa` segundos, para respetar los
    límites de las APIs. Los errores muestran solo `url`, sin los parámetros,
    para que la clave de Last.fm nunca quede en un log.
    """
    for espera in (*ESPERAS_REINTENTO, None):
        try:
            respuesta = requests.get(url, params=params, headers=headers, timeout=60)
        except requests.RequestException as error:
            raise RuntimeError(
                f"Fallo de conexión con {url}: {type(error).__name__}"
            ) from None

        estado = respuesta.status_code
        if estado != 429 and estado < 500:
            if estado >= 400:
                raise RuntimeError(f"HTTP {estado} en {url}")
            time.sleep(pausa)
            return respuesta.json()
        if espera is None:
            raise RuntimeError(f"HTTP {estado} en {url} después de reintentar")
        print(f"HTTP {estado}: reintento en {espera} s")
        time.sleep(espera)


def guardar_json(nombre, datos, carpeta=CARPETA_RAW):
    """Guarda `datos` en <carpeta>/<nombre>_<fecha>.json y devuelve la ruta."""
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{nombre}_{hoy()}.json"
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2)
    return ruta


def con_cache(nombre, pedir):
    """Devuelve la respuesta guardada hoy con ese nombre o la pide y la guarda.

    Sirve para retomar una extracción cortada sin repetir pedidos.
    """
    ruta = CARPETA_CACHE / f"{nombre}_{hoy()}.json"
    if ruta.exists():
        with open(ruta, encoding="utf-8") as archivo:
            return json.load(archivo)
    datos = pedir()
    guardar_json(nombre, datos, CARPETA_CACHE)
    return datos
