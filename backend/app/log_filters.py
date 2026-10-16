import logging


# Access logs keep method, path, and status but drop the query string, which can carry
# search terms such as patient names. Matches uvicorn's 5-argument access log format.
class DropQueryString(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and len(record.args) == 5:
            client, method, path, http_version, status = record.args
            record.args = (client, method, str(path).split("?", 1)[0], http_version, status)
        return True
