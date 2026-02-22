"""
Tests for the invite system.

Covers:
  - POST /api/servers/{id}/invites  (create, admin-only)
  - GET  /api/invites/{code}         (preview, public)
  - POST /api/invites/{code}/redeem  (redeem, auth required)
  - DELETE /api/servers/{id}/invites/{code} (revoke, admin-only)
  - Expiry, max-uses, idempotent redeem
"""

from fastapi.testclient import TestClient

from app.models.user import User
from app.tests.conftest import auth_headers


def _grant_create(db, username: str) -> None:
    user = db.query(User).filter(User.username == username).first()
    assert user is not None
    user.can_create_server = True
    db.commit()


def _create_server(client, headers, db, username, slug="invitesrv"):
    _grant_create(db, username)
    resp = client.post(
        "/api/servers",
        json={"name": "Invite Test", "slug": slug},
        headers=headers,
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()


def _create_invite(client, headers, server_id, **kwargs):
    resp = client.post(
        f"/api/servers/{server_id}/invites",
        json=kwargs,
        headers=headers,
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()


# ---------------------------------------------------------------------------
# Create invite
# ---------------------------------------------------------------------------


class TestCreateInvite:
    def test_create_invite_as_owner(self, client: TestClient, db):
        headers = auth_headers(client, username="inv_owner1", email="inv_owner1@example.com")
        server = _create_server(client, headers, db, "inv_owner1", slug="cinv-srv1")
        resp = client.post(f"/api/servers/{server['id']}/invites", json={}, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert "code" in data
        assert data["use_count"] == 0

    def test_create_invite_with_max_uses(self, client: TestClient, db):
        headers = auth_headers(client, username="inv_maxu", email="inv_maxu@example.com")
        server = _create_server(client, headers, db, "inv_maxu", slug="cinv-maxu")
        data = _create_invite(client, headers, server["id"], max_uses=3)
        assert data["max_uses"] == 3

    def test_create_invite_with_expiry(self, client: TestClient, db):
        headers = auth_headers(client, username="inv_exp1", email="inv_exp1@example.com")
        server = _create_server(client, headers, db, "inv_exp1", slug="cinv-exp1")
        data = _create_invite(client, headers, server["id"], expires_in_hours=24)
        assert data["expires_at"] is not None

    def test_create_invite_requires_admin(self, client: TestClient, db):
        h_owner = auth_headers(client, username="inv_adm_own", email="inv_adm_own@example.com")
        h_member = auth_headers(client, username="inv_adm_mem", email="inv_adm_mem@example.com")
        server = _create_server(client, h_owner, db, "inv_adm_own", slug="cinv-admin")

        # Member joins via existing invite from owner
        invite = _create_invite(client, h_owner, server["id"])
        client.post(f"/api/invites/{invite['code']}/redeem", headers=h_member)

        # Member (not admin) tries to create another invite
        resp = client.post(f"/api/servers/{server['id']}/invites", json={}, headers=h_member)
        assert resp.status_code == 403

    def test_create_invite_max_uses_must_be_positive(self, client: TestClient, db):
        headers = auth_headers(client, username="inv_pos", email="inv_pos@example.com")
        server = _create_server(client, headers, db, "inv_pos", slug="cinv-pos")
        resp = client.post(
            f"/api/servers/{server['id']}/invites",
            json={"max_uses": 0},
            headers=headers,
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Preview invite
# ---------------------------------------------------------------------------


class TestPreviewInvite:
    def test_preview_returns_server_info(self, client: TestClient, db):
        headers = auth_headers(client, username="prev1", email="prev1@example.com")
        server = _create_server(client, headers, db, "prev1", slug="prev-srv1")
        invite = _create_invite(client, headers, server["id"])

        resp = client.get(f"/api/invites/{invite['code']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["server_name"] == "Invite Test"
        assert data["member_count"] >= 1

    def test_preview_not_found(self, client: TestClient):
        resp = client.get("/api/invites/no-such-code")
        assert resp.status_code == 404

    def test_preview_revoked_returns_410(self, client: TestClient, db):
        headers = auth_headers(client, username="prev2", email="prev2@example.com")
        server = _create_server(client, headers, db, "prev2", slug="prev-srv2")
        invite = _create_invite(client, headers, server["id"])

        client.delete(f"/api/servers/{server['id']}/invites/{invite['code']}", headers=headers)
        resp = client.get(f"/api/invites/{invite['code']}")
        assert resp.status_code == 410


# ---------------------------------------------------------------------------
# Redeem invite
# ---------------------------------------------------------------------------


class TestRedeemInvite:
    def test_redeem_adds_membership(self, client: TestClient, db):
        h_owner = auth_headers(client, username="rdm_owner", email="rdm_owner@example.com")
        h_joiner = auth_headers(client, username="rdm_joiner", email="rdm_joiner@example.com")
        server = _create_server(client, h_owner, db, "rdm_owner", slug="rdm-srv")
        invite = _create_invite(client, h_owner, server["id"])

        resp = client.post(f"/api/invites/{invite['code']}/redeem", headers=h_joiner)
        assert resp.status_code == 200
        assert resp.json()["already_member"] is False
        assert resp.json()["server_id"] == server["id"]

    def test_redeem_idempotent_for_existing_member(self, client: TestClient, db):
        h_owner = auth_headers(client, username="rdm_idem_own", email="rdm_idem_own@example.com")
        h_joiner = auth_headers(client, username="rdm_idem_join", email="rdm_idem_join@example.com")
        server = _create_server(client, h_owner, db, "rdm_idem_own", slug="rdm-idem-srv")
        invite = _create_invite(client, h_owner, server["id"])

        client.post(f"/api/invites/{invite['code']}/redeem", headers=h_joiner)
        resp = client.post(f"/api/invites/{invite['code']}/redeem", headers=h_joiner)
        assert resp.status_code == 200
        assert resp.json()["already_member"] is True

    def test_redeem_max_uses_exhausted_returns_410(self, client: TestClient, db):
        h_owner = auth_headers(client, username="rdm_max_own", email="rdm_max_own@example.com")
        h_j1 = auth_headers(client, username="rdm_max_j1", email="rdm_max_j1@example.com")
        h_j2 = auth_headers(client, username="rdm_max_j2", email="rdm_max_j2@example.com")
        server = _create_server(client, h_owner, db, "rdm_max_own", slug="rdm-max-srv")
        invite = _create_invite(client, h_owner, server["id"], max_uses=1)

        client.post(f"/api/invites/{invite['code']}/redeem", headers=h_j1)
        resp = client.post(f"/api/invites/{invite['code']}/redeem", headers=h_j2)
        assert resp.status_code == 410

    def test_redeem_requires_auth(self, client: TestClient, db):
        headers = auth_headers(client, username="rdm_auth", email="rdm_auth@example.com")
        server = _create_server(client, headers, db, "rdm_auth", slug="rdm-auth-srv")
        invite = _create_invite(client, headers, server["id"])

        resp = client.post(f"/api/invites/{invite['code']}/redeem")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Revoke invite
# ---------------------------------------------------------------------------


class TestRevokeInvite:
    def test_revoke_invite(self, client: TestClient, db):
        headers = auth_headers(client, username="rev1", email="rev1@example.com")
        server = _create_server(client, headers, db, "rev1", slug="rev-srv1")
        invite = _create_invite(client, headers, server["id"])

        resp = client.delete(f"/api/servers/{server['id']}/invites/{invite['code']}", headers=headers)
        assert resp.status_code == 204

        # Subsequent preview should return 410
        resp = client.get(f"/api/invites/{invite['code']}")
        assert resp.status_code == 410

    def test_revoke_requires_admin(self, client: TestClient, db):
        h_owner = auth_headers(client, username="rev_own", email="rev_own@example.com")
        h_member = auth_headers(client, username="rev_mem", email="rev_mem@example.com")
        server = _create_server(client, h_owner, db, "rev_own", slug="rev-adm-srv")
        invite = _create_invite(client, h_owner, server["id"])
        client.post(f"/api/invites/{invite['code']}/redeem", headers=h_member)

        invite2 = _create_invite(client, h_owner, server["id"])
        resp = client.delete(f"/api/servers/{server['id']}/invites/{invite2['code']}", headers=h_member)
        assert resp.status_code == 403
