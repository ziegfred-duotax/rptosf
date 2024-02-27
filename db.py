from mysql.connector import connect


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
            self.conn.close()

    def save_rp_id(self, rp_id: int):
        self.cursor.execute(f"INSERT IGNORE INTO {self.config['table']}(RP_ID) VALUES(%s)", rp_id)

    def save_rp_ids(self, rp_ids: list):
        self.cursor.executemany(f"INSERT IGNORE INTO {self.config['table']}(RP_ID) VALUES(%s)", rp_ids)

    def set_rp_info(self, rp_id: int, rp_info: str):
        self.cursor.execute(f"UPDATE {self.config['table']} SET RP_INFO=%s WHERE RP_ID=%s", (rp_info, rp_id))

    def save_rp_id_and_info(self, rp_id: int, rp_info: str):
        self.cursor.execute(f"INSERT IGNORE INTO {self.config['table']}(RP_ID, RP_INFO) VALUES(%s, %s)", (rp_id, rp_info))
   
    

    
