"""Offline tests: queue validation, scheduling rules and the HTTP flow of each
platform, with every network call mocked."""
import json
from pathlib import Path
from unittest import mock

import pytest
import yaml

from autopilot import main as cli
from autopilot.platforms import facebook, instagram, tiktok, youtube
from autopilot.queue import QueueError, load_queue


def make_post(root: Path, name="tinynotes/2026-11-02_1500_a", when="2026-11-02T15:00:00+01:00", platforms=None):
    folder = root / name
    folder.mkdir(parents=True)
    for f in ("a.png", "b.png", "v.mp4"):
        (folder / f).write_bytes(b"x" * 10)
    spec = {"brand": "tinynotes", "publish_at": when, "platforms": platforms or {
        "instagram": {"kind": "carousel", "media": ["a.png", "b.png"], "caption": "hi\n\n#tag"},
        "tiktok": {"kind": "photo", "media": ["a.png"], "caption": "title line\nmore"},
    }}
    (folder / "post.yaml").write_text(yaml.safe_dump(spec))
    return folder


class Resp:
    def __init__(self, body, status=200, headers=None):
        self._b, self.status_code, self.headers = body, status, headers or {}
        self.ok, self.text = status < 400, json.dumps(body)

    def json(self):
        return self._b


def test_queue_validation(tmp_path):
    make_post(tmp_path)
    assert len(load_queue(tmp_path)) == 1
    make_post(tmp_path, "tinynotes/bad", platforms={"instagram": {"kind": "carousel", "media": ["a.png"]}})
    with pytest.raises(QueueError, match="2-10"):
        load_queue(tmp_path)


def test_timezone_required(tmp_path):
    make_post(tmp_path, when="2026-11-02T15:00:00")
    with pytest.raises(QueueError, match="timezone"):
        load_queue(tmp_path)


def test_due_late_and_dry_run(tmp_path, capsys):
    content, state = tmp_path / "c", tmp_path / "s.json"
    make_post(content, "tinynotes/early", when="2026-11-02T15:00:00+01:00")
    make_post(content, "tinynotes/future", when="2026-11-09T15:00:00+01:00")
    rc = cli.main(["--content", str(content), "--state", str(state), "--dry-run", "--now", "2026-11-02T16:00:00+01:00"])
    out = capsys.readouterr().out
    assert rc == 0 and "early -> instagram" in out and "future" not in out and not state.exists()
    # a day late -> skipped, never posted
    with mock.patch.dict(cli.PUBLISHERS, {"instagram": mock.Mock(), "tiktok": mock.Mock()}) as pubs:
        cli.main(["--content", str(content), "--state", str(state), "--now", "2026-11-03T16:00:00+01:00"])
        assert not pubs["instagram"].called
    assert json.loads(state.read_text())["tinynotes/early::instagram"]["status"] == "skipped"


def test_publish_once_and_retry(tmp_path):
    content, state = tmp_path / "c", tmp_path / "s.json"
    make_post(content)
    ig = mock.Mock(return_value=("1", "https://ig/p/1"))
    tt = mock.Mock(side_effect=RuntimeError("boom"))
    with mock.patch.dict(cli.PUBLISHERS, {"instagram": ig, "tiktok": tt}):
        args = ["--content", str(content), "--state", str(state), "--now", "2026-11-02T15:30:00+01:00"]
        assert cli.main(args) == 1
        cli.main(args)
        cli.main(args)
        cli.main(args)
    assert ig.call_count == 1          # published once, never repeated
    assert tt.call_count == 3          # retried up to MAX_ATTEMPTS, then left alone
    s = json.loads(state.read_text())
    assert s["tinynotes/2026-11-02_1500_a::tiktok"]["status"] == "failed"


def test_instagram_carousel_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("TINYNOTES_IG_USER_ID", "17841")
    monkeypatch.setenv("TINYNOTES_IG_TOKEN", "tok")
    monkeypatch.setenv("MEDIA_BASE_URL", "https://me.github.io/repo")
    make_post(tmp_path)
    post = load_queue(tmp_path)[0]
    posts, ids = [], iter(["c1", "c2", "car", "pub"])

    def fake_post(url, data=None, **kw):
        posts.append((url, data))
        return Resp({"id": next(ids)})

    def fake_get(url, params=None, **kw):
        return Resp({"status_code": "FINISHED", "permalink": "https://instagram.com/p/x"})

    monkeypatch.setattr(instagram.requests, "post", fake_post)
    monkeypatch.setattr(instagram.requests, "get", fake_get)
    media_id, link = instagram.publish(post, post.platforms["instagram"], tmp_path)
    assert media_id == "pub" and link.endswith("/p/x")
    assert posts[0][1]["image_url"] == "https://me.github.io/repo/tinynotes/2026-11-02_1500_a/a.jpg"
    assert posts[0][1]["is_carousel_item"] == "true"
    assert posts[2][1]["media_type"] == "CAROUSEL" and posts[2][1]["children"] == "c1,c2"
    assert posts[3][0].endswith("/17841/media_publish")


