"""Extracción de MusicBrainz: recordings del artista y discos de estudio.

Guarda en data/raw/:
- musicbrainz_recordings_<fecha>.json: todas las grabaciones (estudio y vivo).
- musicbrainz_release_groups_<fecha>.json: todos los álbumes del artista.
- musicbrainz_discos_estudio_<fecha>.json: los discos de estudio y sus temas.

Uso manual, desde airflow/dags:  python -m extraccion.musicbrainz
"""

import os

from extraccion.comun import con_cache, guardar_json, hoy, pedir_json

BASE_URL = "https://musicbrainz.org/ws/2"
MBID_REDONDOS = "956301d0-4b3c-4ffc-9898-b39305d25112"
TAMANO_PAGINA = 100


def pedir(ruta, params):
    """GET a MusicBrainz con el User-Agent propio (la API lo exige)."""
    headers = {"User-Agent": os.environ["MUSICBRAINZ_USER_AGENT"]}
    return pedir_json(f"{BASE_URL}/{ruta}", {**params, "fmt": "json"}, headers)


def pagina_de_recordings(offset):
    """Una página de 100 recordings, con caché por si la extracción se corta."""
    return con_cache(
        f"musicbrainz_recordings_offset{offset}",
        lambda: pedir(
            "recording",
            {"artist": MBID_REDONDOS, "limit": TAMANO_PAGINA, "offset": offset},
        ),
    )


def extraer_recordings():
    """Baja todos los recordings del artista y los guarda crudos."""
    primera = pagina_de_recordings(0)
    total = primera["recording-count"]
    recordings = list(primera["recordings"])
    for offset in range(TAMANO_PAGINA, total, TAMANO_PAGINA):
        recordings += pagina_de_recordings(offset)["recordings"]

    if len(recordings) != total:
        print(f"Aviso: la API dice {total} recordings y se bajaron {len(recordings)}")
    ruta = guardar_json(
        "musicbrainz_recordings",
        {"extraido_el": hoy(), "total": total, "recordings": recordings},
    )
    print(f"{len(recordings)} recordings -> {ruta}")
    return ruta


def discos_de_estudio():
    """Álbumes sin subtipo (sin Live, Compilation, etc.), ordenados por fecha.

    Solo es repetido si coinciden título y desambiguación: las dos entradas
    de "Lobo suelto - Cordero atado" (Naranja y Gris) tienen temas distintos.
    """
    datos = pedir(
        "release-group", {"artist": MBID_REDONDOS, "type": "album", "limit": 100}
    )
    guardar_json(
        "musicbrainz_release_groups",
        {"extraido_el": hoy(), "release_groups": datos["release-groups"]},
    )

    estudio = [
        grupo
        for grupo in datos["release-groups"]
        if grupo.get("primary-type") == "Album" and not grupo.get("secondary-types")
    ]
    estudio.sort(key=lambda grupo: grupo.get("first-release-date", ""))

    sin_repetir = {}
    for grupo in estudio:
        clave = (grupo["title"], grupo.get("disambiguation", ""))
        if clave in sin_repetir:
            print(f"Disco repetido, se descarta: {grupo['title']} ({grupo['id']})")
        else:
            sin_repetir[clave] = grupo
    return list(sin_repetir.values())


def temas_del_disco(grupo):
    """Temas de una edición del disco (la primera que devuelve MusicBrainz)."""
    datos = con_cache(
        f"musicbrainz_disco_{grupo['id']}",
        lambda: pedir(
            "release", {"release-group": grupo["id"], "inc": "recordings", "limit": 1}
        ),
    )
    edicion = datos["releases"][0]
    return {
        "disco": grupo["title"],
        "desambiguacion": grupo.get("disambiguation", ""),
        "fecha": grupo.get("first-release-date"),
        "release_group_id": grupo["id"],
        "release_id": edicion["id"],
        "edicion": edicion["title"],
        "temas": [
            tema["title"] for medio in edicion["media"] for tema in medio["tracks"]
        ],
    }


def extraer_discos_estudio():
    """Baja los discos de estudio con sus temas y los guarda crudos."""
    discos = [temas_del_disco(grupo) for grupo in discos_de_estudio()]
    ruta = guardar_json(
        "musicbrainz_discos_estudio", {"extraido_el": hoy(), "discos": discos}
    )
    cantidad_temas = sum(len(disco["temas"]) for disco in discos)
    print(f"{len(discos)} discos de estudio, {cantidad_temas} temas -> {ruta}")
    return ruta


def main():
    extraer_recordings()
    extraer_discos_estudio()


if __name__ == "__main__":
    main()
