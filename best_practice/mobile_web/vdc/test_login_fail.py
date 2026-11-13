from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def test_valid_crentials_login(mobile_web_driver):
    wait = WebDriverWait(mobile_web_driver, 15)
    open_login_page(mobile_web_driver).send_keys('locked_out_user')
    mobile_web_driver.find_element(By.ID, 'password').send_keys('secret_sauce')
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.btn_action'))).click()

    assert wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '.error-button'))).is_displayed()


def open_login_page(driver):
    # iOS simulators sometimes leave Safari on a blank page after driver.get(); reload until the
    # login form renders instead of failing the test on a browser glitch
    for attempt in range(3):
        driver.get('https://www.saucedemo.com')
        try:
            return WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.ID, 'user-name')))
        except TimeoutException:
            if attempt == 2:
                raise
