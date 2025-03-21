import matplotlib
matplotlib.use('Agg')  # Use the Agg backend for non-GUI image generation

import matplotlib.pyplot as plt
import seaborn as sns
from flask import Flask, render_template, redirect, url_for, request, session, flash
import json
import os
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
import logging

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure logging
logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

def load_users():
    try:
        with open('data/users.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading users: {e}")
        return []

def save_user(user):
    try:
        users = load_users()
        users.append(user)
        with open('data/users.json', 'w') as f:
            json.dump(users, f)
    except Exception as e:
        logging.error(f"Error saving user: {e}")

def generate_food_waste_charts():
    try:
        if not os.path.exists('Food Waste data and research.csv'):
            logging.error("Food Waste data and research.csv file not found.")
            return

        food_waste_df = pd.read_csv('Food Waste data and research.csv')
        food_waste_df.dropna(inplace=True)

        food_waste_by_region = food_waste_df.groupby('Region')['combined figures (kg/capita/year)'].sum()
        food_waste_by_region.plot(kind='pie', autopct='%1.1f%%', figsize=(8, 8), title='Food Waste by Region')
        plt.ylabel('')
        plt.savefig('static/pie_chart_food_waste_by_region.png')
        plt.close()

        plt.figure(figsize=(12, 6))
        sns.histplot(food_waste_df['combined figures (kg/capita/year)'], bins=20, kde=True)
        plt.title('Distribution of Food Waste')
        plt.xlabel('Combined Figures (kg/capita/year)')
        plt.ylabel('Frequency')
        plt.savefig('static/distribution_food_waste.png')
        plt.close()
        
        logging.info("Food waste charts generated successfully.")
    
    except Exception as e:
        logging.error(f"Error generating food waste charts: {e}")

def generate_donation_charts():
    try:
        if not os.path.exists('data/donation_data.json'):
            logging.error("Donation data file not found.")
            return

        with open('data/donation_data.json', 'r') as f:
            donation_data = json.load(f)
        
        donation_df = pd.DataFrame(donation_data)

        if donation_df.empty:
            logging.info("No donation data available for chart generation.")
            return

        donation_df.groupby('item')['waste_quantity'].sum().plot(kind='bar', figsize=(12, 6), title='Total Food Donations by Item')
        plt.xlabel('Food Item')
        plt.ylabel('Total Waste Quantity (kg)')
        plt.xticks(rotation=45)
        plt.savefig('static/bar_chart_donations_by_item.png')
        plt.close()
        
        logging.info("Donation charts generated successfully.")
    
    except Exception as e:
        logging.error(f"Error generating donation charts: {e}")
# User registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        users = load_users()
        
        if any(user['username'] == username for user in users):
            flash('Username already exists')
            return redirect(url_for('register'))
        
        save_user({'username': username, 'password': password})
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            users = load_users()
            
            user = next((u for u in users if u['username'] == username), None)
            if user and check_password_hash(user['password'], password):
                session['username'] = username
                flash('Login successful!')
                return redirect(url_for('home'))
            else:
                flash('Invalid credentials')
                return redirect(url_for('login'))
        except Exception as e:
            logging.error(f"Error during login: {e}")
            flash('An error occurred during login.')
    return render_template('login.html')

@app.route('/food_leftover', methods=['GET', 'POST'])
def food_leftover():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            food_item = request.form['food_item']
            purchased_quantity = int(request.form['purchased_quantity'])
            consumed_quantity = int(request.form['consumed_quantity'])
            waste_quantity = purchased_quantity - consumed_quantity
            
            food_data = {
                'food_item': food_item,
                'purchased_quantity': purchased_quantity,
                'consumed_quantity': consumed_quantity,
                'waste_quantity': waste_quantity
            }
            
            if not os.path.exists('data/food_data.json'):
                with open('data/food_data.json', 'w') as f:
                    json.dump([], f)
            
            with open('data/food_data.json', 'r') as f:
                existing_data = json.load(f)
            
            existing_data.append(food_data)
            
            with open('data/food_data.json', 'w') as f:
                json.dump(existing_data, f)
            
            return redirect(url_for('donate', waste_quantity=waste_quantity))
        except Exception as e:
            logging.error(f"Error processing food leftover: {e}")
            flash('An error occurred while processing food leftover.')
    return render_template('food_leftover.html')
@app.route('/donate/<int:waste_quantity>', methods=['GET', 'POST'])
def donate(waste_quantity):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            donate = request.form['donate']
            if donate == 'yes':
                return redirect(url_for('donation_details', waste_quantity=waste_quantity))
            else:
                # Redirect to the /charts route which will generate the wastage chart
                return redirect(url_for('charts', update_wastage_chart=True))
        except Exception as e:
            logging.error(f"Error handling donation decision: {e}")
            flash('An error occurred while handling donation decision.')
    return render_template('donate.html', waste_quantity=waste_quantity)

@app.route('/charts')
def charts():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    update_wastage_chart = request.args.get('update_wastage_chart', 'false').lower() == 'true'
    
    if not os.path.exists('data/food_data.json'):
        with open('data/food_data.json', 'w') as f:
            json.dump([], f)
    
    with open('data/food_data.json', 'r') as f:
        data = json.load(f)
    
    if len(data) > 0:
        df = pd.DataFrame(data)
        if update_wastage_chart:
            plt.figure(figsize=(10, 6))
            plt.bar(df['food_item'], df['waste_quantity'], color='red')
            plt.xlabel('Food Item')
            plt.ylabel('Wasted Quantity')
            plt.title('Food Wastage Analysis')
            plt.savefig('static/wastage_chart.png')
            plt.close()
        # You might want to generate other charts here as well
        # e.g., generate_food_waste_charts() if needed

    return render_template('charts.html')


@app.route('/donation_details/<int:waste_quantity>', methods=['GET', 'POST'])
def donation_details(waste_quantity):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            item = request.form['item']
            location = request.form['location']
            phone_number = request.form['phone_number']
            
            donation_info = {
                'item': item,
                'location': location,
                'phone_number': phone_number,
                'waste_quantity': waste_quantity
            }
            
            if not os.path.exists('data/donation_data.json'):
                with open('data/donation_data.json', 'w') as f:
                    json.dump([], f)
            
            with open('data/donation_data.json', 'r') as f:
                existing_donations = json.load(f)
            
            existing_donations.append(donation_info)
            
            with open('data/donation_data.json', 'w') as f:
                json.dump(existing_donations, f)
            
            generate_donation_charts()
            return redirect(url_for('thank_you'))
        except Exception as e:
            logging.error(f"Error processing donation details: {e}")
            flash('An error occurred while processing donation details.')
    return render_template('donation_details.html', waste_quantity=waste_quantity)

@app.route('/thank_you')
def thank_you():
    if 'username' not in session:
        return redirect(url_for('login'))

    try:
        generate_food_waste_charts()
        generate_donation_charts()
    except Exception as e:
        logging.error(f"Error on thank you page: {e}")
        flash('An error occurred while generating charts.')
    
    return render_template('thank_you.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
