import sqlite3

# الاتصال بقاعدة البيانات
conn = sqlite3.connect('database.db')
c = conn.cursor()

# إضافة مستخدم جديد
username = "111"  # اسم المستخدم
password = "111"  # كلمة المرور
role = "admin"  # دور المستخدم (admin أو employee)

c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
          (username, password, role))

conn.commit()
conn.close()

print(f"تم إضافة المستخدم {username} بنجاح!")