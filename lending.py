#!/usr/bin/python

import time, hmac, base64, hashlib, requests, os, configparser
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler

LENDING_RATE_TRIGGER = 0.28
BALANCE_TRIGGER = 0.0

config = configparser.ConfigParser()
config.read('config.ini')

def reqKucoin(endpoint):
    api_key = config['KUCOIN']['ApiKey']
    api_secret = config['KUCOIN']['Secret']
    api_passphrase = config['KUCOIN']['Passphrase']

    jsonResp = None
    url = 'https://api.kucoin.com' + endpoint
    now = int(time.time() * 1000)
    str_to_sign = str(now) + 'GET' + endpoint
    
    signature = base64.b64encode(
        hmac.new(api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest())
    passphrase = base64.b64encode(hmac.new(api_secret.encode('utf-8'), api_passphrase.encode('utf-8'), hashlib.sha256).digest())
    headers = {
        "KC-API-SIGN": signature,
        "KC-API-TIMESTAMP": str(now),
        "KC-API-KEY": api_key,
        "KC-API-PASSPHRASE": passphrase,
        "KC-API-KEY-VERSION": "2"
    }

    response = requests.request('get', url, headers=headers)
    jsonResp = response.json()
    return jsonResp["data"]


def sendTelegramNotifications(message):
    sendUrl = "https://api.telegram.org/bot" + config['KUCOIN']['TelegramToken'] + "/sendMessage"
    os.system('curl -s -X POST ' + sendUrl + ' -d chat_id=-' + config['KUCOIN']['ChatID'] + ' -d text="' + message + '"')

def notifyIfBalanceAvailable():
    uri = "/api/v1/accounts"
    data = reqKucoin(uri)
    balance = round(float(data[0]["available"]))

    if balance > BALANCE_TRIGGER:
        sendTelegramNotifications("Balance available with %f$" % balance)
        

def getLendingRates():
    terms = {"7" :[], "14":[], "28":[]}
    uri = "/api/v1/margin/market?currency=USDT&term="

    for t in terms.keys():
        jsonArray = reqKucoin(uri + t)
        terms[t] = jsonArray

    for t in terms.keys():
        dailyIntRate = float(terms[t][0]["dailyIntRate"])*100
        term = terms[t][0]["term"]
        size = terms[t][0]["size"]

        if dailyIntRate >= LENDING_RATE_TRIGGER:      
            sendTelegramNotifications("Interest Lending Rate [%sd] : %f" % (term, dailyIntRate))

def main():
    BGscheduler = BackgroundScheduler()
    BGscheduler.add_job(notifyIfBalanceAvailable, 'interval', minutes=1)
    BGscheduler.start()

    scheduler = BlockingScheduler()
    scheduler.add_job(getLendingRates, 'interval', seconds=1)
    scheduler.start()

if __name__ == "__main__":
    main()

