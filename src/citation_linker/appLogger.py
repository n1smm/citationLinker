import  logging
import  json
import  sys


class JsonLineHandler(logging.StreamHandler):
    """Writes one JSON object per log record to stdout.

    Each line is a self-contained JSON object so a PySide6 frontend subprocess
    can parse records one at a time as they arrive, without buffering or having
    to split on newlines embedded inside a message.

    Schema per line:
        {
          "level":           str,       # "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
          "message":         str,       # human-readable English description
          "article_num":     int|null,  # 1-based article index
          "page_in_article": int|null,  # 1-based page within the current article part
          "page_in_doc":     int|null,  # 1-based global page in the original full document
        }
    """

    def emit(self, record: logging.LogRecord) -> None:
        d = {
            "level":           record.levelname,
            "message":         record.getMessage(),
            "article_num":     getattr(record, "article_num",     None),
            "page_in_article": getattr(record, "page_in_article", None),
            "page_in_doc":     getattr(record, "page_in_doc",     None),
        }
        sys.stdout.write(json.dumps(d, ensure_ascii=False) + "\n")
        sys.stdout.flush()


class ArticleContext(logging.Filter):
    """Injects the current article/page context into every log record.

    Attach once to the shared logger, then update the three attributes as
    processing advances through articles and pages.  Every logger.xxx() call
    in any module will automatically carry the current context without needing
    to pass it through function arguments.

    Usage:
        ctx = ArticleContext()
        logger.addFilter(ctx)

        ctx.article_num     = 2        # starting article 2
        ctx.page_in_doc     = 31       # global page offset (start_clamped + 1)

        ctx.page_in_article = 3        # now on local page 3
        ctx.page_in_doc     = 33       # = start_clamped + local_page
    """

    def __init__(self) -> None:
        super().__init__()
        self.article_num:     int | None = None
        self.page_in_article: int | None = None
        self.page_in_doc:     int | None = None

    def filter(self, record: logging.LogRecord) -> bool:
        record.article_num     = self.article_num
        record.page_in_article = self.page_in_article
        record.page_in_doc     = self.page_in_doc
        return True


def get_logger(name: str = "citation_linker") -> logging.Logger:
    """Return (or create) the shared application logger.

    Call this at module level in every file that needs to log:
        logger = get_logger()

    All modules that call get_logger() with the default name share the same
    Logger instance, so a Filter attached in multiArticle.py is also active
    when referenceConnector.py logs a message.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(JsonLineHandler())
    logger.setLevel(logging.DEBUG)
    return logger
