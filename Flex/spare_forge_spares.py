from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, session
import os
from werkzeug.utils import secure_filename
import sqlite3, uuid

app = Flask(__name__)
app.secret_key = "forge_ultra_secure"

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB = "store.db"
PAYMENT_NUMBER = "0112752649"

# ---------------- INIT ----------------
def init():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS products(
        name TEXT,
        price INTEGER,
        old_price REAL,
        image TEXT,
        code TEXT,
        part_name TEXT,
        part_number TEXT,
        part_description TEXT,
        part_category TEXT,
        part_condition TEXT,
        id INTEGER PRIMARY KEY
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS suggestions(
        id INTEGER PRIMARY KEY,
        message TEXT,
        reply TEXT,
        name TEXT
    )""")

    conn.commit()
    conn.close()

init()

def code():
    return "SFS-" + str(uuid.uuid4())[:5].upper()

@app.route("/delete-product/<code>")
def delete_product(code):
    if not session.get("admin"):
        return redirect("/hidden-admin-portal")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("DELETE FROM products WHERE code=?", (code,))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ---------------- HOME ----------------
@app.route("/")
def home():
    q = request.args.get("q", "")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if q:
        c.execute("SELECT * FROM products WHERE LOWER(name) LIKE ?", ('%' + q.lower() + '%',))
    else:
        c.execute("SELECT * FROM products")

    products = c.fetchall()

    c.execute("SELECT * FROM suggestions ORDER BY id DESC")
    suggestions = c.fetchall()

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SPARE FORGE SPARES</title>

<style>
body{margin:0;font-family:Arial;background:white;}

header{
    background:#111;
    color:white;
    padding:15px;
    display:flex;
    justify-content:space-between;
    align-items:center;
}

.logo{font-size:30px;font-weight:bold;}
.slogan{font-style:italic;font-size:12px;}

.search{padding:8px;width:200px;}

.grid{
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(220px,1fr));
    gap:20px;
    padding:25px;
}

.card{
    border:1px solid #eee;
    padding:10px;
    text-align:center;
}

.card p{
    margin:5px 0;
    font-size:13px;
}

.card img{
    width:100%;
    height:auto;
    object-fit:contain;
}

.price{font-weight:bold;}
.code{font-size:11px;color:gray;}

button{
    background:black;
    color:white;
    border:none;
    padding:10px;
}

.cartbtn{background:#ff9800;}


</style>
</head>

<body>

<header>
<div>
<div class="logo">SPARE FORGE SPARES</div>
<div class="slogan">\"Your garage online\"</div>
</div>

<form>
<input class="search" name="q" placeholder="Search..." value="{{q}}">
</form>

<a href="/cart"><button class="cartbtn">Cart</button></a>
</header>

<div class="grid">
{% for p in products %}
<div class="card">
<img src="{{p[3]}}">
<h3 class="title">{{p[0]}}</h3>

<div class="meta">
    <div><span class="label">Part No:</span> {{p[6]}}</div>
    <div><span class="label">Description:</span> {{p[7]}}</div>
    <div><span class="label">Category:</span> {{p[8]}}</div>
    <div><span class="label">Condition:</span> {{p[9]}}</div>
</div>

<div class="price">
{% if p[2] and p[2]|int != p[1]|int %}

    <span style="text-decoration:line-through;color:red;">
        Ksh {{p[2]}}
    </span>

    <span style="color:green;font-weight:bold;">
        Ksh {{p[1]}}
    </span>

{% else %}
    Ksh {{p[1]}}
{% endif %}
</div>

<a href="/add/{{p[10]}}">
<button>Add to Cart</button>
</a>
</div>
{% endfor %}
</div>

<hr>

<h3 style="text-align:center;">What can we find you? Leave a Message</h3>

<form method="post" action="/suggest" style="text-align:center;">
<input name="name" placeholder="Your contact info" required><br><br>
<textarea name="msg" placeholder="Your message..." required style="width:70%;height:80px;"></textarea><br><br>
<button>Send</button>
</form>

<hr>

<h3 style="text-align:center;">Customer Messages</h3>

{% for s in suggestions %}
<div style="border:1px solid #ccc;margin:10px;padding:10px;">
<p><b>{{s[3]}}</b>: {{s[1]}}</p>

{% if s[2] %}
<p style="color:green;"><b>Admin:</b> {{s[2]}}</p>
{% endif %}
</div>
{% endfor %}

<div style="text-align:center;padding:20px;">
<a href="https://www.whatsapp.com/business/" target="_blank">
<button style="background:#25D366;">Chat on WhatsApp</button>
</a>
</div>

</body>
</html>
""", products=products, q=q, suggestions=suggestions)

