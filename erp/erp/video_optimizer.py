"""Make a video as light as what it is for allows — one door for all of them.

A phone clip arrives at 4–10 Mbps (often 1080p or 4K at 60 fps); nobody
looking at it in the ERP or on the storefront needs that. Every place that
stores a video runs the same encode, and what differs is only what the
video is for, so a caller names that — a Profile — and never passes
numbers of its own:

  WEB       product videos: the storefront shows them muted, so the sound
            is dropped.
  DOCUMENT  videos hung off records (a supplier's clip of the goods, a
            customer's complaint): the sound is kept, it may be the point.

Both: H.264, at most 720 px on the short side and 30 fps, CRF 26 capped
at 2.5 Mbps (the cap keeps a fine-detailed fabric from coming out bigger
than it went in), no metadata, faststart so playback starts before the
whole file is in. A smaller clip is never scaled up nor sped up.

    from erp.video_optimizer import DOCUMENT, lighter
    if lighter(source_path, target_path, DOCUMENT): store target_path

ffmpeg does the work. One encode runs at a time per server process: each
one already uses every core, and several at once would only make each
upload wait longer.
"""
import os
import subprocess
import threading
from dataclasses import dataclass

ENCODE_TIMEOUT = 10 * 60
THUMBNAIL_WIDTH = 480

_one_at_a_time = threading.Lock()


@dataclass(frozen=True)
class Profile:
    name: str
    sound: bool
    short_side: int = 720
    fps: int = 30
    crf: int = 26
    maxrate: str = "2500k"
    bufsize: str = "5000k"
    audio_bitrate: str = "128k"


WEB = Profile("web", sound=False)
DOCUMENT = Profile("document", sound=True)


class FfmpegMissing(Exception):
    """ffmpeg is not installed here: try again where it is, later."""


def _run(args, timeout):
    try:
        return subprocess.run(args, capture_output=True, timeout=timeout).returncode == 0
    except FileNotFoundError as exc:
        raise FfmpegMissing(str(exc)) from exc
    except subprocess.TimeoutExpired:
        return False


def encode(source, target, profile):
    """Write `source` re-encoded for `profile` to `target` (an .mp4).
    False when ffmpeg can't read it."""
    side = profile.short_side
    sound = (["-map", "0:a:0?", "-c:a", "aac", "-b:a", profile.audio_bitrate]
             if profile.sound else ["-an"])
    with _one_at_a_time:
        ok = _run([
            "ffmpeg", "-y", "-v", "error", "-i", source,
            "-map", "0:v:0", *sound, "-sn", "-dn", "-map_metadata", "-1",
            "-vf", f"scale='if(gt(iw,ih),-2,min({side},iw))':'if(gt(iw,ih),min({side},ih),-2)'",
            "-fpsmax", str(profile.fps),
            "-c:v", "libx264", "-preset", "medium", "-crf", str(profile.crf),
            "-maxrate", profile.maxrate, "-bufsize", profile.bufsize,
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            target,
        ], ENCODE_TIMEOUT)
    return ok and os.path.exists(target) and os.path.getsize(target) > 0


def lighter(source, target, profile):
    """encode(), and True only when the result is smaller than `source` —
    a file that would come out bigger is better kept as it came."""
    return encode(source, target, profile) and os.path.getsize(target) < os.path.getsize(source)


def first_frame(source, target):
    """Write the video's first frame to `target` as a JPEG."""
    ok = _run([
        "ffmpeg", "-y", "-v", "error", "-i", source,
        "-frames:v", "1", "-q:v", "2", "-vf", f"scale={THUMBNAIL_WIDTH}:-2",
        target,
    ], 60)
    return ok and os.path.exists(target) and os.path.getsize(target) > 0
