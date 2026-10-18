import logging
import uuid
from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import openai
import pytest

from app import generated_summary
from app.generated_summary import (
    NOTE_CHARACTER_LIMIT,
    ProviderError,
    build_prompt,
    get_narrative_writer,
)
from app.main import app
from app.models import Note, Patient, PatientStatus

TZ = ZoneInfo("America/New_York")
TODAY = date(2026, 10, 17)


def make_patient(**overrides) -> Patient:
    fields = {
        "id": uuid.uuid4(),
        "first_name": "Ana",
        "last_name": "Ruiz",
        "date_of_birth": date(1958, 3, 2),
        "phone": "(617) 555-0123",
        "email": "ana.ruiz@example.com",
        "conditions": ["Hypertension"],
        "allergies": None,
        "status": PatientStatus.ACTIVE,
    }
    return Patient(**(fields | overrides))


def make_note(day: str, content: str) -> Note:
    return Note(taken_at=datetime.fromisoformat(f"{day}T14:00:00+00:00"), content=content)


# Prompt


def test_prompt_has_profile_and_full_notes_oldest_first_without_identifiers():
    notes = [
        make_note("2026-03-01", "First visit. BP 150/95. Started lisinopril 10 mg daily."),
        make_note("2026-09-20", "Follow-up. BP 128/82. Tolerating medication well."),
    ]
    prompt = build_prompt(make_patient(), notes, 12, TODAY, TZ)

    assert "Status: active, age 68" in prompt
    assert "Conditions: Hypertension" in prompt
    assert "Allergies: unknown (not recorded)" in prompt
    assert "NOTES (2 most recent of 12, oldest first)" in prompt
    # The full text, not just the first sentence, in date order.
    assert prompt.index("Started lisinopril 10 mg daily.") < prompt.index("Tolerating medication")
    assert "--- Note dated Mar 1, 2026 ---" in prompt
    for identifier in ["Ana", "Ruiz", "1958", "555-0123", "example.com"]:
        assert identifier not in prompt


def test_prompt_shortens_very_long_notes_and_says_so():
    long_note = make_note("2026-09-20", "x" * (NOTE_CHARACTER_LIMIT + 500))
    prompt = build_prompt(make_patient(), [long_note], 1, TODAY, TZ)
    assert "x" * NOTE_CHARACTER_LIMIT + " [note shortened]" in prompt
    assert "x" * (NOTE_CHARACTER_LIMIT + 1) not in prompt


def test_prompt_for_deceased_patient_has_no_age():
    patient = make_patient(status=PatientStatus.DECEASED, allergies=[])
    prompt = build_prompt(patient, [], 0, TODAY, TZ)
    assert "Status: deceased (date of death not recorded)" in prompt
    assert "age" not in prompt.split("\n")[1]
    assert "Allergies: none known" in prompt


# Endpoint


class FakeWriter:
    """Stands in for the provider. Records each prompt and returns a fixed narrative."""

    def __init__(self, result: str | Exception = "Generated narrative."):
        self.result = result
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture
def use_writer(client):
    def _use(writer):
        app.dependency_overrides[get_narrative_writer] = lambda: writer
        return writer

    return _use


@pytest.fixture
def patient_with_notes(client, create_patient):
    patient = create_patient(allergies=["Penicillin"], phone="617-555-0123")
    for day, content in [
        ("2026-03-01T09:00:00-05:00", "First visit. Started lisinopril 10 mg daily."),
        ("2026-09-20T09:30:00-04:00", "Follow-up. BP improved to 128/82."),
    ]:
        response = client.post(
            f"/patients/{patient['id']}/notes", json={"taken_at": day, "content": content}
        )
        assert response.status_code == 201
    return patient


def summary_url(patient_id, **params):
    query = "&".join(f"{key}={value}" for key, value in params.items())
    return f"/patients/{patient_id}/summary" + (f"?{query}" if query else "")


def test_summary_is_generated_when_available_with_facts_from_database(
    client, use_writer, patient_with_notes
):
    writer = use_writer(FakeWriter("Started lisinopril in March; BP improved by September."))
    body = client.get(summary_url(patient_with_notes["id"])).json()

    assert body["source"] == "llm"
    assert body["fallback_reason"] is None
    assert body["narrative"] == "Started lisinopril in March; BP improved by September."
    built_in = client.get(summary_url(patient_with_notes["id"], source="template")).json()
    # Everything except the narrative and source matches the built-in summary.
    for field in ["headline", "allergies", "conditions", "notes_included", "notes_total"]:
        assert body[field] == built_in[field]
    assert body["notes_from"] == "2026-03-01"
    assert body["notes_to"] == "2026-09-20"
    [prompt] = writer.prompts
    assert "Started lisinopril 10 mg daily." in prompt
    assert "Ruiz" not in prompt and "555-0123" not in prompt