# ---------------- SUGGEST ----------------
@app.route("/suggest", methods=["POST"])
def suggest():
    msg = request.form["msg"]
    name = request.form["name"]

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO suggestions(message,reply,name) VALUES(?,?,?)", (msg, "", name))
    conn.commit()
    conn.close()

    return redirect("/")

# ---------------- CART ----------------
@app.route("/add/<int:id>")
def add(id):
    if "cart" not in session:
        session["cart"] = {}

    session["cart"][str(id)] = session["cart"].get(str(id), 0) + 1
    session.modified = True
    return redirect("/cart")

# ---------------- CART ----------------
@app.route("/cart")
def cart():
    cart = session.get("cart", {})
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    items = []
    total = 0

    for k, qty in cart.items():
        c.execute("SELECT * FROM products WHERE id=?", (k,))
        p = c.fetchone()
        if p:
            subtotal = p[1] * qty  # using current price p[1]
            total += subtotal
            items.append((p, qty, subtotal))

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Your Cart</title>
<style>
body{font-family:Arial;padding:20px;}
table{width:100%;border-collapse:collapse;margin-bottom:20px;}
th,td{border:1px solid #ccc;padding:10px;text-align:center;}
button{padding:8px 12px;background:#ff9800;color:white;border:none;cursor:pointer;}
</style>
</head>
<body>

<h2>Your Cart</h2>

{% if items %}
<table>
<tr>
<th>Product</th>
<th>Qty</th>
<th>Price</th>
<th>Subtotal</th>
<th>Action</th>
</tr>

{% for p, qty, subtotal in items %}
<tr>
<td>{{p[0]}}</td>
<td>{{qty}}</td>
<td>Ksh {{p[1]}}</td>
<td>Ksh {{subtotal}}</td>
<td>
<form method="post" action="/remove/{{p[10]}}">
<button>Remove</button>
</form>
</td>
</tr>
{% endfor %}

<tr>
<td colspan="3" style="text-align:right;font-weight:bold;">Total:</td>
<td colspan="2" style="font-weight:bold;">Ksh {{total}}</td>
</tr>
</table>

<p>Copy this number to pay: <b>{{number}}</b></p>

<h3>FAQs & Professional Info</h3>
<ul>
<li>All payments are to be made via M-Pesa or direct transfer.</li>
<li>Shipping takes 1-3 business days after payment confirmation.</li>
<li>For returns or complaints, contact us via WhatsApp.</li>
<li>All products are genuine and quality checked.</li>
</ul>

<a href="/"><button>Continue Shopping</button></a>

{% else %}
<p>Your cart is empty.</p>
<a href="/"><button>Go Shopping</button></a>
{% endif %}

</body>
</html>
""", items=items, total=total, number=PAYMENT_NUMBER)

# ---------------- REMOVE ITEM ----------------
@app.route("/remove/<int:id>", methods=["POST"])
def remove_item(id):
    cart = session.get("cart", {})
    str_id = str(id)
    if str_id in cart:
        del cart[str_id]  # remove item
        session["cart"] = cart
        session.modified = True
    return redirect("/cart")

# ---------------- ADMIN ----------------
ADMIN_USER = "admin"
ADMIN_PASS = "forge2026"

@app.route("/hidden-admin-portal", methods=["GET","POST"])
def admin():
    if request.method == "POST":
        if request.form["u"] == ADMIN_USER and request.form["p"] == ADMIN_PASS:
            session["admin"] = True
            return redirect("/dashboard")

    return """
<form method="post">
<input name="u" placeholder="username"><br><br>
<input name="p" type="password"><br><br>
<button>Login</button>
</form>
"""

# ---------------- DASHBOARD ----------------
@app.route("/dashboard", methods=["GET","POST"])
def dash():
    if not session.get("admin"):
        return redirect("/hidden-admin-portal")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()

    if request.method == "POST":
        file = request.files.get("i")

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(path)
            image_path = "/" + path
        else:
            image_path = ""

        price_raw = request.form["p"].replace(",", "").strip()
        price = int(price_raw) if price_raw.isdigit() else 0

        c.execute("""
        INSERT INTO products (
            name, price, old_price, image, code,
            part_name, part_number, part_description,
            part_category, part_condition
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,?)
        """, (
            request.form["n"],
            price,
            request.form["old_price"],
            image_path,
            code(),
            request.form["pn"],
            request.form["pnum"],
            request.form["pd"],
            request.form["pc"],
            request.form["pcond"]
        ))

        conn.commit()
        return redirect("/dashboard")

    conn.close()

    return render_template_string("""
<div style="max-width:600px;margin:30px auto;font-family:Arial;background:#fff;padding:20px;border:1px solid #eee;border-radius:10px;">

<h2 style="text-align:center;">Dashboard</h2>

<form method="post" enctype="multipart/form-data">

<div style="display:grid;gap:10px;">

<input name="n" placeholder="Display Name" style="padding:10px;">
<input name="p" placeholder="Price" style="padding:10px;">
<input name="old_price" placeholder="Old Price" style="padding:10px;">

<input name="pn" placeholder="Part Name" style="padding:10px;">
<input name="pnum" placeholder="Part Number" style="padding:10px;">
<input name="pd" placeholder="Description" style="padding:10px;">
<input name="pc" placeholder="Category" style="padding:10px;">
<input name="pcond" placeholder="Condition" style="padding:10px;">

<input type="file" name="i">

<button style="background:black;color:white;padding:12px;border:none;width:100%;margin-top:10px;">
Add Product
</button>

</div>
</form>

<hr>

<h3>Manage Products</h3>

{% for p in products %}
<div style="border:1px solid #ccc;padding:10px;margin:10px 0;">
    <b>{{p[0]}}</b> - Ksh {{p[1]}} <br>
    <a href="/delete-product/{{p[4]}}" style="color:red;">Delete</a>
</div>
{% endfor %}

<br>

<div style="text-align:center;">
<a href="/messages">View Messages</a>
</div>

</div>
""", products=products)

# ---------------- ADMIN MESSAGES ----------------
@app.route("/messages", methods=["GET","POST"])
def messages():
    if not session.get("admin"):
        return redirect("/hidden-admin-portal")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if request.method == "POST":
        c.execute("UPDATE suggestions SET reply=? WHERE id=?",
                  (request.form["reply"], request.form["id"]))
        conn.commit()

    c.execute("SELECT * FROM suggestions")
    data = c.fetchall()
    conn.close()

    return render_template_string("""
<h2>Customer Messages</h2>

{% for d in data %}
<div style="border:1px solid #000;padding:10px;margin:10px;">
<p><b>{{d[3]}}</b>: {{d[1]}}</p>
<p><b>Reply:</b> {{d[2]}}</p>

<form method="post">
<input type="hidden" name="id" value="{{d[0]}}">
<input name="reply" placeholder="Reply">
<button>Send</button>
</form>

<a href="/delete-msg/{{d[0]}}">
<button style="background:red;">Delete</button>
</a>
</div>
{% endfor %}
""", data=data)

# ---------------- DELETE MESSAGE ----------------
@app.route("/delete-msg/<int:id>")
def delete_msg(id):
    if not session.get("admin"):
        return redirect("/hidden-admin-portal")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM suggestions WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/messages")

app.run(debug=True)
