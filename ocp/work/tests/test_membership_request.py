# To run this test you'll need to download phantomjs. See:
# https://gist.github.com/telbiyski/ec56a92d7114b8631c906c18064ce620

from django.test import LiveServerTestCase

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from ocp.work.tests import objects_for_work_tests

class MembershipRequestTestCase(LiveServerTestCase):

    # It helps selenium to wait for loading new pages.
    def wait_loading(self, driver, xpath_string):
        try:
            WebDriverWait(driver, 20).until(lambda driver: driver.find_element_by_xpath(xpath_string))
        except TimeoutException as ex:
            print("Exception has been thrown. " + str(ex))
            self.tearDownClass()

    # It helps selenium to wait for js/css changes of element visibility.
    def wait_js(self, driver, xpath_string):
        try:
            WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.XPATH, xpath_string)))
        except TimeoutException as ex:
            print("Exception has been thrown. " + str(ex))
            self.tearDownClass()

    @classmethod
    def setUpClass(cls):
        super(MembershipRequestTestCase, cls).setUpClass()
        cls.selenium = webdriver.PhantomJS()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.save_screenshot('screenshot.png')
        cls.selenium.quit()
        super(MembershipRequestTestCase, cls).tearDownClass()

    # This is the membership request test.
    def test_membership_request(self):
        objects_for_work_tests.initial_test_data()
        s = self.selenium
        s.maximize_window()

        # Anonymous user fills the membership request form.
        s.get('%s%s' % (self.live_server_url, "/"))
        self.wait_loading(s, '//title[contains(text(), "OCP: Open Collaborative Platform")]')
        s.find_element_by_link_text("Join FreedomCoop").click()
        self.wait_loading(s, '//title[contains(text(), "Request Membership at FreedomCoop")]')
        s.find_element_by_id("id_name").send_keys("test_name01")
        s.find_element_by_id("id_requested_username").send_keys("test_user01")
        s.find_element_by_id("id_email_address").send_keys("test_name01@example.com")
        s.find_element_by_id("id_description").send_keys("This is a test user.")
        s.find_element_by_xpath('//input[@value="Submit"]').click()
        self.wait_loading(s, '//title[contains(text(), "Thank you for your membership request")]')

        # Admin login.
        s.get('%s%s' % (self.live_server_url, "/"))
        self.wait_loading(s, '//title[contains(text(), "OCP: Open Collaborative Platform")]')
        s.find_element_by_id("id_username").send_keys("admin_user")
        s.find_element_by_id("id_password").send_keys("admin_passwd")
        s.find_element_by_xpath('//button[@type="submit"]').click()
        self.wait_loading(s, '//title[contains(text(), "| My Dashboard")]')

        # Admin takes the simple task (accounting/work -> Mine!)
        self.wait_js(s, '//a[contains(text(), "admin_agent")]')
        s.find_element_by_partial_link_text("admin_agent").click()
        self.wait_js(s, '//a[contains(text(), "Coop Admin App")]')
        s.find_element_by_partial_link_text('Coop Admin App').click()
        self.wait_loading(s, '//title[contains(text(), "| My Work")]')
        s.find_element_by_partial_link_text("All Work").click()
        self.wait_loading(s, '//title[contains(text(), "| Work")]')
        self.wait_js(s, '//input[@value="Mine!"]')
        s.find_element_by_xpath('//input[@value="Mine!"]').click()
        self.wait_js(s, '//input[@value="Decline"]')

        # Admin creates agent (click Open -> click Create Agent)
        # (open new tab is a mess, so we go to the "Open" link url)
        s.get('%s%s' % (self.live_server_url, "/accounting/membership-request/1/"))
        self.wait_loading(s, '//title[contains(text(), "| Freedom Coop Membership Request for")]')
        s.find_element_by_partial_link_text("Create New Agent").click()
        self.wait_js(s, '//input[@value="Save"]')
        s.find_element_by_xpath('//input[@value="Save"]').click()
        self.wait_loading(s, '//title[contains(text(), "| Agent:")]')

        # Admin creates user (click Create user -> enter new password)
        s.find_element_by_partial_link_text("Create User").click()
        self.wait_js(s, '//button[contains(text(), "Save user")]')
        s.find_element_by_id("id_password1").send_keys("test_user01password")
        s.find_element_by_id("id_password2").send_keys("test_user01password")
        s.find_element_by_xpath('//button[contains(text(), "Save user")]').click()
        self.wait_js(s, '//a[contains(text(), "FairCoin: Faircoin address for test_user01")]')


        # Admin defines associations (click Maintain Associations)
        s.find_element_by_partial_link_text("Maintain Associations").click()
        self.wait_loading(s, '//title[contains(text(), "| Maintain Associations")]')

        # - change "is participant of" -> FC MembershipRequest
        # - change "Active" -> candidate
