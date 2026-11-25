"""Dashboard del proyecto: lee los marts de dbt y guarda una página HTML con Plotly.

Responde la pregunta central: qué canciones y discos de los Redondos son los más
escuchados en Last.fm, y si las canciones con más versiones grabadas (según
MusicBrainz) son también las más escuchadas.

La página tiene modo claro y oscuro: arranca según la configuración del sistema
y se puede cambiar con el botón del encabezado. Los gráficos se arman acá con
los colores del modo claro y un script de la página los repinta al cambiar.

Uso (adentro del contenedor): python /home/airflow/redondos_analytics/dashboard.py
Lo corre la última tarea del DAG, generar_dashboard.
"""

import html
import json
import textwrap
from pathlib import Path

import plotly.graph_objects as go
from plotly.offline import get_plotlyjs_version
from pyspark.sql import SparkSession

CARPETA = Path(__file__).resolve().parent
SALIDA = CARPETA / "dashboard.html"
LOGO = "assets/logo.png"  # relativo al HTML
# Tapas de los discos: se cargan del Cover Art Archive (el archivo de tapas de
# MusicBrainz) con el id de cada disco. No se guardan copias en el repo.
TAPA = "https://coverartarchive.org/release-group/{}/front-250"

# Colores de la banda: rojo, blanco y negro. Las dos épocas son rojo contra
# neutro (negro en modo claro, blanco en modo oscuro): se distinguen bien con
# daltonismo y tienen buen contraste en los dos modos (validado).
TEMAS = {
    "claro": {
        "fondo": "#ffffff",
        "tinta": "#0b0b0b",
        "tinta_suave": "#4a4a4a",
        "gris": "#8a8a8a",
        "grilla": "#e6e6e6",
        "eje": "#c8c8c8",
        "epocas": {"80": "#d4171b", "90": "#2b2b2b"},
    },
    "oscuro": {
        "fondo": "#121212",
        "tinta": "#f5f5f5",
        "tinta_suave": "#c8c8c8",
        "gris": "#8a8a8a",
        "grilla": "#2a2a2a",
        "eje": "#3a3a3a",
        "epocas": {"80": "#e5383b", "90": "#ecebe6"},
    },
}
CLARO = TEMAS["claro"]
EPOCAS = {"80": "Discos de los 80", "90": "Discos de los 90 y 2000"}
FUENTE = 'system-ui, -apple-system, "Segoe UI", sans-serif'

CONSULTA_CANCIONES = """
with ultima as (
    select max(fecha_extraccion) as fecha from redondos_db.fct_popularidad
),
versiones as (
    select
        cancion_id,
        count(*) as versiones,
        sum(cast(marcada_en_vivo as int)) as marcadas_en_vivo
    from redondos_db.fct_grabacion
    group by cancion_id
)
select
    c.nombre_mostrar as cancion,
    d.nombre_mostrar as disco,
    d.disco_id,
    d.anio,
    p.fecha_extraccion,
    p.reproducciones,
    p.oyentes,
    coalesce(v.versiones, 0) as versiones,
    coalesce(v.marcadas_en_vivo, 0) as marcadas_en_vivo
from redondos_db.fct_popularidad as p
inner join ultima on p.fecha_extraccion = ultima.fecha
inner join redondos_db.dim_cancion as c on p.cancion_id = c.cancion_id
inner join redondos_db.dim_disco as d on c.disco_id = d.disco_id
left join versiones as v on p.cancion_id = v.cancion_id
"""


# ---------------------------------------------------------------- utilidades


def miles(numero):
    """12345 -> '12.345' (separador de miles en castellano)."""
    return f"{numero:,.0f}".replace(",", ".")


def decimal(numero):
    """0.4712 -> '0,47'."""
    return f"{numero:.2f}".replace(".", ",")


def partir(texto, ancho=22):
    """Corta nombres largos en varias líneas para las etiquetas de los ejes."""
    return "<br>".join(textwrap.wrap(texto, ancho))


