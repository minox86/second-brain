"""Eccezioni del toolkit. La CLI trasforma ogni SbError in exit code 2."""


class SbError(Exception):
    """Base di tutti gli errori d'uso o d'ambiente del toolkit."""


class UsageError(SbError):
    """Argomenti non validi."""


class WikiError(SbError):
    """La wiki manca, è incompatibile o ha uno schema non valido."""


class PlanError(SbError):
    """Piano di migrazione non valido o non applicabile."""


class FrontmatterError(SbError, ValueError):
    """Frontmatter non conforme al sottoinsieme YAML supportato."""
