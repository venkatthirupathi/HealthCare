"""Tests for PII redaction and prescribing-intent detection."""

from __future__ import annotations

import pytest

from backend.services.guardrails import is_prescribing_intent, redact_pii


# ── PII Redaction ─────────────────────────────────────────────────────────────


class TestRedactPII:
    def test_email_redacted(self):
        text = "Contact john.doe@hospital.org for info"
        result = redact_pii(text)
        assert "[REDACTED:EMAIL]" in result
        assert "john.doe@hospital.org" not in result

    def test_aadhaar_redacted(self):
        text = "Patient Aadhaar 1234 5678 9012 on file"
        result = redact_pii(text)
        assert "[REDACTED:AADHAAR]" in result
        assert "1234 5678 9012" not in result

    def test_pan_redacted(self):
        text = "PAN number ABCDE1234F submitted"
        result = redact_pii(text)
        assert "[REDACTED:PAN]" in result
        assert "ABCDE1234F" not in result

    def test_mrn_redacted(self):
        text = "Patient MRN: 1234567 admitted today"
        result = redact_pii(text)
        assert "[REDACTED:MRN]" in result
        assert "1234567" not in result

    def test_dob_redacted(self):
        text = "DOB: 15/08/1990 recorded"
        result = redact_pii(text)
        assert "[REDACTED:DOB]" in result

    def test_name_after_patient_redacted(self):
        text = "patient Rajesh Kumar was admitted"
        result = redact_pii(text)
        assert "Rajesh Kumar" not in result
        assert "patient" in result.lower()

    def test_no_pii_unchanged(self):
        text = "What is the contraindication for metformin?"
        assert redact_pii(text) == text

    def test_clinical_numbers_not_redacted(self):
        # eGFR values should not be caught by Aadhaar pattern
        text = "eGFR is below 30 mL/min"
        result = redact_pii(text)
        assert "30" in result


# ── Prescribing Intent ────────────────────────────────────────────────────────


class TestPrescribingIntent:
    @pytest.mark.parametrize(
        "question",
        [
            "What should I prescribe for UTI in pregnancy?",
            "What do we prescribe for pneumonia?",
            "Best antibiotic for strep throat?",
            "Best drug for hypertension in elderly?",
            "Can I start metformin in a CKD patient?",
            "Should I give aspirin after MI?",
            "My patient has severe renal failure",
            "My patient is 80 years old with diabetes",
        ],
    )
    def test_prescribing_questions_detected(self, question: str):
        assert is_prescribing_intent(question), f"Expected refusal for: {question!r}"

    @pytest.mark.parametrize(
        "question",
        [
            "What is the renal dosing for metformin?",
            "What are the contraindications for atorvastatin?",
            "What is the half-life of amoxicillin?",
            "What does the label say about boxed warnings for metformin?",
            "What are the adverse reactions to amoxicillin?",
        ],
    )
    def test_label_queries_not_refused(self, question: str):
        assert not is_prescribing_intent(question), f"Should NOT refuse: {question!r}"

    def test_case_insensitive(self):
        assert is_prescribing_intent("WHAT SHOULD I PRESCRIBE FOR FEVER?")
        assert is_prescribing_intent("what SHOULD i give to this patient?")
