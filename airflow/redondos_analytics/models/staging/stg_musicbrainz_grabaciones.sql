-- Una fila por grabación (recording) de MusicBrainz y por extracción.
-- Una canción tiene varias grabaciones: la de estudio, las en vivo, remasters.

with extracciones as (

    select
        extraido_el,
        explode(recordings) as grabacion
    from {{ source('crudo', 'musicbrainz_recordings') }}

)

select
    cast(extraido_el as date) as fecha_extraccion,
    grabacion.id as grabacion_id,
    grabacion.title as titulo_original,
    {{ normalizar_titulo('grabacion.title') }} as titulo_normalizado,
    nullif(grabacion.disambiguation, '') as desambiguacion,
    -- Ojo: solo es "true" si MusicBrainz la etiquetó como live. Muchas
    -- grabaciones en vivo vienen sin etiqueta, así que esto es un mínimo.
    coalesce(lower(grabacion.disambiguation) like 'live%', false) as marcada_en_vivo,
    -- Viene como AAAA, AAAA-MM o AAAA-MM-DD; se deja como texto y se saca el año.
    nullif(grabacion.`first-release-date`, '') as fecha_primera_edicion,
    cast(left(nullif(grabacion.`first-release-date`, ''), 4) as int) as anio_primera_edicion,
    -- MusicBrainz da la duración en milisegundos.
    round(grabacion.length / 1000) as duracion_segundos
from extracciones
