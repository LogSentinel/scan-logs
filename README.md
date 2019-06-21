# LogSentinel's Scan Logs command-line tool

The scan-logs script does the following:
- scans for log files in a system
- scans for running databases and tries to find tables that contain an audit log
- scans for enabled database-native audit trail (e.g. for MS SQL Server or Oracle)
- scans for running log collectors

Invoking the script:

There are two ways to invoke the script. The easiest one is to download the scan-logs.sh shell script and simply run it:

    > sudo scan-logs.sh

If you already have pip installed, you can download the python script and the html report templace and run it as follows:

    > sudo python scan-logs.py 

After running the script, an HTML report is generated in the current folder.