import os

import pytest
import urllib3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions

urllib3.disable_warnings()


def sauce_tags(*tags):
    # Sauce Labs tags for filtering jobs by repo/framework/use case; SAUCE_TAGS (comma-separated,
    # e.g. "ci:cron") is appended so scheduled runs can be told apart from manual ones.
    extra = [t.strip() for t in os.environ.get('SAUCE_TAGS', '').split(',') if t.strip()]
    return ['repo:demo-python', 'lang:python', *tags, *extra]


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    # Keep each phase's report on the test item so the driver fixture can send the real result
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)

@pytest.fixture()
def driver(request):
    options = ChromeOptions()
    options.browser_version = 'latest'
    options.platform_name = 'Windows 10'
    # Chrome upgrades http:// to https:// by default; some demo pages (watir.com) only serve http
    options.add_argument('--disable-features=HttpsUpgrades,HttpsFirstBalancedModeAutoEnable')

    sauce_options = {'username': os.environ["SAUCE_USERNAME"],
                     'accessKey': os.environ["SAUCE_ACCESS_KEY"],
                     'name': request.node.name,
                     'build': os.environ.get('BUILD_TAG', 'Selenium-4-Python-Examples'),
                     'tags': sauce_tags('framework:selenium', 'cli:pytest', 'usecase:selenium4-features',
                                        'browser:chrome', 'os:windows-10')}

    options.set_capability('sauce:options', sauce_options)
    region = os.environ.get('SAUCE_REGION', 'us-west-1')
    sauce_url = "https://ondemand.{}.saucelabs.com/wd/hub".format(region)

    driver = webdriver.Remote(command_executor=sauce_url, options=options)

    yield driver

    if driver is not None:
        report = getattr(request.node, 'rep_call', None)
        sauce_result = "passed" if report is not None and report.passed else "failed"
        driver.execute_script("sauce:job-result={}".format(sauce_result))

        driver.quit()
