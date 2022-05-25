from requests_oauthlib import OAuth2Session
from flask import Flask, request, redirect, session, url_for, render_template
from requests.auth import HTTPBasicAuth
from datetime import datetime
from flask_mail import Mail, Message
import requests
import json
import uuid
import plotly
import plotly.graph_objects as go

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'memcached'
app.config['SECRET_KEY'] = 'Insert Secret Key'

client_id = "Insert Client ID"
client_secret = "Insert Secret Key"

authorization_base_url = 'https://apm.tp.sandbox.fidorfzco.com/oauth/authorize'
token_url = 'https://apm.tp.sandbox.fidorfzco.com/oauth/token'
redirect_uri = 'http://localhost:5000/callback'

mail= Mail(app)

app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'Insert Email Address'
app.config['MAIL_PASSWORD'] = 'Insert Email Password'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)

@app.route('/', methods=["GET"])
@app.route('/index', methods=["GET"])
def default():

    try:
        fidor = OAuth2Session(client_id,redirect_uri=redirect_uri)
        authorization_url, state = fidor.authorization_url(authorization_base_url)
        print("State is " + state)
        session['oauth_state'] = state
        print("Authorization URL is = " + authorization_url)
        return redirect(authorization_url)
    except KeyError:
        print("Error: Returning to index...")
        return redirect(url_for('default'))

@app.route('/callback', methods=["GET"])
def callback():

    try:
        fidor = OAuth2Session(state=session['oauth_state'])
        authorizationCode = request.args.get('code')
        body = 'grant_type="authorization_code&code=' + authorizationCode + \
        '&redirect_uri=' + redirect_uri + '&client_id=' + client_id
        auth = HTTPBasicAuth(client_id, client_secret)
        token = fidor.fetch_token(token_url, auth=auth, code=authorizationCode, body=body, method='POST')

        session['oauth_token'] = token
        return redirect(url_for('.services'))
    except KeyError:
        print("Error: Returning to index...")
        return redirect(url_for('default'))

@app.route('/menu', methods=["GET"])
def services():

    try:
        token = session['oauth_token']
        url = "https://api.tp.sandbox.fidorfzco.com/accounts"
        payload = "https://api.tp.sandbox.fidorfzco.com/accounts"
        headers = {
            'Accept': 'application/vnd.fidor.de;version=1;text/json',
            'Authorization': "Bearer " + token["access_token"]
        }
        response = requests.request("GET", url, data=payload, headers=headers)
        customersAccount = json.loads(response.text)
        customerDetails = customersAccount['data'][0]
        customerInformation = customerDetails['customers'][0]
        session['fidor_customer'] = customersAccount
        session['customer_first_name'] = customerInformation['first_name']
        session['customer_last_name'] = customerInformation['last_name']

        return render_template('Menu.html', fID = customerInformation["id"],
        fFirstName = customerInformation["first_name"], fLastName = customerInformation['last_name'],
        fAccountNo = customerDetails['account_number'], fBalance = "{:,.2f}".format(customerDetails['balance']/100)) 
    except KeyError:
        print("Error: Returning to index...")
        return redirect(url_for('default'))

@app.route('/quick_transfer', methods=["GET"])
def transfer():

    try:
        fFirstName = session['customer_first_name']
        fLastName = session['customer_last_name']
    
        return render_template('QuickTransferPage.html', fFirstName = fFirstName, fLastName = fLastName) 
    except KeyError:
        print("Error: Returning to index...")
        return redirect(url_for('default'))