def epoca(anio):
    return "80" if anio < 1990 else "90"


def intensidad(r):
    if abs(r) < 0.3:
        return "débil"
    if abs(r) < 0.6:
        return "moderada"
    return "fuerte"


# ------------------------------------------------------------------ gráficos


def estilo(fig, titulo, subtitulo, alto):
    """Estilo común. Los colores son los del modo claro; el script de la página
    los cambia si el modo es oscuro."""
    fig.update_layout(
        title={
            "text": titulo,
            "subtitle": {"text": subtitulo, "font": {"color": CLARO["tinta_suave"]}},
            "x": 0,
            "xanchor": "left",
            "font": {"size": 18, "color": CLARO["tinta"]},
        },
        height=alto,
        autosize=True,
        template="none",
        font={"family": FUENTE, "size": 13, "color": CLARO["tinta_suave"]},
        paper_bgcolor=CLARO["fondo"],
        plot_bgcolor=CLARO["fondo"],
        separators=",.",  # coma decimal, punto de miles
        margin={"l": 10, "r": 70, "t": 110, "b": 50},
        legend={"orientation": "h", "y": 1.0, "yanchor": "bottom", "x": 0},
        hoverlabel={"font": {"family": FUENTE}},
        barcornerradius=4,
    )
    ejes = {"gridcolor": CLARO["grilla"], "linecolor": CLARO["eje"], "zeroline": False}
    fig.update_xaxes(**ejes)
    fig.update_yaxes(**ejes, automargin=True)
    return fig


def barras(datos, etiqueta, valor, titulo, subtitulo):
    """Barras horizontales de mayor a menor, coloreadas por época.

    Va una serie por época (así aparece la leyenda), apiladas en modo
    "relative": como cada barra está en una sola serie, no se superponen.
    """
    datos = datos.sort_values(valor)  # Plotly dibuja de abajo hacia arriba
    fig = go.Figure()
    for clave, nombre in EPOCAS.items():
        grupo = datos[datos.epoca == clave]
        fig.add_trace(
            go.Bar(
                x=grupo[valor],
                y=grupo[etiqueta],
                name=nombre,
                orientation="h",
                meta={"epoca": clave},
                marker={"color": CLARO["epocas"][clave], "line": {"width": 0}},
                width=0.62,
                text=[miles(v) for v in grupo[valor]],
                textposition="outside",
                textfont={"color": CLARO["tinta_suave"]},
                cliponaxis=False,
                customdata=grupo["hover"],
                hovertemplate="%{customdata}<extra></extra>",
            )
        )
    fig.update_layout(barmode="relative")
    fig.update_yaxes(
        showgrid=False, categoryorder="array", categoryarray=list(datos[etiqueta])
    )
    fig.update_xaxes(showticklabels=False, showgrid=False)
    estilo(fig, titulo, subtitulo, alto=130 + 40 * len(datos))
    # Sin eje de valores abajo: los números van en la punta de cada barra.
    return fig.update_layout(margin={"b": 10})


def grafico_top_canciones(canciones):
    top = canciones.nlargest(10, "reproducciones").copy()
    top["hover"] = [
        f"<b>{c}</b><br>{d} ({a})<br>{miles(r)} reproducciones<br>{miles(o)} oyentes"
        for c, d, a, r, o in zip(
            top.cancion, top.disco, top.anio, top.reproducciones, top.oyentes
        )
    ]
    return barras(
        top,
        "cancion",
        "reproducciones",
        "Las 10 canciones más escuchadas",
        "Reproducciones en Last.fm, sumando todas las formas en que aparece cada título",
    )


def tabla_discos(canciones):
    discos = (
        canciones.groupby(["disco_id", "disco", "anio"])
        .agg(reproducciones=("reproducciones", "sum"), temas=("cancion", "count"))
        .reset_index()
    )
    discos["promedio"] = discos.reproducciones / discos.temas
    discos["epoca"] = discos.anio.map(epoca)
    discos["etiqueta"] = discos.disco.map(partir)
    discos["hover"] = [
        f"<b>{d} ({a})</b><br>{miles(r)} reproducciones en total<br>"
        f"{t} temas · {miles(p)} por tema"
        for d, a, r, t, p in zip(
            discos.disco,
            discos.anio,
            discos.reproducciones,
            discos.temas,
            discos.promedio,
        )
    ]
    return discos


