# ========================= app.py =========================

from flask import Flask, render_template, request, redirect, session, flash, send_file
import sqlite3
import pandas as pd
import joblib
from datetime import datetime
from fpdf import FPDF
import random
import os
import requests
from flask import jsonify
import smtplib
from email.mime.text import MIMEText


app = Flask(__name__)

app.secret_key = "heart_ai_secret"

# ================= ADMIN LOGIN =================

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"

# ================= MODEL =================

try:

    model = joblib.load("heart_model.pkl")
    columns = joblib.load("columns.pkl")

    print("Model Type:", type(model))
    print(model)

except:

    model = None
    columns = []

    print("Model Files Not Found")

# ================= DATABASE =================

def get_db():

    conn = sqlite3.connect(

        "database.db",

        check_same_thread=False

    )

    return conn


def init_db():

    conn = get_db()

    cursor = conn.cursor()

    # USERS TABLE

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS users(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT UNIQUE,

            password TEXT

        )

    """)

    # PATIENT TABLE

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS patients(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT,

            age INTEGER,

            gender TEXT,

            bp INTEGER,

            chol INTEGER,

            result TEXT,

            risk TEXT,

            date TEXT

        )

    """)

    conn.commit()

    conn.close()


init_db()


# ================= HOME =================

@app.route('/')
def home():

    return render_template('login.html')

# ================= REGISTER PAGE =================

@app.route('/register')
def register():

    return render_template('register.html')

# ================= CREATE ACCOUNT =================

@app.route('/create_account', methods=['POST'])
def create_account():

    username = request.form['username']

    password = request.form['password']

    conn = get_db()

    cursor = conn.cursor()

    try:

        cursor.execute(

            "INSERT INTO users(username,password) VALUES(?,?)",

            (username, password)

        )

        conn.commit()

        conn.close()

        flash("Account Created Successfully")

        return redirect('/')

    except:

        conn.close()

        flash("Username Already Exists")

        return redirect('/register')

# ================= USER LOGIN =================

@app.route('/user_login', methods=['POST'])
def user_login():

    username = request.form['username']

    password = request.form['password']

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute(

        "SELECT * FROM users WHERE username=? AND password=?",

        (username, password)
    )

    user = cursor.fetchone()

    conn.close()

    if user:

        session['user'] = username

        return redirect('/dashboard')

    else:

        flash("Invalid Username or Password")

        return redirect('/')

# ================= DASHBOARD =================

@app.route('/dashboard')
def dashboard():

    weather = get_weather()

    return render_template(
        'dashboard.html',
        weather=weather
    )
# ================= TESTING CHATBOT =================

@app.route('/testing')
def testing():


    return render_template('testing2.html')



# weather

def get_weather():
    API_KEY = "d7ecb5668dfba83e55103dff8fc71b48"

    city = "indore"

    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={"d7ecb5668dfba83e55103dff8fc71b48"}&units=metric"

    response = requests.get(url)
    data = response.json()

    weather = {
        "city": data["name"],
        "temperature": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "condition": data["weather"][0]["description"]
    }

    return weather


# ================= ADMIN PAGE =================

@app.route('/admin')
def admin():

    return render_template('admin.html')

# ================= ADMIN LOGIN =================

@app.route('/admin_login', methods=['POST'])
def admin_login():

    username = request.form['username']

    password = request.form['password']

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:

        session['admin'] = True

        return redirect('/admin_panel')

    else:

        flash("Wrong Username or Password")

        return redirect('/admin')

# ================= LOGOUT =================

@app.route('/logout')
def logout():

    session.pop('user', None)

    session.pop('admin', None)

    flash("Logged Out Successfully")

    return redirect('/admin')

# ================= PREDICT =================

