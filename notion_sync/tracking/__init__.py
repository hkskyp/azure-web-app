"""Tracking package — re-exports key functions for convenience."""

from notion_sync.tracking.state import (
    get_notion_client,
    fetch_dropbox_url,
    fetch_watch_state,
    fetch_initial_watched_time,
    get_watch_log,
    upsert_watch_start,
    upsert_progress,
    upsert_complete,
    sync_to_notion,
    build_notion_start_properties,
    build_notion_progress_properties,
    build_notion_complete_properties,
)
from notion_sync.tracking.video_parser import (
    probe_video_duration,
    convert_dropbox_url,
)

__all__ = [
    "get_notion_client",
    "fetch_dropbox_url",
    "fetch_watch_state",
    "fetch_initial_watched_time",
    "get_watch_log",
    "upsert_watch_start",
    "upsert_progress",
    "upsert_complete",
    "sync_to_notion",
    "build_notion_start_properties",
    "build_notion_progress_properties",
    "build_notion_complete_properties",
    "probe_video_duration",
    "convert_dropbox_url",
]
