"""Notion API client and low-level property helpers.

This module is the single source of truth. It is copied to
functions/, timer/, and webapp/ at deploy time via GitHub Actions.
Do NOT edit the copies directly — edit this file instead.
"""

import hashlib
import hmac
import logging
import time

from notion_client import Client

logger = logging.getLogger("notion_helpers")

notion: Client | None = None


def init_notion(token: str):
    """Initialize the Notion client."""
    global notion
    notion = Client(auth=token)


def query_database(db_id: str, filter: dict = None, sorts: list = None) -> dict:
    """Query a Notion data source via direct HTTP (API 2025-09-03)."""
    import httpx
    body = {}
    if filter:
        body["filter"] = filter
    if sorts:
        body["sorts"] = sorts
    resp = httpx.post(
        f"https://api.notion.com/v1/data_sources/{db_id}/query",
        headers={
            "Authorization": f"Bearer {notion.options.auth}",
            "Notion-Version": "2025-09-03",
        },
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def api_call(fn, *args, max_retries=5, **kwargs):
    """Execute a Notion API call with 429 retry and exponential back-off."""
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate" in err_str.lower():
                wait = min(2 ** attempt, 10)
                logger.info(f"Rate limited, waiting {wait}s (attempt {attempt+1})")
                time.sleep(wait)
            else:
                raise
    raise Exception("Max retries exceeded")


# ---------------------------------------------------------------------------
# Property extraction
# ---------------------------------------------------------------------------

def extract_plain_text(prop: dict):
    """Extract a plain Python value from a single Notion property object."""
    ptype = prop.get("type", "")
    if ptype == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    elif ptype == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    elif ptype == "number":
        return prop.get("number")
    elif ptype == "checkbox":
        return prop.get("checkbox", False)
    elif ptype == "select":
        sel = prop.get("select")
        return sel["name"] if sel else None
    elif ptype == "date":
        d = prop.get("date")
        return d.get("start") if d else None
    elif ptype == "url":
        return prop.get("url")
    elif ptype == "relation":
        return [r["id"] for r in prop.get("relation", [])]
    return None


def extract_props(page: dict) -> dict:
    """Extract all properties from a Notion page into a plain dict."""
    return {name: extract_plain_text(prop)
            for name, prop in page.get("properties", {}).items()}


def build_notion_props(data: dict, prop_types: dict) -> dict:
    """Build Notion API property dict from plain data and type map."""
    props = {}
    for key, value in data.items():
        if key.startswith("_") and key != "_sync_id":
            continue
        if value is None:
            continue
        ptype = prop_types.get(key)
        if not ptype or ptype in ("formula", "rollup"):
            continue

        if ptype == "title":
            props[key] = {"title": [{"text": {"content": str(value)}}]}
        elif ptype == "rich_text":
            props[key] = {"rich_text": [{"text": {"content": str(value)}}]}
        elif ptype == "number":
            props[key] = {"number": value}
        elif ptype == "checkbox":
            props[key] = {"checkbox": bool(value)}
        elif ptype == "date":
            props[key] = {"date": {"start": str(value)}}
        elif ptype == "url":
            props[key] = {"url": str(value)}
        elif ptype == "select":
            props[key] = {"select": {"name": str(value)}}
        elif ptype == "relation":
            if isinstance(value, list):
                props[key] = {"relation": [{"id": pid} for pid in value]}
            else:
                props[key] = {"relation": [{"id": str(value)}]}
    return props


# Underscore-prefixed aliases (used by functions/ and webapp/)
_extract_plain_text = extract_plain_text
_extract_props = extract_props
_build_notion_props = build_notion_props


# ---------------------------------------------------------------------------
# Sync-id lookup helpers
# ---------------------------------------------------------------------------

def normalize_page_id(pid: str) -> str:
    """Ensure page ID has dashes (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)."""
    pid = pid.strip()
    if len(pid) == 32 and "-" not in pid:
        return f"{pid[:8]}-{pid[8:12]}-{pid[12:16]}-{pid[16:20]}-{pid[20:]}"
    return pid


def _find_by_sync_id(db_id: str, sync_id: str) -> str | None:
    """Find a page in a DB by its _sync_id property. Returns page_id only."""
    sync_id = normalize_page_id(sync_id)
    result = query_database(
        db_id,
        filter={"property": "_sync_id", "rich_text": {"equals": sync_id}},
    )
    pages = result.get("results", [])
    return pages[0]["id"] if pages else None


def find_by_sync_id_with_props(db_id: str, sync_id: str) -> tuple[str, dict] | None:
    """Find a page by _sync_id and return (page_id, extracted_props) or None."""
    sync_id = normalize_page_id(sync_id)
    result = query_database(
        db_id,
        filter={"property": "_sync_id", "rich_text": {"equals": sync_id}},
    )
    pages = result.get("results", [])
    if not pages:
        return None
    return pages[0]["id"], extract_props(pages[0])


# ---------------------------------------------------------------------------
# Block / data-source conversion
# ---------------------------------------------------------------------------

def _block_to_ds_id(block_id: str) -> str:
    """Convert a child_database block_id to data_source_id via GET /databases/{id}."""
    import httpx
    try:
        resp = httpx.get(
            f"https://api.notion.com/v1/databases/{block_id}",
            headers={
                "Authorization": f"Bearer {notion.options.auth}",
                "Notion-Version": "2025-09-03",
            },
            timeout=30,
        )
        if resp.status_code == 200:
            ds_list = resp.json().get("data_sources", [])
            if ds_list:
                return ds_list[0]["id"]
    except Exception:
        pass
    return block_id


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------

def verify_webhook_signature(req_body: bytes, signature: str, token: str) -> bool:
    """Verify HMAC-SHA256 webhook signature."""
    expected = "sha256=" + hmac.new(
        token.encode(), req_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