@app.route('/predict', methods=['POST'])
def predict():

    if 'user' not in session:
        return redirect('/')

    try:

        name = request.form['name']
        age = int(request.form['age'])
        sex = int(request.form['sex'])
        cp = int(request.form['cp'])
        bp = int(request.form['trestbps'])
        chol = int(request.form['chol'])

        fbs_real = float(request.form['fbs_real'])
        fbs = 1 if fbs_real > 120 else 0

        restecg = int(request.form['restecg'])
        thalach = int(request.form['thalach'])
        exang = int(request.form['exang'])
        oldpeak = float(request.form['oldpeak'])
        slope = int(request.form['slope'])
        ca = int(request.form['ca'])
        thal = int(request.form['thal'])

        weight = float(request.form.get('weight', 70))
        height = float(request.form.get('height', 170))

        bmi = round(
            weight / ((height / 100) ** 2),
            2
        )

        if model is None:
            return "heart_model.pkl not found"

        input_data = pd.DataFrame([{
            'age': age,
            'sex': sex,
            'cp': cp,
            'trestbps': bp,
            'chol': chol,
            'fbs': fbs,
            'restecg': restecg,
            'thalach': thalach,
            'exang': exang,
            'oldpeak': oldpeak,
            'slope': slope,
            'ca': ca,
            'thal': thal
        }])

        input_data = input_data.reindex(
            columns=columns,
            fill_value=0
        )

        prediction = model.predict(input_data)[0]

        probability = model.predict_proba(
            input_data
        )[0][1]

        risk_value = round(probability * 100)
       # result

        if prediction == 0:
            result = "Low Risk of Heart Disease"
            emergency = False
        else:
            result = "High Risk of Heart Disease"
            emergency = True

        risk = str(risk_value)

        # save databse

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO patients(
                name,
                age,
                gender,
                bp,
                chol,
                result,
                risk,
                date
            )
            VALUES(?,?,?,?,?,?,?,?)
        """, (
            name,
            age,
            'Male' if sex == 1 else 'Female',
            bp,
            chol,
            result,
            risk,
            datetime.now().strftime('%d-%m-%Y %H:%M')
        ))

        conn.commit()
        conn.close()

        return render_template(
            'result.html',
            name=name,
            age=age,
            sex=sex,
            cp=cp,
            bp=bp,
            chol=chol,
            fbs=fbs,
            bmi=bmi,
            result=result,
            risk=risk,
            emergency=emergency
        )

    except Exception as e:
        return f"Prediction Error: {str(e)}"
    


    

    
# ================= ADMIN PANEL =================

@app.route('/admin_panel')
def admin_panel():

    if 'admin' not in session:

        return redirect('/admin')

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute(

        "SELECT * FROM patients ORDER BY id DESC"

    )

    data = cursor.fetchall()

    conn.close()

    return render_template(

        'admin_panel.html',

        records=data

    )

# ================= SEARCH =================

@app.route('/search', methods=['POST'])
def search():

    if 'admin' not in session:

        return redirect('/admin')

    search_name = request.form['search']

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute(

        "SELECT * FROM patients WHERE name LIKE ?",

        ('%' + search_name + '%',)

    )

    data = cursor.fetchall()

    conn.close()

    return render_template(

        'history.html',

        records=data

    )

# ================= HISTORY =================

@app.route('/history')
def history():

    if 'admin' not in session:

        return redirect('/admin')

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute(

        "SELECT * FROM patients ORDER BY id DESC"

    )

    data = cursor.fetchall()

    conn.close()

    return render_template(

        'history.html',

        records=data

    )

# ================= ANALYTICS =================

@app.route('/analytics')
def analytics():

    if 'admin' not in session:

        return redirect('/admin')

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM patients")

    records = cursor.fetchall()

    conn.close()

    total_patients = len(records)

    high_risk = sum(

        1 for row in records

        if "High" in str(row[6])

    )

    low_risk = total_patients - high_risk

    return render_template(

        'analytics.html',

        total=total_patients,

        high=high_risk,

        low=low_risk

    )

# ================= EXPORT CSV =================

@app.route('/export')
def export():

    if 'admin' not in session:

        return redirect('/admin')

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM patients")

    data = cursor.fetchall()

    conn.close()

    df = pd.DataFrame(

        data,

        columns=[

            'ID',
            'Name',
            'Age',
            'Gender',
            'Blood Pressure',
            'Cholesterol',
            'Result',
            'Risk',
            'Date'
        ]

    )

    filename = "patients_report.csv"

    df.to_csv(filename, index=False)

    return send_file(

        filename,

        as_attachment=True

    )

# ================= PDF REPORT =================

@app.route('/download/<name>/<age>/<sex>/<cp>/<bp>/<chol>/<fbs>/<result>/<risk>')
def download_report(

    name,
    age,
    sex,
    cp,
    bp,
    chol,
    fbs,
    result,
    risk

):

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"{name}_{timestamp}.pdf"

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font("Arial", 'B', 22)

    pdf.set_text_color(0, 102, 204)

    pdf.cell(

        200,

        15,

        txt="Heart Disease Prediction Report",

        ln=True,

        align='C'

    )

    pdf.ln(20)

    pdf.set_font("Arial", 'B', 16)

    pdf.cell(200, 10, txt="Patient Information", ln=True)

    pdf.ln(5)

    pdf.set_font("Arial", size=14)

    pdf.cell(200, 10, txt=f"Name : {name}", ln=True)

    pdf.cell(200, 10, txt=f"Age : {age}", ln=True)

    pdf.cell(

        200,

        10,

        txt=f"Gender : {'Male' if sex == '1' else 'Female'}",

        ln=True

    )

    pdf.cell(200, 10, txt=f"Blood Pressure : {bp}", ln=True)

    pdf.cell(200, 10, txt=f"Cholesterol : {chol}", ln=True)

    pdf.cell(200, 10, txt=f"Prediction Result : {result}", ln=True)

    pdf.cell(200, 10, txt=f"Risk Percentage : {risk}%", ln=True)

    pdf.output(filename)

    return send_file(

        filename,

        as_attachment=True

    )

# sos system
# ================= SOS SYSTEM =================
@app.route('/send_sos', methods=['POST'])
def send_sos():

    try:

        data = request.get_json()

        print("SOS Route Called")

        latitude = data.get("latitude")
        longitude = data.get("longitude")

        print("Latitude:", latitude)
        print("Longitude:", longitude)

        if latitude is None or longitude is None:

            return jsonify({
                "status": "error",
                "message": "Location not received"
            })

        location_link = f"https://maps.google.com/?q={latitude},{longitude}"

        sender = "laadshailee@gmail.com"

        # YAHAN APNA GMAIL APP PASSWORD DALNA HAI
        app_password = "YOUR_APP_PASSWORD"

        receiver = "deepaklaad1975@gmail.com"

        message = f"""
