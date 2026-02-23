"""
Tests for server CRUD, membership management, and role/ownership transfers.

Covers:
  - POST /api/servers (create)
  - GET  /api/servers (list my servers)
  - GET  /api/servers/{id}
  - PATCH /api/servers/{id} (update, including icon_url validation)
  - DELETE /api/servers/{id}
  - GET  /api/servers/{id}/members
  - DELETE /api/servers/{id}/members/{uid}
  - PATCH /api/servers/{id}/members/{uid}/role
  - POST /api/servers/{id}/transfer-ownership
"""

from fastapi.testclient import TestClient

from app.models.user import User
from app.tests.conftest import auth_headers, get_server_id


def _grant_create(db, username: str) -> None:
    """Grant can_create_server permission to a user."""
    user = db.query(User).filter(User.username == username).first()
    assert user is not None
    user.can_create_server = True
    db.commit()


def _create_server(client, headers, db, username, name="My Server", slug=None):
    _grant_create(db, username)
    if slug is None:
        slug = name.lower().replace(" ", "")
    resp = client.post(
        "/api/servers",
        json={"name": name, "slug": slug, "description": "desc"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()


def _create_invite(client, headers, server_id):
    resp = client.post(f"/api/servers/{server_id}/invites", json={}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Create / List / Get
# ---------------------------------------------------------------------------


class TestServerCRUD:
    def test_create_server(self, client: TestClient, db):
        headers = auth_headers(client, username="creator1", email="creator1@example.com")
        _grant_create(db, "creator1")
        resp = client.post(
            "/api/servers",
            json={"name": "Alpha", "slug": "alphaserver", "description": "test"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Alpha"
        assert data["slug"] == "alphaserver"
        assert data["member_count"] == 1
        assert data["current_user_role"] == "owner"

    def test_create_server_slug_conflict(self, client: TestClient, db):
        headers = auth_headers(client, username="creator2", email="creator2@example.com")
        _grant_create(db, "creator2")
        client.post("/api/servers", json={"name": "Beta", "slug": "betaslug"}, headers=headers)
        resp = client.post(
            "/api/servers",
            json={"name": "Beta 2", "slug": "betaslug"},
            headers=headers,
        )
        assert resp.status_code == 409

    def test_create_server_invalid_slug(self, client: TestClient, db):
        headers = auth_headers(client, username="creator3", email="creator3@example.com")
        _grant_create(db, "creator3")
        resp = client.post(
            "/api/servers",
            json={"name": "Bad", "slug": "UPPERCASE"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_create_server_requires_permission(self, client: TestClient):
        headers = auth_headers(client, username="noperm", email="noperm@example.com")
        resp = client.post(
            "/api/servers",
            json={"name": "Blocked", "slug": "blocked"},
            headers=headers,
        )
        assert resp.status_code == 403

    def test_list_my_servers_includes_created(self, client: TestClient, db):
        headers = auth_headers(client, username="lister1", email="lister1@example.com")
        _create_server(client, headers, db, "lister1", name="Listable", slug="listablesrv")
        resp = client.get("/api/servers", headers=headers)
        assert resp.status_code == 200
        slugs = [s["slug"] for s in resp.json()]
        assert "listablesrv" in slugs

    def test_get_server(self, client: TestClient, db):
        headers = auth_headers(client, username="getter1", email="getter1@example.com")
        server = _create_server(client, headers, db, "getter1", slug="gettersrv")
        resp = client.get(f"/api/servers/{server['id']}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == server["id"]
        assert resp.json()["member_count"] >= 1

    def test_get_server_requires_membership(self, client: TestClient, db):
        h1 = auth_headers(client, username="ownerget", email="ownerget@example.com")
        h2 = auth_headers(client, username="outsiderget", email="outsiderget@example.com")
        server = _create_server(client, h1, db, "ownerget", slug="privateget")
        resp = client.get(f"/api/servers/{server['id']}", headers=h2)
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


class TestServerUpdate:
    def test_update_name(self, client: TestClient, db):
        headers = auth_headers(client, username="upd1", email="upd1@example.com")
        server = _create_server(client, headers, db, "upd1", slug="updnamesrv")
        resp = client.patch(
            f"/api/servers/{server['id']}",
            json={"name": "Renamed"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed"

    def test_update_icon_url_valid(self, client: TestClient, db):
        headers = auth_headers(client, username="upd2", email="upd2@example.com")
        server = _create_server(client, headers, db, "upd2", slug="iconvalidsrv")
        resp = client.patch(
            f"/api/servers/{server['id']}",
            json={"icon_url": "https://example.com/icon.png"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["icon_url"] == "https://example.com/icon.png"

    def test_update_icon_url_invalid_scheme(self, client: TestClient, db):
        headers = auth_headers(client, username="upd3", email="upd3@example.com")
        server = _create_server(client, headers, db, "upd3", slug="iconinvalidsrv")
        resp = client.patch(
            f"/api/servers/{server['id']}",
            json={"icon_url": "javascript:alert(1)"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_update_icon_url_relative_rejected(self, client: TestClient, db):
        headers = auth_headers(client, username="upd4", email="upd4@example.com")
        server = _create_server(client, headers, db, "upd4", slug="iconrelativesrv")
        resp = client.patch(
            f"/api/servers/{server['id']}",
            json={"icon_url": "/local/path.png"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_update_requires_admin(self, client: TestClient, db):
        h_owner = auth_headers(client, username="updowner", email="updowner@example.com")
        h_member = auth_headers(client, username="updmember", email="updmember@example.com")
        server = _create_server(client, h_owner, db, "updowner", slug="updateadminsrv")
        invite = _create_invite(client, h_owner, server["id"])
        client.post(f"/api/invites/{invite['code']}/redeem", headers=h_member)

        resp = client.patch(
            f"/api/servers/{server['id']}",
            json={"name": "Hacked"},
            headers=h_member,
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class TestServerDelete:
    def test_delete_server(self, client: TestClient, db):
        headers = auth_headers(client, username="del1", email="del1@example.com")
        server = _create_server(client, headers, db, "del1", slug="deletablesrv")
        resp = client.delete(f"/api/servers/{server['id']}", headers=headers)
        assert resp.status_code == 204

    def test_delete_server_non_owner_rejected(self, client: TestClient, db):
        h_owner = auth_headers(client, username="delown", email="delown@example.com")
        h_other = auth_headers(client, username="deloth", email="deloth@example.com")
        server = _create_server(client, h_owner, db, "delown", slug="nodeletesrv")
        resp = client.delete(f"/api/servers/{server['id']}", headers=h_other)
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


class TestServerMembers:
    def test_list_members(self, client: TestClient, db):
        headers = auth_headers(client, username="memlist1", email="memlist1@example.com")
        server = _create_server(client, headers, db, "memlist1", slug="memlistsrv")
        resp = client.get(f"/api/servers/{server['id']}/members", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1
        roles = [m["role"] for m in resp.json()]
        assert "owner" in roles

    def test_update_member_role(self, client: TestClient, db):
        h_owner = auth_headers(client, username="roleowner", email="roleowner@example.com")
        h_member = auth_headers(client, username="rolemember", email="rolemember@example.com")
        server = _create_server(client, h_owner, db, "roleowner", slug="rolesrv")

        invite = _create_invite(client, h_owner, server["id"])
        client.post(f"/api/invites/{invite['code']}/redeem", headers=h_member)

        me = client.get("/api/auth/me", headers=h_member).json()
        resp = client.patch(
            f"/api/servers/{server['id']}/members/{me['id']}/role",
            json={"role": "admin"},
            headers=h_owner,
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    def test_update_role_invalid_value(self, client: TestClient):
        headers = auth_headers(client, username="badrole", email="badrole@example.com")
        sid = get_server_id(client, headers)
        me = client.get("/api/auth/me", headers=headers).json()
        resp = client.patch(
            f"/api/servers/{sid}/members/{me['id']}/role",
            json={"role": "superadmin"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_transfer_ownership(self, client: TestClient, db):
        h_owner = auth_headers(client, username="xferowner", email="xferowner@example.com")
        h_new = auth_headers(client, username="xfernew", email="xfernew@example.com")
        server = _create_server(client, h_owner, db, "xferowner", slug="xfersrv")

        invite = _create_invite(client, h_owner, server["id"])
        client.post(f"/api/invites/{invite['code']}/redeem", headers=h_new)

        new_user = client.get("/api/auth/me", headers=h_new).json()
        resp = client.post(
            f"/api/servers/{server['id']}/transfer-ownership",
            json={"new_owner_id": new_user["id"]},
            headers=h_owner,
        )
        assert resp.status_code == 200
        assert resp.json()["new_owner_id"] == new_user["id"]

    def test_transfer_ownership_non_member_rejected(self, client: TestClient, db):
        h_owner = auth_headers(client, username="xfailowner", email="xfailowner@example.com")
        h_stranger = auth_headers(client, username="xfailstr", email="xfailstr@example.com")
        server = _create_server(client, h_owner, db, "xfailowner", slug="xfailsrv")

        stranger = client.get("/api/auth/me", headers=h_stranger).json()
        resp = client.post(
            f"/api/servers/{server['id']}/transfer-ownership",
            json={"new_owner_id": stranger["id"]},
            headers=h_owner,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Icon upload
# ---------------------------------------------------------------------------


class TestServerIconUpload:
    def test_upload_icon_sets_icon_url(self, client: TestClient, db):
        headers = auth_headers(client, username="iconown", email="iconown@example.com")
        server = _create_server(client, headers, db, "iconown", slug="iconsrv")
        png_1px = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
            b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        resp = client.post(
            f"/api/servers/{server['id']}/icon",
            headers=headers,
            files={"file": ("icon.png", png_1px, "image/png")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["icon_url"].startswith("/uploads/")
        assert data["id"] == server["id"]

    def test_upload_icon_non_member_forbidden(self, client: TestClient, db):
        h_owner = auth_headers(client, username="iconown2", email="iconown2@example.com")
        h_other = auth_headers(client, username="iconoth", email="iconoth@example.com")
        server = _create_server(client, h_owner, db, "iconown2", slug="iconsrv2")
        png_1px = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        resp = client.post(
            f"/api/servers/{server['id']}/icon",
            headers=h_other,
            files={"file": ("icon.png", png_1px, "image/png")},
        )
        assert resp.status_code in (403, 404)

    def test_upload_icon_wrong_mime_type_rejected(self, client: TestClient, db):
        headers = auth_headers(client, username="iconmime", email="iconmime@example.com")
        server = _create_server(client, headers, db, "iconmime", slug="iconmimesrv")
        resp = client.post(
            f"/api/servers/{server['id']}/icon",
            headers=headers,
            files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert resp.status_code == 415
