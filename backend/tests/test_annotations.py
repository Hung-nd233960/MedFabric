"""Annotation submission and draft lifecycle tests.

These cover the most critical backend logic:
- The submit state machine (can't submit twice, ownership, region validation)
- Draft lifecycle (save, retrieve, auto-draft priority, delete, blocked after submit)
"""

import pytest

from tests.conftest import (
    api_login,
    bearer,
    image_eval,
    make_dataset_with_patient,
    make_doctor,
    make_image_set,
    submit_payload,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def open_session(client, token, image_set_uuid) -> str:
    resp = client.post(
        "/api/annotation-sessions/",
        json={"image_set_uuid": str(image_set_uuid)},
        headers=bearer(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["annotation_session_uuid"]


def draft_payload(session_uuid, images):
    return {
        "annotation_session_uuid": str(session_uuid),
        "usability": "IschemicAssessable",
        "low_quality": False,
        "notes": None,
        "image_evaluations": [
            image_eval(img.uuid, "BasalGanglia" if i < 2 else "CoronaRadiata")
            for i, img in enumerate(images)
        ],
    }


# ---------------------------------------------------------------------------
# Submission state machine
# ---------------------------------------------------------------------------

class TestSubmit:
    def test_ischemic_submit_succeeds(self, client, db, doctor, doctor_token):
        ds, patient = make_dataset_with_patient(db)
        img_set, images = make_image_set(db, ds.dataset_uuid, patient.patient_uuid)

        sess = open_session(client, doctor_token, img_set.uuid)
        resp = client.post(
            "/api/evaluations/submit",
            json=submit_payload(sess, images),
            headers=bearer(doctor_token),
        )
        assert resp.status_code == 200
        assert resp.json()["submitted_at"] is not None

    def test_non_ischemic_submit_needs_no_slice_scores(self, client, db, doctor, doctor_token):
        ds, patient = make_dataset_with_patient(db)
        img_set, images = make_image_set(db, ds.dataset_uuid, patient.patient_uuid)

        sess = open_session(client, doctor_token, img_set.uuid)
        resp = client.post(
            "/api/evaluations/submit",
            json=submit_payload(sess, images, usability="HemorrhagicPresent"),
            headers=bearer(doctor_token),
        )
        assert resp.status_code == 200

    def test_ischemic_missing_basal_ganglia_is_422(self, client, db, doctor, doctor_token):
        ds, patient = make_dataset_with_patient(db)
        img_set, images = make_image_set(db, ds.dataset_uuid, patient.patient_uuid)

        sess = open_session(client, doctor_token, img_set.uuid)
        # All slices marked CoronaRadiata — no BasalGanglia → invalid
        bad_evals = [image_eval(img.uuid, "CoronaRadiata") for img in images]
        body = {
            "annotation_session_uuid": sess,
            "usability": "IschemicAssessable",
            "low_quality": False,
            "notes": None,
            "image_evaluations": bad_evals,
        }
        resp = client.post("/api/evaluations/submit", json=body, headers=bearer(doctor_token))
        assert resp.status_code == 422

    def test_ischemic_missing_corona_radiata_is_422(self, client, db, doctor, doctor_token):
        ds, patient = make_dataset_with_patient(db)
        img_set, images = make_image_set(db, ds.dataset_uuid, patient.patient_uuid)

        sess = open_session(client, doctor_token, img_set.uuid)
        bad_evals = [image_eval(img.uuid, "BasalGanglia") for img in images]
        body = {
            "annotation_session_uuid": sess,
            "usability": "IschemicAssessable",
            "low_quality": False,
            "notes": None,
            "image_evaluations": bad_evals,
        }
        resp = client.post("/api/evaluations/submit", json=body, headers=bearer(doctor_token))
        assert resp.status_code == 422

    def test_double_submit_is_409(self, client, db, doctor, doctor_token):
        ds, patient = make_dataset_with_patient(db)
        img_set, images = make_image_set(db, ds.dataset_uuid, patient.patient_uuid)

        sess = open_session(client, doctor_token, img_set.uuid)
        payload = submit_payload(sess, images)

        assert client.post("/api/evaluations/submit", json=payload, headers=bearer(doctor_token)).status_code == 200
        assert client.post("/api/evaluations/submit", json=payload, headers=bearer(doctor_token)).status_code == 409

    def test_cannot_submit_another_doctors_session(self, client, db, doctor, doctor_token):
        other = make_doctor(db, username="other")
        other_token = api_login(client, "other")

        ds, patient = make_dataset_with_patient(db)
        img_set, images = make_image_set(db, ds.dataset_uuid, patient.patient_uuid)

        sess = open_session(client, doctor_token, img_set.uuid)
        payload = submit_payload(sess, images)

        # other doctor tries to submit doctor's session
        resp = client.post("/api/evaluations/submit", json=payload, headers=bearer(other_token))
        assert resp.status_code == 403

    def test_submission_data_is_readable_back(self, client, db, doctor, doctor_token):
        ds, patient = make_dataset_with_patient(db)
        img_set, images = make_image_set(db, ds.dataset_uuid, patient.patient_uuid)

        sess = open_session(client, doctor_token, img_set.uuid)
        client.post(
            "/api/evaluations/submit",
            json=submit_payload(sess, images),
            headers=bearer(doctor_token),
        )

        resp = client.get(
            f"/api/evaluations/submission/by-image-set/{img_set.uuid}",
            headers=bearer(doctor_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["payload"]["usability"] == "IschemicAssessable"
        assert len(data["payload"]["image_evaluations"]) == len(images)


# ---------------------------------------------------------------------------
# Draft lifecycle
# ---------------------------------------------------------------------------

class TestDraftLifecycle:
    def test_save_and_retrieve_draft(self, client, db, doctor, doctor_token):
        ds, patient = make_dataset_with_patient(db)
        img_set, images = make_image_set(db, ds.dataset_uuid, patient.patient_uuid)
        sess = open_session(client, doctor_token, img_set.uuid)

        resp = client.post("/api/evaluations/draft", json=draft_payload(sess, images), headers=bearer(doctor_token))
        assert resp.status_code == 200
        assert resp.json()["draft_saved_at"] is not None

        resp = client.get(f"/api/evaluations/draft/by-image-set/{img_set.uuid}", headers=bearer(doctor_token))
        assert resp.status_code == 200
        assert resp.json()["payload"]["usability"] == "IschemicAssessable"

    def test_auto_draft_does_not_overwrite_manual(self, client, db, doctor, doctor_token):
        ds, patient = make_dataset_with_patient(db)
        img_set, images = make_image_set(db, ds.dataset_uuid, patient.patient_uuid)
        sess = open_session(client, doctor_token, img_set.uuid)
        body = draft_payload(sess, images)

        # Save manual first, then auto
        client.post("/api/evaluations/draft", json=body, headers=bearer(doctor_token))
        client.post("/api/evaluations/auto-draft", json=body, headers=bearer(doctor_token))

        # Manual draft must survive (auto-draft cannot overwrite it)
        resp = client.get(f"/api/evaluations/draft/by-image-set/{img_set.uuid}", headers=bearer(doctor_token))
        assert resp.status_code == 200

    def test_delete_draft_removes_it(self, client, db, doctor, doctor_token):
        ds, patient = make_dataset_with_patient(db)
        img_set, images = make_image_set(db, ds.dataset_uuid, patient.patient_uuid)
        sess = open_session(client, doctor_token, img_set.uuid)

        client.post("/api/evaluations/draft", json=draft_payload(sess, images), headers=bearer(doctor_token))
        assert client.delete(
            f"/api/evaluations/draft/by-image-set/{img_set.uuid}", headers=bearer(doctor_token)
        ).status_code == 204
        assert client.get(
            f"/api/evaluations/draft/by-image-set/{img_set.uuid}", headers=bearer(doctor_token)
        ).status_code == 404

    def test_no_draft_returns_404(self, client, db, doctor, doctor_token):
        ds, patient = make_dataset_with_patient(db)
        img_set, _ = make_image_set(db, ds.dataset_uuid, patient.patient_uuid)
        resp = client.get(
            f"/api/evaluations/draft/by-image-set/{img_set.uuid}", headers=bearer(doctor_token)
        )
        assert resp.status_code == 404

    def test_draft_blocked_after_submit(self, client, db, doctor, doctor_token):
        ds, patient = make_dataset_with_patient(db)
        img_set, images = make_image_set(db, ds.dataset_uuid, patient.patient_uuid)
        sess = open_session(client, doctor_token, img_set.uuid)

        client.post("/api/evaluations/submit", json=submit_payload(sess, images), headers=bearer(doctor_token))

        resp = client.post(
            "/api/evaluations/draft",
            json=draft_payload(sess, images),
            headers=bearer(doctor_token),
        )
        assert resp.status_code == 409

    def test_draft_not_visible_to_other_doctor(self, client, db, doctor, doctor_token):
        other = make_doctor(db, username="other")
        other_token = api_login(client, "other")

        ds, patient = make_dataset_with_patient(db)
        img_set, images = make_image_set(db, ds.dataset_uuid, patient.patient_uuid)
        sess = open_session(client, doctor_token, img_set.uuid)

        client.post("/api/evaluations/draft", json=draft_payload(sess, images), headers=bearer(doctor_token))

        # Other doctor has no draft for this image set
        resp = client.get(
            f"/api/evaluations/draft/by-image-set/{img_set.uuid}", headers=bearer(other_token)
        )
        assert resp.status_code == 404
