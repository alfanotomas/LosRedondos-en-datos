-- Los 10 discos de estudio, una fila por disco.
-- Sale de la última extracción: el catálogo no cambia de un día al otro.

with temas as (

    select *
    from {{ ref('stg_discos_temas') }}
    where fecha_extraccion = (select max(fecha_extraccion) from {{ ref('stg_discos_temas') }})

)

select
    disco_id,
    disco,
    disco_desambiguacion,
    -- Nombre para el dashboard: distingue las dos partes de Lobo suelto.
    case
        when disco_desambiguacion is null then disco
        else concat(disco, ' (', disco_desambiguacion, ')')
    end as nombre_mostrar,
    anio,
    concat(cast(floor(anio / 10) * 10 as int), 's') as decada,
    count(*) as cantidad_temas
from temas
group by disco_id, disco, disco_desambiguacion, anio
