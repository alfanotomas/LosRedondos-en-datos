-- Una fila por tema de cada disco de estudio y por extracción.
-- Es la lista "oficial" de canciones contra la que se cruzan las otras fuentes.

with discos as (

    select
        extraido_el,
        explode(discos) as disco
    from {{ source('crudo', 'musicbrainz_discos_estudio') }}

),

temas as (

    -- posexplode además de abrir la lista devuelve la posición (desde 0),
    -- que sirve como número de tema.
    select
        extraido_el,
        disco,
        posexplode(disco.temas) as (posicion, tema)
    from discos

)

select
    cast(extraido_el as date) as fecha_extraccion,
    disco.release_group_id as disco_id,
    disco.disco as disco,
    -- Solo Lobo suelto - Cordero atado la usa ("Naranja" / "Gris").
    nullif(disco.desambiguacion, '') as disco_desambiguacion,
    -- La fecha viene como AAAA o AAAA-MM-DD; para el análisis alcanza el año.
    cast(left(disco.fecha, 4) as int) as anio,
    posicion + 1 as numero_tema,
    tema as titulo_original,
    {{ normalizar_titulo('tema') }} as titulo_normalizado
from temas
