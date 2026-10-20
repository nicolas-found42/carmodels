"""Offline controls for optional performance advice, including uncertainty and service failure."""

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import check_advice as advice

STATE = {
    "question": "Where should freshness be profiled next?",
    "observations": ["Vertex transforms consume 80% of measured CPU time."],
}


def response(label="cpu"):
    questions = advice.questions_for()
    answers = {
        "direction": {
            "type": "choice",
            "choice": label,
            "confidence": 1,
            "probabilities": {k: float(k == label) for k in advice.ACTIONS},
        },
        "specificity": {
            "type": "score",
            "score": 2,
            "confidence": 1,
            "probabilities": {"0": 0.0, "1": 0.0, "2": 1.0},
            "legend": {str(i): level for i, level in enumerate(advice.LEVELS)},
        },
    }
    answers.update(
        {
            k: {"type": "noul", "noul": float(k == "fits_" + label)}
            for k in questions
            if k.startswith("fits_")
        }
    )
    return {
        "model": "served-model",
        "usage": {"input_tokens": 10, "output_tokens": 20, "cost": 0.001},
        "answers": answers,
    }


class Client:
    def __init__(self, raw=None, error=None):
        self.raw = response() if raw is None else raw
        self.error, self.calls = error, []

    def system_one(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.raw


class AdviceTests(unittest.TestCase):
    def test_all_actions_are_advisory_and_one_request_batches_independent_questions(
        self,
    ):
        for label in advice.ACTIONS:
            client = Client(response(label))
            result = advice.advise(STATE, client)
            self.assertEqual(
                result["suggestion"], None if label == "no_match" else label
            )
            self.assertEqual(
                result["status"], "review" if label == "no_match" else "advisory"
            )
            self.assertEqual(len(client.calls), 1)
            self.assertEqual(len(client.calls[0]["questions"]), 6)
            self.assertEqual(client.calls[0]["state"], STATE)
            self.assertEqual(result["usage"]["cost"], 0.001)
            self.assertNotIn("command", result)

    def test_weak_or_conflicting_judgments_withhold_suggestion(self):
        cases = []
        weak = response()
        weak["answers"]["fits_cpu"]["noul"] = 0.6
        cases.append(weak)
        weak = response()
        weak["answers"]["specificity"].update(
            score=1, probabilities={"0": 0.0, "1": 1.0, "2": 0.0}
        )
        cases.append(weak)
        weak = response()
        weak["answers"]["direction"].update(
            confidence=0.625,
            probabilities={
                "cpu": 0.7,
                "transport": 0.3,
                "pool": 0.0,
                "io": 0.0,
                "no_match": 0.0,
            },
        )
        cases.append(weak)
        for raw in cases:
            result = advice.advise(STATE, Client(raw))
            self.assertEqual(result["status"], "review")
            self.assertIsNone(result["suggestion"])

    def test_malformed_warning_and_failed_responses_are_errors(self):
        for change in (
            lambda r: r.update(warnings=["incomplete"]),
            lambda r: r.update(status="invalid_response"),
            lambda r: r.pop("usage"),
            lambda r: r["usage"].update(cost=-1),
            lambda r: r["usage"].update(input_tokens=True),
            lambda r: r["answers"].pop("fits_io"),
            lambda r: r["answers"]["fits_cpu"].update(noul=float("nan")),
            lambda r: r["answers"]["fits_cpu"].update(status="error"),
            lambda r: r["answers"]["direction"].update(choice="io"),
            lambda r: r["answers"]["direction"].update(confidence=0.3),
            lambda r: r["answers"]["direction"]["probabilities"].pop("io"),
            lambda r: r["answers"]["specificity"].update(legend={}),
            lambda r: r["answers"]["specificity"].update(score=1.5),
            lambda r: r["answers"]["specificity"].update(confidence=0.5),
        ):
            raw = copy.deepcopy(response())
            change(raw)
            result = advice.advise(STATE, Client(raw))
            self.assertEqual(result["status"], "error")
            self.assertEqual(result["reason"], "invalid_response")
            self.assertIsNone(result["suggestion"])
            json.dumps(result, allow_nan=False)

    def test_provider_errors_are_redacted_and_missing_cost_is_unknown(self):
        result = advice.advise(
            STATE, Client(error=RuntimeError("Authorization: SECRET"))
        )
        self.assertEqual(result["reason"], "provider_error")
        self.assertNotIn("SECRET", json.dumps(result))
        raw = response()
        raw["usage"].pop("cost")
        self.assertEqual(advice.advise(STATE, Client(raw))["status"], "advisory")
        self.assertNotIn("cost", advice.advise(STATE, Client(raw))["usage"])

    def test_input_bounds_reject_unexpected_fields_before_calling(self):
        client = Client()
        for state in (
            {},
            {**STATE, "credential": "SECRET"},
            {**STATE, "question": " "},
            {**STATE, "observations": []},
            {**STATE, "observations": ["x"] * 13},
            {**STATE, "observations": ["x" * 1201]},
            {**STATE, "observations": [None]},
        ):
            with self.assertRaises(ValueError):
                advice.advise(state, client)
        self.assertEqual(client.calls, [])

    def test_whitespace_counts_toward_transmitted_input_bounds(self):
        for field, limit in (("question", 500), ("observations", 1200)):
            for padded in (" " * limit + "x", "x" + " " * limit):
                state = {
                    **STATE,
                    field: [padded] if field == "observations" else padded,
                }
                client = Client()
                with (
                    self.subTest(field=field, padding=padded[:1]),
                    self.assertRaises(ValueError),
                ):
                    advice.advise(state, client)
                self.assertEqual(client.calls, [])
            boundary = " " * (limit - 1) + "x"
            state = {
                **STATE,
                field: [boundary] if field == "observations" else boundary,
            }
            client = Client()
            self.assertEqual(advice.advise(state, client)["status"], "advisory")
            self.assertEqual(client.calls[0]["state"], state)

    def test_output_is_reserved_before_client_and_live_opt_in_is_required(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.object(advice, "make_client") as client,
        ):
            source, output = (
                Path(temp) / "diagnostics.json",
                Path(temp) / "receipt.json",
            )
            source.write_text(json.dumps(STATE))
            output.write_text("previous evidence")
            for flags in ([], ["--live"]):
                with (
                    patch.object(
                        sys,
                        "argv",
                        ["check_advice", str(source), "--output", str(output), *flags],
                    ),
                    patch.object(sys, "stderr"),
                    self.assertRaises(SystemExit) as caught,
                ):
                    advice.main()
                self.assertEqual(caught.exception.code, 2)
            client.assert_not_called()
            self.assertEqual(output.read_text(), "previous evidence")
            new_output = Path(temp) / "new.json"
            client.side_effect = RuntimeError("SECRET")
            with patch.object(
                sys,
                "argv",
                ["check_advice", str(source), "--live", "--output", str(new_output)],
            ):
                self.assertEqual(advice.main(), 1)
            self.assertEqual(
                json.loads(new_output.read_text())["reason"], "client_unavailable"
            )
            self.assertNotIn("SECRET", new_output.read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
