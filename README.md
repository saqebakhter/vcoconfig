# vcoconfig
VCO Config Backup and Compare Tool

Python3 is required to run this script.

Install requirements for the script 

pip3 install -r requirements.txt 

Modify config.ini , with your VCO IP, and Username/Password.

Launch app with:

python3 app.py, it will host the application at http://127.0.0.1:5000

By default data will be retained in a sqllite3 database at in the same directory as the app.py file "database.db" that can be changed or persisted to other DB types like MySQL by modifying app.py.
