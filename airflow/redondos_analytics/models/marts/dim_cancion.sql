-- Las canciones de estudio, una fila por canción. Es el alcance del análisis:
-- lo que no está acá (temas solo en vivo, medleys, basura) queda afuera.

with temas as (

    select *
    from {{ ref('stg_discos_temas') }}
    where fecha_extraccion = (select max(fecha_extraccion) from {{ ref('stg_discos_temas') }})

),

alias as (

    select * from {{ ref('alias_canciones') }}

)

select
    -- Clave: el nombre canónico del seed (el título de estudio, normalizado).
    coalesce(alias.cancion, temas.titulo_normalizado) as cancion_id,
    -- Nombre para el dashboard, con tildes y mayúsculas como en el disco.
    temas.titulo_original as nombre_mostrar,
    temas.disco_id,
    temas.numero_tema
from temas
left join alias
    on temas.titulo_normalizado = alias.titulo_normalizado
