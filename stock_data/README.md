 **STOCK DATA**

 This folder contains 4 files. Here is what they look like :
 
 (1) allstocks.py
 
    allstocks = {'FR0000062507': 'Fin.Etang Berre Pf', 'FR0013240322': 'EDF DS', 'FR0004038263': 'Parrot', 'FR0010211615': 'Quotium Techno'}
    ***
    -Key is ISIN
    -Value is quote name
    
 (2) amf.db
 
 sqlite database, see AMF crawler for headers
 
 (3) amf.csv
 
 csv file that can be downloaded at https://lestransactions.fr/data/data.csv
 
  (4) trade.json
  
      {"FR0011858190": 28.8, "FR0000053142": 105.95, "FR0000052292": 517.6}
      **
      -Key is ISIN
      -Value is last trading price (from euronext)
