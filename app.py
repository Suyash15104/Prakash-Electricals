from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
import sqlite3
from datetime import datetime, date
import csv
from io import StringIO
from io import BytesIO

app = Flask(__name__)
app.secret_key = "your_secret_key"

# --- Database Setup ---
def get_db_connection():
    conn = sqlite3.connect("shop.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        quantity INTEGER,
        price REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT,
        quantity INTEGER,
        price_per_unit REAL,
        total REAL,
        date_time TEXT,
        payment_method TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == "admin" and password == "1234":
            session["user"] = username
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials.", "danger")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template("dashboard.html", products=products)

@app.route("/add")
def add():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("add_product.html")

@app.route("/add_product", methods=["POST"])
def add_product():
    if "user" not in session:
        return redirect(url_for("login"))
    name = request.form["name"]
    quantity = request.form["quantity"]
    price = request.form["price"]
    conn = get_db_connection()
    conn.execute("INSERT INTO products (name, quantity, price) VALUES (?, ?, ?)", (name, quantity, price))
    conn.commit()
    conn.close()
    flash("Product added successfully.", "success")
    return redirect(url_for("dashboard"))

@app.route("/sell_product", methods=["POST"])
def sell_product():
    if "user" not in session:
        return redirect(url_for("login"))
    name = request.form["name"]
    quantity = int(request.form["quantity"])
    price = float(request.form["price"])
    discount_input = request.form.get("discount", "0")
    discount = float(discount_input) if discount_input.strip() else 0.0
    payment_method = request.form["payment_method"]
    total = max(0, quantity * price - discount)
    date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO sales (product_name, quantity, price_per_unit, total, date_time, payment_method)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, quantity, price, total, date_time, payment_method))
    conn.commit()
    conn.close()
    flash(f"Sold {quantity} of '{name}' for ₹{total:.2f} via {payment_method}", "success")
    return redirect(url_for("dashboard"))

@app.route("/product_names")
def product_names():
    conn = get_db_connection()
    products = conn.execute("SELECT name FROM products").fetchall()
    conn.close()
    return jsonify(names=[product["name"] for product in products])

@app.route("/daily_report")
def daily_report():
    if "user" not in session:
        return redirect(url_for("login"))

    today = date.today().strftime("%Y-%m-%d")
    conn = get_db_connection()
    sales = conn.execute("SELECT * FROM sales WHERE date(date_time) = ?", (today,)).fetchall()
    conn.close()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["ID", "Product Name", "Quantity", "Price/unit", "Total", "Date/Time", "Payment Method"])
    for s in sales:
        cw.writerow([s["id"], s["product_name"], s["quantity"], s["price_per_unit"], s["total"], s["date_time"], s["payment_method"]])

    
    si.seek(0)
    output = BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)

    return send_file(
       output,
       mimetype='text/csv',
       as_attachment=True,
       download_name=f"daily_report_{today}.csv"
)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))
@app.route("/get_price")
def get_price():
    name = request.args.get("name")
    conn = get_db_connection()
    product = conn.execute("SELECT price FROM products WHERE name = ?", (name,)).fetchone()
    conn.close()
    if product:
        return jsonify(price=product["price"])
    else:
        return jsonify(price=None)


if __name__ == "__main__":
    app.run(debug=True)
