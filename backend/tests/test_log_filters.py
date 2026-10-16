import logging

from app.log_filters import DropQueryString


def access_record(path: str) -> logging.LogRecord:
    args = ("172.18.0.1:5000", "GET", path, "1.1", 200)
    message = '%s - "%s %s HTTP/%s" %d'
    return logging.LogRecord("uvicorn.access", logging.INFO, "", 0, message, args, None)


def test_access_log_drops_query_string():
    record = access_record("/patients?search=Ruiz&status=active")
    assert DropQueryString().filter(record)
    assert record.getMessage() == '172.18.0.1:5000 - "GET /patients HTTP/1.1" 200'


def test_access_log_keeps_path_without_query():
    record = access_record("/patients/123")
    DropQueryString().filter(record)
    assert record.getMessage() == '172.18.0.1:5000 - "GET /patients/123 HTTP/1.1" 200'