def graficos_discos(discos):
    total = barras(
        discos,
        "etiqueta",
        "reproducciones",
        "Discos: reproducciones totales",
        "Suma de sus temas (un disco con más temas suma más)",
    )
    promedio = barras(
        discos,
        "etiqueta",
        "promedio",
        "Discos: promedio por tema",
        "Corrige la diferencia en la cantidad de temas",
    )
    return total, promedio


def grafico_versiones(canciones):
    correlacion = canciones.versiones.corr(canciones.reproducciones)
    mediana_x = canciones.versiones.median()
    mediana_y = canciones.reproducciones.median()

    fig = go.Figure()
    for clave, nombre in EPOCAS.items():
        grupo = canciones[canciones.epoca == clave]
        fig.add_trace(
            go.Scatter(
                x=grupo.versiones,
                y=grupo.reproducciones,
                mode="markers",
                name=nombre,
                meta={"epoca": clave},
                marker={
                    "size": 11,
                    "color": CLARO["epocas"][clave],
                    "line": {"width": 2, "color": CLARO["fondo"]},
                },
                customdata=grupo[["cancion", "disco", "marcadas_en_vivo"]],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>%{customdata[1]}<br>"
                    "%{x} versiones registradas (al menos %{customdata[2]} en vivo)<br>"
                    "%{y:,.0f} reproducciones<extra></extra>"
                ),
            )
        )

    # Líneas de la mediana: parten el gráfico en 4 zonas. Mediana y no
    # promedio porque unas pocas canciones muy escuchadas tirarían el
    # promedio para arriba.
    linea = {"color": CLARO["gris"], "width": 1, "dash": "solid"}
    fig.add_vline(x=mediana_x, line=linea, layer="below", name="mediana")
    fig.add_hline(y=mediana_y, line=linea, layer="below", name="mediana")
    zonas = [
        (1, 1, "right", "top", "Muchas versiones<br>y muy escuchadas"),
        (1, 0, "right", "bottom", "Muchas versiones<br>pero poco escuchadas"),
    ]
    for x, y, xanchor, yanchor, texto in zonas:
        fig.add_annotation(
            x=x,
            y=y,
            xref="paper",
            yref="paper",
            xanchor=xanchor,
            yanchor=yanchor,
            align=xanchor,
            text=texto,
            showarrow=False,
            name="zona",
            font={"size": 12, "color": CLARO["gris"]},
        )

    # Nombres solo en las que se destacan: las 3 más escuchadas y las 3 con
    # más versiones.
    destacadas = (
        canciones.nlargest(3, "reproducciones")
        .merge(canciones.nlargest(3, "versiones"), how="outer")
        .drop_duplicates("cancion")
    )
    for fila in destacadas.itertuples():
        fig.add_annotation(
            x=fila.versiones,
            y=fila.reproducciones,
            text=fila.cancion,
            showarrow=False,
            xanchor="right" if fila.versiones > 15 else "left",
            xshift=-9 if fila.versiones > 15 else 9,
            name="etiqueta",
            font={"size": 12, "color": CLARO["tinta_suave"]},
        )

    fig.update_xaxes(title="Versiones registradas en MusicBrainz", dtick=2)
    fig.update_yaxes(title="Reproducciones en Last.fm", tickformat=",.0f")
    return estilo(
        fig,
        "¿Las canciones con más versiones son las más escuchadas?",
        f"Una canción por punto · correlación {decimal(correlacion)} "
        f"({intensidad(correlacion)}) · las líneas marcan la mediana",
        alto=620,
    )


# -------------------------------------------------------------------- página


