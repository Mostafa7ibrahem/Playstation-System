from flask import Flask, request, render_template, redirect, url_for
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

# إنشاء جدول العملاء في قاعدة البيانات
def create_table():
    conn = sqlite3.connect('playstation.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS customers
                 (id INTEGER PRIMARY KEY, name TEXT, hours REAL, cost REAL, start_time TEXT, end_time TEXT, is_open_ended BOOLEAN)''')
    conn.commit()
    conn.close()

# إضافة عميل جديد إلى قاعدة البيانات
def add_customer(name, hours, cost, start_time, end_time, is_open_ended):
    conn = sqlite3.connect('playstation.db')
    c = conn.cursor()
    c.execute("INSERT INTO customers (name, hours, cost, start_time, end_time, is_open_ended) VALUES (?, ?, ?, ?, ?, ?)",
              (name, hours, cost, start_time, end_time, is_open_ended))
    conn.commit()
    conn.close()

# استرجاع جميع العملاء من قاعدة البيانات
def get_customers():
    conn = sqlite3.connect('playstation.db')
    c = conn.cursor()
    c.execute("SELECT * FROM customers")
    customers = c.fetchall()
    conn.close()
    return customers

# حساب إجمالي الأرباح اليومية
def get_daily_revenue():
    conn = sqlite3.connect('playstation.db')
    c = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute("SELECT SUM(cost) FROM customers WHERE DATE(start_time) = ?", (today,))
    daily_revenue = c.fetchone()[0] or 0
    conn.close()
    return daily_revenue

# إنهاء الوقت المفتوح وحساب التكلفة النهائية
@app.route('/end_session/<int:customer_id>')
def end_session(customer_id):
    conn = sqlite3.connect('playstation.db')
    c = conn.cursor()
    
    # استرجاع بيانات العميل
    c.execute("SELECT start_time, is_open_ended FROM customers WHERE id = ?", (customer_id,))
    customer = c.fetchone()
    
    if customer and customer[1]:  # إذا كان الوقت مفتوحًا
        start_time = datetime.strptime(customer[0], '%I:%M %p')
        end_time = datetime.now()
        time_diff = end_time - start_time  # حساب الفرق الزمني
        total_minutes = time_diff.total_seconds() / 60  # تحويل الفرق إلى دقائق
        hours = total_minutes // 60  # عدد الساعات
        minutes = total_minutes % 60  # عدد الدقائق
        
        rate_per_hour = 10  # سعر الساعة (10 جنيه للساعة)
        total_cost = (hours + (minutes / 60)) * rate_per_hour  # حساب التكلفة
        
        # تحويل وقت الانتهاء إلى تنسيق 12 ساعة
        end_time_formatted = end_time.strftime('%I:%M %p')
        
        # تحديث بيانات العميل
        c.execute("UPDATE customers SET hours = ?, cost = ?, end_time = ?, is_open_ended = ? WHERE id = ?",
                  (f"{int(hours)}:{int(minutes)}", total_cost, end_time_formatted, False, customer_id))
        conn.commit()
    
    conn.close()
    return redirect(url_for('home'))

# الصفحة الرئيسية
@app.route('/')
def home():
    create_table()  # تأكد من وجود الجدول
    customers = get_customers()
    daily_revenue = get_daily_revenue()
    today = datetime.now().strftime('%Y-%m-%d')  # تاريخ اليوم
    return render_template('index.html', customers=customers, daily_revenue=daily_revenue, today=today)

# حساب التكلفة وإضافة العميل
@app.route('/calculate', methods=['POST'])
def calculate():
    name = request.form['name']
    total_time = float(request.form['total_time'])  # الوقت الإجمالي (ساعات ودقائق معًا)
    date = request.form['date']  # تاريخ اليوم (يتم إرساله تلقائيًا)
    time = request.form['time']  # الوقت (يدخله المستخدم)
    is_open_ended = 'open_ended' in request.form  # تحقق إذا كان العميل اختار "وقت مفتوح"
    
    # دمج التاريخ والوقت في حقل واحد
    start_time = f"{date}T{time}"
    start_time_obj = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
    
    if is_open_ended:
        # إذا كان الوقت مفتوحًا، يتم تعيين وقت الانتهاء إلى "مفتوح" مؤقتًا
        end_time_formatted = "مفتوح"
        total_cost = 0  # التكلفة المؤقتة للوقت المفتوح
    else:
        # حساب وقت الانتهاء إذا لم يكن الوقت مفتوحًا
        end_time_obj = start_time_obj + timedelta(hours=total_time)
        end_time_formatted = end_time_obj.strftime('%I:%M %p')  # تنسيق 12 ساعة
        rate_per_hour = 10  # سعر الساعة (10 جنيه للساعة)
        total_cost = total_time * rate_per_hour  # حساب التكلفة
    
    # تحويل وقت البدء إلى تنسيق 12 ساعة
    start_time_formatted = start_time_obj.strftime('%I:%M %p')
    
    # إضافة العميل إلى قاعدة البيانات
    add_customer(name, f"{total_time} ساعات", total_cost, start_time_formatted, end_time_formatted, is_open_ended)
    
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)