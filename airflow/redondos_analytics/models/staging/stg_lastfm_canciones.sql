-- Una fila por entrada de Last.fm y por extracción.
-- Una misma canción puede tener varias entradas (títulos escritos distinto);
-- se juntan más adelante, en marts, con el seed de alias.

with extracciones as (

    -- El JSON crudo es una fila por archivo con todas las canciones en un
    -- array: explode lo abre en una fila por canción.
    select
        extraido_el,
        explode(canciones) as cancion
    from {{ source('crudo', 'lastfm_toptracks') }}

)

select
    cast(extraido_el as date) as fecha_extraccion,
    cast(cancion.`@attr`.rank as int) as puesto,
    cancion.name as titulo_original,
    {{ normalizar_titulo('cancion.name') }} as titulo_normalizado,
    -- La API devuelve los números como texto.
    cast(cancion.playcount as bigint) as reproducciones,
    cast(cancion.listeners as bigint) as oyentes,
    nullif(cancion.mbid, '') as mbid_lastfm,
    cancion.url
from extracciones
