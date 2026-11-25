{#
    Normaliza un título de canción para poder cruzar fuentes. Es la versión SQL
    de normalizar_titulo() de notebooks/limpieza.py, con los mismos pasos:

      1. minúsculas
      2. sin tildes: las letras con tilde de un solo carácter (translate) y las
         tildes sueltas que vienen después de la letra (\p{M}), que también
         aparecen en los datos. \p{Cf} borra caracteres invisibles (hay un
         "Invocación" que empieza con uno)
      3. sin marcas de versión entre paréntesis: "(en vivo)", "(ft. ...)",
         "(version ...)", "(1993)", etc.
      4. signos de puntuación -> espacio
      5. espacios de más afuera

    (?U) hace que \w y \s reconozcan letras de cualquier idioma, igual que en
    Python. En los strings de Spark SQL la barra va doble: '\\s' es \s.
#}
{% macro normalizar_titulo(columna) %}
    trim(regexp_replace(
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    translate(
                        lower({{ columna }}),
                        'áéíóúàèìòùäëïöüâêîôûãõñńçå',
                        'aeiouaeiouaeiouaeiouaonnca'
                    ),
                    '[\\p{M}\\p{Cf}]', ''
                ),
                '\\s*\\((?:ft\\.|version|bis|instrumental|en vivo|presentacion por|problemas tecnicos|breve intermedio|\\d)[^)]*\\)', ''
            ),
            '(?U)[^\\w\\s]', ' '
        ),
        '(?U)\\s+', ' '
    ))
{% endmacro %}