def test_template_source_never_contacts_the_model(client, use_writer, patient_with_notes):
    writer = use_writer(FakeWriter())
    body = client.get(summary_url(patient_with_notes["id"], source="template")).json()
    assert body["source"] == "template"
    assert body["fallback_reason"] is None
    assert writer.prompts == []


def test_unknown_source_is_rejected(client, patient_with_notes):
    response = client.get(summary_url(patient_with_notes["id"], source="magic"))
    assert response.status_code == 422


def test_summary_without_notes_contacts_nothing(client, use_writer, create_patient):
    writer = use_writer(FakeWriter())
    body = client.get(summary_url(create_patient()["id"])).json()
    assert body["source"] == "template"
    assert body["fallback_reason"] is None
    assert body["narrative"] == "No clinical notes on file."
    assert writer.prompts == []


def test_falls_back_to_built_in_when_not_configured(client, patient_with_notes):
    response = client.get(summary_url(patient_with_notes["id"]))
    assert response.status_code == 200
    assert response.json()["source"] == "template"
    assert response.json()["fallback_reason"] == "not_configured"


def test_falls_back_to_built_in_when_provider_fails(client, use_writer, patient_with_notes):
    use_writer(FakeWriter(ProviderError()))
    response = client.get(summary_url(patient_with_notes["id"]))
    assert response.status_code == 200
    assert response.json()["source"] == "template"
    assert response.json()["fallback_reason"] == "provider_error"
    assert response.json()["narrative"].startswith("Mar 1, 2026: ")


def test_generated_narrative_is_reused_until_notes_change(client, use_writer, patient_with_notes):
    writer = use_writer(FakeWriter())
    url = summary_url(patient_with_notes["id"])
    client.get(url)
    client.get(url)
    assert len(writer.prompts) == 1

    client.post(
        f"/patients/{patient_with_notes['id']}/notes",
        json={"taken_at": "2026-10-01T10:00:00-04:00", "content": "Phone check-in."},
    )
    client.get(url)
    assert len(writer.prompts) == 2
    assert "Phone check-in." in writer.prompts[-1]


def test_failures_are_not_remembered(client, use_writer, patient_with_notes):
    url = summary_url(patient_with_notes["id"])
    use_writer(FakeWriter(ProviderError()))
    assert client.get(url).json()["fallback_reason"] == "provider_error"
    use_writer(FakeWriter("Recovered."))
    assert client.get(url).json()["narrative"] == "Recovered."


def test_summary_is_404_for_missing_patient(client, use_writer):
    writer = use_writer(FakeWriter())
    response = client.get(summary_url("00000000-0000-0000-0000-000000000000"))
    assert response.status_code == 404
    assert writer.prompts == []


# Provider call


class FakeResponses:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return SimpleNamespace(output_text=self.outcome)


def openai_writer_with(monkeypatch, outcome):
    responses = FakeResponses(outcome)
    monkeypatch.setattr(
        generated_summary.openai, "OpenAI", lambda **_: SimpleNamespace(responses=responses)
    )
    return generated_summary._openai_writer("sk-test", "test-model"), responses


def test_openai_writer_sends_instructions_and_asks_not_to_store(monkeypatch):
    write, responses = openai_writer_with(monkeypatch, "  A narrative.  ")
    assert write("PROMPT") == "A narrative."
    [call] = responses.calls
    assert call["model"] == "test-model"
    assert call["input"] == "PROMPT"
    assert call["instructions"] == generated_summary.INSTRUCTIONS
    assert call["store"] is False


@pytest.mark.parametrize(
    "outcome", [openai.APIConnectionError(request=None), "   "], ids=["error", "empty"]
)
def test_openai_writer_failures_become_provider_errors_without_logging_data(
    monkeypatch, caplog, outcome
):
    write, _ = openai_writer_with(monkeypatch, outcome)
    with caplog.at_level(logging.WARNING), pytest.raises(ProviderError):
        write("Patient note text that must not be logged")
    assert "must not be logged" not in caplog.text
    assert "Summary provider" in caplog.text


def test_no_key_means_no_writer(monkeypatch):
    monkeypatch.setattr(generated_summary.settings, "openai_api_key", None)
    assert get_narrative_writer() is None
