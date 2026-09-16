"""One-time, resumable catch-up for the technology Telegram group.

Run with CONFIG_MODE=local so this batch uses the existing local archive and
cookies without amplifying Notion API requests. The normal service remains in
Notion mode and delivers downloaded files from the same group folder.
"""

import datetime as dt
import json
import os
import sys
from pathlib import Path

import yt_dlp
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from config import COOKIES_FILE, get_config_provider  # noqa: E402
from task.channel_listing import fetch_channel_entries  # noqa: E402
from task.dl_audio import dl_audio_latest  # noqa: E402

GROUP_NAME = "唏噓電臺-科技"
EXPECTED_CHAT_ID = "-1002794044093"
CHANNELS = ("@StorytellerFan", "@bestpartners", "@TheValley101")
AUDIO_FOLDER = ROOT / "au" / "xixu1"
MANIFEST = ROOT / "data" / "backfill_tech_20260916.json"
WINDOW_DAYS = 10
PER_TAB_LIMIT = 60
BATCH_SIZE = 5


def save_manifest(manifest):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    temporary = MANIFEST.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(MANIFEST)


def validate_group():
    snapshot = yaml.safe_load(
        (ROOT / "config" / "notion-synced-config.yaml").read_text(encoding="utf-8")
    ) or {}
    groups = [
        group for group in snapshot.get("channel_groups", [])
        if group.get("name") == GROUP_NAME
    ]
    if len(groups) != 1:
        raise RuntimeError("Technology group not found uniquely in Notion snapshot")
    group = groups[0]
    if not group.get("enabled"):
        raise RuntimeError("Technology group is disabled in Notion snapshot")
    if str(group.get("telegram_chat_id")) != EXPECTED_CHAT_ID:
        raise RuntimeError("Technology group chat ID changed")
    if tuple(group.get("youtube_channels") or ()) != CHANNELS:
        raise RuntimeError("Technology source channels changed")
    if (ROOT / group.get("audio_folder", "")).resolve() != AUDIO_FOLDER.resolve():
        raise RuntimeError("Technology audio folder changed")


def create_manifest():
    started_at = dt.datetime.now(dt.timezone.utc)
    cutoff = started_at - dt.timedelta(days=WINDOW_DAYS)
    manifest = {
        "group_name": GROUP_NAME,
        "chat_id": EXPECTED_CHAT_ID,
        "started_at": started_at.isoformat(),
        "cutoff": cutoff.isoformat(),
        "window_days": WINDOW_DAYS,
        "per_tab_limit": PER_TAB_LIMIT,
        "channels": {},
    }
    for channel in CHANNELS:
        listing = fetch_channel_entries(
            channel_name=channel,
            max_videos=PER_TAB_LIMIT,
            cookies_file=COOKIES_FILE,
        )
        if any((listing.get("tab_errors") or {}).values()):
            raise RuntimeError(f"Listing failed for {channel}; no manifest saved")
        entries = [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "webpage_url": item.get("webpage_url") or item.get("url"),
            }
            for item in listing["entries"]
            if item.get("id")
        ]
        manifest["channels"][channel] = {
            "entries": entries,
            "tab_counts": listing["tab_counts"],
            "results": {},
        }
        print(f"LISTED {channel}: {len(entries)} unique candidates", flush=True)
    save_manifest(manifest)
    return manifest


def check_boundary(manifest):
    """Refuse a silently truncated 10-day listing."""
    if manifest.get("boundary_checked"):
        return
    cutoff = dt.datetime.fromisoformat(manifest["cutoff"])
    with yt_dlp.YoutubeDL({"quiet": True, "cookiefile": COOKIES_FILE}) as ydl:
        for channel in CHANNELS:
            data = manifest["channels"][channel]
            counts = data["tab_counts"]
            entries = data["entries"]
            boundaries = []
            if counts.get("videos", 0) >= PER_TAB_LIMIT:
                boundaries.append(entries[counts["videos"] - 1])
            if counts.get("streams", 0) >= PER_TAB_LIMIT:
                boundaries.append(entries[-1])
            for entry in boundaries:
                video_id = entry["id"]
                info = ydl.extract_info(
                    f"https://www.youtube.com/watch?v={video_id}", download=False
                )
                raw_date = info.get("upload_date") if info else None
                if not raw_date:
                    raise RuntimeError(f"Cannot verify listing boundary: {video_id}")
                boundary = dt.datetime.strptime(raw_date, "%Y%m%d").replace(
                    tzinfo=dt.timezone.utc
                )
                if boundary >= cutoff:
                    raise RuntimeError(
                        f"Listing boundary {video_id} is inside the 10-day window; "
                        "increase PER_TAB_LIMIT before running"
                    )
    manifest["boundary_checked"] = True
    save_manifest(manifest)


