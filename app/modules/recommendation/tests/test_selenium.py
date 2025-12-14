from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def test_recommendation200():
    """
    Test E2E: abrir dataset 'Sample dataset 8 GPX'.
    """
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # 1. Ir a la home (equivalente a http://127.0.0.1:5000/)
        driver.get(f"{host}/")
        driver.set_window_size(706, 961)

        # 2. Esperar a que el link esté presente y hacer clic
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.LINK_TEXT, "Sample dataset 8 GPX")))
        driver.find_element(By.LINK_TEXT, "Sample dataset 8 GPX").click()

        # 3. (Opcional) Alguna verificación mínima para que el test tenga aserción
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        assert "sample" in driver.page_source.lower()

        print("✅ Test test_recommendation200 PASSED")

    finally:
        # Cerrar el driver con tu helper común
        close_driver(driver)


if __name__ == "__main__":
    test_recommendation200()
    print("\n🎉 All versioning Selenium tests passed!")
