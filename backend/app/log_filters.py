import logging


class DropQueryString(logging.Filter):
    """Remove the query string from uvicorn's access log lines.

    Search terms, such as patient names, travel in the query string.
    Access logs shouldn't hold patient data, so only the method, path, and status are kept.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # uvicorn logs (client, method, path, http_version, status); other records pass unchanged.
        if isinstance(record.args, tuple) and len(record.args) == 5:
            client, method, path, http_version, status = record.args
            record.args = (client, method, str(path).split("?", 1)[0], http_version, status)
        return True
