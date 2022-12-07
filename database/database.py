import sqlite3
import configparser
from contextlib import contextmanager


CONFIG_PATH='config.ini'
config = configparser.ConfigParser()
config.read(CONFIG_PATH)

DATABASE_PATH = config.get('database','path')
BACKUP_PATH = config.get('database','backuppath')

EMAIL_REGEX = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"

def create_backup():
    """Creates a backup in the path specified in the config.ini.
    """
    with database_connection() as database_conn:
        with database_connection(BACKUP_PATH) as backup_conn:
            database_conn.backup(backup_conn)


@contextmanager
def database_connection(path=DATABASE_PATH):
    conn = connect(path)
    try:
        yield conn
    finally:
        close_connection(conn)
    

def connect(path=DATABASE_PATH) -> sqlite3.Connection | None:
    """creates a connection to the database specified in the congig.ini.

    Returns:
        sqlite3.Connection: Connection to the sqlite database or None.
    """
    #threading mode     threadsafety attribute
    #single-thread 	    0
    #multi-thread 	    1
    #serialized 	    3
    if sqlite3.threadsafety == 3:
        check_same_thread = False
    else:
        check_same_thread = True

    conn = None
    try:
        conn = sqlite3.connect(path, check_same_thread=check_same_thread)
        return conn
    except Exception as e:
        print(e)

    return conn

def close_connection(conn:sqlite3.Connection)->None:
    """closes active sqlite3 connection.

    Args:
        conn (sqlite3.Connection): Connection to a sqlite database.
    """
    try:
        conn.close()

    except sqlite3.Error as e:
        print(e)

def create_table(create_table_sql:str)-> None:
    """create a table from the create_table_sql statement

    Args:
        conn (sqlite3.Connection): Connection object
        create_table_sql (str): a CREATE TABLE statement
    """
    try:
        with database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(create_table_sql)
            conn.commit()
            cursor.close()
    except sqlite3.Error as e:
        print(e)

