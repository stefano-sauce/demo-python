*** Settings ***
Library    AppiumLibrary
Variables  ../../sauce_tags.py  framework:robotframework  cli:pabot  library:appiumlibrary
...        usecase:native-app  feature:network-capture  platform:android  device:real-device

*** Variables ***
${REMOTE_URL}       ${DATA_CENTER}

*** Keywords ***
Start Session
    &{sauce_options}=  Create Dictionary
    ...  username=%{SAUCE_USERNAME}
    ...  accessKey=%{SAUCE_ACCESS_KEY}
    ...  build=Python-Robot-Appium-RDC-Android
    ...  name=${TEST_NAME}
    ...  appiumVersion=latest
    ...  tags=${SAUCE_TAGS_LIST}
    ...  networkCapture=${True}
    Open Application  ${REMOTE_URL}
    ...  platformName=${platformName}
    ...  appium:platformVersion=${platformVersion}
    ...  appium:deviceName=${deviceName}
    ...  appium:automationName=UiAutomator2
    ...  appium:orientation=${deviceOrientation}
    ...  appium:app=https://github.com/saucelabs/sample-app-mobile/releases/download/2.7.1/Android.SauceLabs.Mobile.Sample.app.2.7.1.apk
    ...  sauce:options=${sauce_options}

End Session
    Run Keyword If  '${TEST_STATUS}'== 'PASS'  Execute Script  sauce:job-result\=passed
    ...  ELSE  Execute Script  sauce:job-result\=failed
    Close All Applications

Login As Standard User
    Input Text  accessibility_id=test-Username  standard_user
    Input Text  accessibility_id=test-Password  secret_sauce
    Click Element  accessibility_id=test-LOGIN

Login As Invalid User
    Input Text  accessibility_id=test-Username  invalid
    Input Text  accessibility_id=test-Password  invalid
    Click Element  accessibility_id=test-LOGIN