@app.route('/transferMoney', methods=["POST"])
def process():

    if request.method == "POST":
        token = session['oauth_token']
        customersAccount = session['fidor_customer']
        customerDetails = customersAccount['data'][0]

        fidorID = customerDetails['id']
        custEmail = request.form['customerEmailAddress']
        transferAmt = int(float(request.form['transferAmount'])*100)
        transferRemarks = request.form['transferRemarks']
        transactionID = str(uuid.uuid4())

        url = "https://api.tp.sandbox.fidorfzco.com/internal_transfers"

        payload = "{\n\t\"account_id\": \"" + fidorID + "\", \n\t\"receiver\": \"" + \
            custEmail + "\", \n\t\"external_uid\": \"" + transactionID + "\", \n\t\"amount\": " + \
            str(transferAmt) + ", \n\t\"subject\": \"" + transferRemarks + "\"\n}\n"

        headers = {
            'Accept': 'application/vnd.fidor.de; version=1,text/json',
            'Authorization': "Bearer " + token["access_token"],
            'Content-Type': "application/json"
        }

        response = requests.request("POST", url, data=payload, headers=headers)
        transactionDetails = json.loads(response.text)
        fFirstName = session['customer_first_name']
        fLastName = session['customer_last_name']
        return render_template('QuickTransferResultPage.html', fFirstName = fFirstName, fLastName = fLastName, fTransactionID = transactionDetails["id"],
        custEmail = transactionDetails["receiver"], fRemarks = transactionDetails["subject"],
        fAmount = "{:,.2f}".format((float(transactionDetails["amount"])/100)), fRecipientName = transactionDetails["recipient_name"], fTimestamp = transactionDetails['created_at'])

