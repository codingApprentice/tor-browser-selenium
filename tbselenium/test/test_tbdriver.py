import tempfile
import unittest
from os import remove
from os.path import getsize, exists
from time import sleep

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from tbselenium import common as cm
from tbselenium.tbdriver import TorBrowserDriver
from tbselenium.test import TBB_PATH
from tbselenium.utils import get_hash_of_directory

TEST_LONG_WAIT = 60


WEBGL_URL = "https://developer.mozilla.org/samples/webgl/sample1/index.html"

# Test URLs are taken from the TBB test suit
# https://gitweb.torproject.org/boklm/tor-browser-bundle-testsuite.git/tree/marionette/tor_browser_tests/test_https-everywhere.py#n18
TEST_HTTP_URL = "http://www.freedomboxfoundation.org/thanks/"
TEST_HTTPS_URL = "https://www.freedomboxfoundation.org/thanks/"


class TBDriverTest(unittest.TestCase):
    def setUp(self):
        self.tb_driver = TorBrowserDriver(TBB_PATH, tbb_logfile_path="tbb.log")

    def tearDown(self):
        self.tb_driver.quit()

    def test_tbdriver_simple_visit(self):
        """checktor.torproject.org should detect Tor IP."""
        self.tb_driver.get(cm.CHECK_TPO_URL)
        self.tb_driver.implicitly_wait(TEST_LONG_WAIT)
        h1_on = self.tb_driver.find_element_by_css_selector("h1.on")
        self.assertTrue(h1_on)

    def test_tbdriver_profile_not_modified(self):
        """Visiting a site should not modify the original profile contents."""
        profile_hash_before = get_hash_of_directory(cm.DEFAULT_TBB_PROFILE_PATH)
        self.tb_driver.get(cm.CHECK_TPO_URL)
        profile_hash_after = get_hash_of_directory(cm.DEFAULT_TBB_PROFILE_PATH)
        self.assertEqual(profile_hash_before, profile_hash_after)

    def test_httpseverywhere(self):
        """HTTPSEverywhere should redirect to HTTPS version."""
        self.tb_driver.get(TEST_HTTP_URL)
        try:
            WebDriverWait(self.tb_driver, TEST_LONG_WAIT).\
                until(EC.title_contains("thanks"))
        except TimeoutException:
            self.fail("Unexpected page title %s" % self.tb_driver.title)
        self.assertEqual(self.tb_driver.current_url, TEST_HTTPS_URL)

    def test_noscript(self):
        """NoScript should disable WebGL."""
        self.tb_driver.get(WEBGL_URL)
        try:
            WebDriverWait(self.tb_driver, TEST_LONG_WAIT).\
                until(EC.alert_is_present())
        except TimeoutException:
            self.fail("WebGL error alert should be present")
        self.tb_driver.switch_to.alert.dismiss()
        self.tb_driver.implicitly_wait(TEST_LONG_WAIT / 2)
        el = self.tb_driver.find_element_by_class_name("__noscriptPlaceholder__ ")
        self.assertTrue(el)
        # sanity check for the above test
        self.assertRaises(NoSuchElementException,
                          self.tb_driver.find_element_by_class_name, "__nosuch_class_exist")


class ScreenshotTest(unittest.TestCase):
    def setUp(self):
        _, self.temp_file = tempfile.mkstemp()

    def tearDown(self):
        if exists(self.temp_file):
            remove(self.temp_file)

    def test_screen_capture(self):
        """Check for screenshot after visit."""
        self.tb_driver = TorBrowserDriver(TBB_PATH,
                                          canvas_exceptions=[cm.CHECK_TPO_URL])
        self.tb_driver.get(cm.CHECK_TPO_URL)
        sleep(3)
        try:
            self.tb_driver.get_screenshot_as_file(self.temp_file)
        except Exception as e:
            self.fail("An exception occurred while taking screenshot: %s" % e)
        self.tb_driver.quit()
        # A blank page for https://check.torproject.org/ amounts to ~4.8KB.
        # A real screen capture on the other hand, is ~57KB. If the capture
        # is not blank it should be at least greater than 20KB.
        self.assertGreater(getsize(self.temp_file), 20000)


class HTTPSEverywhereDisabledTest(unittest.TestCase):
    def test_https_everywhere_disabled(self):
        """Make sure the HTTP->HTTPS redirection observed in the
        previous (test_httpseverywhere) test is due to HTTPSEverywhere -
        not because the site is forwarding to HTTPS by default.
        """
        disable_HE_pref = {"extensions.https_everywhere.globalEnabled": False}
        with TorBrowserDriver(TBB_PATH, pref_dict=disable_HE_pref) as driver:
            driver.get(TEST_HTTP_URL)
            sleep(1)
            # make sure it doesn't redirect to https when HTTPEverywhere is disabled
            self.assertEqual(driver.current_url, TEST_HTTP_URL,
                             """This test should be updated to use a site that
                             doesn't auto-forward HTTP to HTTPS. %s """ %
                             driver.current_url)