def test_tiktok_photo_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("TINYNOTES_TT_REFRESH_TOKEN", "r")
    monkeypatch.setenv("MEDIA_BASE_URL", "https://me.github.io/repo")
    monkeypatch.delenv("TIKTOK_PRIVACY", raising=False)
    make_post(tmp_path)
    post = load_queue(tmp_path)[0]
    sent = {}

    def fake_post(url, json=None, data=None, headers=None, **kw):
        ok = {"error": {"code": "ok"}}
        if url.endswith("/oauth/token/"):
            return Resp({"access_token": "a"})
        if url.endswith("creator_info/query/"):
            return Resp({**ok, "data": {"privacy_level_options": ["SELF_ONLY", "PUBLIC_TO_EVERYONE"]}})
        if url.endswith("content/init/"):
            sent.update(json)
            return Resp({**ok, "data": {"publish_id": "p1"}})
        if url.endswith("status/fetch/"):
            return Resp({**ok, "data": {"status": "PUBLISH_COMPLETE"}})
        raise AssertionError(url)

    monkeypatch.setattr(tiktok.requests, "post", fake_post)
    pid, _ = tiktok.publish(post, post.platforms["tiktok"], tmp_path)
    assert pid == "p1"
    assert sent["post_info"]["privacy_level"] == "SELF_ONLY"   # private until the app is audited
    assert sent["post_info"]["title"] == "title line"
    assert sent["source_info"]["photo_images"][0].endswith("/a.jpg")


def test_tiktok_video_chunking(tmp_path, monkeypatch):
    monkeypatch.setenv("FACTYEAP_TT_REFRESH_TOKEN", "r")
    folder = make_post(tmp_path, "factyeap/v", platforms={"tiktok": {"kind": "video", "media": ["v.mp4"], "caption": "c"}})
    (folder / "v.mp4").write_bytes(b"0" * (25 * 1024 * 1024 + 7))
    spec = yaml.safe_load((folder / "post.yaml").read_text()); spec["brand"] = "factyeap"
    (folder / "post.yaml").write_text(yaml.safe_dump(spec))
    post = load_queue(tmp_path)[0]
    init, ranges = {}, []

    def fake_post(url, json=None, data=None, headers=None, **kw):
        ok = {"error": {"code": "ok"}}
        if url.endswith("/oauth/token/"):
            return Resp({"access_token": "a"})
        if url.endswith("creator_info/query/"):
            return Resp({**ok, "data": {"privacy_level_options": ["SELF_ONLY"]}})
        if url.endswith("video/init/"):
            init.update(json)
            return Resp({**ok, "data": {"publish_id": "v1", "upload_url": "https://up"}})
        return Resp({**ok, "data": {"status": "PUBLISH_COMPLETE"}})

    def fake_put(url, data=None, headers=None, **kw):
        ranges.append(headers["Content-Range"])
        return Resp({}, 206)

    monkeypatch.setattr(tiktok.requests, "post", fake_post)
    monkeypatch.setattr(tiktok.requests, "put", fake_put)
    tiktok.publish(post, post.platforms["tiktok"], tmp_path)
    size = 25 * 1024 * 1024 + 7
    assert init["source_info"]["total_chunk_count"] == 2 and init["post_info"]["is_aigc"] is True
    assert ranges[-1].endswith(f"-{size - 1}/{size}")


def test_youtube_upload_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("FACTYEAP_YT_REFRESH_TOKEN", "r")
    folder = make_post(tmp_path, "factyeap/s", platforms={"youtube": {"kind": "short", "media": ["v.mp4"], "title": "Honey thief", "description": "d"}})
    spec = yaml.safe_load((folder / "post.yaml").read_text()); spec["brand"] = "factyeap"
    (folder / "post.yaml").write_text(yaml.safe_dump(spec))
    post = load_queue(tmp_path)[0]
    meta = {}

    def fake_post(url, data=None, json=None, **kw):
        if "oauth2" in url:
            return Resp({"access_token": "a"})
        meta.update(json)
        return Resp({}, 200, {"Location": "https://upload/session"})

    monkeypatch.setattr(youtube.requests, "post", fake_post)
    monkeypatch.setattr(youtube.requests, "put", lambda *a, **k: Resp({"id": "abc"}))
    vid, url = youtube.publish(post, post.platforms["youtube"], tmp_path)
    assert url == "https://youtube.com/shorts/abc"
    assert meta["snippet"]["title"] == "Honey thief #shorts"
    assert meta["status"]["containsSyntheticMedia"] is True


