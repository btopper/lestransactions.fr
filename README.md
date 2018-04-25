# lestransactions.fr

LesTransactions.fr is based on python3.6.
LesTransactions.fr architecture is as follows :

***SERVER SIDE***

  (1) AMF_crawler.py

  Contains 4 classes :
  
    - AMFdata, which crawls AMF website, parses the pdf files and inserts data into stock_data/amf.db
    
    - Tradingdata, which crawls Euronext website to get last trading price.
    
    - Mail, to send e-mail alerts to users.
    
    - CsvWriter, to write data in a csv file.

   AMF_crawler is automatically launched everyday at 7pm using cron.

  (2) Stock Data
  
  Located in stock_data/
  
    - allstocks.py is a dict of all stocks in db
    
    - amf.db is the sqlite3 db file
    
    - amf.csv is the csv counterpart of the sqlite3 db file
    
    - trade.json is a json file which has last quote for each stock
 
***WEB***

  (1) server.fcgi

  Based on Flask framework.
  
  Homepage, Bdd, Login, Logout, etc.

  (2) Templates
  
  Located in templates/
  
  Based on Jinja2
  
  (3) Static
  
  JS file
  
  (4) User Data
  
  Located in user_data/
  
    - users.py is a dict that looks like this : users={email1:{pwd:xxx},email2:{pwd:yyy}}
    - subscriptions.py is a dict that looks like this : subscriptions={email1:{global:value,FRXX:value,FRYY:value},email2:{global:value,FRXX:value,FRYY:value}}
      - global is for global alerts, value is the threshold for emails
      - FRXX is an ISIN, value is the threshold for emails
 
 ***MISC***
 
 Root folder also contains a local.env file with passwords and API_keys
 All files/folders are distributed under CC BY-NC-SA 4.0 licence (see licence file)

  Contact : contact@lestransactions.fr
