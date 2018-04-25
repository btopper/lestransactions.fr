import subprocess
import re
import urllib.request
import csv
import time
import datetime
from urllib.request import urlopen
import requests
import sqlite3
import smtplib
import json
from data.subscriptions import subscriptions
from local.env import MAIL_PASSWD, BASE_DIR, SMTP_ADDRESS


class AMFdata(object):

    def run():
        if len(str(datetime.datetime.today().day)) == 1:
            day = ''.join(('0', str(datetime.datetime.today().day)))
        else:
            day = str(datetime.datetime.today().day)
        if len(str(datetime.datetime.today().month)) == 1:
            month = ''.join(('0', str(datetime.datetime.today().month)))
        else:
            month = str(datetime.datetime.today().month)
        year = str(datetime.datetime.today().year)
        date = [day, month, year]
        print(day, month, year)
        for page in range(1, 11):  # loop on pages
            page_number = str(page)
            amf_search = "http://www.amf-france.org/Resultat-de-recherche-BDIF.html?PAGE_NUMBER=" + page_number + "&formId=BDIF&LANGUAGE=fr&BDIF_NOM_PERSONNE=&valid_form=Lancer+la+recherche&DATE_OBSOLESCENCE=" + date[0] + "%2F" + date[1] + "%2F" + date[
                2] + "&BDIF_TYPE_INFORMATION=BDIF_TYPE_INFORMATION_DECLARATION_DIRIGEANT&bdifJetonSociete=&subFormId=dd&DOC_TYPE=BDIF&BDIF_RAISON_SOCIALE=&isSearch=true&REFERENCE=&DATE_PUBLICATION=" + date[0] + "%2F" + date[1] + "%2F" + date[2]
            f = requests.get(amf_search)  # connect to amf website
            if f.status_code == 404:
                break  # if page doesnt exist, go to next loop
            amf_search_result = f.text
            theseregexp = "(/technique/proxy-lien?)(.+?)(class=)"  # pattern for search result page
            pattern = re.compile(theseregexp)
            content = re.findall(pattern, amf_search_result)  # get a list of all the results on result page
            for cont in content:  # navigate in each result
                doc_search = "http://www.amf-france.org" + cont[0] + cont[1]
                f = urllib.request.urlopen(doc_search)
                doc_file = f.read().decode('utf-8')
                # ge the pattern for file link
                theseregexp = "(/technique/multimedia?)(.+?)(>Consulter le document)"
                pattern = re.compile(theseregexp)
                doc_content = re.findall(pattern, doc_file)
                for doc_cont in doc_content:
                    try:
                        # get the file and convert it to html
                        pdf_address = "http://www.amf-france.org" + doc_cont[0] + doc_cont[1]
                        final_pdf = urllib.request.urlretrieve(
                            pdf_address[:-1], BASE_DIR+'test.pdf')  # download file
                        # convert file to html
                        bash_command = ''.join(("pdftohtml ", BASE_DIR+'test.pdf'))
                        subprocess.call(bash_command, shell=True, stdout=subprocess.PIPE)
                        subprocess.call('rm '+BASE_DIR+'test.html', shell=True)
                        subprocess.call('rm '+BASE_DIR+'test.pdf', shell=True)
                        subprocess.call('rm '+BASE_DIR+'test_ind.html', shell=True)
                        # prepare all regexp
                        isinregex = "[A-Z][A-Z][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]"  # ISIN
                        isinpattern = re.compile(isinregex)
                        nameregex = "NOM :"  # company name
                        namepattern = re.compile(nameregex)
                        theseregexp = "</b>(.+?)<br/>"  # global match regexp
                        pattern = re.compile(theseregexp)
                        transac_page = []
                        datalist = [{"Nature": "NATURE DE LA TRANSACTION"},
                                    {"Prix": "PRIX :"},
                                    {"Prix unitaire": "PRIX UNITAIRE :"},
                                    {"Volume": "VOLUME :"},
                                    {'Date': 'DATE DE LA TRANSACTION'},
                                    {"Instrument": "INSTRUMENT FINANCIER :"}]

                        # open html file and get a first read to analyze the number or transactions in file
                        with open(BASE_DIR+"tests.html", 'r') as file:
                            i = 0
                            k = 0
                            for line in file:
                                content = re.findall("DETAIL DE LA TRANSACTION", line)
                                if content:
                                    try:
                                        transac_page.append(i)
                                    except KeyError:
                                        transac_page = [i]
                                isin = re.findall(isinpattern, line)
                                if isin:
                                    isin_name = re.findall(isinpattern, line)  # match ISIN
                                name = re.findall(namepattern, line)
                                if name:
                                    company_name = re.findall(pattern, line)  # match company name
                                if k == 1:
                                    manager_name = re.findall(re.compile('(.+?)<br/>'), line)  # match manager name
                                    k = 0
                                manager = re.findall(
                                    "<b>NOM /FONCTION DE LA PERSONNE EXERCANT DES RESPONSABILITES DIRIGEANTES OU DE LA<br/>PERSONNE ETROITEMENT LIEE :</b><br/>", line)
                                if manager:
                                    k += 1
                                i += 1
                            if len(transac_page) == 0:
                                transac_page.append(0)
                            transac_page.append(i)  # get a list of all the lines

                        # parse file to match all the global regexp list
                        for transac_line in range(len(transac_page) - 1):
                            op = {}
                            op['pdf'] = [pdf_address[:-1]]
                            for data in datalist:
                                for key, value in data.items():
                                    with open(BASE_DIR+"tests.html", 'r') as file:
                                        i = 0
                                        for line in file:
                                            if i >= transac_page[transac_line] and i <= transac_page[transac_line + 1]:
                                                content = re.findall(value, line)
                                                if content:
                                                    try:
                                                        op[key].append(re.findall(pattern, line)[0])
                                                    except KeyError:
                                                        op[key] = re.findall(pattern, line)
                                            else:
                                                pass
                                            i += 1
                            op['Société'] = company_name
                            op['ISIN'] = isin_name
                            op['Déclarant'] = manager_name

                            # treat al the specific cases
                            try:
                                if float(op["Prix"][0][:-5].replace(' ', '')) == 0:
                                    op["Prix"] = [float(op["Prix unitaire"][0][:-5].replace(' ', ''))]
                                elif float(op["Prix"][0][:-5].replace(' ', '')) > 2 * float(op["Prix unitaire"][0][:-5].replace(' ', '')):
                                    op["Total"] = [float(op["Prix"][0][:-5].replace(' ', ''))]
                                else:
                                    op["Prix"] = [float(op["Prix"][0][:-5].replace(' ', ''))]
                                op['Monnaie'] = ['Euros']
                            except ValueError:  # dollar des etat-unis
                                if float(op["Prix"][0][:-22].replace(' ', '')) == 0:
                                    op["Prix"] = [float(op["Prix unitaire"][0][:-22].replace(' ', ''))]
                                else:
                                    op["Prix"] = [float(op["Prix"][0][:-22].replace(' ', ''))]
                                op['Monnaie'] = ['Dollars']
                            op["Volume"] = [max([float(op["Volume"][i].replace(' ', ''))
                                                 for i in range(len(op["Volume"]))])]
                            try:
                                op["Total"]
                                op["Prix"] = [op["Total"][0] / op["Volume"][0]]
                            except KeyError:
                                op["Total"] = [op["Volume"][0] * op["Prix"][0]]
                            del op["Prix unitaire"]
                            for key, value in op.items():
                                op[key] = value[0]

                            # convert transaction date to YYYY-MM-DD format for the db to be able to sort it
                            month = {'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04', 'mai': '05', 'juin': '06',
                                     'juillet': '07', 'août': '08', 'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'}
                            op['Date'] = '-'.join((op['Date'][-4:], month[op['Date'][3:-5]], op['Date'][:2]))

                            # eurnoext quote and capitalisation

                            euronext = 'https://www.euronext.com/fr/nyx_eu_listings/real-time/quote?isin=' + \
                                op['ISIN'] + '&mic=XPAR'
                            f = requests.get(euronext)  # connect to amf website
                            file = f.text

                            capitalisation = '(<td  id="marketCapvalue" >)(.+?)(</td>)'
                            capi = re.compile(capitalisation)
                            capifind = re.findall(capi, file)
                            op['Part du capital'] = 100 * float(op["Total"]) / int(capifind[0]
                                                                                   [1].replace('&euro;', '').replace('M', '000000'))
                            if op['Part du capital'] < 0.01:
                                op['Part du capital'] = 0

                            # connect to the db and save the data
                            conn = sqlite3.connect(BASE_DIR+'stock_data/amf.db')
                            c = conn.cursor()
                            c.execute("INSERT INTO stocks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [
                                      op["ISIN"], op["Société"], op["Déclarant"], op["Date"], op["Nature"], op["Instrument"], op["Prix"], int(op["Volume"]), int(op["Total"]), op['Part du capital'], op['Monnaie'], op["pdf"]])
                            conn.commit()

                            for user in subscriptions.keys():
                                for isin, capi_isin in subscriptions[user].items():
                                    if isin != 'global' and isin != '0' and isin != 'Vide':
                                        if op['ISIN'] == isin.replace(' ', '') and op['Part du capital'] >= float(capi_isin):
                                            Mail.send_mail(op, user)
                                            print('mail envoyé :', op['ISIN'], user)
                                try:
                                    subscriptions[user]['global']
                                except KeyError:
                                    subscriptions[user]['global'] = 0
                                capi = float(subscriptions[user]['global'])
                                if capi == 0:
                                    continue
                                elif float(op['Part du capital']) > capi and float(op['Part du capital']) < 100:
                                    Mail.send_mail(op, user)
                                    print('mail envoyé :', op['ISIN'], user)
                    except:
                        print('error')
                        pass


