# import flask and its components
from flask import *
import os
from flask_cors import CORS
import pymysql
import requests
import datetime
import base64
from requests.auth import HTTPBasicAuth

# create a flask application and give it a name
app = Flask(__name__)

# ✅ FIX 1: CORS was called incorrectly — app(CORS) is wrong syntax
# Correct usage is CORS(app)
CORS(app)

# ✅ FIX 2: Two separate upload folders — one for images, one for PDF files
app.config["UPLOAD_FOLDER_IMAGES"] = "static/images"
app.config["UPLOAD_FOLDER_FILES"]  = "static/files"   # your existing static/files folder

# ✅ Make sure both folders exist on startup so saves never fail silently
os.makedirs(app.config["UPLOAD_FOLDER_IMAGES"], exist_ok=True)
os.makedirs(app.config["UPLOAD_FOLDER_FILES"],  exist_ok=True)


# ── Signup ──────────────────────────────────────────────────────
@app.route("/api/signup", methods=["POST"])
def signup():
    username = request.form["username"]
    email    = request.form["email"]
    password = request.form["password"]
    phone    = request.form["phone"]

    connection = pymysql.connect(
        host="mysql-tashaandeso.alwaysdata.net",
        user="tashaandeso",
        password="modcom1234",
        database="tashaandeso_sokogarden"
    )
    cursor = connection.cursor()
    sql    = "INSERT INTO users(username, email, phone, password) VALUES(%s, %s, %s, %s)"
    data   = (username, email, phone, password)
    cursor.execute(sql, data)
    connection.commit()
    connection.close()   # ✅ FIX 3: always close connections

    return jsonify({"message": "User registered successfully."})


# ── Signin ──────────────────────────────────────────────────────
@app.route("/api/signin", methods=["POST"])
def signin():
    email    = request.form["email"]
    password = request.form["password"]

    connection = pymysql.connect(
        host="mysql-tashaandeso.alwaysdata.net",
        user="tashaandeso",
        password="modcom1234",
        database="tashaandeso_sokogarden"
    )
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    sql    = "SELECT * FROM users WHERE email = %s AND password = %s"
    data   = (email, password)
    cursor.execute(sql, data)
    count  = cursor.rowcount

    if count == 0:
        connection.close()
        return jsonify({"message": "login failed"})
    else:
        user = cursor.fetchone()
        connection.close()
        return jsonify({"message": "user logged in successfully", "user": user})


# ── Add Product ─────────────────────────────────────────────────
@app.route("/api/add_product", methods=["POST"])
def Addproducts():
    product_name        = request.form["product_name"]
    product_description = request.form["product_description"]
    product_cost        = request.form["product_cost"]

    product_photo = request.files["product_photo"]
    product_file  = request.files["product_file"]

    photo_filename = product_photo.filename
    file_filename  = product_file.filename

    # ✅ FIX 4: PDF was being saved to static/images — now saved to static/files
    photo_path = os.path.join(app.config["UPLOAD_FOLDER_IMAGES"], photo_filename)
    file_path  = os.path.join(app.config["UPLOAD_FOLDER_FILES"],  file_filename)

    product_photo.save(photo_path)
    product_file.save(file_path)   # ✅ PDF now saves to the correct folder

    # ✅ FIX 5: Validate that both files were actually received before saving to DB
    if not photo_filename or not file_filename:
        return jsonify({"message": "Missing photo or PDF file"}), 400

    connection = pymysql.connect(
        host="mysql-tashaandeso.alwaysdata.net",
        user="tashaandeso",
        password="modcom1234",
        database="tashaandeso_sokogarden"
    )
    cursor = connection.cursor()
    sql    = "INSERT INTO product_details(product_name, product_description, product_cost, product_photo, product_file) VALUES (%s, %s, %s, %s, %s)"
    data   = (product_name, product_description, product_cost, photo_filename, file_filename)
    cursor.execute(sql, data)
    connection.commit()
    connection.close()

    return jsonify({"message": "Product and PDF file added successfully"})


# ── Get Products ────────────────────────────────────────────────
@app.route("/api/get_products")
def get_products():
    connection = pymysql.connect(
        host="mysql-tashaandeso.alwaysdata.net",
        user="tashaandeso",
        password="modcom1234",
        database="tashaandeso_sokogarden"
    )
    cursor   = connection.cursor(pymysql.cursors.DictCursor)
    sql      = "SELECT * FROM product_details"
    cursor.execute(sql)
    products = cursor.fetchall()
    connection.close()

    return jsonify(products)


# ── Mpesa Payment ───────────────────────────────────────────────
@app.route('/api/mpesa_payment', methods=['POST'])
def mpesa_payment():
    amount = request.form['amount']
    phone  = request.form['phone']

    consumer_key    = "GTWADFxIpUfDoNikNGqq1C3023evM6UH"
    consumer_secret = "amFbAoUByPV2rM5A"
    api_URL         = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    r            = requests.get(api_URL, auth=HTTPBasicAuth(consumer_key, consumer_secret))
    access_token = "Bearer " + r.json()['access_token']

    timestamp          = datetime.datetime.today().strftime('%Y%m%d%H%M%S')
    passkey            = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
    business_short_code = "174379"
    raw_data           = business_short_code + passkey + timestamp
    password           = base64.b64encode(raw_data.encode()).decode('utf-8')

    payload = {
        "BusinessShortCode": "174379",
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": "174379",
        "PhoneNumber": phone,
        "CallBackURL": "https://modcom.co.ke/api/confirmation.php",
        "AccountReference": "account",
        "TransactionDesc": "account"
    }
    headers  = {"Authorization": access_token, "Content-Type": "application/json"}
    url      = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    response = requests.post(url, json=payload, headers=headers)
    print(response.text)

    return jsonify({"message": "Please complete payment in your phone and we will deliver in minutes"})


# ── Run ─────────────────────────────────────────────────────────
if __name__ == "__main__":   # ✅ FIX 6: best practice guard so the app doesn't run on import
    app.run(debug=True)