def tarjetas(canciones, discos):
    top = canciones.loc[canciones.reproducciones.idxmax()]
    disco = discos.loc[discos.reproducciones.idxmax()]
    maximo = canciones.versiones.max()
    con_mas_versiones = canciones[canciones.versiones == maximo].cancion.tolist()
    correlacion = canciones.versiones.corr(canciones.reproducciones)

    if len(con_mas_versiones) == 1:
        detalle_versiones = f"{maximo} versiones registradas"
    else:
        detalle_versiones = (
            f"y {' y '.join(con_mas_versiones[1:])} · {maximo} versiones cada una"
        )
    datos = [
        (
            "Canción más escuchada",
            top.cancion,
            f"{miles(top.reproducciones)} reproducciones",
        ),
        (
            "Disco más escuchado",
            disco.disco,
            f"{miles(disco.reproducciones)} reproducciones · {miles(disco.promedio)} por tema",
        ),
        ("Más versiones grabadas", con_mas_versiones[0], detalle_versiones),
        (
            "Versiones vs. reproducciones",
            f"Correlación {decimal(correlacion)}",
            f"{intensidad(correlacion).capitalize()}: más versiones no garantiza más escuchas",
        ),
    ]
    return "".join(
        f"<div class='tarjeta'><div class='rotulo'>{html.escape(r)}</div>"
        f"<div class='valor'>{html.escape(v)}</div>"
        f"<div class='detalle'>{html.escape(d)}</div></div>"
        for r, v, d in datos
    )


def discografia(discos):
    """Las tapas de los 10 discos en orden cronológico, con su puesto en
    reproducciones totales."""
    puestos = discos.reproducciones.rank(ascending=False).astype(int)
    fichas = []
    for _, f in discos.assign(puesto=puestos).sort_values("anio").iterrows():
        clase = "puesto primero" if f.puesto == 1 else "puesto"
        fichas.append(
            "<figure class='disco'><div class='tapa'>"
            f"<img src='{TAPA.format(f.disco_id)}' loading='lazy' "
            f"alt='Tapa de {html.escape(f.disco, quote=True)}' "
            "onerror=\"this.style.display='none'\">"
            f"<span class='{clase}'>#{f.puesto}</span></div>"
            f"<figcaption><b>{html.escape(f.disco)}</b>{f.anio} · "
            f"{miles(f.reproducciones)} reprod.</figcaption></figure>"
        )
    return (
        "<h2>Discografía de estudio</h2>"
        "<p class='bajada'>En orden de salida · el número es su puesto por "
        "reproducciones totales · tapas del Cover Art Archive</p>"
        f"<div class='discos'>{''.join(fichas)}</div>"
    )


def tabla(canciones):
    filas = "".join(
        "<tr>"
        f"<td>{html.escape(f.cancion)}</td><td>{html.escape(f.disco)}</td>"
        f"<td class='n'>{f.anio}</td><td class='n'>{miles(f.reproducciones)}</td>"
        f"<td class='n'>{miles(f.oyentes)}</td><td class='n'>{f.versiones}</td>"
        f"<td class='n'>{f.marcadas_en_vivo}</td>"
        "</tr>"
        for f in canciones.sort_values("reproducciones", ascending=False).itertuples()
    )
    return (
        "<table><thead><tr><th>Canción</th><th>Disco</th><th class='n'>Año</th>"
        "<th class='n'>Reproducciones</th><th class='n'>Oyentes</th>"
        "<th class='n'>Versiones</th><th class='n'>Marcadas en vivo</th></tr></thead>"
        f"<tbody>{filas}</tbody></table>"
    )


def grafico_html(fig, id_div):
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,  # se carga una sola vez, en el <head>
        div_id=id_div,
        default_width="100%",
        config={"displayModeBar": False, "responsive": True},
    )