class CsvWriter(object):

    def run():
        print('writing csv')
        conn = sqlite3.connect(BASE_DIR+'stock_data/amf.db')
        c = conn.cursor()
        data = c.execute('''SELECT * FROM stocks''')
        csvWriter = csv.writer(open(BASE_DIR+"stock_data/data.csv", "w"), delimiter=';')
        csvWriter.writerow(['Téléchargé sur lestransactions.fr sous Licence CC-BY-NC-SA'])
        csvWriter.writerow(["ISIN", "Société", "Déclarant", "Date", "Nature", "Instrument",
                            "Prix", "Volume", "Total", "Total en part de la capitalisation (x%)", 'Monnaie', "pdf"])
        for row in data:
            csvWriter.writerow(row)
        print('done')


class Tradingdata(object):

    def run():
        print('getting trading data')
        conn = sqlite3.connect(BASE_DIR+'stock_data/amf.db')
        c = conn.cursor()
        data = c.execute('''SELECT DISTINCT isin FROM stocks''')
        tradedict = {}
        for da in data:
            try:
                euronext = 'https://www.euronext.com/fr/nyx_eu_listings/real-time/quote?isin=' + da[0] + '&mic=XPAR'
                f = requests.get(euronext)  # connect to euronext website
                file = f.text
                cours = '(<td>&euro;)(.+?)(&nbsp;)(.+?)(</td>)'
                cours2 = re.compile(cours)
                coursfind = re.findall(cours2, file)
                tradedict[da[0]] = float(coursfind[0][1].replace(',', '.'))
                print(da[0])
            except:
                try:
                    time.sleep(5)
                    euronext = 'https://www.euronext.com/fr/nyx_eu_listings/real-time/quote?isin=' + \
                        da[0] + '&mic=XPAR'
                    f = requests.get(euronext)  # connect to euronext website
                    file = f.text
                    cours = '(<td>&euro;)(.+?)(&nbsp;)(.+?)(</td>)'
                    cours2 = re.compile(cours)
                    coursfind = re.findall(cours2, file)
                    tradedict[da[0]] = float(coursfind[0][1].replace(',', '.'))
                    print(da[0])
                except:
                    print('error :', da[0])
                    pass
            time.sleep(2)
        with open(BASE_DIR+'stock_data/trade.json', 'w+') as trade:
            json.dump(tradedict, trade)
        print('done')


