from __future__ import annotations

from fastapi.testclient import TestClient

from reconcileflow.api.app import create_app
from reconcileflow.bootstrap import build_container
from reconcileflow.settings import Settings


def client() -> TestClient:
    container = build_container(
        Settings(
            environment="test",
            repository_backend="memory",
            async_enabled=False,
            async_row_threshold=100,
            max_upload_bytes=1024 * 1024,
        )
    )
    return TestClient(create_app(container))


def upload(api: TestClient, side: str, filename: str, body: str) -> dict[str, object]:
    response = api.post(
        "/api/v1/datasets",
        data={"side": side},
        files={"file": (filename, body.encode(), "text/csv")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def map_dataset(api: TestClient, dataset_id: str) -> dict[str, object]:
    response = api.put(
        f"/api/v1/datasets/{dataset_id}/mapping",
        json={
            "amount": "amount",
            "currency": "currency",
            "booking_date": "date",
            "transaction_id": "id",
            "document": "document",
            "reference": "reference",
            "default_currency": "BRL",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_api_contract_covers_upload_mapping_run_review_audit_and_export() -> None:
    with client() as api:
        health = api.get("/health/live", headers={"X-Correlation-Id": "health-corr"})
        assert health.status_code == 200
        assert health.headers["X-Correlation-Id"] == "health-corr"

        header = "id,amount,currency,date,document,reference\n"
        dataset_a = upload(
            api,
            "A",
            "a.csv",
            header + "A1,100.00,BRL,2026-01-01,DOC,SOURCE\n",
        )
        dataset_b = upload(
            api,
            "B",
            "b.csv",
            header
            + "B1,100.00,BRL,2026-01-01,DOC,TARGET-1\n"
            + "B2,100.00,BRL,2026-01-01,DOC,TARGET-2\n",
        )
        mapped_a = map_dataset(api, str(dataset_a["dataset_id"]))
        mapped_b = map_dataset(api, str(dataset_b["dataset_id"]))
        assert mapped_a["is_mapped"] is True
        assert mapped_b["row_count"] == 2

        profiles = api.get("/api/v1/profiles")
        assert profiles.status_code == 200
        assert profiles.json()[0]["rule_id"] == "standard"
        run_response = api.post(
            "/api/v1/runs",
            headers={"X-Idempotency-Key": "run-1", "X-Correlation-Id": "run-corr"},
            json={
                "dataset_a_id": dataset_a["dataset_id"],
                "dataset_b_id": dataset_b["dataset_id"],
                "profile_id": "standard",
                "profile_version": "1",
            },
        )
        assert run_response.status_code == 201, run_response.text
        run = run_response.json()
        assert run["status"] == "COMPLETED"
        assert run["correlation_id"] == "run-corr"
        assert run["counts"]["AMBIGUOUS"] == 1

        run_id = run["run_id"]
        decisions_response = api.get(
            f"/api/v1/runs/{run_id}/decisions", params={"status": "AMBIGUOUS"}
        )
        assert decisions_response.status_code == 200
        decisions = decisions_response.json()
        assert len(decisions) == 1
        assert decisions[0]["rule_id"] == "amount_date_tolerance"
        assert decisions[0]["evidence"]

        decision_id = decisions[0]["decision_id"]
        detail = api.get(f"/api/v1/runs/{run_id}/decisions/{decision_id}")
        assert detail.status_code == 200
        review = api.post(
            f"/api/v1/runs/{run_id}/decisions/{decision_id}/reviews",
            headers={"X-Actor-Id": "analyst", "X-Idempotency-Key": "review-1"},
            json={"action": "APPROVE", "reason": "Evidence checked"},
        )
        assert review.status_code == 201, review.text
        assert review.json()["actor_id"] == "analyst"
        reviews = api.get(f"/api/v1/runs/{run_id}/reviews")
        assert reviews.status_code == 200
        assert reviews.json()[0]["decision_id"] == decision_id
        audit = api.get(f"/api/v1/runs/{run_id}/audit")
        assert audit.status_code == 200
        assert audit.json()[0]["event_type"] == "manual_review_recorded"

        exported = api.post(
            f"/api/v1/runs/{run_id}/exports",
            headers={"X-Actor-Id": "analyst", "X-Idempotency-Key": "export-1"},
        )
        assert exported.status_code == 200
        assert exported.content.startswith(b"PK")
        assert exported.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument"
        )
        assert exported.headers["etag"]

        run_list = api.get("/api/v1/runs")
        dataset_list = api.get("/api/v1/datasets")
        assert len(run_list.json()) == 1
        assert len(dataset_list.json()) == 2


def test_api_returns_standardized_validation_and_not_found_errors() -> None:
    with client() as api:
        missing_header = api.post(
            "/api/v1/runs",
            json={"dataset_a_id": "a", "dataset_b_id": "b"},
        )
        assert missing_header.status_code == 422
        assert missing_header.json()["error"]["code"] == "request_validation_failed"
        assert {issue["msg"] for issue in missing_header.json()["error"]["issues"]} == {
            "Campo obrigatório."
        }
        assert missing_header.headers["X-Correlation-Id"]

        missing = api.get("/api/v1/runs/not-found")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "not_found"

        invalid_upload = api.post(
            "/api/v1/datasets",
            data={"side": "A"},
            files={"file": ("bad.txt", b"x", "text/plain")},
        )
        assert invalid_upload.status_code == 422
        assert invalid_upload.json()["error"]["issues"][0]["code"] == "unsupported_file_type"

        oversized_correlation = api.get("/health/live", headers={"X-Correlation-Id": "x" * 101})
        assert oversized_correlation.status_code == 400
        assert oversized_correlation.json()["error"]["code"] == "invalid_correlation_id"


def test_openapi_exposes_versioned_product_routes() -> None:
    with client() as api:
        schema = api.get("/openapi.json").json()
    assert schema["info"]["title"] == "ReconcileFlow API"
    paths = schema["paths"]
    assert "/api/v1/datasets" in paths
    assert "/api/v1/runs/{run_id}/decisions/{decision_id}/reviews" in paths
    assert "/api/v1/runs/{run_id}/reviews" in paths
    assert "/api/v1/runs/{run_id}/exports" in paths
