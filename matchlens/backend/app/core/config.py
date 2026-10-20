import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_mode: str = "local_only" if os.getenv("APP_MODE", "local_only") == "local_demo" else os.getenv("APP_MODE", "local_only")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./matchlens.db")
    local_storage_dir: str = os.getenv("LOCAL_STORAGE_DIR", "./local-videos")
    max_video_size_bytes: int = int(os.getenv("MAX_VIDEO_SIZE_MB", "500")) * 1024 * 1024
    robot_detector_model: str | None = os.getenv("ROBOT_DETECTOR_MODEL") or None
    robot_detector_classes: tuple[str, ...] = tuple(
        name.strip().casefold()
        for name in os.getenv("ROBOT_DETECTOR_CLASSES", "robot,ftc robot").split(",")
        if name.strip()
    )
    robot_detector_confidence: float = float(os.getenv("ROBOT_DETECTOR_CONFIDENCE", "0.35"))
    robot_detector_tracker: str = os.getenv("ROBOT_DETECTOR_TRACKER", "bytetrack.yaml")
    supabase_url: str | None = os.getenv("SUPABASE_URL") or None
    supabase_anon_key: str | None = os.getenv("SUPABASE_ANON_KEY") or None

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)


settings = Settings()