class Mail(object):

    def send_mail(op, email):
        mailserver = smtplib.SMTP(SMTP_ADDRESS)
        mailserver.ehlo()
        mailserver.starttls()
        mailserver.login("lestransactions@alwaysdata.net", MAIL_PASSWD)
        msg = "\r\n".join([
            "Subject: [LesTransactions.fr] Alerte email " + str(op['Société']),
            "Bonjour,",
            " ",
            "Vous recevez cet e-mail en raison de la transaction suivante : ",
            " ",
            "ISIN : " + str(op['ISIN']),
            "Societe : " + str(op["Société"]),
            "Declarant : " + str(op["Déclarant"]),
            "Date de transaction : " + str(op["Date"]),
            "Nature : " + str(op["Nature"]),
            "Instrument : " + str(op["Instrument"]),
            "Prix : " + str(op["Prix"]),
            "Volume : " + str(int(op["Volume"])),
            "Montant total : " + str(int(op["Total"])),
            "Total en part de la capitalisation (x%) : " + str(op['Part du capital']),
            "Monnaie : " + str(op['Monnaie']),
            "Lien : " + str(op["pdf"]),
            " ",
            "Pour vous désabonner, rendez-vous dans votre espace personnel : https://lestransactions.fr/login"
        ])
        mailserver.sendmail("robot@lestransactions.fr", email, msg.encode('utf-8'))
        return True


AMFdata.run()  # launch AMF crawler and save in DB
Tradingdata.run()  # Get trading data from euronext
CsvWriter.run()  # export to csv
