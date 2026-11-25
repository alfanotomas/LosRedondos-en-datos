{#
    Registra los JSON crudos (capa bronce) como vistas temporales globales,
    así dbt los puede leer como sources desde `global_temp`.

    Por qué vistas y no tablas: el catálogo por defecto es Iceberg, que no
    admite tablas sobre archivos JSON. Las vistas viven lo que dura la sesión
    de Spark, por eso se crean al arrancar cada corrida (on-run-start).

    Cada archivo es un JSON de varias líneas (indent=2), de ahí multiLine.
    Cada archivo es una fila: una extracción, con su fecha en `extraido_el`.
#}
{% macro registrar_fuentes_crudas() %}
    {% set carpeta = env_var('RUTA_DATOS', '/home/airflow/data') ~ '/raw' %}
    {# vista: patrón de archivos. El "_2*" deja afuera lastfm_toptracks_p1_... #}
    {% set fuentes = {
        'lastfm_toptracks': 'lastfm_toptracks_2*.json',
        'musicbrainz_recordings': 'musicbrainz_recordings_2*.json',
        'musicbrainz_discos_estudio': 'musicbrainz_discos_estudio_2*.json',
    } %}
    {% for vista, patron in fuentes.items() %}
        {% call statement('registrar_' ~ vista) %}
            create or replace global temporary view {{ vista }}
            using json
            options (path '{{ carpeta }}/{{ patron }}', multiLine 'true')
        {% endcall %}
    {% endfor %}
{% endmacro %}
