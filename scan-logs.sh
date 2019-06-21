#!/bin/sh

curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py 
python get-pip.py

curl https://github.com/LogSentinel/scan-logs/blob/master/scan-logs.py -o scan-logs.py
curl https://github.com/LogSentinel/scan-logs/blob/master/report.html -o report.html

python scan-logs.py