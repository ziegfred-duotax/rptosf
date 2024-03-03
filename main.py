from dotenv import load_dotenv
from bot_constants import *
from bot_settings import *
from db import RPDataDB
from urllib.parse import quote
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
import selenium.webdriver.support.expected_conditions as EC
import seleniumwire.undetected_chromedriver as uc
import os
import time
import logging
import json
import gzip

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

selenium_logger = logging.getLogger('selenium')
seleniumwire_logger = logging.getLogger('seleniumwire')

load_dotenv()

BOT_ENV = os.getenv('BOT_ENV', 'DEBUG')
logger.info(f"BOT RUNNING IN {BOT_ENV}")
if BOT_ENV in ["DEBUG", "TEST"]:
    selenium_logger.setLevel(logging.DEBUG)
    seleniumwire_logger.setLevel(logging.DEBUG)

elif BOT_ENV == "PRODUCTION":
    selenium_logger.setLevel(logging.ERROR)
    seleniumwire_logger.setLevel(logging.ERROR)


DB_CONFIG = {
    'auth': {
        'user': os.environ.get('DB_USERNAME'),
        'password': os.environ.get('DB_PASSWORD'),
        'host': os.environ.get('DB_HOST'),
        'database': os.environ.get('DB_NAME')
    },
    'table': 'properties'
}

SF_EMAIL = os.environ.get('SF_EMAIL')
SF_PASSWORD = os.environ.get('SF_PASSWORD')
RP_EMAIL = os.environ.get('RP_EMAIL')
RP_PASSWORD = os.environ.get('RP_PASSWORD')

CURRENT_ACCOUNT = None


def get_driver():
    options = uc.ChromeOptions()
    user_data_dir = CHROME_USER_DATA_DIR
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument(f"--profile-directory={CHROME_PROFILE_NAME}")
    driver = uc.Chrome(
        options=options, driver_executable_path=os.environ.get('CHROMEDRIVER_PATH'))
    driver.maximize_window()
    return driver


driver = get_driver()
driver.get(SF_CLASSIC_HOME_URL)

WINDOW_HANDLES = {
    "SF": driver.current_window_handle,
    "AUTH": None,
    "RP": None
}


def is_in_login_page_sf():
    if driver.find_elements(By.ID, "Login"):
        return True
    return False


def is_in_login_page_rp():
    if driver.find_elements(By.CSS_SELECTOR, "a#signOnButton"):
        return True
    return False


def login_sf():
    logger.info("LOGGING IN TO SALESFORCE")
    if driver.current_window_handle != WINDOW_HANDLES['SF']:
        driver.switch_to.window(WINDOW_HANDLES['SF'])
    driver.get(SF_CLASSIC_HOME_URL)
    while driver.find_elements(By.ID, "Login"):
        username = driver.find_element(By.ID, "username")
        password = driver.find_element(By.ID, "password")
        login_button = driver.find_element(By.ID, "Login")
        # ActionChains(driver, 500).move_to_element(username).click().send_keys(SF_EMAIL).move_to_element(password).click().send_keys(SF_PASSWORD).move_to_element(login_button).click().perform()
        ActionChains(driver, 500).move_to_element(
            login_button).click().perform()
        try:
            WebDriverWait(driver, 10).until(
                EC.url_contains(
                    "https://duotax.my.salesforce.com/_ui/identity/verification/method/")
            )
            break
        except:
            pass

    logger.info("AUTHENTICATING")
    while driver.find_elements(By.ID, "save"):
        if not WINDOW_HANDLES['AUTH']:
            driver.execute_script("window.open()")
            time.sleep(0.3)
            WINDOW_HANDLES['AUTH'] = driver.window_handles[-1]
            time.sleep(0.3)

        driver.switch_to.window(WINDOW_HANDLES['AUTH'])
        driver.get(AUTHENTICATOR_URL)

        code_el = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class='code']"))
        )
        code = code_el.get_attribute('innerText').strip()
        driver.switch_to.window(WINDOW_HANDLES['SF'])
        code_input = driver.find_element(
            By.CSS_SELECTOR, "div.formArea > input")
        submit_button = driver.find_element(
            By.CSS_SELECTOR, "input[type='submit']")
        ActionChains(driver, 500).move_to_element(code_input).click().send_keys(
            code).move_to_element(submit_button).click().perform()
        time.sleep(3)
    logger.info("SUCCESSFULLY LOGGED IN TO SALESFORCE")


