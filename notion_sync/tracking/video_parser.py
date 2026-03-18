"""Video duration probing via HTTP Range requests on MP4 files."""

import logging
import struct
import urllib.request

logger = logging.getLogger("webapp.tracking.video_parser")


def probe_video_duration(url: str) -> float | None:
    """HTTP Range request to extract duration (seconds) from MP4 mvhd box.
    
    Strategy: HEAD → front 64KB → back 256KB → 1MB → 4MB (progressive)
    """
    try:
        head_req = urllib.request.Request(url, method="HEAD")
        head_req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(head_req, timeout=10) as resp:
            content_length = int(resp.headers.get("Content-Length", 0))

        if content_length == 0:
            return None

        # 1. faststart: front 64KB
        duration = _parse_mvhd_range(url, 0, min(65535, content_length - 1))
        if duration is not None:
            return duration

        # 2. moov at end: progressively larger chunks from tail
        for tail_size in (65536, 262144, 1048576, 4194304):  # 64KB, 256KB, 1MB, 4MB
            if content_length <= tail_size:
                continue
            start = content_length - tail_size
            duration = _parse_mvhd_range(url, start, content_length - 1)
            if duration is not None:
                return duration

        return None
    except Exception as e:
        logger.error(f"probe_video_duration failed: {e}")
        return None


def _parse_mvhd_range(url: str, start: int, end: int) -> float | None:
    """Find mvhd box in the given byte range and return duration in seconds."""
    try:
        req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        idx = data.find(b"mvhd")
        if idx < 0:
            return None
        box = data[idx + 4:]
        if len(box) < 16:
            return None
        version = box[0]
        if version == 0:
            if len(box) < 20:
                return None
            timescale = struct.unpack(">I", box[12:16])[0]
            duration_val = struct.unpack(">I", box[16:20])[0]
        elif version == 1:
            if len(box) < 32:
                return None
            timescale = struct.unpack(">I", box[20:24])[0]
            duration_val = struct.unpack(">Q", box[24:32])[0]
        else:
            return None
        return duration_val / timescale if timescale > 0 else None
    except Exception as e:
        logger.warning(f"_parse_mvhd_range({start}-{end}) failed: {e}")
        return None


def convert_dropbox_url(url: str) -> str:
    """Convert a Dropbox sharing URL to a direct download URL (dl=1)."""
    if not url:
        return ""
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    params["dl"] = ["1"]
    return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))


def convert_dropbox_stream_url(url: str) -> str:
    """Convert a Dropbox sharing URL to a streamable URL.

    Uses dl.dropboxusercontent.com + raw=1 for direct content serving
    without HTML wrapper or Content-Disposition headers.
    Works with both old (/s/) and new (/scl/fi/) Dropbox URL formats.
    """
    if not url:
        return ""
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    params.pop("dl", None)
    params["raw"] = ["1"]
    parsed = parsed._replace(
        netloc="dl.dropboxusercontent.com",
        query=urlencode(params, doseq=True),
    )
    return urlunparse(parsed)
