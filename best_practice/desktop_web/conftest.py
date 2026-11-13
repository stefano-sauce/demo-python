import pytest
from os import environ

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.safari.options import Options as SafariOptions

BROWSER_OPTIONS = {
    'chrome': ChromeOptions,
    'firefox': FirefoxOptions,
    'microsoftedge': EdgeOptions,
    'safari': SafariOptions,
}

desktop_browsers = [
    {
        "platformName": "Windows 10",
        "browserName": "MicrosoftEdge",
        "platformVersion": "latest",
        "sauce:options": {}
    }, {
        "platformName": "Windows 10",
        "browserName": "firefox",
        "platformVersion": "latest-1",
        "sauce:options": {}
    }, {
        # Internet Explorer can't render saucedemo.com (a React app), so Chrome on Windows 11 replaces it
        "platformName": "Windows 11",
        "browserName": "chrome",
        "platformVersion": "latest",
        "sauce:options": {}
    }, {
        # OS X 10.14 is retired on Sauce Labs; extended debugging needs macOS 13 or later
        "platformName": "macOS 13",
        "browserName": "safari",
        "platformVersion": "latest",
        "sauce:options": {}
    }, {
        "platformName": "macOS 13",
        "browserName": "chrome",
        "platformVersion": "latest",
        "sauce:options": {
            "extendedDebugging": True
        }
    }]


def slug(value):
    return value.lower().replace(' ', '-')


def sauce_tags(*tags):
    # Sauce Labs tags for filtering jobs by repo/framework/use case; SAUCE_TAGS (comma-separated,
    # e.g. "ci:cron") is appended so scheduled runs can be told apart from manual ones.
    extra = [t.strip() for t in environ.get('SAUCE_TAGS', '').split(',') if t.strip()]
    return ['repo:demo-python', 'lang:python', *tags, *extra]


def pytest_addoption(parser):
    parser.addoption("--dc", action="store", default='us', help="Set Sauce Labs Data Center (US or EU)")


@pytest.fixture
def data_center(request):
    return request.config.getoption('--dc')


@pytest.fixture(params=desktop_browsers)
def desktop_web_driver(request, data_center):

    test_name = request.node.name
    build_tag = environ.get('BUILD_TAG', "Sauce-Best-Practices-Python-Desktop-Web")

    username = environ['SAUCE_USERNAME']
    access_key = environ['SAUCE_ACCESS_KEY']

    if data_center and data_center.lower() == 'eu':
        selenium_endpoint = "https://{}:{}@ondemand.eu-central-1.saucelabs.com/wd/hub".format(username, access_key)
    else:
        selenium_endpoint = "https://{}:{}@ondemand.us-west-1.saucelabs.com/wd/hub".format(username, access_key)

    browser_name = request.param['browserName']
    options = BROWSER_OPTIONS[browser_name.lower()]()
    options.platform_name = request.param['platformName']
    options.browser_version = request.param['platformVersion']
    sauce_options = dict(request.param['sauce:options'])
    sauce_options.update({
        'build': build_tag,
        'name': test_name,
        'tags': sauce_tags('framework:selenium', 'cli:pytest', 'usecase:desktop-web-best-practices',
                           'browser:' + slug(browser_name), 'os:' + slug(request.param['platformName'])),
    })
    options.set_capability('sauce:options', sauce_options)

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
    browser.execute_script("sauce:job-result={}".format(sauce_result))
    browser.quit()


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    # this sets the result as a test attribute for Sauce Labs reporting.
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # set an report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"
    setattr(item, "rep_" + rep.when, rep)
