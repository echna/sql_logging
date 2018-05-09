import json
from getpass import getuser
from socket import gethostname, gethostbyname
from time import gmtime, strftime
import pyodbc

def logged(funct_version="0.0.0"):
    """
        logging wrapper for simplest logging if a function
        creates entry in log table : "log_funct_" + funct.__name__ with the function's arguments as log_detail
        updates the log entry after completion of function with status=100 and log_detail of function's arguments and ouput of the function

        :param: funct_version -- optional version string

        Usage:
            @logged
            def sum(a,b,c):
                return a+b+c

        now any call of sum() will be logged.
    """
    def inner(funct):
        def wrapper(*args, **kwargs):
            log_entry = Log(
                app_name    = funct.__name__,
                app_version = funct_version,
                log_tb      = "log_funct_" + funct.__name__,
                log_detail  = json.JSONEncoder().encode({"args" : args, "kwargs" : kwargs})
            )
            rv = funct(*args, **kwargs)
            log_entry.update(
                100,
                json.JSONEncoder().encode({"args" : args, "kwargs" : kwargs, "return" : rv})
            )
            return rv
        return wrapper
    return inner

class Log():
    """
        Class whose objects create an entry in a log table and update it
        :param: app_name -- string specifying name of the process to be logged
        :param: app_version -- string specifying the version of the process to be logged
        :param: log_tb -- string specifying the log table name to be used. Database and Server are hard coded
        :param: log_detail -- string to cover all possible detail of what is being logged, preferably in JSON format.

        Usage:
            my_log = Log(
                app_name='best App',
                app_version='9001',
                log_tb='best_App_log_tb',
                log_detail='json string of the detail of what the App just did,'
            )

            *execute the things described in the log*

            my_log.update(log_status=100, log_detail='Same detail as above apended with any relevant information from the run app.')


    """
    _log_sv       = None
    _log_db       = None
    _log_tb       = None
    _log_id       = None
    _log_status   = 0
    _log_detail   = None
    _log_saved    = False

    _app_name     = None
    _app_version  = None

    _user_machine = None
    _user_ip      = None
    _user_name    = None


    def __init__(self, app_name, app_version, log_tb, log_detail, log_sv='192.168.99.100', log_db='test_db', user_machine=gethostname(), user_ip=gethostbyname(gethostname()), user_name=getuser()):

        self._app_name      = app_name
        self._app_version   = app_version
        self._log_tb        = log_tb
        self._log_detail    = log_detail
        self._log_sv        = log_sv
        self._log_db        = log_db
        self._user_machine  = user_machine
        self._user_ip       = user_ip
        self._user_name     = user_name
        # create a the log table log_tb if it doesn't already exist
        self._create_log_db()
        self._create_log_tb()
        # write entry into log table log_tb
        self._save()

    def update(self, log_status, log_detail):
        """
            Update a log entry with a new status and detail
            Also updates the time ellapsed and end time automatically
            :param: log_status - int specifying  current status of process being logged.
                status code convention:
                    start:       status = 0
                    in progress: 0 < status < 100
                    finished:    status = 100
                    failed:      status = 400
            :param: log_detail - string containing all detail of process being logged, preferably in JSON format.
        """

        if self._log_id is not None:

            self._log_status = str(log_status)
            self._log_detail = log_detail

            with self._conn() as conn:
                with conn.cursor() as cur:
                    try:
                        cur.execute(self._update_qy())
                        cur.commit()
                    except pyodbc.Error as e:
                        print("---LOG--- UPDATE ERROR: ")
                        print(e)


    def _save(self):
        """ Create a new entry in the log table """
        if not self._log_saved:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    try:
                        self._log_id = str(cur.execute(self._save_qy()).fetchall()[0][0])
                        cur.commit()
                        self._log_saved = True
                    except pyodbc.Error as e:
                        print("---LOG--- SAVE ERROR: ")
                        print(e)

    def _save_qy(self):
        """ Create the SQL query to create a new entry in the log table """
        entry = {
            'status'        : self._log_status,
            'user_name'	    : self._user_name,
            'user_ip'       : self._user_ip,
            'user_machine'	: self._user_machine,
            'app_name'	    : self._app_name,
            'app_version'   : self._app_version,
            'time_start'	: strftime("%Y-%m-%d %H:%M:%S", gmtime()),
            'time_end'	    : None,
            'time_elapsed'	: None,
            'detail'	    : self._log_detail
        }

        qy = "INSERT INTO " + sql_db_dbo_tb(self._log_db, self._log_tb) + " (" + ", ".join(entry.keys()) + ")"
        qy += " OUTPUT inserted.id "
        qy += " VALUES (" + ", ".join(str_none_to_null(value) for value in entry.values()) + ")"

        return qy


    def _update_qy(self):
        """ Create the SQL query to update a log entry  """

        time = strftime("%Y-%m-%d %H:%M:%S", gmtime())

        qy =  "Update " + sql_db_dbo_tb(self._log_db, self._log_tb)
        qy += "  set status = " + self._log_status
        qy += ", time_end = '" + time + "'"
        qy += ", time_elapsed = ( SELECT DATEDIFF(SECOND, '19000101', CAST('" + time
        qy += "' as DATETIME) - CAST([time_start] as DATETIME )) FROM [" + self._log_db + "].[dbo].[" + self._log_tb + "] "
        qy += " where id = '" + self._log_id + "')"
        qy += ", detail = '" + self._log_detail + "'"
        qy += " where id = '" + self._log_id  + "'"

        return qy


    def _conn(self):
        """ Create a connection object to the logging database  """
        return pyodbc.connect('DRIVER={SQL Server};SERVER=' + self._log_sv + ';UID=SA;PWD=Pa__w0rd;')



    def _create_log_tb(self):
        """ Create the log table if it doesn't exist already  """

        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(self._create_log_tb_qy())
                cur.commit()


    def _create_log_tb_qy(self):
        """ Create the SQL query to create a log table if it doesn't exist already  """

        qy = """
            IF (NOT EXISTS (
                SELECT *
                    FROM """ + self._log_db +  """.INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = 'dbo'
                    AND  TABLE_NAME = '""" + self._log_tb + """'))
            BEGIN

            create table """ + sql_db_dbo_tb(self._log_db, self._log_tb) + """
            (
                ID	            int IDENTITY(1,1),
                status	        int,
                user_name	    nvarchar(255),
                user_machine	nvarchar(255),
                user_ip         nvarchar(255),
                app_name	    nvarchar(255),
                app_version	    nvarchar(255),
                time_start	    nvarchar(255),
                time_end	    nvarchar(255),
                time_elapsed	int,
                detail	        nvarchar(MAX),
            )
            END
        """

        return qy

    def _create_log_db(self):
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("If DB_ID(N'" + self._log_db + "') IS NULL BEGIN; CREATE DATABASE " + self._log_db + "; END;")
                cur.commit()


def str_none_to_null(string):
    if string is None:
        return "NULL"
    return "'" + str(string) + "'"

def sql_db_dbo_tb(db, tb):
    return("[" + db +  "].[dbo].[" + tb + "]")

if __name__ == '__main__':
    print("Creating log")
    test_log = Log(
        app_name = 'test_app',
        app_version = '1.1.1',
        log_tb = 'test_tb',
        log_detail = 'Not much to say.'
    )

    test_log.update(
        log_status = 100,
        log_detail = 'Nothign else to tell.'
    )
    print("Created log")