ESTILOS = (
    """
:root {
  color-scheme: light;
  --pagina: #f2f2f2; --fondo: #ffffff; --tinta: #0b0b0b; --tinta-suave: #4a4a4a;
  --gris: #8a8a8a; --grilla: #e6e6e6; --borde: rgba(0,0,0,.12);
  --rojo: #d4171b;
}
:root[data-tema="oscuro"] {
  color-scheme: dark;
  --pagina: #000000; --fondo: #121212; --tinta: #f5f5f5; --tinta-suave: #c8c8c8;
  --gris: #8a8a8a; --grilla: #2a2a2a; --borde: rgba(255,255,255,.12);
  --rojo: #e5383b;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-tema="claro"]) {
    color-scheme: dark;
    --pagina: #000000; --fondo: #121212; --tinta: #f5f5f5; --tinta-suave: #c8c8c8;
    --gris: #8a8a8a; --grilla: #2a2a2a; --borde: rgba(255,255,255,.12);
    --rojo: #e5383b;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--pagina); color: var(--tinta); font-family: FUENTE; }
/* Encabezado con el póster de fondo: un degradé negro desde la izquierda
   deja leer el título y el póster se ve a la derecha. */
header { color: #ffffff; border-bottom: 4px solid #d4171b;
  background:
    linear-gradient(90deg, #000 30%, rgba(0,0,0,.7) 55%, rgba(0,0,0,.15) 100%),
    url("POSTER") right 9% / 62% auto no-repeat, #000; }
.cabecera { max-width: 1200px; margin: 0 auto; padding: 20px 16px;
  min-height: 360px; display: flex; align-items: flex-end; gap: 20px; }
@media (max-width: 800px) {
  header { background:
    linear-gradient(0deg, #000 25%, rgba(0,0,0,.55) 100%),
    url("POSTER") center 22% / cover no-repeat, #000; }
  .cabecera { min-height: 280px; }
}
.cabecera img { width: 84px; height: 84px; flex: none; }
.cabecera .textos { flex: 1; min-width: 0; }
h1 { margin: 0; font-size: 40px; letter-spacing: -.01em; }
h1 span { color: #ff3b3b; }
.resumen { margin: 6px 0 0; color: #c3c2b7; }
#tema { flex: none; align-self: flex-start; background: rgba(0,0,0,.55); color: #f0efec; cursor: pointer;
  border: 1px solid rgba(255,255,255,.3); border-radius: 999px; padding: 8px 14px;
  font: inherit; font-size: 14px; }
#tema:hover { border-color: #ff3b3b; }
main { max-width: 1200px; margin: 0 auto; padding: 24px 16px 40px; }
.tarjetas { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(240px, 100%), 1fr));
  gap: 12px; margin-bottom: 16px; }
.tarjeta, section, details { background: var(--fondo); border: 1px solid var(--borde);
  border-radius: 10px; }
.tarjeta { padding: 16px 18px; border-top: 3px solid var(--rojo); }
.rotulo { font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--gris); }
.valor { font-size: 24px; font-weight: 700; margin: 6px 0 4px; line-height: 1.15; }
.detalle { color: var(--tinta-suave); font-size: 14px; }
section { padding: 12px 16px; margin-bottom: 16px; min-width: 0; }
.doble { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(420px, 100%), 1fr)); gap: 16px; }
.doble section { margin-bottom: 0; }
.doble + * { margin-top: 16px; }
details { padding: 16px; margin-bottom: 16px; }
summary { cursor: pointer; font-weight: 600; }
.tabla { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 14px; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--grilla); }
th { color: var(--gris); font-weight: 600; }
.n { text-align: right; font-variant-numeric: tabular-nums; }
.notas { color: var(--tinta-suave); font-size: 14px; line-height: 1.55; }
h2 { font-size: 18px; font-weight: 600; margin: 4px 0 2px; }
.bajada { color: var(--tinta-suave); font-size: 14px; margin: 0 0 14px; }
.discos { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }
@media (max-width: 800px) { .discos { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 480px) { .discos { grid-template-columns: repeat(2, 1fr); } }
.disco { margin: 0; }
.tapa { position: relative; aspect-ratio: 1; border-radius: 6px; overflow: hidden;
  background: #000; box-shadow: 0 1px 3px rgba(0,0,0,.3); }
.tapa img { width: 100%; height: 100%; object-fit: cover; display: block; }
.puesto { position: absolute; top: 6px; left: 6px; background: #000; color: #fff;
  font-size: 12px; font-weight: 700; padding: 2px 7px; border-radius: 999px;
  border: 1px solid rgba(255,255,255,.35); }
.puesto.primero { background: #d4171b; border-color: #d4171b; }
.disco figcaption { margin-top: 8px; font-size: 13px; color: var(--tinta-suave);
  line-height: 1.35; }
.disco figcaption b { display: block; color: var(--tinta); font-size: 14px; }
/* Franja con la foto en vivo: presenta la pregunta central. Encuadrada en
   la banda y el público, oscurecida abajo para que se lea el texto. */
.en-vivo { position: relative; min-height: 420px; margin-bottom: 16px;
  border-radius: 10px; overflow: hidden; display: flex; align-items: flex-end;
  padding: 32px; color: #fff; border: 1px solid var(--borde);
  background:
    linear-gradient(180deg, rgba(0,0,0,.1) 30%, rgba(0,0,0,.85) 100%),
    url("EN_VIVO") center 72% / cover no-repeat, #000; }
.en-vivo h2 { font-size: 30px; margin: 0 0 6px; max-width: 720px; line-height: 1.15; }
.en-vivo h2 span { color: #ff3b3b; }
.en-vivo p { margin: 0; color: #d6d6d6; max-width: 640px; }
@media (max-width: 800px) {
  .en-vivo { min-height: 300px; padding: 20px; }
  .en-vivo h2 { font-size: 22px; }
}
@media (max-width: 600px) {
  .cabecera { flex-wrap: wrap; }
  .cabecera img { width: 64px; height: 64px; }
  h1 { font-size: 24px; }
  .doble { grid-template-columns: 1fr; }
}
""".replace("FUENTE", FUENTE)
    .replace("POSTER", "assets/poster.png")
    .replace("EN_VIVO", "assets/en_vivo.png")
)

