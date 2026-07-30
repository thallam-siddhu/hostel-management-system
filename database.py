import sqlite3
from werkzeug.security import generate_password_hash

DATABASE = "hostel.db"

conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

# Enable foreign keys
cursor.execute("PRAGMA foreign_keys = ON")

# -----------------------------
# Colleges
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS colleges(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    college_name TEXT NOT NULL,
    college_code TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

# -----------------------------
# Blocks
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS blocks(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    college_code TEXT NOT NULL,
    block_name TEXT NOT NULL,

    FOREIGN KEY(college_code)
    REFERENCES colleges(college_code)
    ON DELETE CASCADE
)
""")

# -----------------------------
# Floors
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS floors(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_id INTEGER NOT NULL,
    floor_name TEXT NOT NULL,

    FOREIGN KEY(block_id)
    REFERENCES blocks(id)
    ON DELETE CASCADE
)
""")

# -----------------------------
# Rooms
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS rooms(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    floor_id INTEGER NOT NULL,
    room_no TEXT NOT NULL,
    capacity INTEGER NOT NULL,
    occupied INTEGER DEFAULT 0,

    FOREIGN KEY(floor_id)
    REFERENCES floors(id)
    ON DELETE CASCADE
)
""")

# -----------------------------
# Students
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS students(
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    college_code TEXT NOT NULL,

    register_no TEXT NOT NULL,

    student_name TEXT NOT NULL,

    department TEXT NOT NULL,

    year TEXT NOT NULL,

    gender TEXT NOT NULL,

    mobile TEXT NOT NULL,

    password TEXT NOT NULL,

    room_id INTEGER,

    FOREIGN KEY(college_code)
    REFERENCES colleges(college_code)
    ON DELETE CASCADE,

    FOREIGN KEY(room_id)
    REFERENCES rooms(id)
    ON DELETE SET NULL,

    UNIQUE(college_code, register_no)
)
""")

# -----------------------------
# Outing Requests
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS outing_requests(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    student_id INTEGER NOT NULL,

    outing_type TEXT NOT NULL,

    destination TEXT NOT NULL,

    reason TEXT NOT NULL,

    out_date TEXT NOT NULL,

    out_time TEXT NOT NULL,

    return_date TEXT NOT NULL,

    return_time TEXT NOT NULL,

    parent_mobile TEXT,

    status TEXT DEFAULT 'Pending',

    permission_id TEXT UNIQUE,

    exit_time TEXT,

    entry_time TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(student_id)
    REFERENCES students(id)
    ON DELETE CASCADE

)
""")

# -----------------------------
# Outing History
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS outing_history(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    outing_id INTEGER NOT NULL,

    student_id INTEGER NOT NULL,

    action TEXT NOT NULL,

    approved_by TEXT,

    approved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(outing_id)
    REFERENCES outing_requests(id)
    ON DELETE CASCADE,

    FOREIGN KEY(student_id)
    REFERENCES students(id)
    ON DELETE CASCADE

)
""")

# -----------------------------
# Complaints
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS complaints(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    student_id INTEGER NOT NULL,

    complaint_type TEXT NOT NULL,

    subject TEXT NOT NULL,

    description TEXT NOT NULL,

    status TEXT DEFAULT 'Pending',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(student_id)
    REFERENCES students(id)
    ON DELETE CASCADE

)
""")

# -----------------------------
# Hostel Notices
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS notices(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    college_code TEXT NOT NULL,

    title TEXT NOT NULL,

    message TEXT NOT NULL,

    notice_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(college_code)
    REFERENCES colleges(college_code)
    ON DELETE CASCADE

)
""")


# -----------------------------
# Room Change Requests
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS room_change_requests(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    student_id INTEGER NOT NULL,

    current_room_id INTEGER NOT NULL,

    requested_room_id INTEGER NOT NULL,

    reason TEXT NOT NULL,

    status TEXT DEFAULT 'Pending',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    approved_at TIMESTAMP,

    FOREIGN KEY(student_id)
    REFERENCES students(id)
    ON DELETE CASCADE,

    FOREIGN KEY(current_room_id)
    REFERENCES rooms(id),

    FOREIGN KEY(requested_room_id)
    REFERENCES rooms(id)

)
""")

# -----------------------------
# Security
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS security(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    college_code TEXT NOT NULL,

    security_name TEXT NOT NULL,

    username TEXT UNIQUE NOT NULL,

    mobile TEXT NOT NULL,

    password TEXT NOT NULL,

    FOREIGN KEY(college_code)
    REFERENCES colleges(college_code)
    ON DELETE CASCADE

)
""")

# -----------------------------
# Insert Default Admin College
# -----------------------------
cursor.execute("""
INSERT OR IGNORE INTO colleges
(
    college_name,
    college_code,
    password
)
VALUES (?, ?, ?)
""",
(
    "Demo College",
    "ADMIN001",
    generate_password_hash("12345")
))

# -----------------------------
# Insert Default Security User
# -----------------------------
cursor.execute("""
INSERT OR IGNORE INTO security
(
    college_code,
    security_name,
    username,
    mobile,
    password
)
VALUES (?, ?, ?, ?, ?)
""",
(
    "ADMIN001",
    "Main Security",
    "security",
    "9999999999",
    generate_password_hash("1234")
))


cursor.execute("""
CREATE TABLE IF NOT EXISTS promotion_history(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    college_code TEXT,
    from_year TEXT,
    to_year TEXT,
    promoted_count INTEGER,
    promoted_date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS promotion_history(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    college_code TEXT,
    from_year TEXT,
    to_year TEXT,
    promoted_count INTEGER,
    promoted_date TEXT
)
""")

# -----------------------------
# Mess Menu
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS mess_menu(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    college_code TEXT NOT NULL,
    day TEXT NOT NULL,
    breakfast TEXT NOT NULL,
    lunch TEXT NOT NULL,
    snacks TEXT NOT NULL,
    dinner TEXT NOT NULL
)
""")

# -----------------------------
# Food Feedback & Reviews
# -----------------------------

cursor.execute("""
DROP TABLE IF EXISTS food_feedback
""")


cursor.execute("""
CREATE TABLE food_feedback(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    college_code TEXT NOT NULL,

    student_id INTEGER NOT NULL,

    rating INTEGER NOT NULL,

    review TEXT NOT NULL,

    feedback_date TEXT NOT NULL

)
""")

conn.commit()
conn.close()

print("Database Created Successfully")