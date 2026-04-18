"""
Video Thumbnail Generator

Extracts the first frame from a video file using ffmpeg
and uploads it to Bunny CDN as a JPEG thumbnail.
"""

import subprocess
import tempfile
import os

from .bunny_storage import upload_to_bunny


def generate_video_thumbnail(video_file, cdn_folder):
    """
    Extract first frame from a video file and upload as a JPEG thumbnail.

    Args:
        video_file: Django UploadedFile or file-like object with a .name attribute
        cdn_folder: CDN folder path (e.g., 'media/product_images/product_SKU123')

    Returns:
        CDN URL of the thumbnail, or None on failure
    """
    tmp_video = None
    tmp_thumb = None
    try:
        # Write the uploaded video to a temp file so ffmpeg can read it
        suffix = os.path.splitext(video_file.name)[1] if hasattr(video_file, 'name') else '.mp4'
        tmp_video = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        video_file.seek(0)
        for chunk in video_file.chunks() if hasattr(video_file, 'chunks') else [video_file.read()]:
            tmp_video.write(chunk)
        tmp_video.flush()
        tmp_video.close()

        # Extract first frame with ffmpeg
        tmp_thumb = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        tmp_thumb.close()

        result = subprocess.run(
            [
                'ffmpeg', '-y',
                '-i', tmp_video.name,
                '-vframes', '1',        # just one frame
                '-q:v', '2',            # high quality JPEG
                '-vf', 'scale=480:-2',  # 480px wide, keep aspect ratio
                tmp_thumb.name,
            ],
            capture_output=True,
            timeout=15,
        )

        if result.returncode != 0:
            print(f"[THUMBNAIL] ffmpeg failed: {result.stderr.decode()[:300]}")
            return None

        if not os.path.exists(tmp_thumb.name) or os.path.getsize(tmp_thumb.name) == 0:
            print("[THUMBNAIL] ffmpeg produced empty output")
            return None

        # Upload thumbnail to Bunny CDN
        base_name = os.path.splitext(os.path.basename(video_file.name))[0] if hasattr(video_file, 'name') else 'video'
        thumb_path = f"{cdn_folder.rstrip('/')}/{base_name}_thumb.jpg"

        with open(tmp_thumb.name, 'rb') as f:
            thumb_url = upload_to_bunny(f, thumb_path)

        print(f"[THUMBNAIL] Generated: {thumb_url}")
        return thumb_url

    except FileNotFoundError:
        print("[THUMBNAIL] ffmpeg not found - install with: brew install ffmpeg")
        return None
    except subprocess.TimeoutExpired:
        print("[THUMBNAIL] ffmpeg timed out")
        return None
    except Exception as e:
        print(f"[THUMBNAIL] Error: {e}")
        return None
    finally:
        if tmp_video and os.path.exists(tmp_video.name):
            os.unlink(tmp_video.name)
        if tmp_thumb and os.path.exists(tmp_thumb.name):
            os.unlink(tmp_thumb.name)