def login_rp():
    logger.info("LOGGING IN TO RP DATA")
    if not WINDOW_HANDLES['RP']:
        driver.execute_script("window.open()")
        time.sleep(0.3)
        for i in driver.window_handles:
            if i not in WINDOW_HANDLES.values():
                WINDOW_HANDLES['RP'] = i
    CURRENT_ACCOUNT = None
    while True:
        with RPDataDB(DB_CONFIG) as conn:
            CURRENT_ACCOUNT = conn.get_account()
            if CURRENT_ACCOUNT is not None:
                break
            conn.reset_account_page_scraped_count()

    driver.switch_to.window(WINDOW_HANDLES['RP'])
    driver.get(RP_BASE_URL)
    while not driver.find_elements(By.CSS_SELECTOR, "h1#crux-home-greeting"):
        try:
            login_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#signOnButtonSpan"))
            )
            username = driver.find_element(By.CSS_SELECTOR, "#username")
            password = driver.find_element(By.CSS_SELECTOR, "#password")
            username.clear()
            password.clear()
            ActionChains(driver, 500).move_to_element(username).click().key_down(Keys.LEFT_CONTROL).send_keys('a').key_up(Keys.LEFT_CONTROL).send_keys(Keys.BACK_SPACE).send_keys(CURRENT_ACCOUNT['USERNAME']).move_to_element(
                password).click().key_down(Keys.LEFT_CONTROL).send_keys('a').key_up(Keys.LEFT_CONTROL).send_keys(Keys.BACK_SPACE).send_keys(CURRENT_ACCOUNT['PASSWORD']).move_to_element(login_button).click().perform()
            # ActionChains(driver, 500).move_to_element(
            #     login_button).click().perform()
            time.sleep(6)
        except:
            pass

    logger.info("SUCCESSFULLY LOGGED IN TO RP DATA")


def switch_to_sf():
    driver.switch_to.window(WINDOW_HANDLES['SF'])
    if is_in_login_page_sf():
        login_sf()


def switch_to_rp():
    if WINDOW_HANDLES['RP'] is None:
        login_rp()
    else:
        driver.switch_to.window(WINDOW_HANDLES['RP'])
        if is_in_login_page_rp():
            login_rp()
        if '/api/' in driver.current_url:
            if 'unauthenticated' in driver.page_source:
                login_rp()


