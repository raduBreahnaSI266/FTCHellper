import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app import main as api_module
from app.models.base import Base
from app.vision.detector import RobotDetection

client = TestClient(api_module.app)


@pytest.fixture(autouse=True)
def isolate_api_storage(tmp_path, monkeypatch):
    test_engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    test_storage = tmp_path / "videos"
    test_storage.mkdir()
    Base.metadata.create_all(test_engine)
    monkeypatch.setattr(api_module, "engine", test_engine)
    monkeypatch.setattr(api_module, "storage_dir", test_storage)
    yield
    test_engine.dispose()


def test_health_reports_explicit_local_mode() -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["mode"] == "local_only"
    assert response.json()["supabase_configured"] is False


def test_synthetic_demo_endpoint_is_removed() -> None:
    assert client.get("/api/v1/demo/overview").status_code == 404


def test_team_directory_uses_ftcscout_and_validates_results(monkeypatch) -> None:
    upstream = api_module.httpx.Response(
        200,
        json={"data": {"teamsSearch": [{"number": 12345, "name": "Local FTC Team"}]}},
        request=api_module.httpx.Request("POST", api_module.FTC_SCOUT_GRAPHQL_URL),
    )
    requests = []

    def fake_post(url, **kwargs):
        requests.append((url, kwargs))
        return upstream

    monkeypatch.setattr(api_module.httpx, "post", fake_post)
    response = client.get("/api/v1/teams/directory")

    assert response.status_code == 200
    assert response.json() == [{"number": 12345, "name": "Local FTC Team"}]
    assert requests[0][0] == "https://api.ftcscout.org/graphql"
    assert "teamsSearch(limit: 100000)" in requests[0][1]["json"]["query"]


def test_team_directory_reports_upstream_graphql_errors(monkeypatch) -> None:
    upstream = api_module.httpx.Response(
        200,
        json={"errors": [{"message": "Upstream unavailable"}]},
        request=api_module.httpx.Request("POST", api_module.FTC_SCOUT_GRAPHQL_URL),
    )
    monkeypatch.setattr(api_module.httpx, "post", lambda *args, **kwargs: upstream)

    response = client.get("/api/v1/teams/directory")

    assert response.status_code == 502
    assert response.json()["detail"] == "FTCScout could not provide the team directory."


def test_team_directory_search_for_video_roster(monkeypatch) -> None:
    upstream = api_module.httpx.Response(
        200,
        json={"data": {"teamsSearch": [{"number": 123, "name": "Search Result"}]}},
        request=api_module.httpx.Request("POST", api_module.FTC_SCOUT_GRAPHQL_URL),
    )
    requests = []

    def fake_post(url, **kwargs):
        requests.append(kwargs["json"])
        return upstream

    monkeypatch.setattr(api_module.httpx, "post", fake_post)
    response = client.get("/api/v1/teams/directory", params={"search": "123"})

    assert response.status_code == 200
    assert response.json() == [{"number": 123, "name": "Search Result"}]
    assert requests[0]["variables"] == {"search": "123"}
    assert "searchText: $search" in requests[0]["query"]


def test_video_field_robots_can_be_saved_and_replaced() -> None:
    mp4_header = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00"
    upload = client.post(
        "/api/v1/videos",
        data={"event_name": "Local Test", "season": "2025-2026", "match_number": "3", "alliance": "Blue"},
        files={"file": ("match.mp4", mp4_header, "video/mp4")},
    )
    video_id = upload.json()["id"]
    endpoint = f"/api/v1/videos/{video_id}/field-robots"

    saved = client.put(
        endpoint,
        json={
            "robots": [
                {"team_number": 12345, "team_name": "Local Blue", "alliance": "Blue"},
                {"team_number": 54321, "team_name": "Local Red", "alliance": "Red"},
            ]
        },
    )

    assert saved.status_code == 200
    assert [(robot["team_number"], robot["alliance"]) for robot in saved.json()] == [
        (12345, "Blue"),
        (54321, "Red"),
    ]
    assert client.get(endpoint).json() == saved.json()

    replaced = client.put(
        endpoint,
        json={"robots": [{"team_number": 67890, "team_name": "Replacement", "alliance": "Blue"}]},
    )
    assert replaced.status_code == 200
    assert [robot["team_number"] for robot in client.get(endpoint).json()] == [67890]


@pytest.mark.parametrize(
    "robots",
    [
        [{"team_number": 1, "team_name": "Same", "alliance": "Blue"}] * 2,
        [{"team_number": number, "team_name": str(number), "alliance": "Blue"} for number in range(1, 5)],
        [{"team_number": number, "team_name": str(number), "alliance": "Red"} for number in range(1, 5)],
        [{"team_number": number, "team_name": str(number), "alliance": "Blue"} for number in range(1, 7)],
    ],
)
def test_video_field_robots_reject_invalid_roster(robots) -> None:
    response = client.put(
        "/api/v1/videos/not-a-video/field-robots",
        json={"robots": robots},
    )

    assert response.status_code == 422


def test_video_field_robots_returns_not_found_for_unknown_video() -> None:
    assert client.get("/api/v1/videos/not-a-video/field-robots").status_code == 404


def test_upload_valid_mp4_and_playback() -> None:
    mp4_header = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00"
    response = client.post(
        "/api/v1/videos",
        data={"event_name": "Local Test", "season": "2025-2026", "match_number": "3", "alliance": "Blue"},
        files={"file": ("match.mp4", mp4_header, "video/mp4")},
    )

    assert response.status_code == 201
    uploaded = response.json()
    assert uploaded["original_filename"] == "match.mp4"
    assert uploaded["event_name"] == "Local Test"
    assert uploaded["season"] == "2025-2026"
    assert uploaded["match_number"] == 3
    assert uploaded["alliance"] == "Blue"
    assert uploaded["size_bytes"] == len(mp4_header)
    assert uploaded["status"] == "uploaded"
    assert client.get("/api/v1/videos").json()[0]["id"] == uploaded["id"]
    playback = client.get(f"/api/v1/videos/{uploaded['id']}/file")
    assert playback.status_code == 200
    assert playback.content == mp4_header
    assert client.delete(f"/api/v1/videos/{uploaded['id']}").status_code == 204


