import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


class TestDefaultSuite:
    def setup_method(self, method):
        self.driver = initialize_driver()
        self.host = get_host_for_selenium_testing()
        self.driver.set_window_size(1200, 800)

    def teardown_method(self, method):
        time.sleep(1)
        close_driver(self.driver)

    def test_trendingseeallbutton(self):
        print("Iniciando test: See All Button...")
        self.driver.get(f"{self.host}/")

        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, "See all"))).click()
        print("Click realizado en 'See all'")