def start_rp_to_sf():
    switch_to_sf()
    logger.info(
        f"NAVIGATING TO LIST OF OPPORTUNITIES {SF_CLASSIC_OPPORTUNITIES_LIST_URL}")
    page = 0
    while True:
        if page == SF_SCRAPE_OPPORTUNITIES_PAGE_LIMIT:
            logger.info(
                "THIS ACCOUNT HAS ALREADY REACHED 5 PAGES. TERMINATING...")
            break
        driver.get(SF_CLASSIC_OPPORTUNITIES_LIST_URL)
        opp_rows = None
        try:
            opp_rows = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "div.x-grid3-row"))
            )
        except:
            logger.info("NO OPPORTUNITIES FOUND")
            break

        opps = []
        for opp_row in opp_rows:
            opp_a_tag = opp_row.find_element(
                By.CSS_SELECTOR, 'div.x-grid3-col-OPPORTUNITY_NAME > a')
            opp_url = opp_a_tag.get_attribute('href')
            opp_address = opp_row.find_element(
                By.CSS_SELECTOR, 'div.x-grid3-col-00NOm0000007kSj').get_attribute('innerText').strip()
            opp_name = opp_a_tag.find_element(
                By.CSS_SELECTOR, "span").get_attribute('innerText')
            if 'CC' in opp_name:
                logger.info(f"SKIPPED {opp_url} HAS CC")
                continue
            rp_url = None
            try:
                rp_url = opp_row.find_element(
                    By.CSS_SELECTOR, 'div.x-grid3-col-00N2t000000ui6m > a').get_attribute('href')
            except:
                pass
            opps.append({
                'OPP_URL': opp_url,
                'OPP_ADDRESS': opp_address,
                'RP_URL': rp_url,
                'RP_ID': None if rp_url is None else get_rp_id_from_url(rp_url)
            })

        for opp in opps:
            edited = False
            actions = ActionChains(driver, 600)

            if opp['RP_ID']:
                rp_info_url = RP_PROPERTY_INFO_BASE_URL.replace(
                    '[rpId]', opp['RP_ID'])
                logging.info(
                    f"GETTING PROPERTY INFO FROM RP DATA: {opp['OPP_URL']}")
                time.sleep(0.4)
                property_info = None
                property_info_from_db = False
                with RPDataDB(DB_CONFIG) as conn:
                    property_info = conn.get_property_info(opp['RP_ID'])
                    if property_info:
                        property_info_from_db = True
                while property_info is None:
                    switch_to_rp()
                    driver.get(rp_info_url)
                    property_info = find_property_data_api_response()
                if not property_info_from_db:
                    with RPDataDB(DB_CONFIG) as conn:
                        conn.set_property_info(
                            opp['RP_ID'], json.dumps(property_info))
                switch_to_sf()
                logging.info(f"TRANSFERRING RP DATA TO SF: {opp['OPP_URL']}")
                driver.get(opp['OPP_URL'] + '/e')
                try:
                    WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, '//input[@title="Save"]'))
                    )
                except:
                    logger.error(f"SAVE BUTTON NOT FOUND: {opp['OPP_URL']}")
                    continue

                edited = enter_data_to_sf_fields(opp, property_info, actions)

            else:
                switch_to_rp()
                logger.info(f"GETTING RP DATA ID: {opp['OPP_URL']}")
                suggestions_url = generate_suggestion_api_url_by_property_address(
                    opp['OPP_ADDRESS'])
                driver.get(suggestions_url)
                suggestions = find_property_suggestion_api_response()
                attempt = 0
                while suggestions is None:
                    switch_to_rp()
                    driver.get(suggestions_url)
                    suggestions = find_property_suggestion_api_response()
                    attempt += 1

                if not suggestions:
                    logger.info(f"NO SUGGESTIONS: {opp['OPP_URL']}")
                    continue

                suggestion = None

                rp_properties_to_save = []
                for i in suggestions.copy():
                    if 'suggestionId' in i:
                        rp_properties_to_save.append([i['suggestionId'], i['suggestion'], int(
                            i['isActiveProperty']), int(i['isUnit'])])
                        if suggestion is None:
                            suggestion = i

                if rp_properties_to_save:
                    with RPDataDB(DB_CONFIG) as conn:
                        conn.save_properties(rp_properties_to_save)

                if suggestion is None:
                    logger.info(f"NO SUGGESTIONS: {opp['OPP_URL']}")
                    continue

                opp['RP_ID'] = str(suggestion['suggestionId'])
                opp['RP_URL'] = RP_BASE_PROPERTY_URL.replace(
                    '[rpId]', opp['RP_ID'])
                rp_info_url = RP_PROPERTY_INFO_BASE_URL.replace(
                    '[rpId]', opp['RP_ID'])
                property_info = None
                property_info_from_db = False
                with RPDataDB(DB_CONFIG) as conn:
                    property_info = conn.get_property_info(opp['RP_ID'])
                    if property_info:
                        property_info_from_db = True
                        logger.info("FOUND FROM DATABASE")
                while property_info is None:
                    switch_to_rp()
                    driver.get(rp_info_url)
                    property_info = find_property_data_api_response()

                if not property_info_from_db:
                    with RPDataDB(DB_CONFIG) as conn:
                        conn.set_property_info(
                            opp['RP_ID'], json.dumps(property_info))
                switch_to_sf()
                driver.get(opp['OPP_URL'] + '/e')
                try:
                    WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, '//input[@title="Save"]'))
                    )
                except:
                    logger.error(f"SAVE BUTTON NOT FOUND: {opp['OPP_URL']}")
                    continue
                edited = enter_data_to_sf_fields(opp, property_info, actions)

            if edited:
                rp_data_bot_scraped = driver.find_element(
                    By.XPATH, '//label[text()="RP Data Bot Scraped"]/../..//a')
                save_button = driver.find_element(
                    By.XPATH, '//input[@title="Save"]')
                actions = actions.move_to_element(rp_data_bot_scraped).click(
                    rp_data_bot_scraped).pause(0.8)
                if BOT_ENV == "PROD":
                    actions = actions.click(save_button)
                actions.perform()

                if BOT_ENV == "PROD":
                    try:
                        WebDriverWait(driver, 5).until(
                            EC.url_contains(SF_CLASSIC_HOME_URL)
                        )
                    except:
                        logger.error(
                            f"THERE WAS A PROBLEM SAVING: {opp['OPP_URL']}")
        page += 1
        with RPDataDB(DB_CONFIG) as conn:
            conn.increment_account(CURRENT_ACCOUNT['USERNAME'])
        logger.info("PROCEEDING TO NEXT PAGE")


