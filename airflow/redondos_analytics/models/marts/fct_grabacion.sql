-- Una fila por grabación de MusicBrainz de una canción de estudio.
-- Contando filas por canción sale la métrica "versiones registradas".
-- No separa estudio / vivo: la etiqueta "live" falta en muchas grabaciones,
-- por eso marcada_en_vivo es solo un mínimo.

with grabaciones as (

    select *
    from {{ ref('stg_musicbrainz_grabaciones') }}
    where fecha_extraccion = (select max(fecha_extraccion) from {{ ref('stg_musicbrainz_grabaciones') }})

),

alias as (

    select * from {{ ref('alias_canciones') }}
    where es_cancion

)

select
    grabaciones.grabacion_id,
    cancion.cancion_id,
    grabaciones.titulo_original,
    grabaciones.desambiguacion,
    grabaciones.marcada_en_vivo,
    grabaciones.anio_primera_edicion,
    grabaciones.duracion_segundos
from grabaciones
inner join alias
    on grabaciones.titulo_normalizado = alias.titulo_normalizado
-- El inner join con dim_cancion deja solo las canciones de estudio.
inner join {{ ref('dim_cancion') }} as cancion
    on alias.cancion = cancion.cancion_id
