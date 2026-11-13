*** Settings ***
Library    AppiumLibrary
Variables  ../../sauce_tags.py  framework:robotframework  cli:pabot  library:appiumlibrary
...        usecase:native-app  feature:network-capture  platform:ios  device:real-device

*** Variables ***
${REMOTE_URL}       ${DATA_CENTER}

*** Keywords ***
Start Session
    &{sauce_options}=  Create Dictionary
    ...  username=%{SAUCE_USERNAME}
    ...  accessKey=%{SAUCE_ACCESS_KEY}
    ...  build=Python-Robot-Appium-RDC-iOS
    ...  name=${TEST_NAME}
    ...  appiumVersion=latest
    ...  tags=${SAUCE_TAGS_LIST}
    ...  networkCapture=${True}
    Open Application  ${REMOTE_URL}
    ...  platformName=${platformName}
    ...  appium:deviceName=${deviceName}
    ...  appium:automationName=XCUITest
    ...  appium:app=https://github.com/saucelabs/sample-app-mobile/releases/download/2.7.1/iOS.RealDevice.SauceLabs.Mobile.Sample.app.2.7.1.ipa
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
