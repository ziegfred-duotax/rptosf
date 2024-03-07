from mysql.connector import connect
import json
import datetime


class RPDataDB:
    def __init__(self, config: dict):
        self.config = config
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = connect(**self.config['auth'])
        self.cursor = self.conn.cursor(dictionary=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.commit()
            self.cursor.close()
            self.conn.close()

    def save_rp_id(self, rp_id: int):
        self.cursor.execute(
            "INSERT IGNORE INTO properties(RP_ID) VALUES(%s)", rp_id)

    def save_rp_ids(self, rp_ids):
        self.cursor.executemany(
            "INSERT IGNORE INTO properties(RP_ID) VALUES(%s)", rp_ids)
        
    def save_property(self, rp_id: int, property_address: str, is_active: int, is_unit: int):
        self.cursor.execute("INSERT INTO properties(RP_ID, PROPERTY_ADDRESS, IS_ACTIVE, IS_UNIT) VALUES(%s, %s, %s, %s)", (rp_id, property_address, is_active, is_unit))

    def save_properties(self, properties):
        self.cursor.executemany("INSERT IGNORE INTO properties(RP_ID, PROPERTY_ADDRESS, IS_ACTIVE, IS_UNIT) VALUES(%s, %s, %s, %s)", properties)

    def get_property_info(self, rp_id):
        self.cursor.execute("SELECT PROPERTY_INFO FROM properties WHERE RP_ID=%s AND PROPERTY_INFO IS NOT NULL", (rp_id, ))
        property = self.cursor.fetchone()
        if property:
            property_info = json.loads(property['PROPERTY_INFO'])
            return property_info
        return None
    # def set_rp_suggestion_info(self, rp_id: int, rp_suggestion_info: str):
    #     self.cursor.execute(
    #         "UPDATE properties SET RP_SUGGESTION_INFO=%s WHERE RP_ID=%s", (rp_suggestion_info, rp_id))

    # def save_rp_id_and_suggestion_info(self, rp_id: int, rp_suggestion_info: str):
    #     self.cursor.execute(
    #         "INSERT IGNORE INTO properties(RP_ID, RP_SUGGESTION_INFO) VALUES(%s, %s)", (rp_id, rp_suggestion_info))

    def set_property_info(self, rp_id: int, property_info: str, date_scraped):
        self.cursor.execute("UPDATE properties SET PROPERTY_INFO=%s, DATE_SCRAPED=%s WHERE RP_ID=%s", (property_info, date_scraped, rp_id))

    def reset_account_page_scraped_count(self):
        self.cursor.execute("UPDATE accounts SET SCRAPED_PAGE_COUNT=0")

    def get_account(self, limit):
        self.cursor.execute(
            "SELECT * FROM accounts WHERE SCRAPED_PAGE_COUNT < %s LIMIT 1", (limit, ))
        return self.cursor.fetchone()

    def increment_account(self, username: str, limit):
        self.cursor.execute(
            "UPDATE accounts SET SCRAPED_PAGE_COUNT=SCRAPED_PAGE_COUNT + 1 WHERE USERNAME=%s AND SCRAPED_PAGE_COUNT < %s", (username, limit))