def mark_older_tail(data):
    """Once a dated item is too old, skip the rest of its descending tab."""
    entries = data["entries"]
    results = data["results"]
    video_end = data["tab_counts"].get("videos", 0)
    for start, end in ((0, video_end), (video_end, len(entries))):
        for index in range(start, end):
            result = results.get(entries[index]["id"], {})
            if result.get("status") != "filtered":
                continue
            if "视频超过10天" not in result.get("reason", ""):
                continue
            for older in entries[index + 1:end]:
                results.setdefault(older["id"], {
                    "status": "filtered",
                    "reason": "同一频道列表中位于10天边界之后",
                    "attempts": 0,
                })
            break


def classify_missing_file_errors(manifest, channel):
    """yt-dlp can return no file for a date filter without raising an error."""
    data = manifest["channels"][channel]
    errors = [
        (video_id, result)
        for video_id, result in data["results"].items()
        if result.get("status") == "error"
        and result.get("reason") == "转换失败或文件未找到"
        and result.get("date_check_version", 0) < 2
    ]
    if not errors:
        return
    cutoff = dt.datetime.fromisoformat(manifest["cutoff"])
    with yt_dlp.YoutubeDL({
        "quiet": True,
        "cookiefile": COOKIES_FILE,
        "socket_timeout": 30,
        "retries": 1,
    }) as ydl:
        for video_id, result in errors:
            try:
                info = ydl.extract_info(
                    f"https://www.youtube.com/watch?v={video_id}", download=False
                )
                timestamp = info.get("timestamp") if info else None
                upload_date = info.get("upload_date") if info else None
                if timestamp is not None:
                    is_old = dt.datetime.fromtimestamp(
                        timestamp, tz=dt.timezone.utc
                    ) < cutoff
                elif upload_date:
                    day = dt.datetime.strptime(upload_date, "%Y%m%d").date()
                    is_old = day < cutoff.date()
                else:
                    is_old = False
                if is_old:
                    result["status"] = "filtered"
                    result["reason"] = "视频超过10天"
                result["date_check_version"] = 2
            except Exception as err:
                result["date_check_version"] = 2
                print(f"DATE_CHECK_FAILED {video_id}: {type(err).__name__}", flush=True)


def run():
    if os.environ.get("CONFIG_MODE", "").lower() != "local":
        raise RuntimeError("Run this one-time batch with CONFIG_MODE=local")
    if get_config_provider().__class__.__name__ != "LocalConfigProvider":
        raise RuntimeError("Local provider did not initialize")
    validate_group()

    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if manifest.get("group_name") != GROUP_NAME or manifest.get("window_days") != WINDOW_DAYS:
            raise RuntimeError("Existing manifest does not match this backfill")
        print(f"RESUMING {MANIFEST}", flush=True)
    else:
        manifest = create_manifest()

    check_boundary(manifest)

    requested = os.environ.get("BACKFILL_CHANNELS")
    process_channels = tuple(requested.split(",")) if requested else CHANNELS
    if not process_channels or any(channel not in CHANNELS for channel in process_channels):
        raise RuntimeError("BACKFILL_CHANNELS must contain only configured technology sources")

    for channel in process_channels:
        data = manifest["channels"][channel]
        classify_missing_file_errors(manifest, channel)
        mark_older_tail(data)
        save_manifest(manifest)
        entries = data["entries"]
        results = data["results"]
        while True:
            pending = [
                entry for entry in entries
                if results.get(entry["id"], {}).get("status")
                not in {"success", "archived", "already_exists", "filtered", "member_only"}
                and results.get(entry["id"], {}).get("attempts", 0) < 2
            ]
            if not pending:
                break
            batch = pending[:BATCH_SIZE]
            stats = dl_audio_latest(
                channel_name=channel,
                audio_folder=str(AUDIO_FOLDER),
                group_name=GROUP_NAME,
                filter_days_override=WINDOW_DAYS,
                filter_cutoff_override=dt.datetime.fromisoformat(manifest["cutoff"]),
                max_videos_override=PER_TAB_LIMIT,
                entries_override=batch,
                sync_archive=False,
                return_stats=True,
                inter_video_delay=(0, 0),
                socket_timeout_override=30,
            )
            if not isinstance(stats, dict) or stats.get("total") != len(batch):
                raise RuntimeError(f"Incomplete batch for {channel}; resume later")
            for detail in stats["details"]:
                video_id = detail["id"]
                old = results.get(video_id, {})
                results[video_id] = {
                    "status": detail["status"],
                    "reason": detail["reason"],
                    "attempts": old.get("attempts", 0) + 1,
                }
            classify_missing_file_errors(manifest, channel)
            mark_older_tail(data)
            save_manifest(manifest)
            print(
                f"BATCH {channel}: remaining={len(pending) - len(batch)} "
                f"new={stats['success']} archived={stats['archived']} "
                f"filtered={stats['filtered']} errors={stats['error']}",
                flush=True,
            )

    counts = {}
    for channel in CHANNELS:
        for item in manifest["channels"][channel]["results"].values():
            status = item["status"]
            counts[status] = counts.get(status, 0) + 1
    print("SUMMARY " + json.dumps(counts, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    run()