@app.route('/pm_landing', methods=["GET"])
def metalPrices():

    urlG = "https://www.goldapi.io/api/XAU/SGD?"

    payloadG = ""
    headersG = {
        "x-access-token": "Insert Token"
    }

    responseG = requests.request("GET", urlG, headers=headersG, data=payloadG)
    goldData = json.loads(responseG.text)
    goldPrice = goldData["price"]
    session['gold_price'] = goldPrice

    urlS = "https://www.goldapi.io/api/XAG/SGD?"

    payloadS = ""
    headersS = {
        "x-access-token": "Insert Token"
    }

    responseS = requests.request("GET", urlS, headers=headersS, data=payloadS)
    silverData = json.loads(responseS.text)
    silverPrice = silverData["price"]
    session['silver_price'] = silverPrice

    urlP = "https://www.goldapi.io/api/XPT/SGD?"

    payloadP = ""
    headersP = {
        "x-access-token": "Insert Token"
    }

    responseP = requests.request("GET", urlP, headers=headersP, data=payloadP)
    platinumData = json.loads(responseP.text)
    platinumPrice = platinumData["price"]
    lastUpdated = datetime.fromtimestamp(platinumData['timestamp'])
    session['platinum_price'] = platinumPrice

    fFirstName = session['customer_first_name']
    fLastName = session['customer_last_name']

    urlG = "https://www.metals-api.com/api/timeseries"

    payloadG={}
    headersG = {}

    querystringG = {
        "base": "SGD", "symbols": "XAU", "start_date": "2022-02-19", "end_date": "2022-02-23", "access_key": "Insert Access Key" 
    }

    responseG = requests.request("GET", urlG, params=querystringG, headers=headersG, data=payloadG)
    goldHistoricalData = json.loads(responseG.text)
    goldHistoricalPrices = goldHistoricalData["rates"]
    goldPrice1 = float(goldHistoricalPrices["2022-02-19"]["XAU"])
    goldPrice2 = float(goldHistoricalPrices["2022-02-20"]["XAU"])
    goldPrice3 = float(goldHistoricalPrices["2022-02-21"]["XAU"])
    goldPrice4 = float(goldHistoricalPrices["2022-02-22"]["XAU"])
    goldPrice5 = float(goldHistoricalPrices["2022-02-23"]["XAU"])

    xG = ["19 Feb 2022", "20 Feb 2022", "21 Feb 2022", "22 Feb 2022", "23 Feb 2022"]
    yG = [goldPrice1, goldPrice2, goldPrice3, goldPrice4, goldPrice5]

    figG = go.Figure()
    figG.add_trace(go.Scatter(x=xG, y=yG, name="Gold Price", line=dict(color='#09143c', width=2)))
    figG.update_yaxes(tickprefix="$")
    figG.update_yaxes(range=[2200, 2800])
    figG.update_layout(xaxis_title='Date', yaxis_title='Spot Price of Gold (Per Ounce) in SGD')
    goldHistoricalDataGraph = json.dumps(figG, cls=plotly.utils.PlotlyJSONEncoder)

    urlS = "https://www.metals-api.com/api/timeseries"

    payloadS={}
    headersS = {}

    querystringS = {
        "base": "SGD", "symbols": "XAG", "start_date": "2022-02-19", "end_date": "2022-02-23", "access_key": "Insert Access Key" 
    }

    responseS = requests.request("GET", urlS, params=querystringS, headers=headersS, data=payloadS)
    silverHistoricalData = json.loads(responseS.text)
    silverHistoricalPrices = silverHistoricalData["rates"]
    silverPrice1 = float(silverHistoricalPrices["2022-02-19"]["XAG"])
    silverPrice2 = float(silverHistoricalPrices["2022-02-20"]["XAG"])
    silverPrice3 = float(silverHistoricalPrices["2022-02-21"]["XAG"])
    silverPrice4 = float(silverHistoricalPrices["2022-02-22"]["XAG"])
    silverPrice5 = float(silverHistoricalPrices["2022-02-23"]["XAG"])

    xS = ["19 Feb 2022", "20 Feb 2022", "21 Feb 2022", "22 Feb 2022", "23 Feb 2022"]
    yS = [silverPrice1, silverPrice2, silverPrice3, silverPrice4, silverPrice5]

    figS = go.Figure()
    figS.add_trace(go.Scatter(x=xS, y=yS, name="Silver Price", line=dict(color='#09143c', width=2)))
    figS.update_yaxes(tickprefix="$")
    figS.update_yaxes(range=[0, 60])
    figS.update_layout(xaxis_title='Date', yaxis_title='Spot Price of Silver (Per Ounce) in SGD')
    silverHistoricalDataGraph = json.dumps(figS, cls=plotly.utils.PlotlyJSONEncoder)

    urlP = "https://www.metals-api.com/api/timeseries"

    payloadP={}
    headersP = {}

    querystringP = {
        "base": "SGD", "symbols": "XPT", "start_date": "2022-02-19", "end_date": "2022-02-23", "access_key": "Insert Access Key" 
    }

    responseP = requests.request("GET", urlP, params=querystringP, headers=headersP, data=payloadP)
    platinumHistoricalData = json.loads(responseP.text)
    platinumHistoricalPrices = platinumHistoricalData["rates"]
    platinumPrice1 = float(platinumHistoricalPrices["2022-02-19"]["XPT"])
    platinumPrice2 = float(platinumHistoricalPrices["2022-02-20"]["XPT"])
    platinumPrice3 = float(platinumHistoricalPrices["2022-02-21"]["XPT"])
    platinumPrice4 = float(platinumHistoricalPrices["2022-02-22"]["XPT"])
    platinumPrice5 = float(platinumHistoricalPrices["2022-02-23"]["XPT"])

    xP = ["19 Feb 2022", "20 Feb 2022", "21 Feb 2022", "22 Feb 2022", "23 Feb 2022"]
    yP = [platinumPrice1, platinumPrice2, platinumPrice3, platinumPrice4, platinumPrice5]

    figP = go.Figure()
    figP.add_trace(go.Scatter(x=xP, y=yP, name="Platinum Price", line=dict(color='#09143c', width=2)))
    figP.update_yaxes(tickprefix="$")
    figP.update_yaxes(range=[1100, 1700])
    figP.update_layout(xaxis_title='Date', yaxis_title='Spot Price of Platinum (Per Ounce) in SGD')
    platinumHistoricalDataGraph = json.dumps(figP, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('PMLandingPage.html', fFirstName = fFirstName, fLastName = fLastName,goldPrice = "{:,.2f}".format(goldPrice),
    silverPrice = "{:,.2f}".format(silverPrice), platinumPrice = "{:,.2f}".format(platinumPrice),
    lastUpdated = lastUpdated, goldHistoricalDataGraph = goldHistoricalDataGraph, silverHistoricalDataGraph = silverHistoricalDataGraph, platinumHistoricalDataGraph = platinumHistoricalDataGraph)

@app.route("/pm_news", methods=["GET"])
def getNews():
    
    url = "https://newsapi.org/v2/everything"

    payload = ""
    headers = {}

    querystring = {
        "q": "Precious Metals", "apiKey": "Insert API Key" 
    }

    response = requests.request("GET", url, params=querystring, headers=headers, data=payload)
    data = json.loads(response.text)
    newsData = data['articles']
    fFirstName = session['customer_first_name']
    fLastName = session['customer_last_name']
    return render_template('PMNewsPage.html', fFirstName = fFirstName, fLastName = fLastName, latestNews = newsData)

@app.route('/pm_purchase', methods=["GET"])
def metalPrice():

    selectedMetal = str(session['metal_preference'])
    if selectedMetal == "XAU":
        goldPrice = session['gold_price']
        metal = "Gold"
        fFirstName = session['customer_first_name']
        fLastName = session['customer_last_name']
        return render_template('PMPurchasePage.html', fFirstName = fFirstName, fLastName = fLastName, selectedMetal = metal, selectedMetalPrice = (float(round(goldPrice, 2))))
    if selectedMetal == "XAG":
        silverPrice = session['silver_price']
        metal = "Silver"
        fFirstName = session['customer_first_name']
        fLastName = session['customer_last_name']
        return render_template('PMPurchasePage.html', fFirstName = fFirstName, fLastName = fLastName, selectedMetal = metal, selectedMetalPrice = (float(round(silverPrice, 2))))
    if selectedMetal == "XPT":
        platinumPrice = session['platinum_price']
        metal = "Platinum"
        fFirstName = session['customer_first_name']
        fLastName = session['customer_last_name']
        return render_template('PMPurchasePage.html', fFirstName = fFirstName, fLastName = fLastName, selectedMetal = metal, selectedMetalPrice = (float(round(platinumPrice, 2))))

@app.route('/buyGold', methods=["POST"])
def buyGold():
    session['metal_preference'] = "XAU"
    return redirect('/pm_purchase')

@app.route('/buySilver', methods=["POST"])
def buySilver():
    session['metal_preference'] = "XAG"
    return redirect('/pm_purchase')

@app.route('/buyPlatinum', methods=["POST"])
def buyPlatinum():
    session['metal_preference'] = "XPT"
    return redirect('/pm_purchase')

@app.route('/calculatePrice', methods=["POST"])
def calculatePrice():

    if request.method == "POST":
        selectedMetal = session['metal_preference']
        if selectedMetal == "XAU":
            metal = "Gold"
            selectedMetalPrice = float(session['gold_price'])
        if selectedMetal == "XAG":
            metal = "Silver"
            selectedMetalPrice = float(session['silver_price'])
        if selectedMetal == "XPT":
            metal = "Platinum"
            selectedMetalPrice = float(session['platinum_price'])

        purchasedWeight = float(request.form['purchasedWeight'])
        purchasePrice = purchasedWeight * selectedMetalPrice
        session['purchase_price'] = purchasePrice

        if purchasePrice > 500.00:
            return render_template('ErrorPage.html')
        else:
            fFirstName = session['customer_first_name']
            fLastName = session['customer_last_name']
            session['metal_purchased_weight'] = purchasedWeight
            return render_template('PMTransactionPage.html', fFirstName = fFirstName, fLastName = fLastName, selectedMetal = metal, selectedMetalPrice = "{:,.2f}".format(selectedMetalPrice), purchasedWeight = purchasedWeight, purchasePrice = "{:,.2f}".format(purchasePrice))

@app.route('/purchaseMetal', methods=["POST"])
def purchaseMetal():

    if request.method == "POST":
        token = session['oauth_token']
        customersAccount = session['fidor_customer']
        customerDetails = customersAccount['data'][0]
        purchasePrice = float(session['purchase_price'])

        fidorID = customerDetails['id']
        sellerEmail = "studentC20@email.com"
        purchaseAmt = int(purchasePrice*100)
        purchaseRemarks = "PRECIOUS METAL PURCHASE"
        purchaseID = str(uuid.uuid4())

        url = "https://api.tp.sandbox.fidorfzco.com/internal_transfers"

        payload = "{\n\t\"account_id\": \"" + fidorID + "\", \n\t\"receiver\": \"" + \
            sellerEmail + "\", \n\t\"external_uid\": \"" + purchaseID + "\", \n\t\"amount\": " + \
            str(purchaseAmt) + ", \n\t\"subject\": \"" + purchaseRemarks + "\"\n}\n"

        headers = {
            'Accept': 'application/vnd.fidor.de; version=1,text/json',
            'Authorization': "Bearer " + token["access_token"],
            'Content-Type': "application/json"
        }

        response = requests.request("POST", url, data=payload, headers=headers)
        transactionDetails = json.loads(response.text)
        fFirstName = session['customer_first_name']
        fLastName = session['customer_last_name']
        purchasedWeight = session['metal_purchased_weight']
        selectedMetal = session['metal_preference']
        if selectedMetal == "XAU":
            metal = "Gold"
            selectedMetalPrice = float(session['gold_price'])
        if selectedMetal == "XAG":
            metal = "Silver"
            selectedMetalPrice = float(session['silver_price'])
        if selectedMetal == "XPT":
            metal = "Platinum"
            selectedMetalPrice = float(session['platinum_price'])
        session['latest_transaction_id'] = transactionDetails['id']
        session['latest_transaction_timestamp'] = transactionDetails['created_at']
        session['latest_transaction_amount'] = transactionDetails['amount']
        return render_template('PMPurchaseResultPage.html', fTransactionID = transactionDetails["id"],
        fFirstName = fFirstName, fLastName = fLastName, selectedMetal = metal, selectedMetalPrice = "{:,.2f}".format(selectedMetalPrice),
        fAmount = "{:,.2f}".format((float(transactionDetails["amount"])/100)), purchasedWeight = float(purchasedWeight), fTimestamp = transactionDetails['created_at'])

@app.route('/transaction_history', methods=["GET"])
def transactions():

    try:
        token = session['oauth_token']
        url = "https://api.tp.sandbox.fidorfzco.com/transactions"
        payload = "https://api.tp.sandbox.fidorfzco.com/trasactions"
        headers = {
            'Accept': 'application/vnd.fidor.de;version=1;text/json',
            'Authorization': "Bearer " + token["access_token"]
        }
        response = requests.request("GET", url, data=payload, headers=headers)
        transactions = json.loads(response.text)
        transactionDetails = transactions['data']
        fFirstName = session['customer_first_name']
        fLastName = session['customer_last_name']
        return render_template('Transactions.html', fFirstName = fFirstName, fLastName = fLastName, transactions = transactionDetails) 
    except KeyError:
        print("Error: Returning to index...")
        return redirect(url_for('default'))

@app.route('/customer_profile', methods=["GET"])
def profile():

    try:
        token = session['oauth_token']
        url = "https://api.tp.sandbox.fidorfzco.com/accounts"
        payload = "https://api.tp.sandbox.fidorfzco.com/accounts"
        headers = {
            'Accept': 'application/vnd.fidor.de;version=1;text/json',
            'Authorization': "Bearer " + token["access_token"]
        }
        response = requests.request("GET", url, data=payload, headers=headers)
        customersData = json.loads(response.text)
        accountInformation = customersData['data'][0]
        customerInformation = accountInformation['customers'][0]
        fBalance = accountInformation['balance']
        fFirstName = session['customer_first_name']
        fLastName = session['customer_last_name']
        return render_template('Profile.html', fFirstName = fFirstName, fLastName = fLastName, fBalance = "{:,.2f}".format(fBalance/100), accountInformation = accountInformation, customerInformation = customerInformation) 
    except KeyError:
        print("Error: Returning to index...")
        return redirect(url_for('default'))

@app.route('/email_receipt', methods=["POST"])
def emailReceipt():

    fFirstName = session['customer_first_name']
    fLastName = session['customer_last_name']
    purchasedWeight = session['metal_purchased_weight']
    selectedMetal = session['metal_preference']
    if selectedMetal == "XAU":
        metal = "Gold"
        selectedMetalPrice = float(session['gold_price'])
    if selectedMetal == "XAG":
        metal = "Silver"
        selectedMetalPrice = float(session['silver_price'])
    if selectedMetal == "XPT":
        metal = "Platinum"
        selectedMetalPrice = float(session['platinum_price'])

    fTransactionID = session['latest_transaction_id']
    fTimestamp = session['latest_transaction_timestamp']
    fAmount = session['latest_transaction_amount']

    emailAddress = request.form['customerEmail']
    
    msg = Message('Fidor Bank - Precious Metals Purchase Email Receipt', sender = 'Insert Email Address', recipients = [emailAddress])
    msg.html = render_template('EmailTemplate.html', fTransactionID = fTransactionID, selectedMetal = metal, selectedMetalPrice = "{:,.2f}".format(selectedMetalPrice), fAmount = "{:,.2f}".format((float(fAmount)/100)), purchasedWeight = float(purchasedWeight), fTimestamp = fTimestamp)
    mail.send(msg)
    return render_template('EmailReceipt.html', fFirstName = fFirstName, fLastName = fLastName)