from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def test_testbutton():
    """
    Test E2E: botón 'See all' desde la home.
    """
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # 1. Ir a la home
        driver.get(f"{host}/")
        driver.set_window_size(810, 1063)

        # 2. Click en "See all"
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, "See all"))).click()

        # 3. Verificación: esperar a que cargue algo característico de la página
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        # Ajusta el texto a algo que realmente veas en esa página
        assert "explore" in driver.page_source.lower()

        print("✅ Test test_testbutton PASSED")

    finally:
        close_driver(driver)


if __name__ == "__main__":
    test_testbutton()
    print("\n🎉 All trending Selenium tests passed!")
