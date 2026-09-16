"""The suite's runner, named by TEST_RUNNER in settings.

Its one job beyond Django's default is to put the Bunny CDN out of
reach for the length of a run.

Creating an order uploads a QR code, so most of the operating suite
touches the CDN, and nearly every one of those tests already carries an
@patch for it — on setUp, where the patch lifts the moment setUp
returns and the test body goes to the real network. On a developer's
machine that looked like it worked: .env holds a live
BUNNY_STORAGE_API_KEY, so the upload really did succeed, against
production storage. CI has no key, so the upload 401s, order creation
aborts, and twenty-eight tests fail for a reason that has nothing to do
with what any of them assert.

One stub here fixes all of them and stops the next one happening. A
test that wants to watch an upload FAIL still patches it itself; an
inner patch wins over this one and is restored to this one on exit.
"""
from unittest.mock import patch

from django.test.runner import DiscoverRunner


class NoCdnTestRunner(DiscoverRunner):
    def run_tests(self, *args, **kwargs):
        patcher = patch("marketing.utils.bunny_storage.upload_to_bunny",
                        return_value="https://mock-cdn.invalid/test.png")
        patcher.start()
        try:
            return super().run_tests(*args, **kwargs)
        finally:
            patcher.stop()