# Repinta los gráficos al cambiar de modo y recuerda la elección del usuario.
SCRIPT = """
const TEMAS = TEMAS_JSON;
const raiz = document.documentElement;
const boton = document.getElementById("tema");
const sistemaOscuro = window.matchMedia("(prefers-color-scheme: dark)");

function guardado() {
  try { return localStorage.getItem("tema"); } catch (e) { return null; }
}

function pintar(div, t) {
  const capa = {
    paper_bgcolor: t.fondo, plot_bgcolor: t.fondo,
    "font.color": t.tinta_suave, "title.font.color": t.tinta,
    "title.subtitle.font.color": t.tinta_suave,
    "xaxis.gridcolor": t.grilla, "yaxis.gridcolor": t.grilla,
    "xaxis.linecolor": t.eje, "yaxis.linecolor": t.eje,
    "hoverlabel.bgcolor": t.fondo, "hoverlabel.font.color": t.tinta,
    "hoverlabel.bordercolor": t.eje,
  };
  (div.layout.annotations || []).forEach((a, i) => {
    capa[`annotations[${i}].font.color`] = a.name === "zona" ? t.gris : t.tinta_suave;
  });
  (div.layout.shapes || []).forEach((s, i) => {
    capa[`shapes[${i}].line.color`] = t.gris;
  });
  const datos = {
    "marker.color": div.data.map(d => t.epocas[d.meta.epoca]),
    "marker.line.color": div.data.map(() => t.fondo),
    "textfont.color": div.data.map(() => t.tinta_suave),
  };
  Plotly.update(div, datos, capa);
}

function aplicar(nombre) {
  raiz.dataset.tema = nombre;
  boton.textContent = nombre === "oscuro" ? "☀ Modo claro" : "☾ Modo oscuro";
  document.querySelectorAll(".js-plotly-plot").forEach(div => pintar(div, TEMAS[nombre]));
}

boton.addEventListener("click", () => {
  const nuevo = raiz.dataset.tema === "oscuro" ? "claro" : "oscuro";
  try { localStorage.setItem("tema", nuevo); } catch (e) {}
  aplicar(nuevo);
});
sistemaOscuro.addEventListener("change", e => {
  if (!guardado()) aplicar(e.matches ? "oscuro" : "claro");
});
window.addEventListener("load", () => {
  aplicar(guardado() || (sistemaOscuro.matches ? "oscuro" : "claro"));
});
""".replace("TEMAS_JSON", json.dumps(TEMAS))


