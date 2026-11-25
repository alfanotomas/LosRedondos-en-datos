import re
import unicodedata

# Paréntesis que son una marca de versión y no parte del título.
# Se comparan sin acentos y en minúsculas. No incluye subtítulos reales,
# como "nena (la jubilación)" o "reina momo (la tomatita)".
MARCAS = (
    "ft.",
    "version",
    "bis",
    "instrumental",
    "en vivo",
    "presentacion por",
    "problemas tecnicos",
    "breve intermedio",
)
PATRON_MARCAS = re.compile(
    r"\s*\((?:" + "|".join(re.escape(m) for m in MARCAS) + r"|\d)[^)]*\)"
)


def normalizar_titulo(titulo):
    """Devuelve el título en minúsculas, sin acentos, sin marcas de versión
    entre paréntesis y sin puntuación."""
    t = titulo.lower()
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = PATRON_MARCAS.sub("", t)
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()
