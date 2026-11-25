# Proyecto - Redondos

Pipeline de datos sobre la discografía de Patricio Rey y sus Redonditos de Ricota.

> Borrador. Se completa a medida que avanza el proyecto.

## Pregunta que responde

¿Cuáles son las canciones y discos más escuchados de los Redondos, y las canciones con más versiones grabadas (estudio y vivo) son también las más escuchadas?

## Arquitectura

Arquitectura de 3 saltos, orquestada con Airflow, transformada con dbt sobre Spark.

1. **Cruda:** datos tal cual llegan de MusicBrainz y Last.fm.
2. **Limpia (`staging`):** títulos y fechas normalizados, duplicados resueltos.
3. **Modelo final (`marts`):** `dim_disco`, `dim_cancion`, `fct_grabacion`, `fct_popularidad`.

(Pendiente: diagrama.)

## Fuentes de datos

- **MusicBrainz:** catálogo (discos, grabaciones, fechas).
- **Last.fm:** reproducciones y oyentes.

## Limitaciones de los datos

- Las reproducciones de Last.fm son una muestra de sus usuarios, no el total real.
- Las "versiones registradas" en MusicBrainz no equivalen a las veces que se tocó una canción en vivo.

(Pendiente: completar.)

## Cómo ejecutarlo

1. Copiar `.env.example` como `.env` y completar la clave de Last.fm.
2. `docker compose up -d --build` (la primera vez tarda, descarga Spark y Airflow).
3. Airflow en http://localhost:8080 y Jupyter en http://localhost:8888.

(Pendiente: pasos finales.)
