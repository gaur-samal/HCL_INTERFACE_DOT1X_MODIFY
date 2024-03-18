This script would modify the interface config based on the input file given which will be a CSV file consisting of 2 columns (Device IP and Port name). Sample file is attached. this script would either add or remove the dot1x config from ports mentioned in CSV file. it will give an option to retry the failed devices ( due to connectivity or some other issues) for the same option. this script gives a summary of devices logged in and IP addresses of devices, of which login failed.

USAGE:

download the file from github:

git clone https://github.com/gaur-samal/HCL_INTERFACE_DOT1X_MODIFY.git

if you have proxy then,

https_proxy=your proxy:80 git clone https://github.com/gaur-samal/HCL_INTERFACE_DOT1X_MODIFY.git

go to the directory:

cd HCL_INTERFACE_DOT1X_MODIFY/

change permissions:

chmod 700 dot1x.py

execute the script:

./dot1x.py test.csv << replace the test.csv with the csv file having device IP and Port name. this is for demo purpose.
