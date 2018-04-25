#!/usr/bin/eval PYTHONPATH=/home/example/modules python

from flask import Flask, render_template, Response, request, redirect, url_for, send_from_directory
import os
import sqlite3
import csv
import smtplib
import json
import requests
from flipflop import WSGIServer
import hashlib
from base64 import b64encode
import flask_login
from user_data.subscriptions import subscriptions
from user_data.users import users
from stock_data.allstocks import allstocks
import sqlite3
from flask_cors import CORS
from local.env import API_KEY, MAIL_PASSWD, SMTP_ADDRESS

app = Flask(__name__) 
app.secret_key = b64encode(os.urandom(64)).decode('utf-8') 
cors = CORS(app, resources={r"/api": {"origins": "*"}})

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

class ScriptNameStripper(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        environ['SCRIPT_NAME'] = ''
        return self.app(environ, start_response)

app.wsgi_app = ScriptNameStripper(app.wsgi_app)

'''HOME PAGE'''

@app.route('/')  # root page : get index.html template
def server():
    c = sqlite3.connect('stock_data/amf.db')
    cur = c.cursor()
    cur.execute("SELECT * from stocks ORDER BY date_transac DESC")
    amf = cur.fetchall()  # get db data
    file = open('stock_data/trade.json')
    json_file = file.read()
    hashsum = hashlib.sha256(open('stock_data/data.csv', 'rb').read()).hexdigest()
    datasize = round(float(os.path.getsize('stock_data/data.csv'))/float(10**6),3)
    trade_data = json.loads(json_file)
    return render_template('index.html', data=amf, trade=trade_data, hashsum=hashsum, datasize=datasize)  # pass db data to html template

''' DATABASE PAGE '''

@app.route('/bdd')  # bdd page : consult database on separate page
def bdd():
    c = sqlite3.connect('stock_data/amf.db')
    cur = c.cursor()
    cur.execute("SELECT * from stocks ORDER BY date_transac DESC")
    amf = cur.fetchall()  # get db data
    file = open('stock_data/trade.json')
    json_file = file.read()
    hashsum = hashlib.sha256(open('stock_data/data.csv', 'rb').read()).hexdigest()
    datasize = round(float(os.path.getsize('stock_data/data.csv'))/float(10**6),3)
    trade_data = json.loads(json_file)
    return render_template('bdd.html', data=amf, trade=trade_data, hashsum=hashsum, datasize=datasize)  # pass db data to html template

''' DATABASE CSV '''

@app.route('/data/data.csv')  # csv download link
def data():
    with open("stock_data/data.csv") as file:
        csv = file.read()
    return Response(csv, mimetype="text/csv", headers={"Content-disposition": "attachment; filename=stock_data/data.csv"})


''' SIGNUP PAGE '''

@app.route('/signup', methods=['POST'])
def signup():
    email = request.form['email']
    pwd = b64encode(os.urandom(8)).decode('utf-8')
    try:
        users[email]
        pwd=users[email]['pwd']
    except KeyError:
        users.update({email:{'pwd':pwd}})
    try:
        subscriptions[email]
    except KeyError:
        capi='0'
        subscriptions[email] = {'global':capi}
    with open("user_data/users.py", 'w') as myfile:
        content="users = {}".format(users)
        myfile.write(content)
    with open("user_data/subscriptions.py", 'w') as myfile:
        content="subscriptions = {}".format(subscriptions)
        myfile.write(content)
    mailserver = smtplib.SMTP(SMTP_ADDRESS)
    mailserver.ehlo()
    mailserver.starttls()
    mailserver.login("lestransactions@alwaysdata.net", MAIL_PASSWD)
    msg = "\r\n".join([
        "Subject: [LesTransactions.fr] Inscription pour des alertes e-mail",
        "Bonjour,",
        "",
        "Retrouvez et gérez vos alertes depuis votre espace perso sur https://lestransactions.fr/login",
        "",
        "Identifiant : " + str(email),
        "Mot de passe : " + str(pwd) ,
        "",
        "NB : Il n'est pour l'instant pas possible de changer son mot de passe.",
        "",
    ])
    mailserver.sendmail("robot@lestransactions.fr", email, msg.encode('utf-8'))
    return redirect(url_for('login'))

class User(flask_login.UserMixin):
    pass

@login_manager.user_loader
def user_loader(email):
    if email not in users:
        return

    user = User()
    user.id = email
    return user

@login_manager.request_loader
def request_loader(request):
    email = request.form.get('email')
    if email not in users:
        return

    user = User()
    user.id = email

    # DO NOT ever store passwords in plaintext and always compare password
    # hashes using constant-time comparison!
    user.is_authenticated = request.form['pwd'] == users[email]['pwd']

    return user

''' LOGIN PAGE '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return '''
               <center>
               <title>Connexion - LesTransactions.fr</title>
               <h3>Votre espace personnel LesTransactions.fr</h3>
               <form action='login' method='POST'>
                <input type='text' name='email' id='email' placeholder='E-mail'></input>
                <input type='password' name='pwd' id='pwd' placeholder='Mot de passe'></input>
                <input type='submit' name='submit' value='Me connecter'></input>
               </form>
               NB : Il n'est pour l'instant pas possible de changer son mot de passe.<br><br>
               Retour à <a href="https://lestransactions.fr">l\'accueil</a> ou découvrir la nouvelle <a href="api">API</a><br><br>
               <hr><form action="/signup" method="POST" style="font-size:90%">
               Mot de passe oublié ? <input type="email" id="email" name="email" placeholder="E-mail" required/><button type="submit">Recevoir mon mot de passe par mail</button></form><br>
               </center>
               '''

    email = request.form['email']
    try:
        if request.form['pwd'] == users[email]['pwd']:
            user = User()
            user.id = email
            flask_login.login_user(user)
            return redirect(url_for('maselection'))
    except KeyError:
        return 'Mauvais login ou mot de passe.<br>Merci de vous <a href="https://lestransactions.fr/login"> reconnecter</a> ou <a href="https://lestransactions.fr">revenez à l\'accueil</a>' 
    return 'Mauvais login ou mot de passe.<br> Merci de vous <a href="https://lestransactions.fr/login"> reconnecter</a> ou <a href="https://lestransactions.fr">revenez à l\'accueil</a>'

''' USER STOCK SELECTION PAGE '''

@app.route('/maselection', methods=['GET', 'POST'])
@flask_login.login_required
def maselection():
    if request.method=='POST':
        user = request.form['user']
        try:
            capi=request.form['global']
            if capi!='':
                try:
                    subscriptions[user].update({'global':capi})
                except KeyError:
                    return 'Erreur dans l\'actualisation de vos alertes, merci de contacter l\'administrateur du site. Retour à <a href="https://lestransactions.fr">l\'accueil</a>.'
        except KeyError:
            pass
        try:
            for key,value in request.form.items():
                if key!='user' and key!='isin' and key[0:6]!='delete' and key!='new_isin' and key!='capi_isin' and key!='add' and value!='':
                    subscriptions[user].update({key:value})
        except (KeyError, IndexError):
            pass
        try:
            for key,value in request.form.items():
                if key[0:6]=='delete':
                    del subscriptions[user][value]
        except (KeyError, IndexError):
            pass
        try:
            subscriptions[user][request.form['new_isin'].replace(' ','')]=request.form['capi_isin']
        except KeyError:
            pass
        with open("user_data/subscriptions.py", 'w') as myfile:
            content="subscriptions = {}".format(subscriptions)
            myfile.write(content)
        return render_template('maselection.html', subscription = subscriptions[flask_login.current_user.id], user=flask_login.current_user.id, stocks=allstocks)
    try:
        return render_template('maselection.html', subscription = subscriptions[flask_login.current_user.id], user=flask_login.current_user.id, stocks=allstocks)
    except KeyError:
        return 'Bonjour ' + flask_login.current_user.id + '<br>' + 'Pas d\'abonnement connu. <br> Merci de vous <a href="https://lestransactions.fr/login"> reconnecter</a> ou <a href="https://lestransactions.fr">revenez à l\'accueil</a>'

''' LOGOUT PAGE '''

@app.route('/logout')
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return 'Déconnecté, retourner à <a href="https://lestransactions.fr">l\'accueil</a>'


''' DELETE ACCOUNT PAGE '''

@app.route('/delete_my_account', methods=['GET', 'POST'])
@flask_login.login_required
def delete_my_account():
     user = request.form['user']
     del subscriptions[user]
     del users[user]
     with open("user_data/subscriptions.py", 'w') as myfile:
        content="subscriptions = {}".format(subscriptions)
        myfile.write(content)     
     with open("user_data/users.py", 'w') as myfile:
        content="users = {}".format(users)
        myfile.write(content)
     flask_login.logout_user()
     return 'Toutes vos informations ont été supprimées. Vous êtes déconnecté, retourner à <a href="https://lestransactions.fr">l\'accueil</a>'

@login_manager.unauthorized_handler
def unauthorized_handler():
    return 'Merci de vous <a href="https://lestransactions.fr/login">reconnecter</a> ou <a href="https://lestransactions.fr">revenez à l\'accueil</a>'

@app.route('/verify')
def verify():
    params = {'apikey': API_KEY, 'url':'https://lestransactions.fr/data/data.csv'}
    response = requests.post('https://www.virustotal.com/vtapi/v2/url/scan', data=params)
    json_response=response.json()
    return redirect(json_response['permalink'])

@app.route('/api', methods=['GET','POST'])
def api():
    if request.method=='POST':
        try:
            result_dict={}
            userdata=request.form['isin']
            conn = sqlite3.connect('stock_data/amf.db')
            c = conn.cursor()
            resultdata=c.execute('''SELECT * FROM stocks where isin = ? ORDER BY date_transac ASC''', [userdata])
            for i,da in enumerate(resultdata):
                result_dict[i]={'isin':da[0], 'company':da[1], 'manager':da[2], 'date_transac':da[3], 'nature':da[4], 'instrument':da[5], 'price':da[6], 'qty':da[7], 'total':da[8], 'capital_share':da[9], 'currency':da[10], 'ref':da[11]}
            return json.dumps(result_dict, ensure_ascii=False)
        except KeyError:
            result_dict={}
            userdata=request.form['date']
            conn = sqlite3.connect('stock_data/amf.db')
            c = conn.cursor()
            resultdata=c.execute('''SELECT * FROM stocks where date_transac = ? ''', [userdata])
            for i,da in enumerate(resultdata):
                result_dict[i]={'isin':da[0], 'company':da[1], 'manager':da[2], 'date_transac':da[3], 'nature':da[4], 'instrument':da[5], 'price':da[6], 'qty':da[7], 'total':da[8], 'capital_share':da[9], 'currency':da[10], 'ref':da[11]}
            return json.dumps(result_dict, ensure_ascii=False)
        except:
            return json.dumps({'ERROR':'bad request'})
    return render_template('api.html')

''' MISC '''

@app.route('/robots.txt')
@app.route('/sitemap.xml')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])

if __name__ == '__main__':
    app.debug = False
    WSGIServer(app).run()
