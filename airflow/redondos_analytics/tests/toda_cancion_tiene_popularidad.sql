-- Test de calidad: cada canción de estudio tiene que tener datos de Last.fm
-- en la última extracción. Si devuelve filas, falta alguna (por ejemplo, un
-- título nuevo que el seed de alias todavía no reconoce) y el test falla.

select cancion.cancion_id
from {{ ref('dim_cancion') }} as cancion
left join {{ ref('fct_popularidad') }} as popularidad
    on cancion.cancion_id = popularidad.cancion_id
    and popularidad.fecha_extraccion = (
        select max(fecha_extraccion) from {{ ref('fct_popularidad') }}
    )
where popularidad.cancion_id is null