def pagina(canciones, discos, figuras):
    fecha = canciones.fecha_extraccion.max()
    top10, versiones, total, promedio = (
        grafico_html(fig, f"grafico-{i}") for i, fig in enumerate(figuras)
    )
    resumen = (
        f"{len(canciones)} canciones de estudio · {len(discos)} discos · "
        f"{miles(canciones.reproducciones.sum())} reproducciones en Last.fm · "
        f"datos del {fecha:%d/%m/%Y}"
    )
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Los Redondos en datos</title>
<style>{ESTILOS}</style>
<!-- Plotly desde internet: la página queda liviana (sin esto pesaría ~5 MB). -->
<script src="https://cdn.plot.ly/plotly-{get_plotlyjs_version()}.min.js" charset="utf-8"></script>
</head>
<body>
<header>
  <div class="cabecera">
    <img src="{LOGO}" alt="Logo de Patricio Rey y sus Redonditos de Ricota"
         onerror="this.remove()">
    <div class="textos">
      <h1>Los Redondos <span>en datos</span></h1>
      <p class="resumen">{resumen}</p>
    </div>
    <button id="tema" type="button">☾ Modo oscuro</button>
  </div>
</header>
<main>
  <div class="tarjetas">{tarjetas(canciones, discos)}</div>
  <section>{discografia(discos)}</section>
  <div class="en-vivo" role="img" aria-label="La banda tocando en vivo ante el público">
    <div>
      <h2>Del escenario a los <span>auriculares</span></h2>
      <p>¿Las canciones con más versiones grabadas son también las que más se
      escuchan hoy?</p>
    </div>
  </div>
  <section>{versiones}</section>
  <section>{top10}</section>
  <div class="doble">
    <section>{total}</section>
    <section>{promedio}</section>
  </div>
  <details>
    <summary>Ver las {len(canciones)} canciones en una tabla</summary>
    <div class="tabla">{tabla(canciones)}</div>
  </details>
  <div class="notas">
    <p><b>Sobre los datos.</b> Las reproducciones y los oyentes salen de Last.fm:
    son una muestra (solo cuentan a quienes usan Last.fm), no el total real.
    Las versiones son las grabaciones registradas en MusicBrainz, no las veces
    que la banda tocó cada tema. Muchas grabaciones en vivo no tienen la
    etiqueta "live", por eso "marcadas en vivo" es un mínimo. Los medleys y los
    temas que solo aparecen en vivo quedan afuera. El logo, las tapas y
    las imágenes pertenecen a la banda y a sus autores (las tapas se muestran
    desde el Cover Art Archive de MusicBrainz; la imagen del encabezado es un
    póster de fan, con la firma de su autor en la imagen); este es un proyecto
    de fan sin fines de lucro.</p>
  </div>
</main>
<script>{SCRIPT}</script>
</body>
</html>
"""


def main():
    spark = SparkSession.builder.appName("dashboard_redondos").getOrCreate()
    canciones = spark.sql(CONSULTA_CANCIONES).toPandas()
    canciones["epoca"] = canciones.anio.map(epoca)
    discos = tabla_discos(canciones)
    total, promedio = graficos_discos(discos)
    figuras = [
        grafico_top_canciones(canciones),
        grafico_versiones(canciones),
        total,
        promedio,
    ]
    SALIDA.write_text(pagina(canciones, discos, figuras), encoding="utf-8")
    print(f"Dashboard guardado en {SALIDA}")


if __name__ == "__main__":
    main()
