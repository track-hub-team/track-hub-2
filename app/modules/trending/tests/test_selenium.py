import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


class TestDefaultSuite:
    def setup_method(self, method):
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

        self.driver.implicitly_wait(10)

        self.vars = {}

    def teardown_method(self, method):
        time.sleep(1)
        self.driver.quit()

    def test_trendingredirectdataset(self):
        print("Iniciando test: Redirect Dataset...")
        self.driver.get("https://track-hub-2-staging.onrender.com/")
        self.driver.set_window_size(1200, 800)

        time.sleep(1)

        self.driver.find_element(By.LINK_TEXT, "Prueba GPX Zenodo").click()
        print("Click realizado en 'Prueba GPX Zenodo'")

    def test_trendingbuttonview(self):
        print("Iniciando test: Button View...")
        self.driver.get("https://track-hub-2-staging.onrender.com/")
        self.driver.set_window_size(1200, 800)

        time.sleep(1)

        self.driver.find_element(By.LINK_TEXT, "View").click()
        print("Click realizado en 'View'")

    def test_trendingseeallbutton(self):
        print("Iniciando test: See All Button...")
        self.driver.get("https://track-hub-2-staging.onrender.com/")
        self.driver.set_window_size(1200, 800)

        time.sleep(1)

        self.driver.find_element(By.LINK_TEXT, "See all").click()
        print("Click realizado en 'See all'")
