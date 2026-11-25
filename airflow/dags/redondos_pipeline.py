"""Pipeline de los Redondos: baja los datos de las APIs y los transforma con dbt.

    extraer_mb_recordings >> extraer_mb_discos_estudio ┐
                                                       ├> dbt_seed >> dbt_run
    extraer_lastfm ────────────────────────────────────┘     >> dbt_test >> dbt_docs_gen
                                                              >> generar_dashboard

Las dos tareas de MusicBrainz van en fila (no en paralelo) porque la API
permite una consulta por segundo. Last.fm es otra API, así que corre al mismo
tiempo.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, task

# Al ejecutar una tarea, Airflow 3 no suma la carpeta de DAGs a los lugares
# donde Python busca módulos, y no encontraría el paquete `extraccion`.
CARPETA_DAGS = str(Path(__file__).resolve().parent)
if CARPETA_DAGS not in sys.path:
    sys.path.insert(0, CARPETA_DAGS)

DBT = "/home/airflow/.venv/bin/dbt"
PYTHON = "/home/airflow/.venv/bin/python"
PROYECTO_DBT = "/home/airflow/redondos_analytics"
OPCIONES_DBT = f"--project-dir {PROYECTO_DBT} --profiles-dir {PROYECTO_DBT}"

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    dag_id="redondos_pipeline",
    description="Extrae MusicBrainz y Last.fm y arma el modelo con dbt",
    schedule="@daily",  # una foto de popularidad por día
    start_date=datetime(2026, 11, 1),
    catchup=False,  # no correr los días pasados
    max_active_runs=1,
    default_args=default_args,
    tags=["redondos", "musicbrainz", "lastfm", "dbt"],
)
def redondos_pipeline():
    # Los imports van adentro de cada tarea: Airflow lee este archivo cada
    # pocos segundos y así no carga requests ni los extractores cada vez.

    @task
    def extraer_mb_recordings():
        from extraccion.musicbrainz import extraer_recordings

        return str(extraer_recordings())

    @task
    def extraer_mb_discos_estudio():
        from extraccion.musicbrainz import extraer_discos_estudio

        return str(extraer_discos_estudio())

    @task
    def extraer_lastfm():
        from extraccion.lastfm import extraer_top_tracks

        return str(extraer_top_tracks())

    def dbt(comando, task_id):
        return BashOperator(
            task_id=task_id,
            bash_command=f"{DBT} {comando} {OPCIONES_DBT}",
        )

    dbt_seed = dbt("seed", "dbt_seed")
    dbt_run = dbt("run", "dbt_run")
    dbt_test = dbt("test", "dbt_test")
    dbt_docs_gen = dbt("docs generate", "dbt_docs_gen")

    # Lee los marts y guarda redondos_analytics/dashboard.html.
    generar_dashboard = BashOperator(
        task_id="generar_dashboard",
        bash_command=f"{PYTHON} {PROYECTO_DBT}/dashboard.py",
    )

    musicbrainz = extraer_mb_recordings() >> extraer_mb_discos_estudio()
    [musicbrainz, extraer_lastfm()] >> dbt_seed
    dbt_seed >> dbt_run >> dbt_test >> dbt_docs_gen >> generar_dashboard


redondos_pipeline()
