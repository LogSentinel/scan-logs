#!/usr/bin/python

import os
import socket
import re
import sys
import subprocess
import datetime
import getpass

def handle_mssql(username, password):
    try:
        install_package("pyodbc")
        import pyodbc
        pyodbc.connect("UID=" + username + ";PWD=" + password)
        # TODO fetch native driver and fill ad configuration template before connecting
        # SELECT * FROM sys.schemas
    except SystemExit as e:
        pass

def handle_mysql(username, password):
    try:
        install_package("mysql-connector")
        import mysql.connector
        mydb = mysql.connector.connect(
          host = "localhost",
          user = username,
          passwd = password
        )
        audit_tables = []

        cursor = mydb.cursor()
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        for database in databases:
            if database[0] == "information_schema":
                continue

            cursor.execute("SHOW TABLES IN " + database[0])
            tables = cursor.fetchall()
            for table in tables:
                if is_audit_table(table[0]):
                    audit_tables.append(database[0] + "." + table[0])

        return audit_tables
    except SystemExit as e:
        pass

def handle_postgres(username, password):
    try:
        install_package("psycopg2")
        import psycopg2
        connection = psycopg2.connect(user = username,
                                      password = password,
                                      host = "127.0.0.1")
        audit_tables = []

        cursor = connection.cursor()
        cursor.execute("SELECT schemaname, tablename FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema';")
        tables = cursor.fetchall();

        for table in tables:
            if is_audit_table(table[1]):
                audit_tables.append(tables[0] + "." + table[1])

    except SystemExit as e:
        pass

def handle_oracle(username, password):
   try:
       # in order for that to work on Windows, the latest python 2.x must be installed
       # as well as https://www.microsoft.com/en-us/download/details.aspx?id=44266
       install_package("cx_Oracle")
       import cx_Oracle
       service = raw_input("Enter Oracle service name: ")
       port = raw_input("Enter Oracle port: ")
       connection = cx_Oracle.connect(username + "/" + password + "@localhost:" + port + "/" + service, mode=cx_Oracle.SYSDBA)
       audit_tables = []
       cursor = connection.cursor()
       cursor.execute("SELECT DISTINCT OWNER, OBJECT_NAME FROM ALL_OBJECTS WHERE OBJECT_TYPE = 'TABLE'")
       tables = cursor.fetchall()
       for table in tables:
           if is_audit_table(table[1]):
               audit_tables.append(tables[0] + "." + table[1])

       cursor.execute("SELECT COUNT(*) FROM DBA_AUDIT_TRAIL")
       count = cursor.fetchone()

       audit_trail_enabled = False
       if count[0] > 0:
           audit_trail_enabled = True

       return (audit_tables, audit_trail_enabled)
   except SystemExit as e:
       pass

def is_audit_table(name):
    return name.endswith("log") or "audit" in name or "trail" in name

def is_critical(log_file):
	return False

def install_package(package):
    subprocess.call([sys.executable, "-m", "pip", "install", package])

# TODO: install pip curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py python get-pip.py
# Make a bash script that curl gets this script, then installs pip, then calls this script

path = "/"

# 1. find text log files
log_files = []
log_collectors = []

# r=root, d=directories, f = files
for r, d, f in os.walk(path):
    for file in f:
        if ((file.endswith(".log") or ".log." in file
          or "/log/" in r or "/logs/" in r or r.endswith("/log") or r.endswith("/logs"))
          and file != "change.log" and not file.endswith(".rst")):
            log_files.append(os.path.join(r, file))

        # Fill log collectors
        if "/graylog" in r:
            log_collectors.append("graylog")
        if "/splunk" in r:
            log_collectors.append("splunk")
        if "/logstash" in r:
            log_collectors.append("logstash")
        if "/fluentd" in r:
            log_collectors.append("fluentd")


# 2. find database servers
db_ports = {}
db_ports["mssql"] = 1433
db_ports["mysql"] = 3306
db_ports["postgres"] = 5432
db_ports["oracle"] = 1521
# TODO support more databases
#db_ports["cassandra"] = 9042
#db_ports["mongo"] = 27017
#db_ports["redis"] = 6379
#db_ports["firebird"] = 3050
#db_ports["db2"] = 50000

running_databases = []

# Create a TCP socket
s = socket.socket()
for db, port in db_ports.items():
    try:
        s.connect(("localhost", port))
        running_databases.append(db);
        print "Connected to %s on port %s" % (db, port)
    except socket.error, e:
        pass

audit_tables = []
for db in running_databases:
    username = raw_input("Enter username for " + db + ": ")
    password = getpass.getpass("Enter password for " + db + ": ")
    if db == "mssql":
        tables = handle_mssql(username, password)
        audit_tables.extend(tables)
    if db == "mysql":
        tables = handle_mysql(username, password)
        audit_tables.extend(tables)
    if db == "postgres":
        tables = handle_postgres(username, password)
        audit_tables.extend(tables)
    if db == "oracle":
        (tables, audit_log_enabled) = handle_oracle(username, password)
        audit_tables.extend(tables)
        print("Oracle audit log enabled: " + str(audit_log_enabled))

#------------

install_package("Jinja2")
from jinja2 import Template
f = open("report.html", "r")
template_text = f.read()
f.close()

template = Template(template_text)
report = template.render(audit_logs = list(map(lambda f: {"path": f, "critical": is_critical(f)}, log_files)), 
	audit_log_tables = list(map(lambda t: {"name": t, "native_audit_trail": False}, audit_tables)), 
	log_collectors = log_collectors)

d = datetime.datetime.today()

report_name = "log-report-" + str(d.year) + "-" + str(d.month) + "-" + str(d.day) + ".html"
f = open(report_name, "w")
f.write(report)
f.close()

print("Generated " + report_name)