def test_upload_rejects_non_mp4_and_invalid_container() -> None:
    form_data = {"event_name": "Local Test", "season": "2025-2026", "match_number": "3", "alliance": "Blue"}
    wrong_extension = client.post(
        "/api/v1/videos", data=form_data, files={"file": ("match.mov", b"video", "video/quicktime")}
    )
    bad_container = client.post(
        "/api/v1/videos", data=form_data, files={"file": ("match.mp4", b"not an mp4 file", "video/mp4")}
    )

    assert wrong_extension.status_code == 415
    assert bad_container.status_code == 415
    assert client.get("/api/v1/videos").json() == []


def test_manual_annotation_crud_and_verification() -> None:
    mp4_header = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00"
    upload = client.post(
        "/api/v1/videos",
        data={"event_name": "Local Test", "season": "2025-2026", "match_number": "3", "alliance": "Blue"},
        files={"file": ("match.mp4", mp4_header, "video/mp4")},
    )
    video_id = upload.json()["id"]

    created = client.post(
        f"/api/v1/videos/{video_id}/annotations",
        json={
            "event_type": "candidate_score",
            "timestamp_seconds": 14.25,
            "end_timestamp_seconds": 16.0,
            "robot_label": "Blue 1",
            "note": "Possible scoring action; verify against frame evidence.",
        },
    )

    assert created.status_code == 201
    annotation = created.json()
    assert annotation["detection_source"] == "manual"
    assert annotation["verification_status"] == "unreviewed"
    assert client.get(f"/api/v1/videos/{video_id}/annotations").json()[0]["id"] == annotation["id"]

    updated = client.patch(
        f"/api/v1/videos/{video_id}/annotations/{annotation['id']}",
        json={"event_type": "confirmed_score", "verification_status": "confirmed"},
    )
    assert updated.status_code == 200
    assert updated.json()["verification_status"] == "confirmed"
    assert updated.json()["event_type"] == "confirmed_score"

    assert client.delete(
        f"/api/v1/videos/{video_id}/annotations/{annotation['id']}"
    ).status_code == 204
    assert client.get(f"/api/v1/videos/{video_id}/annotations").json() == []
    assert client.delete(f"/api/v1/videos/{video_id}").status_code == 204


def test_annotation_rejects_invalid_time_interval() -> None:
    response = client.post(
        "/api/v1/videos/not-a-video/annotations",
        json={"event_type": "inactivity", "timestamp_seconds": 20, "end_timestamp_seconds": 10},
    )

    assert response.status_code == 422


def test_video_analysis_persists_measured_metadata(monkeypatch) -> None:
    mp4_header = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00"
    upload = client.post(
        "/api/v1/videos",
        data={"event_name": "Local Test", "season": "2025-2026", "match_number": "3", "alliance": "Blue"},
        files={"file": ("match.mp4", mp4_header, "video/mp4")},
    )
    video_id = upload.json()["id"]
    progress_values: list[int] = []

    class FakeDetector:
        model_name = "robots-test.pt"
        model_version = "test-version"
        confidence_threshold = 0.4
        configuration = "classes=['robot']; tracker=bytetrack.yaml"

    fake_detector = FakeDetector()
    detections = [
        RobotDetection("7", "robot", 0.91, 100, 100, 300, 300, 0.0),
        RobotDetection("7", "robot", 0.88, 200, 150, 400, 350, 1.0),
    ]

    def fake_analysis(path, report_progress, detector, unavailable_message):
        assert path.is_file()
        assert detector is fake_detector
        assert unavailable_message == ""
        report_progress(55)
        progress_values.append(55)
        return {
            "duration_seconds": 90.0,
            "fps": 30.0,
            "frame_count": 2700,
            "width": 1280,
            "height": 720,
            "sampled_frames": 90,
            "detector_status": "available",
            "detector_message": "",
            "detector_model": fake_detector.model_name,
            "detector_version": fake_detector.model_version,
            "detector_configuration": fake_detector.configuration,
            "confidence_threshold": fake_detector.confidence_threshold,
            "detections": detections,
        }

    monkeypatch.setattr(api_module, "create_robot_detector", lambda *args: (fake_detector, ""))
    monkeypatch.setattr(api_module, "analyze_video_file", fake_analysis)
    response = client.post(f"/api/v1/videos/{video_id}/analyze")

    assert response.status_code == 202
    result = client.get(f"/api/v1/videos/{video_id}").json()
    assert result["status"] == "needs_review"
    assert result["analysis_progress"] == 100
    assert result["duration_seconds"] == 90.0
    assert result["frame_count"] == 2700
    assert result["sampled_frames"] == 90
    assert result["detector_status"] == "available"
    assert result["detector_model"] == "robots-test.pt"
    tracks = client.get(f"/api/v1/videos/{video_id}/tracks").json()["tracks"]
    assert len(tracks) == 1
    assert tracks[0]["source_track_id"] == "7"
    assert tracks[0]["model_version"] == "test-version"
    assert len(tracks[0]["points"]) == 2
    assert tracks[0]["points"][0]["x_normalized"] == 200 / 1280
    assert tracks[0]["points"][0]["y_normalized"] == 200 / 720
    assert tracks[0]["points"][0]["confidence"] == 0.91
    assert progress_values == [55]