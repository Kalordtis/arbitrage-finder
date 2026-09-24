from flask import Flask, render_template, redirect, url_for
import sqlite3
import requests
import datetime

app = Flask(__name__)
API_KEY = 'YOUR_API_KEY' 

# FILTER THRESHOLDS
MIN_PROFIT_PCT = 0.5   # Ignore margins smaller than 0.5% (often wiped out by rounding/fees)
MAX_PROFIT_PCT = 3.5   # Drop anything > 3.5% (almost always stale data or palpable errors)
MAX_ODDS_PRICE = 5.0   # Ignore extreme longshots (> 5.0 / +400) where lag is rampant

def init_db():
    conn = sqlite3.connect('arbitrage.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mismatches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            home_team TEXT,
            away_team TEXT,
            home_odds REAL,
            home_book TEXT,
            away_odds REAL,
            away_book TEXT,
            home_stake REAL,
            away_stake REAL,
            profit_percentage REAL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    init_db()
    conn = sqlite3.connect('arbitrage.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM mismatches ORDER BY timestamp DESC')
    mismatches = cursor.fetchall()
    conn.close()
    return render_template('index.html', mismatches=mismatches)

@app.route('/scan')
def scan():
    url = f'https://api.the-odds-api.com/v4/sports/upcoming/odds/?apiKey={API_KEY}&regions=us&markets=h2h'
    response = requests.get(url)
    
    if response.status_code == 200:
        games = response.json()
        conn = sqlite3.connect('arbitrage.db')
        cursor = conn.cursor()
        
        for game in games:
            home_team = game['home_team']
            away_team = game['away_team']
            best_home, best_away = {'price': 0, 'book': ''}, {'price': 0, 'book': ''}
            
            for bookmaker in game['bookmakers']:
                book_name = bookmaker['title']
                for market in bookmaker['markets']:
                    if market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home_team and outcome['price'] > best_home['price']:
                                best_home = {'price': outcome['price'], 'book': book_name}
                            elif outcome['name'] == away_team and outcome['price'] > best_away['price']:
                                best_away = {'price': outcome['price'], 'book': book_name}
                                
            if best_home['price'] > 0 and best_away['price'] > 0:
                # 1. Reject if either price is an extreme longshot
                if best_home['price'] > MAX_ODDS_PRICE or best_away['price'] > MAX_ODDS_PRICE:
                    continue

                implied_home = 1 / best_home['price']
                implied_away = 1 / best_away['price']
                margin = implied_home + implied_away
                
                # Check for an arbitrage condition
                if margin < 1.0:
                    profit = round(((1.0 - margin) / margin) * 100, 2)
                    
                    # 2. Check if the profit margin falls strictly within the realistic window
                    if MIN_PROFIT_PCT <= profit <= MAX_PROFIT_PCT:
                        total_investment = 100.00
                        home_stake = round((total_investment * implied_home) / margin, 2)
                        away_stake = round((total_investment * implied_away) / margin, 2)
                        
                        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        cursor.execute('''
                            INSERT INTO mismatches 
                            (timestamp, home_team, away_team, home_odds, home_book, away_odds, away_book, home_stake, away_stake, profit_percentage)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (timestamp, home_team, away_team, best_home['price'], best_home['book'], best_away['price'], best_away['book'], home_stake, away_stake, profit))
        
        conn.commit()
        conn.close()
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
def init_db():
    conn = sqlite3.connect('arbitrage.db')
    cursor = conn.cursor()
    # Added home_stake and away_stake to the table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mismatches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            home_team TEXT,
            away_team TEXT,
            home_odds REAL,
            home_book TEXT,
            away_odds REAL,
            away_book TEXT,
            home_stake REAL,
            away_stake REAL,
            profit_percentage REAL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    init_db()
    conn = sqlite3.connect('arbitrage.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM mismatches ORDER BY timestamp DESC')
    mismatches = cursor.fetchall()
    conn.close()
    return render_template('index.html', mismatches=mismatches)

@app.route('/scan')
def scan():
    url = f'https://api.the-odds-api.com/v4/sports/upcoming/odds/?apiKey={API_KEY}&regions=us&markets=h2h'
    response = requests.get(url)
    
    if response.status_code == 200:
        games = response.json()
        conn = sqlite3.connect('arbitrage.db')
        cursor = conn.cursor()
        
        for game in games:
            home_team = game['home_team']
            away_team = game['away_team']
            best_home, best_away = {'price': 0, 'book': ''}, {'price': 0, 'book': ''}
            
            for bookmaker in game['bookmakers']:
                book_name = bookmaker['title']
                for market in bookmaker['markets']:
                    if market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home_team and outcome['price'] > best_home['price']:
                                best_home = {'price': outcome['price'], 'book': book_name}
                            elif outcome['name'] == away_team and outcome['price'] > best_away['price']:
                                best_away = {'price': outcome['price'], 'book': book_name}
                                
            if best_home['price'] > 0 and best_away['price'] > 0:
                implied_home = 1 / best_home['price']
                implied_away = 1 / best_away['price']
                margin = implied_home + implied_away
                
                if margin < 1.0:
                    # Calculate exactly how to divide $100 to guarantee the profit
                    total_investment = 100.00
                    home_stake = round((total_investment * implied_home) / margin, 2)
                    away_stake = round((total_investment * implied_away) / margin, 2)
                    profit = round(((1.0 - margin) / margin) * 100, 2)
                    
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    cursor.execute('''
                        INSERT INTO mismatches 
                        (timestamp, home_team, away_team, home_odds, home_book, away_odds, away_book, home_stake, away_stake, profit_percentage)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (timestamp, home_team, away_team, best_home['price'], best_home['book'], best_away['price'], best_away['book'], home_stake, away_stake, profit))
        
        conn.commit()
        conn.close()
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
def init_db():
    conn = sqlite3.connect('arbitrage.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mismatches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            home_team TEXT,
            away_team TEXT,
            home_odds REAL,
            home_book TEXT,
            away_odds REAL,
            away_book TEXT,
            profit_percentage REAL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    init_db()
    conn = sqlite3.connect('arbitrage.db')
    cursor = conn.cursor()
    # Fetch all logged mismatches, newest first
    cursor.execute('SELECT * FROM mismatches ORDER BY timestamp DESC')
    mismatches = cursor.fetchall()
    conn.close()
    return render_template('index.html', mismatches=mismatches)

@app.route('/scan')
def scan():
    url = f'https://api.the-odds-api.com/v4/sports/upcoming/odds/?apiKey={API_KEY}&regions=us&markets=h2h'
    response = requests.get(url)
    
    if response.status_code == 200:
        games = response.json()
        conn = sqlite3.connect('arbitrage.db')
        cursor = conn.cursor()
        
        for game in games:
            home_team = game['home_team']
            away_team = game['away_team']
            best_home, best_away = {'price': 0, 'book': ''}, {'price': 0, 'book': ''}
            
            for bookmaker in game['bookmakers']:
                book_name = bookmaker['title']
                for market in bookmaker['markets']:
                    if market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home_team and outcome['price'] > best_home['price']:
                                best_home = {'price': outcome['price'], 'book': book_name}
                            elif outcome['name'] == away_team and outcome['price'] > best_away['price']:
                                best_away = {'price': outcome['price'], 'book': book_name}
                                
            if best_home['price'] > 0 and best_away['price'] > 0:
                margin = (1 / best_home['price']) + (1 / best_away['price'])
                if margin < 1.0:
                    profit = round(((1.0 - margin) / margin) * 100, 2)
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute('''
                        INSERT INTO mismatches 
                        (timestamp, home_team, away_team, home_odds, home_book, away_odds, away_book, profit_percentage)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (timestamp, home_team, away_team, best_home['price'], best_home['book'], best_away['price'], best_away['book'], profit))
        
        conn.commit()
        conn.close()
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)