HEART EMERGENCY ALERT

Patient may be in danger.

Live Location:
{location_link}

Please contact immediately.
"""

        msg = MIMEText(message)

        msg["Subject"] = "Heart Emergency Alert"
        msg["From"] = sender
        msg["To"] = receiver

        server = smtplib.SMTP("smtp.gmail.com", 587)

        server.starttls()

        server.login(sender, app_password)

        server.send_message(msg)

        server.quit()

        print("Email Sent Successfully")

        return jsonify({
            "status": "success",
            "message": "SOS Alert Sent Successfully"
        })

    except Exception as e:

        print("SOS ERROR:", str(e))

        return jsonify({
            "status": "error",
            "message": str(e)
        })
# ================= CHATBOT =================

@app.route('/chatbot')
def chatbot():

    return render_template('chatbot.html')

@app.route('/get')
def get_bot_response():

    user_text = request.args.get('msg').lower()

    if 'tips' in user_text:

        return "Exercise daily and avoid oily food."

    elif 'bp' in user_text:

        return "Normal blood pressure should be around 120/80."

    elif 'exercise' in user_text:

        return "Walking daily is very good for heart."

    elif 'diet' in user_text:

        return "Eat fruits and avoid junk food."

    elif 'hello' in user_text:

        return "Hello! How can I help you?"

    else:

        return "Please consult a doctor for detailed advice."

# ================= RUN APP =================

if __name__ == '__main__':

    app.run(debug=True)