-- Popularidad en Last.fm: una fila por canción de estudio y por extracción.
-- Guarda todas las fechas, así se puede ver la evolución si el DAG corre a diario.
--
-- Una canción puede tener varias entradas en Last.fm (ej. Soga de Caín tiene 3).
-- Criterio del proyecto:
--   reproducciones = suma de todas las entradas (cada una es gente que la escuchó)
--   oyentes = la entrada principal (los oyentes no se pueden sumar: la misma
--             persona puede estar en varias entradas y se contaría dos veces)

with lastfm as (

    select * from {{ ref('stg_lastfm_canciones') }}

),

alias as (

    select * from {{ ref('alias_canciones') }}
    where es_cancion

)

select
    concat(cast(lastfm.fecha_extraccion as string), '|', cancion.cancion_id) as popularidad_id,
    lastfm.fecha_extraccion,
    cancion.cancion_id,
    sum(lastfm.reproducciones) as reproducciones,
    max(lastfm.oyentes) as oyentes,
    count(*) as entradas_lastfm
from lastfm
inner join alias
    on lastfm.titulo_normalizado = alias.titulo_normalizado
inner join {{ ref('dim_cancion') }} as cancion
    on alias.cancion = cancion.cancion_id
group by lastfm.fecha_extraccion, cancion.cancion_id
