from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

# إعداد Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# نموذج المستخدم
class User(UserMixin):
    def __init__(self, id, username, password, role):
        self.id = id
        self.username = username
        self.password = password
        self.role = role

# تحميل المستخدم
@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_data = c.fetchone()
    conn.close()
    if user_data:
        return User(id=user_data[0], username=user_data[1], password=user_data[2], role=user_data[3])
    return None

# إنشاء قاعدة البيانات والجداول
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS invoices
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  device_name TEXT,
                  customer_name TEXT,
                  start_time TEXT,
                  end_time TEXT,
                  cost TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS devices
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE,
                  rate_per_hour REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  role TEXT)''')
    conn.commit()
    conn.close()

# تهيئة قاعدة البيانات
init_db()

# جلب الأجهزة من قاعدة البيانات
def get_devices():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT name, rate_per_hour FROM devices")
    devices = {row[0]: {"rate_per_hour": row[1], "start_time": None, "end_time": None, "customer_name": None, "reserved_minutes": None, "open_end": False} for row in c.fetchall()}
    conn.close()
    return devices

# تحديث الأجهزة
devices = get_devices()

# تسجيل الدخول
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_data = c.fetchone()
        conn.close()
        if user_data and user_data[2] == password:  # التحقق من كلمة المرور
            user = User(id=user_data[0], username=user_data[1], password=user_data[2], role=user_data[3])
            login_user(user)
            flash("تم تسجيل الدخول بنجاح!", "success")
            return redirect(url_for("index"))
        else:
            flash("اسم المستخدم أو كلمة المرور غير صحيحة!", "danger")
    return render_template("login.html")

# تسجيل الخروج
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("تم تسجيل الخروج بنجاح!", "success")
    return redirect(url_for("login"))

# الصفحة الرئيسية
@app.route("/")
@login_required
def index():
    return render_template("index.html", devices=devices, time=time)

# بدء الجهاز
@app.route("/start/<device_name>", methods=["POST"])
@login_required
def start_device(device_name):
    if device_name in devices:
        if devices[device_name]["start_time"] is not None:
            flash(f"الجهاز {device_name} محجوز بالفعل!", "danger")
            return redirect(url_for("index"))
        
        customer_name = request.form.get("customer_name")
        reservation_time = request.form.get("reservation_time")
        
        if not customer_name or not reservation_time:
            flash("يرجى إدخال اسم العميل ووقت الحجز!", "danger")
            return redirect(url_for("index"))
        
        try:
            hours, minutes = map(int, reservation_time.split(':'))
            if minutes < 0 or minutes >= 60:
                flash("الدقائق يجب أن تكون بين 0 و 59!", "danger")
                return redirect(url_for("index"))
            reserved_minutes = hours * 60 + minutes
        except (ValueError, AttributeError):
            flash("وقت الحجز يجب أن يكون بتنسيق صحيح (ساعات:دقائق)، مثال: 1:30", "danger")
            return redirect(url_for("index"))
        
        devices[device_name]["start_time"] = time.time()
        devices[device_name]["customer_name"] = customer_name
        devices[device_name]["reserved_minutes"] = reserved_minutes
        devices[device_name]["open_end"] = False
        
        flash(f"تم بدء الجهاز {device_name} بنجاح للعميل {customer_name} لمدة {hours} ساعة و {minutes} دقيقة!", "success")
    return redirect(url_for("index"))

# إيقاف الجهاز
@app.route("/stop/<device_name>", methods=["POST"])
@login_required
def stop_device(device_name):
    if device_name in devices:
        if devices[device_name]["start_time"] is None:
            flash(f"الجهاز {device_name} غير محجوز!", "warning")
            return redirect(url_for("index"))
        
        devices[device_name]["end_time"] = time.time()
        elapsed_time = devices[device_name]["end_time"] - devices[device_name]["start_time"]
        cost = (elapsed_time / 3600) * devices[device_name]["rate_per_hour"]
        
        start_time = datetime.fromtimestamp(devices[device_name]["start_time"]).strftime('%Y-%m-%d %H:%M:%S')
        end_time = datetime.fromtimestamp(devices[device_name]["end_time"]).strftime('%Y-%m-%d %H:%M:%S')
        customer_name = devices[device_name].get("customer_name", "غير معروف")
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO invoices (device_name, customer_name, start_time, end_time, cost) VALUES (?, ?, ?, ?, ?)",
                  (device_name, customer_name, start_time, end_time, f"{cost:.2f} جنيه"))
        conn.commit()
        conn.close()

        devices[device_name]["start_time"] = None
        devices[device_name]["end_time"] = None
        devices[device_name]["customer_name"] = None
        devices[device_name]["reserved_minutes"] = None
        devices[device_name]["open_end"] = False

        flash(f"الوقت المستخدم: {elapsed_time / 60:.2f} دقيقة\nالتكلفة: {cost:.2f} جنيه", "info")
    return redirect(url_for("index"))

# الوقت المفتوح
@app.route("/open_end/<device_name>", methods=["POST"])
@login_required
def open_end(device_name):
    if device_name in devices:
        if devices[device_name]["start_time"] is not None:
            flash(f"الجهاز {device_name} محجوز بالفعل!", "danger")
            return redirect(url_for("index"))
        
        customer_name = request.form.get("customer_name")
        
        if not customer_name:
            flash("يرجى إدخال اسم العميل!", "danger")
            return redirect(url_for("index"))
        
        # حساب تكلفة الوقت المفتوح بناءً على سعر الجهاز لكل ساعة
        rate_per_hour = devices[device_name]["rate_per_hour"]
        fixed_cost = rate_per_hour  # تكلفة الوقت المفتوح تساوي سعر الساعة
        
        start_time = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO invoices (device_name, customer_name, start_time, end_time, cost) VALUES (?, ?, ?, ?, ?)",
                  (device_name, customer_name, start_time, "وقت مفتوح", f"{fixed_cost:.2f} جنيه"))
        conn.commit()
        conn.close()

        devices[device_name]["start_time"] = time.time()
        devices[device_name]["customer_name"] = customer_name
        devices[device_name]["open_end"] = True

        flash(f"تم تفعيل الوقت المفتوح للجهاز {device_name} للعميل {customer_name}. التكلفة: {fixed_cost:.2f} جنيه", "warning")
    return redirect(url_for("index"))

# حذف الجهاز
@app.route("/delete_device/<device_name>", methods=["POST"])
@login_required
def delete_device(device_name):
    if device_name in devices:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("DELETE FROM devices WHERE name = ?", (device_name,))
        conn.commit()
        conn.close()
        del devices[device_name]
        flash(f"تم حذف الجهاز {device_name} بنجاح!", "success")
    else:
        flash(f"الجهاز {device_name} غير موجود!", "danger")
    return redirect(url_for("index"))

# صفحة التقارير
@app.route("/reports")
@login_required
def reports():
    # جلب البيانات من قاعدة البيانات
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM invoices")
    invoices = c.fetchall()
    conn.close()

    # تحسين تنسيق البيانات
    formatted_invoices = []
    for invoice in invoices:
        formatted_invoice = list(invoice)
        try:
            # تحسين تنسيق الوقت والتاريخ
            if formatted_invoice[3] and is_valid_datetime_format(formatted_invoice[3]):  # start_time
                formatted_invoice[3] = datetime.strptime(formatted_invoice[3], '%Y-%m-%d %H:%M:%S').strftime('%H:%M:%S %Y-%m-%d')
            else:
                formatted_invoice[3] = formatted_invoice[3] if formatted_invoice[3] else "غير معروف"
            
            if formatted_invoice[4] and is_valid_datetime_format(formatted_invoice[4]):  # end_time
                formatted_invoice[4] = datetime.strptime(formatted_invoice[4], '%Y-%m-%d %H:%M:%S').strftime('%H:%M:%S %Y-%m-%d')
            else:
                formatted_invoice[4] = formatted_invoice[4] if formatted_invoice[4] else "غير معروف"
        except Exception as e:
            # إذا حدث خطأ غير متوقع، نعرض القيمة كما هي
            formatted_invoice[3] = formatted_invoice[3] if formatted_invoice[3] else "غير معروف"
            formatted_invoice[4] = formatted_invoice[4] if formatted_invoice[4] else "غير معروف"
        
        # استبدال None بـ "غير معروف"
        formatted_invoice = [value if value is not None else "غير معروف" for value in formatted_invoice]
        formatted_invoices.append(formatted_invoice)

    return render_template("reports.html", invoices=formatted_invoices)

# صفحة إضافة جهاز جديد
@app.route("/add_device_page")
@login_required
def add_device_page():
    return render_template("add_device.html")

# إضافة جهاز جديد
@app.route("/add_device", methods=["POST"])
@login_required
def add_device():
    device_name = request.form.get("device_name")
    rate_per_hour = request.form.get("rate_per_hour")
    
    if not device_name or not rate_per_hour:
        flash("يرجى إدخال اسم الجهاز والسعر لكل ساعة!", "danger")
        return redirect(url_for("add_device_page"))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO devices (name, rate_per_hour) VALUES (?, ?)",
              (device_name, rate_per_hour))
    conn.commit()
    conn.close()
    
    devices[device_name] = {"rate_per_hour": float(rate_per_hour), "start_time": None, "end_time": None, "customer_name": None, "reserved_minutes": None, "open_end": False}
    
    flash(f"تم إضافة الجهاز {device_name} بنجاح!", "success")
    return redirect(url_for("index"))

# حذف فاتورة
@app.route("/delete_invoice/<int:invoice_id>", methods=["POST"])
@login_required
def delete_invoice(invoice_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
    conn.commit()
    conn.close()
    flash(f"تم حذف الفاتورة رقم {invoice_id} بنجاح!", "success")
    return redirect(url_for("reports"))

# حذف جميع الفواتير
@app.route("/delete_all_invoices", methods=["POST"])
@login_required
def delete_all_invoices():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM invoices")
    conn.commit()
    conn.close()
    flash("تم حذف جميع الفواتير بنجاح!", "success")
    return redirect(url_for("reports"))

# تحقق من تنسيق الوقت والتاريخ
def is_valid_datetime_format(datetime_str, format='%Y-%m-%d %H:%M:%S'):
    """تحقق من أن تنسيق الوقت والتاريخ صحيح."""
    try:
        datetime.strptime(datetime_str, format)
        return True
    except ValueError:
        return False

if __name__ == "__main__":
    app.run(debug=True)