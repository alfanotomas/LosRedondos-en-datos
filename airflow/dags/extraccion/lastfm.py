"""Extracción de Last.fm: canciones del artista con reproducciones y oyentes.

Guarda en data/raw/lastfm_toptracks_<fecha>.json todas las páginas de
artist.getTopTracks. Se bajan todas (no solo la primera) porque el criterio
del proyecto suma las reproducciones de todas las entradas de cada canción.

Uso manual, desde airflow/dags:  python -m extraccion.lastfm
"""

import os

from extraccion.comun import guardar_json, hoy, pedir_json

URL = "https://ws.audioscrobbler.com/2.0/"
MBID_REDONDOS = "956301d0-4b3c-4ffc-9898-b39305d25112"
TAMANO_PAGINA = 1000  # máximo que aceptó la API en la prueba del 2026-11-23


def pedir_pagina(pagina):
    """Una página del top de canciones del artista."""
    params = {
        "method": "artist.getTopTracks",
        "mbid": MBID_REDONDOS,
        "api_key": os.environ["LASTFM_API_KEY"],
        "format": "json",
        "limit": TAMANO_PAGINA,
        "page": pagina,
    }
    return pedir_json(URL, params)["toptracks"]


def extraer_top_tracks():
    """Baja todas las páginas y las guarda crudas en un solo archivo."""
    primera = pedir_pagina(1)
    total = int(primera["@attr"]["total"])
    total_paginas = int(primera["@attr"]["totalPages"])

    canciones = list(primera["track"])
    for pagina in range(2, total_paginas + 1):
        canciones += pedir_pagina(pagina)["track"]

    ruta = guardar_json(
        "lastfm_toptracks",
        {"extraido_el": hoy(), "total": total, "canciones": canciones},
    )
    print(f"{len(canciones)} de {total} canciones ({total_paginas} páginas) -> {ruta}")
    return ruta


if __name__ == "__main__":
    extraer_top_tracks()