def test_missing_secrets_wait_without_burning_attempts(tmp_path, monkeypatch):
    for k in ("TINYNOTES_IG_TOKEN", "TINYNOTES_IG_USER_ID", "TINYNOTES_TT_REFRESH_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    content, state = tmp_path / "c", tmp_path / "s.json"
    make_post(content)
    args = ["--content", str(content), "--state", str(state), "--now", "2026-11-02T15:30:00+01:00"]
    for _ in range(4):
        assert cli.main(args) == 0
    assert not state.exists() or json.loads(state.read_text()) == {}


def test_instagram_login_token_uses_instagram_host():
    assert instagram.api_base("IGAAabc").startswith("https://graph.instagram.com/")
    assert instagram.api_base("EAAGxyz").startswith("https://graph.facebook.com/")


def test_instagram_access_error_waits(tmp_path, monkeypatch):
    from autopilot.platforms.base import NotConfigured
    monkeypatch.setenv("FACTYEAP_IG_USER_ID", "1")
    monkeypatch.setenv("FACTYEAP_IG_TOKEN", "EAAx")
    monkeypatch.setenv("MEDIA_BASE_URL", "https://x")
    folder = make_post(tmp_path, "factyeap/a", platforms={"instagram": {"kind": "image", "media": ["a.png"], "caption": "c"}})
    spec = yaml.safe_load((folder / "post.yaml").read_text()); spec["brand"] = "factyeap"
    (folder / "post.yaml").write_text(yaml.safe_dump(spec))
    post = load_queue(tmp_path)[0]
    err = Resp({"error": {"message": "Unsupported post request. Object with ID '1' does not exist, cannot be loaded due to missing permissions"}}, 400,
               {"content-type": "application/json"})
    monkeypatch.setattr(instagram.requests, "post", lambda *a, **k: err)
    with pytest.raises(NotConfigured):
        instagram.publish(post, post.platforms["instagram"], tmp_path)


def test_facebook_mirrors_instagram(tmp_path):
    make_post(tmp_path)
    post = load_queue(tmp_path)[0]
    fb = post.platforms["facebook"]
    assert fb.kind == "carousel" and [m.name for m in fb.media] == ["a.png", "b.png"]


def test_facebook_carousel_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("META_SYSTEM_TOKEN", "sys")
    monkeypatch.setenv("TINYNOTES_FB_PAGE_ID", "55")
    monkeypatch.setenv("MEDIA_BASE_URL", "https://me.github.io/repo")
    make_post(tmp_path)
    post = load_queue(tmp_path)[0]
    calls = []

    def fake_get(url, params=None, **kw):
        return Resp({"access_token": "pagetok", "name": "TinyNotes"})

    ids = iter(["p1", "p2", "55_999"])

    def fake_post(url, data=None, **kw):
        calls.append((url, data))
        return Resp({"id": next(ids)})

    monkeypatch.setattr(facebook.requests, "get", fake_get)
    monkeypatch.setattr(facebook.requests, "post", fake_post)
    pid, link = facebook.publish(post, post.platforms["facebook"], tmp_path)
    assert pid == "55_999"
    assert calls[0][1]["published"] == "false" and calls[0][1]["url"].endswith("/a.jpg")
    assert json.loads(calls[2][1]["attached_media"]) == [{"media_fbid": "p1"}, {"media_fbid": "p2"}]
    assert calls[2][1]["access_token"] == "pagetok"


def test_facebook_reel_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("META_SYSTEM_TOKEN", "sys")
    monkeypatch.setenv("FACTYEAP_FB_PAGE_ID", "77")
    monkeypatch.setenv("MEDIA_BASE_URL", "https://me.github.io/repo")
    folder = make_post(tmp_path, "factyeap/r", platforms={"instagram": {"kind": "reel", "media": ["v.mp4"], "caption": "cap"}})
    spec = yaml.safe_load((folder / "post.yaml").read_text()); spec["brand"] = "factyeap"
    (folder / "post.yaml").write_text(yaml.safe_dump(spec))
    post = load_queue(tmp_path)[0]
    seen = {}

    def fake_get(url, params=None, **kw):
        if params and params.get("fields") == "access_token,name":
            return Resp({"access_token": "pt"})
        return Resp({"status": {"uploading_phase": {"status": "complete"}}})

    def fake_post(url, data=None, headers=None, **kw):
        if "rupload" in url:
            seen["upload"] = headers
            return Resp({"success": True})
        if data["upload_phase"] == "start":
            return Resp({"video_id": "v9", "upload_url": "https://rupload.facebook.com/video-upload/v22.0/v9"})
        seen["finish"] = data
        return Resp({"success": True})

    monkeypatch.setattr(facebook.requests, "get", fake_get)
    monkeypatch.setattr(facebook.requests, "post", fake_post)
    vid, _ = facebook.publish(post, post.platforms["facebook"], tmp_path)
    assert vid == "v9"
    assert seen["upload"]["file_url"].endswith("/v.mp4") and seen["upload"]["Authorization"] == "OAuth pt"
    assert seen["finish"]["video_state"] == "PUBLISHED" and seen["finish"]["description"] == "cap"
