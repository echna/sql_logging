# SQL logging

## Description

Python Class to allow simple logging of processes in SQL server

## Usage

At the moment the logging is configure for running with a local mssql docker image which happens to run on 192.168.99.100:

```shell
docker run -e "ACCEPT_EULA=Y" -e "SA_PASSWORD=Pa__w0rd" -p 1433:1433 --name sql1 -d microsoft/mssql-server-linux:latest
```

The package contains three main features:

    1. Log() class
    2. PeriodicLog() class
    3. logged() decorator

### Log() class

This class create a log object by:

```Python
    my_log = Log(
        app_name='best App',
        app_version='9001',
        log_tb='best_App_log_tb',
        log_detail='json string of the detail of what the App just did,'
    )
    * run the APP *
```

Which may then be updated using the update() method:

```Python
    my_log.update(log_status=50, log_detail='Same detail as above apended with any relevant information from the running app.')
    * run more APP *
    my_log.update(log_status=100, log_detail='Same detail as above apended with any relevant information from the run app.')
```

### PeriodicLog() class

This class simply creates a log and keeps updating itself every N second, where N is given by the period parameter.

In the event it receives a SIGINT stop message it will write a last update.


### logged() decorator

Logging wrapper for simplest logging of a function.
Creates entry in log table : "log_funct_" + funct.__name__ with the function's arguments as log_detail
Updates the log entry after completion of function with status=100 and log_detail of function's arguments and ouput of the function

Usage:

```Python
    @logged
    def sum(a,b,c):
        return a+b+c
```

now any call of sum() will be logged.
