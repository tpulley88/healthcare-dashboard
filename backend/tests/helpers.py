MISSING_ID = "00000000-0000-0000-0000-000000000000"


# Top-level field names from a 422 response, e.g. {"phone"} or {"allergies"}.
def error_fields(response) -> set[str]:
    assert response.status_code == 422, response.text
    return {error["loc"][1] for error in response.json()["detail"]}