def enter_data_to_sf_fields(opp: dict, property_info: dict, actions: ActionChains):
    edited = False

    rp_id = driver.find_element(
        By.XPATH, '//label[text()="RP Data Property ID"]/../..//input')
    rp_street_addr_input = driver.find_element(
        By.XPATH, '//label[text()="RP Street Address"]/../..//input')
    rp_street_number_input = driver.find_element(
        By.XPATH, '//label[text()="RP Street Number"]/../..//input')
    rp_year_built_input = driver.find_element(
        By.XPATH, '//label[text()="RP Year Built"]/../..//input')
    rp_company_name = driver.find_element(
        By.XPATH, '//label[text()="RP Data Company Name"]/../..//input')
    rp_company_number = driver.find_element(
        By.XPATH, '//label[text()="RP Data Company Number"]/../..//input')
    rp_agent_name = driver.find_element(
        By.XPATH, '//label[text()="RP Data Agent Name"]/../..//input')
    rp_agent_number = driver.find_element(
        By.XPATH, '//label[text()="RP Data Agent Number"]/../..//input')

    rp_id_val = rp_id.get_attribute('value')
    if not bool(rp_id_val):
        actions = actions.move_to_element(
            rp_id).send_keys_to_element(rp_id, opp['RP_ID'])
        edited = True
    rp_street_addr_input_val = rp_street_addr_input.get_attribute('value')
    if not rp_street_addr_input_val:
        actions = actions.move_to_element(rp_street_addr_input).click(
        ).send_keys(property_info['location']['street']['singleLine'])
        edited = True
    rp_street_number_input_val = rp_street_number_input.get_attribute('value')
    if not rp_street_number_input_val:
        actions = actions.move_to_element(rp_street_number_input).click().send_keys(
            property_info['location']['street']['nameAndNumber'].title())
        edited = True
    rp_year_built_input_val = rp_year_built_input.get_attribute('value')
    if not rp_year_built_input_val and 'yearBuilt' in property_info['attrAdditional']:
        actions = actions.move_to_element(rp_year_built_input).click(
        ).send_keys(property_info['attrAdditional']['yearBuilt'])
        edited = True
    if property_info['rentCampaignList']:
        latest_campaign = property_info['rentCampaignList']['forRentPropertyCampaign']['campaigns'][0]
        if 'agency' in latest_campaign:
            rp_company_name_value = rp_company_name.get_attribute('value')
            if not rp_company_name_value and 'companyName' in latest_campaign['agency']:
                actions = actions.send_keys_to_element(
                    rp_company_name, latest_campaign['agency']['companyName'])
                edited = True
            rp_company_number_value = rp_company_number.get_attribute('value')
            if not rp_company_number_value and 'phoneNumber' in latest_campaign['agency']:
                actions = actions.send_keys_to_element(
                    rp_company_number, latest_campaign['agency']['phoneNumber'])
                edited = True
        if 'agent' in latest_campaign:
            rp_agent_name_value = rp_agent_name.get_attribute('value')
            if not rp_agent_name_value and 'agent' in latest_campaign['agent']:
                actions = actions.send_keys_to_element(
                    rp_agent_name, latest_campaign['agent']['agent'])
                edited = True
            rp_agent_number_value = rp_agent_number.get_attribute('value')
            if not rp_agent_number_value and 'phoneNumber' in latest_campaign['agent']:
                actions = actions.send_keys_to_element(
                    rp_agent_number, latest_campaign['agent']['phoneNumber'])
                edited = True
    return edited


def generate_suggestion_api_url_by_property_address(address):
    return RP_PROPERTY_SUGGESSTIONS_BASE_URL.replace('[address]', quote(address))


def find_property_data_api_response():
    for req in driver.requests:
        if 'propertyTimeline?includeCommons=true' in req.url:
            raw_obj = gzip.decompress(req.response.body).decode('utf-8')
            del driver.requests
            if 'isActiveProperty' not in raw_obj:
                return None
            obj = json.loads(raw_obj)
            return obj
    return None


def find_property_suggestion_api_response():
    for req in driver.requests:
        if '/api/clapi/suggestions?' in req.url:
            raw_obj = gzip.decompress(req.response.body).decode('utf-8')
            del driver.requests
            if 'suggestions' not in raw_obj:
                return None
            obj = json.loads(raw_obj)
            return obj['suggestions']
    return None


def get_rp_id_from_url(rp_url: str):
    return rp_url.removeprefix('https://rpp.corelogic.com.au/property/')


if __name__ == '__main__':
    start_rp_to_sf()
    driver.quit()
