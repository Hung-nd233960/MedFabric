"""Auth endpoint tests — login, logout, session invalidation, password flows."""

from tests.conftest import api_login, bearer, make_doctor
from app.db.models import DoctorRole


class TestLogin:
    def test_success_returns_token(self, client, doctor):
        resp = client.post("/api/auth/login", json={"username": "doc1", "password": "pass123!"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["must_change_password"] is False
        assert data["must_set_name"] is False

    def test_wrong_password_is_401(self, client, doctor):
        resp = client.post("/api/auth/login", json={"username": "doc1", "password": "wrong"})
        assert resp.status_code == 401

    def test_unknown_user_is_401(self, client):
        resp = client.post("/api/auth/login", json={"username": "ghost", "password": "x"})
        assert resp.status_code == 401

    def test_inactive_account_is_403(self, client, db):
        make_doctor(db, username="inactive", is_active=False)
        resp = client.post("/api/auth/login", json={"username": "inactive", "password": "pass123!"})
        assert resp.status_code == 403

    def test_must_change_password_flag_surfaced(self, client, db):
        make_doctor(db, username="forced", must_change_password=True)
        resp = client.post("/api/auth/login", json={"username": "forced", "password": "pass123!"})
        assert resp.status_code == 200
        assert resp.json()["must_change_password"] is True


class TestMe:
    def test_returns_profile(self, client, doctor, doctor_token):
        resp = client.get("/api/auth/me", headers=bearer(doctor_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "doc1"
        assert data["role"] == "Doctor"

    def test_unauthenticated_is_401(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_malformed_token_is_401(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.token"})
        assert resp.status_code == 401


class TestLogout:
    def test_logout_invalidates_session(self, client, doctor, doctor_token):
        # Token works before logout
        assert client.get("/api/auth/me", headers=bearer(doctor_token)).status_code == 200

        resp = client.post("/api/auth/logout", headers=bearer(doctor_token))
        assert resp.status_code == 204

        # Same token is now rejected because the LoginSession is deactivated
        assert client.get("/api/auth/me", headers=bearer(doctor_token)).status_code == 401


class TestChangePassword:
    def test_change_password_success(self, client, doctor, doctor_token):
        resp = client.post(
            "/api/auth/change-password",
            json={"current_password": "pass123!", "new_password": "newpass456!"},
            headers=bearer(doctor_token),
        )
        assert resp.status_code == 204

        # Old password no longer works
        assert client.post(
            "/api/auth/login", json={"username": "doc1", "password": "pass123!"}
        ).status_code == 401

        # New password works
        assert client.post(
            "/api/auth/login", json={"username": "doc1", "password": "newpass456!"}
        ).status_code == 200

    def test_wrong_current_password_is_401(self, client, doctor, doctor_token):
        resp = client.post(
            "/api/auth/change-password",
            json={"current_password": "wrong", "new_password": "newpass456!"},
            headers=bearer(doctor_token),
        )
        assert resp.status_code == 401

    def test_missing_current_password_is_400(self, client, doctor, doctor_token):
        resp = client.post(
            "/api/auth/change-password",
            json={"new_password": "newpass456!"},
            headers=bearer(doctor_token),
        )
        assert resp.status_code == 400


class TestAdminAccess:
    def test_doctor_cannot_hit_admin_endpoints(self, client, doctor, doctor_token):
        resp = client.get("/api/admin/doctors", headers=bearer(doctor_token))
        assert resp.status_code == 403

    def test_admin_can_hit_admin_endpoints(self, client, admin, admin_token):
        resp = client.get("/api/admin/doctors", headers=bearer(admin_token))
        assert resp.status_code == 200
