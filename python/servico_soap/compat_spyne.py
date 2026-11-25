"""Ajuste de compatibilidade do Spyne 2.14 com Python 3.12+.

O Spyne 2.14 (última versão no PyPI) traz embutida uma cópia antiga da biblioteca
"six" que não funciona no Python 3.12+ (ModuleNotFoundError: spyne.util.six.moves).
Aqui carregamos o "six" atual (instalado via requirements.txt) no lugar da cópia
antiga, ANTES de importar o Spyne. No Python 3.13+ o módulo "cgi" (removido da
biblioteca padrão) é fornecido pelo pacote "legacy-cgi", também no requirements.txt.

Basta fazer "import compat_spyne" antes de "import spyne". Não altera nada instalado.
"""
import importlib.util
import sys

if sys.version_info >= (3, 12) and "spyne.util.six" not in sys.modules:
    import operator

    import six as _six

    _spec = importlib.util.spec_from_file_location("spyne.util.six", _six.__file__)
    _modulo = importlib.util.module_from_spec(_spec)
    sys.modules["spyne.util.six"] = _modulo
    _spec.loader.exec_module(_modulo)
    # única função que a cópia do Spyne tinha a mais que o "six" oficial
    _modulo.get_function_name = operator.attrgetter("__name__")
