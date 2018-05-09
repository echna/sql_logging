# from lib.python.sql import execute_general_qy
import sys
import time
import threading
import signal
import logging_sql.logging_sql as logging


class SignalHandler:
    """
        The object that will handle signals and stop the periodic logging threads.
    """

    #: The pool of worker threads
    periodic_log = None

    def __init__(self, periodic_log):
        self.periodic_log = periodic_log

    def __call__(self, signum, frame):
        """
        This will be called by the python signal module

        https://docs.python.org/3/library/signal.html#signal.signal
        """
        self.periodic_log.stop()



class PeriodicLog(logging.Log):
    """
        Class whose objects create an entry in a log table and updates it at an interval
        :param: app_name -- string specifying name of the process to be logged
        :param: app_version -- string specifying the version of the process to be logged
        :param: log_tb -- string specifying the log table name to be used. Database and Server are hard coded
        :param: log_detail -- string to cover all possible detail of what is being logged, preferably in JSON format.
        :param: period -- int period of log updates in seconds
    """

    _stopper = None
    _period  = None
    thread   = None

    def __init__(self, app_name, app_version, log_tb, log_detail, period):
        print("---PeriodicLog--- Process saving first log entry.")
        super().__init__(app_name, app_version, log_tb, log_detail)
        self._period  = period
        self._stopper = threading.Event()
        self.thread   = threading.Thread(target=self.update_periodic, args=())
        self.thread.start()

        handler = SignalHandler(self)
        signal.signal(signal.SIGINT, handler)

    def update_periodic(self):
        """
            Call update evert _period seconds
            checks every second if it should stop
        """
        log_detail = self._log_detail + " Process is still alive!"
        while not self._stopper.is_set():
            i = 0
            while i < self._period and not self._stopper.is_set():
                time.sleep(1)
                i += 1

            if not self._stopper.is_set():
                self.update(50, log_detail)

    def stop(self):
        """
            Stop periodic logging and log final message
        """
        self._stopper.set()
        self.thread.join()
        print("---PeriodicLog--- Process is writing its shutdown message.")
        log_detail = self._log_detail + " Process was shut down by user."
        self.update(100, log_detail)
        sys.exit(0)

