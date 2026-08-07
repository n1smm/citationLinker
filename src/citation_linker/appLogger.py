import  logging
import  json
import  sys
import  io


_log_buffer = None
_bib_buffer: list = []
_cit_buffer: list = []
_linked_count: int = 0

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
        message = record.getMessage()
        if record.exc_info:
            message = f"{message}\n{logging.Formatter().formatException(record.exc_info)}"
        d = {
            "level":           record.levelname,
            "message":         message,
            "article_num":     getattr(record, "article_num",     None),
            "page_in_article": getattr(record, "page_in_article", None),
            "page_in_doc":     getattr(record, "page_in_doc",     None),
        }
        sys.stdout.write(json.dumps(d, ensure_ascii=False) + "\n")
        sys.stdout.flush()

class StringIoHandler(logging.StreamHandler):
    """ Writes logs to memory buffer (for use with qt UI)
        for retrieving logging info in UI app
    """

    def __init__(self, stream):
        super().__init__(stream)

    def emit(self, record):
        message = record.getMessage()
        if record.exc_info:
            message = f"{message}\n{logging.Formatter().formatException(record.exc_info)}"
        data = {
                "level": record.levelname,
                "message": message,
                "article_num": getattr(record, "article_num", None),
                "page_in_article": getattr(record, "page_in_article", None),
                "page_in_doc": getattr(record, "page_in_doc", None)
        }
        self.stream.write(json.dumps(data, ensure_ascii=False) + "\n")
        self.stream.flush()


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
    
    Note: The logger level should be set once in main() based on the config.
    """
    from citation_linker.configLoad import config
    logger = logging.getLogger(name)
    ui_mode = config.get("UI", ["False"])[0] == "True"
    
    # Check if we need to reconfigure due to UI mode change
    needs_reconfigure = False
    if logger.handlers:
        # Check if current handler matches UI mode
        has_stringio = any(isinstance(h, StringIoHandler) for h in logger.handlers)
        has_jsonline = any(isinstance(h, JsonLineHandler) for h in logger.handlers)
        
        if ui_mode and not has_stringio:
            needs_reconfigure = True
        elif not ui_mode and not has_jsonline:
            needs_reconfigure = True
    
    # Remove all handlers if we need to reconfigure
    if needs_reconfigure:
        logger.handlers.clear()
    
    # Add appropriate handler if none exists
    if not logger.handlers:
        if ui_mode:
            global _log_buffer
            _log_buffer = io.StringIO()
            logger.addHandler(StringIoHandler(_log_buffer))
        else:
            logger.addHandler(JsonLineHandler())

        logger.setLevel(logging.INFO)
    return logger

def get_logs():
    """ retrieve captured logs for UI mode """

    global _log_buffer
    if _log_buffer is not None:
        return _log_buffer.getvalue()

    return ""

def reset_log_buffer():
    """ clear the log buffer for a new run """
    global _log_buffer
    if _log_buffer is not None:
        _log_buffer.seek(0)
        _log_buffer.truncate(0)


def record_bib_entry(entry: dict) -> None:
    """Store one bibliography entry dict for later retrieval by the UI."""
    _bib_buffer.append(entry)


def record_cit_entry(entry: dict) -> None:
    """Store one citation/reference entry dict for later retrieval by the UI."""
    _cit_buffer.append(entry)


def get_bib_entries() -> list:
    return list(_bib_buffer)


def get_cit_entries() -> list:
    return list(_cit_buffer)


def reset_data_buffers() -> None:
    _bib_buffer.clear()
    _cit_buffer.clear()
    global _linked_count
    _linked_count = 0


def record_link_hit() -> None:
    """Increment the linked-citation counter by one."""
    global _linked_count
    _linked_count += 1


def get_linked_count() -> int:
    """Return total number of successfully linked citations."""
    return _linked_count


def get_valid_citation_count() -> int:
    """Count citations that have a year and at least one of surname/name is not 'xxx'."""
    count = 0
    for e in _cit_buffer:
        year = e.get("year", "")
        surname = e.get("surname", "")
        name = e.get("name", "")
        if year and (surname != "xxx" or name != "xxx"):
            count += 1
    return count


def get_valid_bib_count() -> int:
    """Count bibliography entries with valid year (not 'yyy'), surname ≤ 3 words,
    and at least one of surname/name is not 'yyy'."""
    count = 0
    for e in _bib_buffer:
        year = e.get("year", "")
        surname = e.get("surname", "")
        name = e.get("name", "")
        if (year and year != "yyy"
                and (surname != "yyy" or name != "yyy")
                and len(surname.split()) <= 3):
            count += 1
    return count


def get_certain_citation_count() -> int:
    """Count citations where BOTH surname and name are not 'xxx' AND there is a year."""
    count = 0
    for e in _cit_buffer:
        year = e.get("year", "")
        surname = e.get("surname", "")
        name = e.get("name", "")
        if year and surname != "xxx" and name != "xxx":
            count += 1
    return count


def get_certain_bib_count() -> int:
    """Count bibliography entries where BOTH surname and name are not 'yyy',
    year is valid, and surname ≤ 3 words."""
    count = 0
    for e in _bib_buffer:
        year = e.get("year", "")
        surname = e.get("surname", "")
        name = e.get("name", "")
        if (year and year != "yyy"
                and surname != "yyy"
                and name != "yyy"
                and len(surname.split()) <= 3):
            count += 1
    return count