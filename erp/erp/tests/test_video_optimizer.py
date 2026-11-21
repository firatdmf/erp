"""Videos made light for what they are for (erp.video_optimizer), and video
attachments re-encoded with their sound (erp.attachments.lighten_video).

Run with:
    scripts/test_local.sh erp.tests.test_video_optimizer
"""
import json
import os
import shutil
import subprocess
import tempfile
from unittest import skipUnless
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from erp import attachments, video_optimizer
from erp.models import Attachment

HAS_FFMPEG = bool(shutil.which("ffmpeg"))


def clip(folder, size, rate=60, sound=True):
    path = os.path.join(folder, "in.mp4")
    audio = ["-f", "lavfi", "-i", "sine=duration=1", "-c:a", "aac"] if sound else []
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc2=size={size}:rate={rate}:duration=1",
        *audio, "-c:v", "libx264", "-b:v", "8M", "-shortest", path,
    ], check=True)
    return path


def streams(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,width,height,avg_frame_rate", "-of", "json", path],
        capture_output=True, check=True).stdout
    return json.loads(out)["streams"]


@skipUnless(HAS_FFMPEG, "ffmpeg is not installed")
class Encoding(SimpleTestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        self.out = os.path.join(self.dir, "out.mp4")

    def _video(self, path):
        return next(s for s in streams(path) if s["codec_type"] == "video")

    def test_a_landscape_clip_comes_out_720_high_at_30_fps(self):
        self.assertTrue(video_optimizer.encode(clip(self.dir, "1920x1080"), self.out, video_optimizer.WEB))
        video = self._video(self.out)
        self.assertEqual((video["width"], video["height"], video["avg_frame_rate"]), (1280, 720, "30/1"))

    def test_a_portrait_clip_comes_out_720_wide(self):
        video_optimizer.encode(clip(self.dir, "1080x1920"), self.out, video_optimizer.DOCUMENT)
        video = self._video(self.out)
        self.assertEqual((video["width"], video["height"]), (720, 1280))

    def test_a_small_clip_is_not_blown_up_nor_sped_up(self):
        video_optimizer.encode(clip(self.dir, "640x360", rate=24), self.out, video_optimizer.WEB)
        video = self._video(self.out)
        self.assertEqual((video["width"], video["height"], video["avg_frame_rate"]), (640, 360, "24/1"))

    def test_web_drops_the_sound(self):
        video_optimizer.encode(clip(self.dir, "1280x720"), self.out, video_optimizer.WEB)
        self.assertEqual([s["codec_type"] for s in streams(self.out)], ["video"])

    def test_document_keeps_the_sound(self):
        video_optimizer.encode(clip(self.dir, "1280x720"), self.out, video_optimizer.DOCUMENT)
        self.assertEqual(sorted(s["codec_type"] for s in streams(self.out)), ["audio", "video"])

    def test_document_takes_a_silent_clip_too(self):
        self.assertTrue(video_optimizer.encode(
            clip(self.dir, "1280x720", sound=False), self.out, video_optimizer.DOCUMENT))
        self.assertEqual([s["codec_type"] for s in streams(self.out)], ["video"])

    def test_lighter_says_no_when_the_encode_is_not_smaller(self):
        source = clip(self.dir, "320x180", rate=10)
        with patch("erp.video_optimizer.encode", side_effect=lambda s, t, p: shutil.copy(s, t) or True):
            self.assertFalse(video_optimizer.lighter(source, self.out, video_optimizer.WEB))

    def test_the_still_frame_is_a_jpeg(self):
        frame = os.path.join(self.dir, "frame.jpg")
        self.assertTrue(video_optimizer.first_frame(clip(self.dir, "1280x720"), frame))
        with open(frame, "rb") as f:
            self.assertEqual(f.read(2), b"\xff\xd8")


class WithoutFfmpeg(SimpleTestCase):
    def test_a_missing_ffmpeg_is_said_so(self):
        with patch("erp.video_optimizer.subprocess.run", side_effect=FileNotFoundError("ffmpeg")):
            with self.assertRaises(video_optimizer.FfmpegMissing):
                video_optimizer.encode("in.mp4", "out.mp4", video_optimizer.WEB)


def download(body=b"x" * 1000):
    response = MagicMock()
    response.__enter__.return_value = response
    response.iter_content.return_value = [body]
    return response


def writes(size):
    def run(source, target, profile):
        with open(target, "wb") as f:
            f.write(b"v" * size)
        return os.path.getsize(target) < os.path.getsize(source)
    return run


@override_settings(USE_BUNNY_CDN=True)
@patch("marketing.utils.bunny_storage.delete_from_bunny", return_value=True)
@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://cdn.invalid/x")
@patch("marketing.utils.bunny_storage.download_from_bunny", side_effect=lambda *a, **kw: download())
class VideoAttachments(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("burak", password="pw")
        self.attachment = Attachment.objects.create(
            record_type=ContentType.objects.get_for_model(self.user), record_id=self.user.pk,
            name="IMG_0042.MOV", path="Operating/orders/7/abcd1234_IMG_0042.MOV",
            size=1000, content_type="video/quicktime")

    def test_a_lighter_encode_takes_the_originals_place_and_the_original_goes(
            self, dl, upload, delete):
        with patch("erp.video_optimizer.lighter", side_effect=writes(300)) as lighter:
            self.assertTrue(attachments.lighten_video(self.attachment.pk))
        self.assertIs(lighter.call_args.args[2], video_optimizer.DOCUMENT)  # sound kept
        self.attachment.refresh_from_db()
        self.assertRegex(self.attachment.path, r"^Operating/orders/7/[A-Za-z0-9]{8}_IMG_0042\.mp4$")
        self.assertEqual((self.attachment.name, self.attachment.size, self.attachment.content_type),
                         ("IMG_0042.mp4", 300, "video/mp4"))
        self.assertEqual(upload.call_args.args[1], self.attachment.path)
        delete.assert_called_once_with("Operating/orders/7/abcd1234_IMG_0042.MOV")

    def test_a_video_the_encode_cannot_shrink_stays_as_it_came(self, dl, upload, delete):
        with patch("erp.video_optimizer.lighter", return_value=False):
            self.assertFalse(attachments.lighten_video(self.attachment.pk))
        self.attachment.refresh_from_db()
        self.assertEqual(self.attachment.path, "Operating/orders/7/abcd1234_IMG_0042.MOV")
        upload.assert_not_called()
        delete.assert_not_called()

    def test_an_attachment_deleted_meanwhile_takes_the_new_file_too(self, dl, upload, delete):
        def encode_while_deleted(source, target, profile):
            Attachment.objects.filter(pk=self.attachment.pk).update(path="gone")
            return writes(300)(source, target, profile)

        with patch("erp.video_optimizer.lighter", side_effect=encode_while_deleted):
            self.assertFalse(attachments.lighten_video(self.attachment.pk))
        delete.assert_called_once_with(upload.call_args.args[1])

    def test_a_video_upload_is_re_encoded_after_it_is_saved_and_a_pdf_is_not(
            self, dl, upload, delete):
        request = MagicMock(user=self.user)
        request.FILES.getlist.side_effect = lambda key: [
            SimpleUploadedFile("clip.mov", b"mov", "video/quicktime"),
            SimpleUploadedFile("slip.pdf", b"%PDF-1.4", "application/pdf"),
        ] if key == "files" else []
        with patch("erp.attachments.lighten_video_after_commit") as later, \
                patch("erp.pdf_optimizer.optimize_pdf", return_value=None):
            self.assertEqual(attachments.save_uploads(request, self.user, "Operating/orders"), [])
        video = Attachment.objects.get(name="clip.mov")
        later.assert_called_once_with(video.pk)
