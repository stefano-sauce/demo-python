import pytest
from os import environ

from appium.options.common import AppiumOptions
from appium.options.ios import XCUITestOptions
from selenium import webdriver
from appium import webdriver as appiumdriver
from selenium.common.exceptions import WebDriverException

import urllib3

urllib3.disable_warnings()


def sauce_tags(*tags):
    # Sauce Labs tags for filtering jobs by repo/framework/use case; SAUCE_TAGS (comma-separated,
    # e.g. "ci:cron") is appended so scheduled runs can be told apart from manual ones.
    extra = [t.strip() for t in environ.get('SAUCE_TAGS', '').split(',') if t.strip()]
    return ['repo:demo-python', 'lang:python', *tags, *extra]

emusim_browsers = [
    {
        "deviceName": "iPhone 16 Simulator",
        "browserName": "Safari",
        "deviceOrientation": "portrait",
        "platformVersion": "26.5",
        "platformName": "iOS"
    }, {
        "deviceName": "iPhone 11 Simulator",
        "browserName": "Safari",
        "deviceOrientation": "portrait",
        "platformVersion": "26.1",
        "platformName": "iOS"
    }, {
        # The GoogleAPI / Samsung emulators were retired; current Pixel emulators replace them
        "deviceName": "Google Pixel 9 Emulator",
        "browserName": "Chrome",
        "deviceOrientation": "portrait",
        "platformVersion": "16.0",
        "platformName": "Android"
    }, {
        "deviceName": "Google Pixel 7 Emulator",
        "browserName": "Chrome",
        "deviceOrientation": "portrait",
        "platformVersion": "14.0",
        "platformName": "Android"
    }]


def pytest_addoption(parser):
    parser.addoption("--dc", action="store", default='eu', help="Set Sauce Labs Data Center (US or EU)")


@pytest.fixture
def data_center(request):
    return request.config.getoption('--dc')


@pytest.fixture(params=emusim_browsers)
def mobile_web_driver(request, data_center):

    test_name = request.node.name
    build_tag = environ.get('BUILD_TAG', "Sauce-Best-Practices-Python-Mobile-Web")

    username = environ['SAUCE_USERNAME']
    access_key = environ['SAUCE_ACCESS_KEY']

    if data_center and data_center.lower() == 'us':
        selenium_endpoint = "https://@ondemand.us-west-1.saucelabs.com/wd/hub"
    else:
        selenium_endpoint = "https://@ondemand.eu-central-1.saucelabs.com/wd/hub"

    sauce_options = {
        'username': username,
        'accessKey': access_key,
        'build': build_tag,
        'name': test_name,
        # No appiumVersion: emulators/simulators reject the 'latest' alias (real devices accept it),
        # and Sauce Labs then picks the recommended Appium for each emulator/simulator image
        'tags': sauce_tags('framework:appium', 'cli:pytest', 'usecase:mobile-web-best-practices',
                           'platform:' + request.param['platformName'].lower(),
                           'device:' + ('emulator' if request.param['platformName'] == 'Android' else 'simulator'),
                           'browser:' + request.param['browserName'].lower()),
    }
    options = AppiumOptions()
    options.set_capability('sauce:options', sauce_options)
    options.platform_name = request.param['platformName']
    options.browser_name = request.param['browserName']
    # The base AppiumOptions class silently ignores device_name/platform_version/device_orientation
    # (they only exist on the platform-specific classes). Without a device name Sauce Labs runs the
    # session on any available real device instead of the requested emulator/simulator.
    options.set_capability('appium:platformVersion', request.param['platformVersion'])
    options.set_capability('appium:deviceName', request.param['deviceName'])
    options.set_capability('appium:orientation', request.param['deviceOrientation'].upper())
    options.automation_name = 'UiAutomator2' if request.param['platformName'].lower() == 'android' else 'XCUITest'

    browser = webdriver.Remote(
        command_executor=selenium_endpoint,
        options=options,
        keep_alive=True
    )

    # This is specifically for SauceLabs plugin.
    # In case test fails after selenium session creation having this here will help track it down.
    if browser is not None:
        print("SauceOnDemandSessionID={} job-name={}".format(browser.session_id, test_name))
    else:
        raise WebDriverException("Never created!")

    yield browser

    # Teardown starts here
    # report results
    # use the test result to send the pass/fail status to Sauce Labs
    sauce_result = "failed" if request.node.rep_call.failed else "passed"
    if request.node.rep_call.failed:
        print_page_state(browser)
    browser.execute_script("sauce:job-result={}".format(sauce_result))
    browser.quit()


@pytest.fixture
def rdc_browser(request, data_center):

    username = environ['SAUCE_USERNAME']
    access_key = environ['SAUCE_ACCESS_KEY']

    sauce_options = {
        'username': username,
        'accessKey': access_key,
        'build': 'RDC-iOS-Web-Python-Best-Practice',
        'name': request.node.name,
        # Without this, real devices fall back to an old default Appium (1.22) that can't find elements
        'appiumVersion': 'latest',
        'tags': sauce_tags('framework:appium', 'cli:pytest', 'usecase:mobile-web-best-practices',
                           'platform:ios', 'device:real-device', 'browser:safari', 'feature:network-capture'),
        'networkCapture': True,
    }
    options = XCUITestOptions()
    options.set_capability('sauce:options', sauce_options)
    options.platform_name = 'iOS'
    options.browser_name = 'Safari'
    options.device_name = 'iPhone.*'
    # Appium's Safari web context attaches to a blank page on real devices with iOS 14 and iOS 26+
    # (measured on Sauce EU: 0/13 passed there, 31/31 on iOS 16-18), so pin to iOS 18.x
    options.platform_version = '18'

    if data_center and data_center.lower() == 'us':
        sauce_url = 'https://ondemand.us-west-1.saucelabs.com/wd/hub'
    else:
        sauce_url = 'https://ondemand.eu-central-1.saucelabs.com/wd/hub'

    driver = appiumdriver.Remote(sauce_url, options=options)
    yield driver
    sauce_result = "failed" if request.node.rep_call.failed else "passed"
    if request.node.rep_call.failed:
        print_page_state(driver)
    driver.execute_script("sauce:job-result={}".format(sauce_result))
    driver.quit()


def print_page_state(driver):
    # Show what the browser had rendered when a test failed, to help debug flaky runs
    try:
        state = driver.execute_script(
            "return {readyState: document.readyState,"
            " addToCartButtons: document.querySelectorAll('[data-test^=\"add-to-cart\"]').length,"
            " text: document.body ? document.body.innerText.slice(0, 500) : ''};")
        print("Page state at failure: url={} state={}".format(driver.current_url, state))
    except WebDriverException as e:
        print("Could not read page state at failure: {}".format(e.msg))


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    # this sets the result as a test attribute for Sauce Labs reporting.
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # set an report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"
    setattr(item, "rep_" + rep.when, rep)
