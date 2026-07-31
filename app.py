from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = "hostel_secret_key"


# ===============================
# HOME
# ===============================
@app.route("/")
def home():
    return render_template("home.html")


# ===============================
# COLLEGE REGISTRATION
# ===============================
@app.route("/admin/register", methods=["GET", "POST"])
def admin_register():

    if request.method == "POST":

        college_name = request.form["college_name"].strip()
        college_code = request.form["college_code"].strip().upper()

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return "Passwords do not match."

        password = generate_password_hash(password)

        conn = sqlite3.connect("hostel.db")
        cursor = conn.cursor()

        try:

            cursor.execute("""
            INSERT INTO colleges
            (college_name, college_code, password)
            VALUES (?,?,?)
            """,
            (
                college_name,
                college_code,
                password
            ))

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()

            return "College Code already exists."

        conn.close()

        return redirect(url_for("admin_login"))

    return render_template("admin_register.html")


# ===============================
# COLLEGE LOGIN
# ===============================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        college_code = request.form["college_code"].strip().upper()
        password = request.form["password"]

        conn = sqlite3.connect("hostel.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT
            id,
            college_name,
            password
        FROM colleges
        WHERE college_code=?
        """, (college_code,))

        college = cursor.fetchone()

        conn.close()

        if college and check_password_hash(college[2], password):

            session["college_id"] = college[0]
            session["college_name"] = college[1]
            session["college_code"] = college_code

            return redirect(url_for("admin_dashboard"))

        return "Invalid College Code or Password."

    return render_template("admin_login.html")


# ===============================
# ADMIN DASHBOARD
# ===============================
@app.route("/admin/dashboard")
def admin_dashboard():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    college_code = session["college_code"]

    # -----------------------------
    # Pending Complaints
    # -----------------------------
    cursor.execute("""
    SELECT COUNT(*)
    FROM complaints
    JOIN students
    ON complaints.student_id = students.id
    WHERE students.college_code=?
    AND complaints.status='Pending'
    """, (college_code,))

    pending_complaints = cursor.fetchone()[0]

    # -----------------------------
    # Pending Outing Requests
    # -----------------------------
    cursor.execute("""
    SELECT COUNT(*)
    FROM outing_requests
    JOIN students
    ON outing_requests.student_id = students.id
    WHERE students.college_code=?
    AND outing_requests.status='Pending'
    """, (college_code,))

    pending_outings = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        college_name=session["college_name"],
        pending_complaints=pending_complaints,
        pending_outings=pending_outings
    )
# ===============================
# ADD STUDENT
# ===============================
@app.route("/admin/add_student", methods=["GET", "POST"])
def add_student():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    if request.method == "POST":

        register_no = request.form["register_no"].strip()
        student_name = request.form["student_name"]
        department = request.form["department"]
        year = request.form["year"]
        gender = request.form["gender"]
        mobile = request.form["mobile"]
        password = generate_password_hash(request.form["password"])
        room_id = request.form["room_id"]

        # -------------------------------
        # Check duplicate register number
        # -------------------------------
        cursor.execute("""
            SELECT id
            FROM students
            WHERE college_code=? AND register_no=?
        """, (session["college_code"], register_no))

        if cursor.fetchone():
            conn.close()
            return """
            <script>
                alert("Register Number already exists!");
                window.location="/admin/add_student";
            </script>
            """

        # -------------------------------
        # Check Room Capacity
        # -------------------------------
        cursor.execute("""
            SELECT capacity, occupied
            FROM rooms
            WHERE id=?
        """, (room_id,))

        room = cursor.fetchone()

        if room is None:
            conn.close()
            return "Invalid Room."

        capacity, occupied = room

        if occupied >= capacity:
            conn.close()
            return """
            <script>
                alert("Room is Full!");
                window.location="/admin/add_student";
            </script>
            """

        # -------------------------------
        # Insert Student
        # -------------------------------
        cursor.execute("""
            INSERT INTO students
            (
                college_code,
                register_no,
                student_name,
                department,
                year,
                gender,
                mobile,
                password,
                room_id
            )
            VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            session["college_code"],
            register_no,
            student_name,
            department,
            year,
            gender,
            mobile,
            password,
            room_id
        ))

        # -------------------------------
        # Update Room Occupancy
        # -------------------------------
        cursor.execute("""
            UPDATE rooms
            SET occupied = occupied + 1
            WHERE id=?
        """, (room_id,))

        conn.commit()
        conn.close()

        return redirect(url_for("view_students"))

    # Load Blocks
    cursor.execute("""
        SELECT id, block_name
        FROM blocks
        WHERE college_code=?
        ORDER BY block_name
    """, (session["college_code"],))

    blocks = cursor.fetchall()

    conn.close()

    return render_template(
        "add_student.html",
        blocks=blocks
    )

# ===============================
# VIEW STUDENTS
# ===============================
@app.route("/admin/students")
def view_students():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""

    SELECT

    students.register_no,
    students.student_name,
    students.department,
    students.year,
    students.gender,
    students.mobile,

    blocks.block_name,
    floors.floor_name,
    rooms.room_no,

    students.id

    FROM students

    JOIN rooms
    ON students.room_id = rooms.id

    JOIN floors
    ON rooms.floor_id = floors.id

    JOIN blocks
    ON floors.block_id = blocks.id

    WHERE students.college_code=?

    ORDER BY students.register_no

    """, (session["college_code"],))

    students = cursor.fetchall()

    conn.close()

    return render_template(
        "students.html",
        students=students
    )


# ===============================
# GET FLOORS (AJAX)
# ===============================
@app.route("/get_floors/<int:block_id>")
def get_floors(block_id):

    if "college_id" not in session:
        return jsonify([])

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, floor_name
    FROM floors
    WHERE block_id=?
    ORDER BY floor_name
    """, (block_id,))

    floors = cursor.fetchall()

    conn.close()

    return jsonify(floors)


# ===============================
# GET ROOMS (AJAX)
# ===============================
@app.route("/get_rooms/<int:floor_id>")
def get_rooms(floor_id):

    if "college_id" not in session:
        return jsonify([])

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        room_no,
        capacity,
        occupied
    FROM rooms
    WHERE floor_id=?
    ORDER BY room_no
    """, (floor_id,))

    rooms = cursor.fetchall()

    conn.close()

    return jsonify(rooms)

# ===============================
# STUDENT LOGIN
# ===============================
@app.route("/student/login", methods=["GET", "POST"])
def student_login():

    if request.method == "POST":

        register_no = request.form["register_no"].strip().upper()
        password = request.form["password"]

        conn = sqlite3.connect("hostel.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT
            id,
            student_name,
            password
        FROM students
        WHERE register_no=?
        """, (register_no,))

        student = cursor.fetchone()

        conn.close()

        if student and check_password_hash(student[2], password):

            session["student_id"] = student[0]
            session["student_name"] = student[1]
            session["register_no"] = register_no

            return redirect(url_for("student_dashboard"))

        return "Invalid Register Number or Password."

    return render_template("student_login.html")


# ===============================
# STUDENT DASHBOARD
# ===============================
@app.route("/student/dashboard")
def student_dashboard():

    if "student_id" not in session:
        return redirect(url_for("student_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    student_id = session["student_id"]

    # Latest approved outing
    cursor.execute("""
        SELECT id
        FROM outing_requests
        WHERE student_id=?
        AND status='Approved'
        ORDER BY id DESC
        LIMIT 1
    """, (student_id,))

    row = cursor.fetchone()

    approved_outing = row[0] if row else None

    # Permission ID
    permission_id = approved_outing

    # Count pending requests
    cursor.execute("""
        SELECT COUNT(*)
        FROM outing_requests
        WHERE student_id=?
        AND status='Pending'
    """, (student_id,))

    pending = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "student_dashboard.html",
        student_name=session["student_name"],
        approved_outing=approved_outing,
        pending=pending,
        permission_id=permission_id
    )
@app.route("/student/outing")
def student_outing():

    if "student_id" not in session:
        return redirect(url_for("student_login"))

    return render_template("student_outing.html")

# ===============================
# ADD ROOM
# ===============================
@app.route("/admin/add_room", methods=["GET", "POST"])
def add_room():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    if request.method == "POST":

        floor_id = request.form["floor_id"]
        room_no = request.form["room_no"]
        capacity = request.form["capacity"]

        cursor.execute("""
        INSERT INTO rooms
        (
            floor_id,
            room_no,
            capacity,
            occupied
        )
        VALUES (?,?,?,0)
        """,
        (
            floor_id,
            room_no,
            capacity
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("view_rooms"))

    # Load only Blocks
    cursor.execute("""
    SELECT id, block_name
    FROM blocks
    WHERE college_code=?
    ORDER BY block_name
    """, (session["college_code"],))

    blocks = cursor.fetchall()

    conn.close()

    return render_template(
        "add_room.html",
        blocks=blocks
    )

# ===============================
# ROOM MANAGEMENT
# ===============================
@app.route("/admin/room_management")
def room_management():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    return render_template("room_management.html")


# ===============================
# VIEW ROOMS
# ===============================
@app.route("/admin/rooms")
def view_rooms():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        blocks.block_name,
        floors.floor_name,
        rooms.room_no,
        rooms.capacity,
        rooms.occupied,
        rooms.id
    FROM rooms

    JOIN floors
        ON rooms.floor_id = floors.id

    JOIN blocks
        ON floors.block_id = blocks.id

    WHERE blocks.college_code = ?

    ORDER BY
        blocks.block_name,
        floors.floor_name,
        rooms.room_no
    """, (session["college_code"],))

    rooms = cursor.fetchall()

    conn.close()

    return render_template("rooms.html", rooms=rooms)

# ===============================
# ASSIGN ROOM
# ===============================
@app.route("/admin/assign_room/<register_no>", methods=["GET","POST"])
def assign_room(register_no):

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn=sqlite3.connect("hostel.db")
    cursor=conn.cursor()

    if request.method=="POST":

        room_id=request.form["room_id"]

        cursor.execute("""
        SELECT capacity,occupied
        FROM rooms
        WHERE id=?
        """,(room_id,))

        room=cursor.fetchone()

        if room[1] >= room[0]:

            conn.close()

            return "Room is Full."

        cursor.execute("""
        UPDATE students
        SET room_id=?
        WHERE register_no=?
        """,

        (
            room_id,
            register_no
        ))

        cursor.execute("""
        UPDATE rooms
        SET occupied=occupied+1
        WHERE id=?
        """,(room_id,))

        conn.commit()
        conn.close()

        return redirect(url_for("view_students"))

    cursor.execute("""

    SELECT

    rooms.id,

    blocks.block_name,

    floors.floor_name,

    rooms.room_no

    FROM rooms

    JOIN floors
    ON rooms.floor_id=floors.id

    JOIN blocks
    ON floors.block_id=blocks.id

    WHERE

    blocks.college_code=?

    AND

    rooms.occupied < rooms.capacity

    ORDER BY
    blocks.block_name,
    floors.floor_name,
    rooms.room_no

    """,

    (session["college_code"],))

    rooms=cursor.fetchall()

    conn.close()

    return render_template(
        "assign_room.html",
        rooms=rooms,
        register_no=register_no
    )


# ===============================
# EDIT FLOOR
# ===============================
@app.route("/admin/edit_floor/<int:floor_id>", methods=["GET","POST"])
def edit_floor(floor_id):

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn=sqlite3.connect("hostel.db")
    cursor=conn.cursor()

    if request.method=="POST":

        floor_name=request.form["floor_name"]

        cursor.execute("""
        UPDATE floors
        SET floor_name=?
        WHERE id=?
        """,

        (
            floor_name,
            floor_id
        ))

        conn.commit()

        conn.close()

        return redirect(url_for("view_floors"))

    cursor.execute("""
    SELECT
    id,
    floor_name
    FROM floors
    WHERE id=?
    """,

    (floor_id,))

    floor=cursor.fetchone()

    conn.close()

    return render_template(
        "edit_floor.html",
        floor=floor
    )


# ===============================
# DELETE FLOOR
# ===============================
@app.route("/admin/delete_floor/<int:floor_id>")
def delete_floor(floor_id):

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn=sqlite3.connect("hostel.db")
    cursor=conn.cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM rooms
    WHERE floor_id=?
    """,(floor_id,))

    count=cursor.fetchone()[0]

    if count>0:

        conn.close()

        return "Cannot delete this floor because rooms exist."

    cursor.execute("""
    DELETE FROM floors
    WHERE id=?
    """,(floor_id,))

    conn.commit()

    conn.close()

    return redirect(url_for("view_floors"))
# ===============================
# ADD BLOCK
# ===============================
@app.route("/admin/add_block", methods=["GET", "POST"])
def add_block():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    if request.method == "POST":

        block_name = request.form["block_name"].strip().upper()

        conn = sqlite3.connect("hostel.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO blocks
        (college_code, block_name)
        VALUES (?, ?)
        """,
        (
            session["college_code"],
            block_name
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("view_blocks"))

    return render_template("add_block.html")


# ===============================
# VIEW FLOORS
# ===============================
@app.route("/admin/floors")
def view_floors():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        floors.id,
        blocks.block_name,
        floors.floor_name
    FROM floors
    JOIN blocks
    ON floors.block_id = blocks.id
    WHERE blocks.college_code=?
    ORDER BY
        blocks.block_name,
        floors.floor_name
    """, (session["college_code"],))

    floors = cursor.fetchall()

    conn.close()

    return render_template(
        "floors.html",
        floors=floors
    )


# ===============================
# ADD FLOOR
# ===============================
@app.route("/admin/add_floor", methods=["GET", "POST"])
def add_floor():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    if request.method == "POST":

        block_id = request.form["block_id"]
        floor_name = request.form["floor_name"]

        cursor.execute("""
        INSERT INTO floors
        (block_id, floor_name)
        VALUES (?, ?)
        """,
        (
            block_id,
            floor_name
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("view_floors"))

    cursor.execute("""
    SELECT
        id,
        block_name
    FROM blocks
    WHERE college_code=?
    ORDER BY block_name
    """, (session["college_code"],))

    blocks = cursor.fetchall()

    conn.close()

    return render_template(
        "add_floor.html",
        blocks=blocks
    )


# ===============================
# EDIT BLOCK
# ===============================
@app.route("/admin/edit_block/<int:block_id>", methods=["GET", "POST"])
def edit_block(block_id):

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    if request.method == "POST":

        block_name = request.form["block_name"]

        cursor.execute("""
        UPDATE blocks
        SET block_name=?
        WHERE id=?
        """,
        (
            block_name,
            block_id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("view_blocks"))

    cursor.execute("""
    SELECT
        id,
        block_name
    FROM blocks
    WHERE id=?
    """, (block_id,))

    block = cursor.fetchone()

    conn.close()

    return render_template(
        "edit_block.html",
        block=block
    )


# ===============================
# DELETE BLOCK
# ===============================
@app.route("/admin/delete_block/<int:block_id>")
def delete_block(block_id):

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM floors
    WHERE block_id=?
    """, (block_id,))

    count = cursor.fetchone()[0]

    if count > 0:
        conn.close()
        return "Cannot delete this block because it contains floors."

    cursor.execute("""
    DELETE FROM blocks
    WHERE id=?
    """, (block_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("view_blocks"))

@app.route("/admin/blocks")
def view_blocks():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, block_name
    FROM blocks
    WHERE college_code=?
    ORDER BY block_name
    """, (session["college_code"],))

    blocks = cursor.fetchall()

    conn.close()

    return render_template("blocks.html", blocks=blocks)

from datetime import datetime

@app.route("/student/apply_outing", methods=["POST"])
def apply_outing():

    if "student_id" not in session:
        return redirect(url_for("student_login"))

    outing_type = request.form["outing_type"]
    destination = request.form["destination"]
    reason = request.form["reason"]
    out_date = request.form["out_date"]
    out_time = request.form["out_time"]
    return_date = request.form["return_date"]
    return_time = request.form["return_time"]
    parent_mobile = request.form["parent_mobile"]

    # -----------------------------
    # Date Validation
    # -----------------------------
    today = datetime.today().date()

    out_date_obj = datetime.strptime(out_date, "%Y-%m-%d").date()
    return_date_obj = datetime.strptime(return_date, "%Y-%m-%d").date()

    if out_date_obj < today:
        return "❌ Out Date cannot be before today."

    if return_date_obj < out_date_obj:
        return "❌ Return Date cannot be earlier than Out Date."

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    # -----------------------------
    # Maximum 3 Requests Per Day
    # -----------------------------
    cursor.execute("""
    SELECT COUNT(*)
    FROM outing_requests
    WHERE student_id=?
    AND out_date=?
    """, (
        session["student_id"],
        out_date
    ))

    today_count = cursor.fetchone()[0]

    if today_count >= 3:
        conn.close()
        return "❌ You can apply only 3 outing requests for the same day."

    # -----------------------------
    # Prevent Duplicate Request
    # -----------------------------
    cursor.execute("""
    SELECT id
    FROM outing_requests
    WHERE student_id=?
    AND out_date=?
    AND out_time=?
    """, (
        session["student_id"],
        out_date,
        out_time
    ))

    if cursor.fetchone():
        conn.close()
        return "❌ You already have an outing request for this date and time."

    # -----------------------------
    # Insert Outing Request
    # -----------------------------
    cursor.execute("""
    INSERT INTO outing_requests
    (
        student_id,
        outing_type,
        destination,
        reason,
        out_date,
        out_time,
        return_date,
        return_time,
        parent_mobile
    )
    VALUES
    (
        ?,?,?,?,?,?,?,?,?
    )
    """, (
        session["student_id"],
        outing_type,
        destination,
        reason,
        out_date,
        out_time,
        return_date,
        return_time,
        parent_mobile
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("student_outing_history"))

@app.route("/student/outing_history")
def student_outing_history():

    if "student_id" not in session:
        return redirect(url_for("student_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        outing_type,
        destination,
        out_date,
        return_date,
        status,
        permission_id
    FROM outing_requests
    WHERE student_id=?
    ORDER BY id DESC
    """, (session["student_id"],))

    outings = cursor.fetchall()

    conn.close()

    return render_template(
        "outing_history.html",
        outings=outings
    )

@app.route("/admin/outing_requests")
def admin_outing_requests():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        outing_requests.id,
        students.register_no,
        students.student_name,
        outing_requests.outing_type,
        outing_requests.destination,
        outing_requests.reason,
        outing_requests.out_date,
        outing_requests.return_date,
        outing_requests.status

    FROM outing_requests

    JOIN students
        ON outing_requests.student_id = students.id

    WHERE students.college_code=?

    ORDER BY outing_requests.id DESC
    """, (session["college_code"],))

    requests = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_outing_requests.html",
        requests=requests
    )
@app.route("/admin/reject_outing/<int:outing_id>")
def reject_outing(outing_id):

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE outing_requests
    SET status='Rejected'
    WHERE id=?
    """,
    (outing_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_outing_requests"))


@app.route("/student/gate_pass/<int:outing_id>")
def student_gate_pass(outing_id):

    if "student_id" not in session:
        return redirect(url_for("student_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        c.college_name,
        s.student_name,
        s.register_no,
        s.department,
        s.year,
        b.block_name,
        f.floor_name,
        r.room_no,
        o.outing_type,
        o.destination,
        o.reason,
        o.out_date,
        o.out_time,
        o.return_date,
        o.return_time,
        o.status,
        o.qr_code

    FROM outing_requests o

    JOIN students s
        ON o.student_id = s.id

    JOIN rooms r
        ON s.room_id = r.id

    JOIN floors f
        ON r.floor_id = f.id

    JOIN blocks b
        ON f.block_id = b.id

    JOIN colleges c
        ON c.college_code = s.college_code

    WHERE o.id=?
    AND s.id=?
    """, (outing_id, session["student_id"]))

    gatepass = cursor.fetchone()

    conn.close()

    if gatepass is None:
        return "Gate Pass not found."

    if gatepass[15] != "Approved":
        return "Gate Pass is not approved yet."

    return render_template(
        "student_gate_pass.html",
        gatepass=gatepass
    )


import random

@app.route("/admin/approve_outing/<int:outing_id>")
def approve_outing(outing_id):

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    # Generate Permission ID
    permission_id = "PASS" + str(random.randint(100000, 999999))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE outing_requests
    SET
        status=?,
        permission_id=?
    WHERE id=?
    """,
    (
        "Approved",
        permission_id,
        outing_id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_outing_requests"))

@app.route("/security/scan", methods=["GET", "POST"])
def security_scan():

    if "security_id" not in session:
        return redirect(url_for("security_login"))

    if request.method == "POST":

        qr = request.form["qr_code"]

        conn = sqlite3.connect("hostel.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT
            students.student_name,
            students.register_no,
            outing_requests.outing_type,
            outing_requests.destination,
            outing_requests.status
        FROM outing_requests
        JOIN students
            ON outing_requests.student_id = students.id
        WHERE outing_requests.qr_code = ?
        """, (qr,))

        result = cursor.fetchone()

        conn.close()

        return render_template(
            "verify_pass.html",
            result=result
        )

    return render_template("security_scan.html")


@app.route("/student/complaints")
def student_complaints():

    if "student_id" not in session:
        return redirect(url_for("student_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        complaint_type,
        subject,
        status,
        created_at
    FROM complaints
    WHERE student_id=?
    ORDER BY id DESC
    """, (session["student_id"],))

    complaints = cursor.fetchall()

    conn.close()

    return render_template(
        "student_complaints.html",
        complaints=complaints
    )

@app.route("/student/add_complaint", methods=["GET", "POST"])
def add_complaint():

    if "student_id" not in session:
        return redirect(url_for("student_login"))

    if request.method == "POST":

        complaint_type = request.form["complaint_type"]
        subject = request.form["subject"]
        description = request.form["description"]

        conn = sqlite3.connect("hostel.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO complaints
        (
            student_id,
            complaint_type,
            subject,
            description
        )
        VALUES(?,?,?,?)
        """,
        (
            session["student_id"],
            complaint_type,
            subject,
            description
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("student_complaints"))

    return render_template("add_complaint.html")

@app.route("/admin/complaints")
def admin_complaints():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT

    complaints.id,

    students.register_no,

    students.student_name,

    complaints.complaint_type,

    complaints.subject,

    complaints.status,

    complaints.created_at

    FROM complaints

    JOIN students
    ON complaints.student_id = students.id

    WHERE students.college_code=?

    ORDER BY complaints.id DESC
    """, (session["college_code"],))

    complaints = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_complaints.html",
        complaints=complaints
    )
@app.route("/security/login", methods=["GET", "POST"])
def security_login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        conn = sqlite3.connect("hostel.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM security
            WHERE username=?
        """, (username,))

        security = cursor.fetchone()

        conn.close()


        if security:

            if check_password_hash(security["password"], password):

                session["security_id"] = security["id"]
                session["security_username"] = security["username"]

                # IMPORTANT
                session["college_code"] = security["college_code"]

                return redirect(url_for("security_dashboard"))


        return "Invalid Username or Password."


    return render_template("security_login.html")
@app.route("/security/dashboard")
def security_dashboard():

    if "security_id" not in session:
        return redirect(url_for("security_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    # Total students currently OUT
    cursor.execute("""
    SELECT COUNT(*)
    FROM outing_requests
    WHERE status='Approved'
    """)
    total_out = cursor.fetchone()[0]

    # Pending outing requests
    cursor.execute("""
    SELECT COUNT(*)
    FROM outing_requests
    WHERE status='Pending'
    """)
    pending_requests = cursor.fetchone()[0]

    # Rejected outing requests
    cursor.execute("""
    SELECT COUNT(*)
    FROM outing_requests
    WHERE status='Rejected'
    """)
    rejected_requests = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "security_dashboard.html",
        security_username=session["security_username"],
        total_out=total_out,
        pending_requests=pending_requests,
        rejected_requests=rejected_requests
    )


@app.route("/admin/add_security", methods=["GET", "POST"])
def add_security():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    if request.method == "POST":

        security_name = request.form["security_name"]
        username = request.form["username"]
        mobile = request.form["mobile"]
        password = generate_password_hash(request.form["password"])

        conn = sqlite3.connect("hostel.db")
        cursor = conn.cursor()

        # Get the logged-in admin's college code
        cursor.execute("""
        SELECT college_code
        FROM colleges
        WHERE id=?
        """, (session["college_id"],))

        college_code = cursor.fetchone()[0]

        # Insert security user
        cursor.execute("""
        INSERT INTO security
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
            college_code,
            security_name,
            username,
            mobile,
            password
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("view_security"))

    return render_template("add_security.html")

@app.route("/admin/security")
def view_security():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        security_name,
        username,
        mobile
    FROM security
    ORDER BY security_name
    """)

    security = cursor.fetchall()

    conn.close()

    return render_template(
        "security.html",
        security=security
    )


@app.route("/admin/edit_security/<int:security_id>", methods=["GET", "POST"])
def edit_security(security_id):

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    if request.method == "POST":

        security_name = request.form["security_name"]
        username = request.form["username"]
        mobile = request.form["mobile"]

        password = request.form["password"]

        if password == "":

            cursor.execute("""
            UPDATE security
            SET
                security_name=?,
                username=?,
                mobile=?
            WHERE id=?
            """,
            (
                security_name,
                username,
                mobile,
                security_id
            ))

        else:

            password = generate_password_hash(password)

            cursor.execute("""
            UPDATE security
            SET
                security_name=?,
                username=?,
                mobile=?,
                password=?
            WHERE id=?
            """,
            (
                security_name,
                username,
                mobile,
                password,
                security_id
            ))

        conn.commit()
        conn.close()

        return redirect(url_for("view_security"))

    cursor.execute("""
    SELECT
        id,
        security_name,
        username,
        mobile
    FROM security
    WHERE id=?
    """, (security_id,))

    security = cursor.fetchone()

    conn.close()

    return render_template(
        "edit_security.html",
        security=security
    )

@app.route("/admin/delete_security/<int:security_id>")
def delete_security(security_id):

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM security
    WHERE id=?
    """, (security_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("view_security"))




@app.route("/security/student_out/<int:outing_id>")
def student_out(outing_id):

    if "security_id" not in session:
        return redirect(url_for("security_login"))

    exit_time = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE outing_requests
    SET
        status='Out',
        exit_time=?
    WHERE id=?
    """,
    (
        exit_time,
        outing_id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("security_dashboard"))
    


@app.route("/security/student_in/<int:outing_id>")
def student_in(outing_id):

    if "security_id" not in session:
        return redirect(url_for("security_login"))

    entry_time = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE outing_requests
    SET
        status='Completed',
        entry_time=?
    WHERE id=?
    """,
    (
        entry_time,
        outing_id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("security_dashboard"))

@app.route("/security/verify_permission", methods=["GET", "POST"])
def verify_permission():

    if "security_id" not in session:
        return redirect(url_for("security_login"))

    if request.method == "POST":

        permission_id = request.form["permission_id"].strip()

        conn = sqlite3.connect("hostel.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT

            outing_requests.id,
            students.student_name,
            students.register_no,
            outing_requests.outing_type,
            outing_requests.destination,
            outing_requests.reason,
            outing_requests.out_date,
            outing_requests.out_time,
            outing_requests.return_date,
            outing_requests.return_time,
            outing_requests.status,
            outing_requests.permission_id

        FROM outing_requests

        JOIN students
        ON outing_requests.student_id = students.id

        WHERE outing_requests.permission_id=?

        """, (permission_id,))

        outing = cursor.fetchone()

        conn.close()

        if outing is None:
            return "Invalid Permission ID"

        return render_template(
            "verify_permission.html",
            outing=outing
        )

    return render_template("search_permission.html")

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


@app.route("/admin/rooms")
def manage_rooms():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        rooms.id,
        rooms.room_no,
        blocks.block_name,
        floors.floor_name,
        rooms.capacity,
        rooms.occupied

    FROM rooms

    JOIN floors
    ON rooms.floor_id=floors.id

    JOIN blocks
    ON floors.block_id=blocks.id

    ORDER BY blocks.block_name,floors.floor_name,rooms.room_no
    """)

    rooms = cursor.fetchall()

    conn.close()

    return render_template(
        "manage_rooms.html",
        rooms=rooms
    )


@app.route("/admin/edit_room/<int:room_id>", methods=["GET","POST"])
def edit_room(room_id):

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    if request.method == "POST":

        room_no = request.form["room_no"]
        capacity = request.form["capacity"]

        cursor.execute("""
        UPDATE rooms
        SET
            room_no=?,
            capacity=?
        WHERE id=?
        """,
        (
            room_no,
            capacity,
            room_id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("manage_rooms"))

    cursor.execute("""
    SELECT
        id,
        room_no,
        capacity
    FROM rooms
    WHERE id=?
    """,(room_id,))

    room = cursor.fetchone()

    conn.close()

    return render_template(
        "edit_room.html",
        room=room
    )



@app.route("/admin/delete_room/<int:room_id>")
def delete_room(room_id):

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM rooms
    WHERE id=?
    """,(room_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("manage_rooms"))

@app.route("/admin/reports")
def admin_reports():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    college_code = session["college_code"]

    # Total Students
    cursor.execute("""
    SELECT COUNT(*)
    FROM students
    WHERE college_code=?
    """, (college_code,))
    total_students = cursor.fetchone()[0]

    # Total Boys
    cursor.execute("""
    SELECT COUNT(*)
    FROM students
    WHERE college_code=? AND gender='Male'
    """, (college_code,))
    total_boys = cursor.fetchone()[0]

    # Total Girls
    cursor.execute("""
    SELECT COUNT(*)
    FROM students
    WHERE college_code=? AND gender='Female'
    """, (college_code,))
    total_girls = cursor.fetchone()[0]

    # Total Blocks
    cursor.execute("""
    SELECT COUNT(*)
    FROM blocks
    WHERE college_code=?
    """, (college_code,))
    total_blocks = cursor.fetchone()[0]

    # Total Floors
    cursor.execute("""
    SELECT COUNT(*)
    FROM floors
    JOIN blocks
    ON floors.block_id=blocks.id
    WHERE blocks.college_code=?
    """, (college_code,))
    total_floors = cursor.fetchone()[0]

    # Total Rooms
    cursor.execute("""
    SELECT COUNT(*)
    FROM rooms
    JOIN floors
    ON rooms.floor_id=floors.id
    JOIN blocks
    ON floors.block_id=blocks.id
    WHERE blocks.college_code=?
    """, (college_code,))
    total_rooms = cursor.fetchone()[0]

    # Total Capacity
    cursor.execute("""
    SELECT IFNULL(SUM(capacity),0)
    FROM rooms
    JOIN floors
    ON rooms.floor_id=floors.id
    JOIN blocks
    ON floors.block_id=blocks.id
    WHERE blocks.college_code=?
    """, (college_code,))
    total_capacity = cursor.fetchone()[0]

    # Occupied Beds
    cursor.execute("""
    SELECT IFNULL(SUM(occupied),0)
    FROM rooms
    JOIN floors
    ON rooms.floor_id=floors.id
    JOIN blocks
    ON floors.block_id=blocks.id
    WHERE blocks.college_code=?
    """, (college_code,))
    occupied_beds = cursor.fetchone()[0]

    vacant_beds = total_capacity - occupied_beds

    # Pending Complaints
    cursor.execute("""
    SELECT COUNT(*)
    FROM complaints
    JOIN students
    ON complaints.student_id=students.id
    WHERE students.college_code=?
    AND complaints.status='Pending'
    """, (college_code,))
    pending_complaints = cursor.fetchone()[0]

    # Pending Outings
    cursor.execute("""
    SELECT COUNT(*)
    FROM outing_requests
    JOIN students
    ON outing_requests.student_id=students.id
    WHERE students.college_code=?
    AND outing_requests.status='Pending'
    """, (college_code,))
    pending_outings = cursor.fetchone()[0]

    # Students Currently Out
    cursor.execute("""
    SELECT COUNT(*)
    FROM outing_requests
    JOIN students
    ON outing_requests.student_id=students.id
    WHERE students.college_code=?
    AND outing_requests.status='Out'
    """, (college_code,))
    students_out = cursor.fetchone()[0]

    # Security Staff
    cursor.execute("""
    SELECT COUNT(*)
    FROM security
    WHERE college_code=?
    """, (college_code,))
    total_security = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "reports.html",
        total_students=total_students,
        total_boys=total_boys,
        total_girls=total_girls,
        total_blocks=total_blocks,
        total_floors=total_floors,
        total_rooms=total_rooms,
        total_capacity=total_capacity,
        occupied_beds=occupied_beds,
        vacant_beds=vacant_beds,
        students_out=students_out,
        pending_outings=pending_outings,
        pending_complaints=pending_complaints,
        total_security=total_security
    )

@app.route("/admin/student_report")
def student_report():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT

        students.register_no,
        students.student_name,
        students.department,
        students.year,
        students.gender,
        rooms.room_no,
        blocks.block_name

    FROM students

    LEFT JOIN rooms
    ON students.room_id = rooms.id

    LEFT JOIN floors
    ON rooms.floor_id = floors.id

    LEFT JOIN blocks
    ON floors.block_id = blocks.id

    WHERE students.college_code=?

    ORDER BY students.student_name
    """, (session["college_code"],))

    students = cursor.fetchall()

    conn.close()

    return render_template(
        "student_report.html",
        students=students
    )

@app.route("/admin/room_report")
def room_report():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT

        blocks.block_name,
        floors.floor_name,
        rooms.room_no,
        rooms.capacity,
        rooms.occupied,
        (rooms.capacity - rooms.occupied) AS vacant

    FROM rooms

    JOIN floors
    ON rooms.floor_id = floors.id

    JOIN blocks
    ON floors.block_id = blocks.id

    WHERE blocks.college_code=?

    ORDER BY
        blocks.block_name,
        floors.floor_name,
        rooms.room_no
    """, (session["college_code"],))

    rooms = cursor.fetchall()

    conn.close()

    return render_template(
        "room_report.html",
        rooms=rooms
    )

@app.route("/admin/outing_report")
def outing_report():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT

        students.register_no,
        students.student_name,

        outing_requests.outing_type,
        outing_requests.destination,

        outing_requests.out_date,
        outing_requests.return_date,

        outing_requests.permission_id,

        outing_requests.status,

        outing_requests.exit_time,
        outing_requests.entry_time

    FROM outing_requests

    JOIN students
    ON outing_requests.student_id = students.id

    WHERE students.college_code=?

    ORDER BY outing_requests.id DESC
    """, (session["college_code"],))

    outings = cursor.fetchall()

    conn.close()

    return render_template(
        "outing_report.html",
        outings=outings
    )


@app.route("/admin/complaint_report")
def complaint_report():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT

        students.register_no,
        students.student_name,

        complaints.complaint_type,
        complaints.subject,
        complaints.description,

        complaints.status,
        complaints.created_at

    FROM complaints

    JOIN students
    ON complaints.student_id = students.id

    WHERE students.college_code=?

    ORDER BY complaints.id DESC
    """, (session["college_code"],))

    complaints = cursor.fetchall()

    conn.close()

    return render_template(
        "complaint_report.html",
        complaints=complaints
    )


@app.route("/student/profile")
def student_profile():

    if "student_id" not in session:
        return redirect(url_for("student_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT

        register_no,
        student_name,
        department,
        year,
        gender,
        mobile,
        room_id

    FROM students

    WHERE id=?

    """, (session["student_id"],))

    student = cursor.fetchone()

    room_no = "-"

    if student and student[6]:

        cursor.execute("""
        SELECT room_no
        FROM rooms
        WHERE id=?
        """, (student[6],))

        room = cursor.fetchone()

        if room:
            room_no = room[0]

    conn.close()

    return render_template(
        "student_profile.html",
        student=student,
        room_no=room_no
    )

@app.route("/student/room_details")
def student_room_details():

    if "student_id" not in session:
        return redirect(url_for("student_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT

        students.student_name,
        rooms.room_no,
        rooms.capacity,
        rooms.occupied,
        floors.floor_name,
        blocks.block_name

    FROM students

    LEFT JOIN rooms
    ON students.room_id = rooms.id

    LEFT JOIN floors
    ON rooms.floor_id = floors.id

    LEFT JOIN blocks
    ON floors.block_id = blocks.id

    WHERE students.id=?

    """, (session["student_id"],))

    room = cursor.fetchone()

    conn.close()

    return render_template(
        "room_details.html",
        room=room
    )

@app.route("/student/roommates")
def student_roommates():

    if "student_id" not in session:
        return redirect(url_for("student_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    # Get current student's room
    cursor.execute("""
    SELECT room_id
    FROM students
    WHERE id=?
    """, (session["student_id"],))

    result = cursor.fetchone()

    if not result or result[0] is None:
        conn.close()
        return render_template("roommates.html", roommates=[])

    room_id = result[0]

    # Get all students in the same room
    cursor.execute("""
    SELECT
        register_no,
        student_name,
        department,
        year,
        mobile
    FROM students
    WHERE room_id=?
    ORDER BY student_name
    """, (room_id,))

    roommates = cursor.fetchall()

    conn.close()

    return render_template(
        "roommates.html",
        roommates=roommates
    )

@app.route("/admin/notices", methods=["GET", "POST"])
def admin_notices():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("SELECT college_code FROM colleges WHERE id=?",
                   (session["college_id"],))
    college_code = cursor.fetchone()[0]

    if request.method == "POST":

        title = request.form["title"]
        message = request.form["message"]

        cursor.execute("""
        INSERT INTO notices
        (college_code,title,message)
        VALUES(?,?,?)
        """,
        (
            college_code,
            title,
            message
        ))

        conn.commit()

    cursor.execute("""
    SELECT
        id,
        title,
        message,
        notice_date
    FROM notices
    WHERE college_code=?
    ORDER BY id DESC
    """, (college_code,))

    notices = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_notices.html",
        notices=notices
    )

@app.route("/student/notices")
def student_notices():

    if "student_id" not in session:
        return redirect(url_for("student_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT college_code
    FROM students
    WHERE id=?
    """, (session["student_id"],))

    college_code = cursor.fetchone()[0]

    cursor.execute("""
    SELECT
        title,
        message,
        notice_date
    FROM notices
    WHERE college_code=?
    ORDER BY id DESC
    """, (college_code,))

    notices = cursor.fetchall()

    conn.close()

    return render_template(
        "student_notices.html",
        notices=notices
    )

from werkzeug.security import check_password_hash, generate_password_hash

@app.route("/student/change_password", methods=["GET", "POST"])
def student_change_password():

    if "student_id" not in session:
        return redirect(url_for("student_login"))

    if request.method == "POST":

        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        conn = sqlite3.connect("hostel.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT password
        FROM students
        WHERE id=?
        """, (session["student_id"],))

        db_password = cursor.fetchone()[0]

        if not check_password_hash(db_password, current_password):
            conn.close()
            return render_template(
                "student_change_password.html",
                error="Current Password is Incorrect."
            )

        if new_password != confirm_password:
            conn.close()
            return render_template(
                "student_change_password.html",
                error="New Password and Confirm Password do not match."
            )

        new_hash = generate_password_hash(new_password)

        cursor.execute("""
        UPDATE students
        SET password=?
        WHERE id=?
        """,
        (
            new_hash,
            session["student_id"]
        ))

        conn.commit()
        conn.close()

        return render_template(
            "student_change_password.html",
            success="Password Changed Successfully."
        )

    return render_template("student_change_password.html")


@app.route("/admin/change_password", methods=["GET", "POST"])
def admin_change_password():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    if request.method == "POST":

        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        conn = sqlite3.connect("hostel.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT password
        FROM colleges
        WHERE id=?
        """, (session["college_id"],))

        db_password = cursor.fetchone()[0]

        if not check_password_hash(db_password, current_password):

            conn.close()

            return render_template(
                "admin_change_password.html",
                error="Current Password is Incorrect."
            )

        if new_password != confirm_password:

            conn.close()

            return render_template(
                "admin_change_password.html",
                error="New Password and Confirm Password do not match."
            )

        new_hash = generate_password_hash(new_password)

        cursor.execute("""
        UPDATE colleges
        SET password=?
        WHERE id=?
        """,
        (
            new_hash,
            session["college_id"]
        ))

        conn.commit()
        conn.close()

        return render_template(
            "admin_change_password.html",
            success="Password Changed Successfully."
        )

    return render_template("admin_change_password.html")

from werkzeug.security import check_password_hash, generate_password_hash

@app.route("/security/change_password", methods=["GET", "POST"])
def security_change_password():

    if "security_id" not in session:
        return redirect(url_for("security_login"))

    if request.method == "POST":

        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        conn = sqlite3.connect("hostel.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT password
        FROM security
        WHERE id=?
        """, (session["security_id"],))

        db_password = cursor.fetchone()[0]

        if not check_password_hash(db_password, current_password):

            conn.close()

            return render_template(
                "security_change_password.html",
                error="Current Password is Incorrect."
            )

        if new_password != confirm_password:

            conn.close()

            return render_template(
                "security_change_password.html",
                error="New Password and Confirm Password do not match."
            )

        new_hash = generate_password_hash(new_password)

        cursor.execute("""
        UPDATE security
        SET password=?
        WHERE id=?
        """,
        (
            new_hash,
            session["security_id"]
        ))

        conn.commit()
        conn.close()

        return render_template(
            "security_change_password.html",
            success="Password Changed Successfully."
        )

    return render_template("security_change_password.html")

@app.route("/admin/resolve_complaint/<int:complaint_id>")
def resolve_complaint(complaint_id):

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE complaints
    SET status='Resolved'
    WHERE id=?
    """, (complaint_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_complaints"))




@app.route("/student/request_room_change", methods=["GET", "POST"])
def request_room_change():

    if "student_id" not in session:
        return redirect(url_for("student_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    # Get student's current room
    cursor.execute("""
    SELECT room_id
    FROM students
    WHERE id=?
    """, (session["student_id"],))

    current_room_id = cursor.fetchone()[0]

    if request.method == "POST":

        requested_room_id = request.form["requested_room_id"]
        reason = request.form["reason"]

        cursor.execute("""
        INSERT INTO room_change_requests
        (
            student_id,
            current_room_id,
            requested_room_id,
            reason
        )
        VALUES(?,?,?,?)
        """,
        (
            session["student_id"],
            current_room_id,
            requested_room_id,
            reason
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("room_change_status"))

    # Get all rooms except the current room
    cursor.execute("""
    SELECT id, room_no
    FROM rooms
    WHERE id != ?
    ORDER BY room_no
    """, (current_room_id,))

    rooms = cursor.fetchall()

    conn.close()

    return render_template(
        "request_room_change.html",
        rooms=rooms
    )


@app.route("/student/room_change_status")
def room_change_status():

    if "student_id" not in session:
        return redirect(url_for("student_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT

        room_change_requests.id,

        r1.room_no,

        r2.room_no,

        room_change_requests.reason,

        room_change_requests.status,

        room_change_requests.created_at

    FROM room_change_requests

    JOIN rooms r1
    ON room_change_requests.current_room_id = r1.id

    JOIN rooms r2
    ON room_change_requests.requested_room_id = r2.id

    WHERE room_change_requests.student_id=?

    ORDER BY room_change_requests.id DESC
    """, (session["student_id"],))

    requests = cursor.fetchall()

    conn.close()

    return render_template(
        "room_change_status.html",
        requests=requests
    )


@app.route("/admin/room_change_requests")
def room_change_requests():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT

        room_change_requests.id,

        students.register_no,

        students.student_name,

        r1.room_no,

        r2.room_no,

        room_change_requests.reason,

        room_change_requests.status,

        room_change_requests.created_at

    FROM room_change_requests

    JOIN students
    ON room_change_requests.student_id = students.id

    JOIN rooms r1
    ON room_change_requests.current_room_id = r1.id

    JOIN rooms r2
    ON room_change_requests.requested_room_id = r2.id

    WHERE students.college_code=?

    ORDER BY room_change_requests.id DESC
    """, (session["college_code"],))

    requests = cursor.fetchall()

    conn.close()

    return render_template(
        "room_change_requests.html",
        requests=requests
    )

@app.route("/admin/approve_room_change/<int:request_id>")
def approve_room_change(request_id):

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    # Get request details
    cursor.execute("""
    SELECT
        student_id,
        current_room_id,
        requested_room_id
    FROM room_change_requests
    WHERE id=?
    """, (request_id,))

    request = cursor.fetchone()

    if request:

        student_id = request[0]
        old_room = request[1]
        new_room = request[2]

        # Update student's room
        cursor.execute("""
        UPDATE students
        SET room_id=?
        WHERE id=?
        """, (new_room, student_id))

        # Reduce old room occupancy
        cursor.execute("""
        UPDATE rooms
        SET occupied = occupied - 1
        WHERE id=?
        """, (old_room,))

        # Increase new room occupancy
        cursor.execute("""
        UPDATE rooms
        SET occupied = occupied + 1
        WHERE id=?
        """, (new_room,))

        # Update request status
        cursor.execute("""
        UPDATE room_change_requests
        SET
            status='Approved',
            approved_at=CURRENT_TIMESTAMP
        WHERE id=?
        """, (request_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("room_change_requests"))

@app.route("/admin/reject_room_change/<int:request_id>")
def reject_room_change(request_id):

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE room_change_requests
    SET status='Rejected'
    WHERE id=?
    """, (request_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("room_change_requests"))

@app.route("/admin/change_room/<int:student_id>", methods=["GET","POST"])
def change_room(student_id):

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    if request.method == "POST":

        new_room = request.form["room_id"]

        cursor.execute("""
        SELECT room_id
        FROM students
        WHERE id=?
        """,(student_id,))

        old_room = cursor.fetchone()[0]

        if int(old_room) != int(new_room):

            cursor.execute("""
            UPDATE students
            SET room_id=?
            WHERE id=?
            """,(new_room,student_id))

            cursor.execute("""
            UPDATE rooms
            SET occupied=occupied-1
            WHERE id=?
            """,(old_room,))

            cursor.execute("""
            UPDATE rooms
            SET occupied=occupied+1
            WHERE id=?
            """,(new_room,))

            conn.commit()

        conn.close()

        return redirect(url_for("view_students"))

    cursor.execute("""
    SELECT student_name, room_id
    FROM students
    WHERE id=?
    """,(student_id,))

    student = cursor.fetchone()

    cursor.execute("""
    SELECT id, room_no
    FROM rooms
    ORDER BY room_no
    """)

    rooms = cursor.fetchall()

    conn.close()

    return render_template(
        "change_room.html",
        student=student,
        rooms=rooms
    )

@app.route("/admin/room_change_management")
def room_change_management():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    return render_template("room_change_management.html")


@app.route("/admin/direct_change_room", methods=["GET", "POST"])
def direct_change_room():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    if request.method == "POST":

        student_id = request.form["student_id"]
        new_room_id = request.form["room_id"]

        # Get student's current room
        cursor.execute("""
        SELECT room_id
        FROM students
        WHERE id=?
        """, (student_id,))

        result = cursor.fetchone()

        if result is None:
            conn.close()
            flash("Student not found.")
            return redirect(url_for("direct_change_room"))

        old_room_id = result[0]

        # Check if same room selected
        if old_room_id == int(new_room_id):
            conn.close()
            flash("Student is already assigned to this room.")
            return redirect(url_for("direct_change_room"))

        # Check new room capacity
        cursor.execute("""
        SELECT capacity, occupied
        FROM rooms
        WHERE id=?
        """, (new_room_id,))

        room = cursor.fetchone()

        if room is None:
            conn.close()
            flash("Room not found.")
            return redirect(url_for("direct_change_room"))

        capacity, occupied = room

        if occupied >= capacity:
            conn.close()
            flash("Selected room is full.")
            return redirect(url_for("direct_change_room"))

        # Reduce occupied count in old room
        if old_room_id is not None:

            cursor.execute("""
            UPDATE rooms
            SET occupied = occupied - 1
            WHERE id=? AND occupied > 0
            """, (old_room_id,))

        # Increase occupied count in new room
        cursor.execute("""
        UPDATE rooms
        SET occupied = occupied + 1
        WHERE id=?
        """, (new_room_id,))

        # Update student's room
        cursor.execute("""
        UPDATE students
        SET room_id=?
        WHERE id=?
        """, (
            new_room_id,
            student_id
        ))

        conn.commit()
        conn.close()

        flash("Room changed successfully.")

        return redirect(url_for("direct_change_room"))

    # -------------------------
    # Student List
    # -------------------------

    cursor.execute("""
    SELECT
        id,
        student_name,
        register_no
    FROM students
    WHERE college_code=?
    ORDER BY student_name
    """, (session["college_code"],))

    students = cursor.fetchall()

    # -------------------------
    # Available Rooms
    # -------------------------

    cursor.execute("""
    SELECT
        rooms.id,
        rooms.room_no,
        floors.floor_name,
        blocks.block_name,
        rooms.capacity,
        rooms.occupied
    FROM rooms

    JOIN floors
        ON rooms.floor_id = floors.id

    JOIN blocks
        ON floors.block_id = blocks.id

    WHERE blocks.college_code=?

    ORDER BY
        blocks.block_name,
        floors.floor_name,
        rooms.room_no
    """, (session["college_code"],))

    rooms = cursor.fetchall()

    conn.close()

    return render_template(
        "direct_change_room.html",
        students=students,
        rooms=rooms
    )

from datetime import datetime

@app.route("/admin/promote_students", methods=["GET", "POST"])
def promote_students():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    # Open the promotion page
    if request.method == "GET":
        return render_template("promote_students.html")

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    current_year = int(request.form["current_year"])
    new_year = request.form["new_year"]

    # 4th Year Students
    if current_year == 4:

        cursor.execute("""
        SELECT id, room_id
        FROM students
        WHERE year=? AND college_code=?
        """, (4, session["college_code"]))

        students = cursor.fetchall()

        for student in students:

            student_id = student[0]
            room_id = student[1]

            if room_id:

                cursor.execute("""
                UPDATE rooms
                SET occupied = occupied - 1
                WHERE id=? AND occupied>0
                """, (room_id,))

            cursor.execute("""
            DELETE FROM students
            WHERE id=?
            """, (student_id,))

    else:

        cursor.execute("""
        UPDATE students
        SET year=?
        WHERE year=? AND college_code=?
        """, (
            int(new_year),
            current_year,
            session["college_code"]
        ))

    conn.commit()
    conn.close()

    return redirect(url_for("view_students"))
@app.route("/admin/edit_student/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    if request.method == "POST":

        student_name = request.form["student_name"]
        department = request.form["department"]
        year = request.form["year"]
        gender = request.form["gender"]
        mobile = request.form["mobile"]

        cursor.execute("""
        UPDATE students
        SET
            student_name=?,
            department=?,
            year=?,
            gender=?,
            mobile=?
        WHERE id=?
        """, (
            student_name,
            department,
            year,
            gender,
            mobile,
            student_id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("view_students"))

    cursor.execute("""
    SELECT
        register_no,
        student_name,
        department,
        year,
        gender,
        mobile
    FROM students
    WHERE id=?
    """, (student_id,))

    student = cursor.fetchone()

    conn.close()

    return render_template(
        "edit_student.html",
        student=student,
        student_id=student_id
    )

@app.route("/admin/delete_student/<int:student_id>")
def delete_student(student_id):

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    # Find assigned room
    cursor.execute("""
    SELECT room_id
    FROM students
    WHERE id=?
    """, (student_id,))

    row = cursor.fetchone()

    if row and row[0]:

        room_id = row[0]

        cursor.execute("""
        UPDATE rooms
        SET occupied = occupied - 1
        WHERE id=? AND occupied>0
        """, (room_id,))

    cursor.execute("""
    DELETE FROM students
    WHERE id=?
    """, (student_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("view_students"))

@app.route("/admin/outing_history")
def admin_outing_history():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        students.register_no,
        students.student_name,
        outing_requests.outing_type,
        outing_requests.destination,
        outing_requests.out_date,
        outing_requests.return_date,
        outing_requests.status,
        outing_requests.permission_id
    FROM outing_requests

    JOIN students
        ON outing_requests.student_id = students.id

    WHERE students.college_code=?

    ORDER BY outing_requests.id DESC
    """, (session["college_code"],))

    outings = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_outing_history.html",
        outings=outings
    )


@app.route("/admin/mess_menu", methods=["GET", "POST"])
def admin_mess_menu():

    if "college_id" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    if request.method == "POST":

        day = request.form["day"]
        breakfast = request.form["breakfast"]
        lunch = request.form["lunch"]
        snacks = request.form["snacks"]
        dinner = request.form["dinner"]

        # Check if menu already exists
        cursor.execute("""
        SELECT id
        FROM mess_menu
        WHERE college_code=? AND day=?
        """, (session["college_code"], day))

        existing = cursor.fetchone()

        if existing:

            cursor.execute("""
            UPDATE mess_menu
            SET
                breakfast=?,
                lunch=?,
                snacks=?,
                dinner=?
            WHERE id=?
            """, (
                breakfast,
                lunch,
                snacks,
                dinner,
                existing[0]
            ))

        else:

            cursor.execute("""
            INSERT INTO mess_menu(
                college_code,
                day,
                breakfast,
                lunch,
                snacks,
                dinner
            )
            VALUES(?,?,?,?,?,?)
            """, (
                session["college_code"],
                day,
                breakfast,
                lunch,
                snacks,
                dinner
            ))

        conn.commit()

    cursor.execute("""
    SELECT
        id,
        day,
        breakfast,
        lunch,
        snacks,
        dinner
    FROM mess_menu
    WHERE college_code=?
    ORDER BY
    CASE day
        WHEN 'Monday' THEN 1
        WHEN 'Tuesday' THEN 2
        WHEN 'Wednesday' THEN 3
        WHEN 'Thursday' THEN 4
        WHEN 'Friday' THEN 5
        WHEN 'Saturday' THEN 6
        WHEN 'Sunday' THEN 7
    END
    """, (session["college_code"],))

    menus = cursor.fetchall()

    conn.close()

    return render_template(
        "mess_menu.html",
        menus=menus
    )

@app.route("/admin/edit_menu/<int:menu_id>", methods=["GET", "POST"])
def admin_edit_menu(menu_id):

    if "college_code" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    # Update menu
    if request.method == "POST":

        day = request.form["day"]
        breakfast = request.form["breakfast"]
        lunch = request.form["lunch"]
        dinner = request.form["dinner"]

        cursor.execute("""
            UPDATE mess_menu
            SET day = ?,
                breakfast = ?,
                lunch = ?,
                dinner = ?
            WHERE id = ?
            AND college_code = ?
        """, (
            day,
            breakfast,
            lunch,
            dinner,
            menu_id,
            session["college_code"]
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("admin_mess_management"))


    # Fetch existing menu data
    cursor.execute("""
        SELECT id, day, breakfast, lunch, dinner
        FROM mess_menu
        WHERE id = ?
        AND college_code = ?
    """, (
        menu_id,
        session["college_code"]
    ))

    menu = cursor.fetchone()

    conn.close()

    if menu is None:
        return "Menu not found"


    return render_template(
        "edit_menu.html",
        menu=menu
    )

@app.route("/admin/delete_menu/<int:menu_id>")
def admin_delete_menu(menu_id):

    if "college_code" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM mess_menu
        WHERE id = ?
        AND college_code = ?
    """, (
        menu_id,
        session["college_code"]
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_mess_management"))

@app.route("/admin/mess_management")
def admin_mess_management():

    if "college_code" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id,
               day,
               breakfast,
               lunch,
               dinner
        FROM mess_menu
        WHERE college_code = ?
        ORDER BY id DESC
    """, (session["college_code"],))

    menus = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_mess_management.html",
        menus=menus
    )
@app.route("/student/mess")
def student_mess():

    if "student_id" not in session:
        return redirect(url_for("student_login"))


    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()


    # Get student's college code
    cursor.execute("""
        SELECT college_code
        FROM students
        WHERE id = ?
    """, (session["student_id"],))


    student = cursor.fetchone()


    if student is None:
        conn.close()
        return "Student not found"


    college_code = student[0]


    cursor.execute("""
        SELECT id,
               day,
               breakfast,
               lunch,
               dinner
        FROM mess_menu
        WHERE college_code = ?
        ORDER BY id
    """, (college_code,))


    menus = cursor.fetchall()


    conn.close()


    return render_template(
        "student_mess.html",
        menus=menus
    )

@app.route("/admin/add_menu", methods=["POST"])
def admin_add_menu():

    if "college_code" not in session:
        return redirect(url_for("admin_login"))


    day = request.form["day"]
    breakfast = request.form["breakfast"]
    lunch = request.form["lunch"]
    snacks = request.form["snacks"]
    dinner = request.form["dinner"]


    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()


    cursor.execute("""
        INSERT INTO mess_menu
        (
            college_code,
            day,
            breakfast,
            lunch,
            snacks,
            dinner
        )

        VALUES (?, ?, ?, ?, ?, ?)

    """,
    (
        session["college_code"],
        day,
        breakfast,
        lunch,
        snacks,
        dinner
    ))


    conn.commit()
    conn.close()


    return redirect(url_for("admin_mess_management"))

@app.route("/admin/food_feedback")
def admin_food_feedback():

    if "college_code" not in session:
        return redirect(url_for("admin_login"))


    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()


    # Get student reviews
    cursor.execute("""
        SELECT 
            students.student_name,
            food_feedback.rating,
            food_feedback.review,
            food_feedback.feedback_date,
            food_feedback.id

        FROM food_feedback

        JOIN students
        ON food_feedback.student_id = students.id

        WHERE food_feedback.college_code = ?

        ORDER BY food_feedback.id DESC

    """,
    (
        session["college_code"],
    ))


    feedbacks = cursor.fetchall()



    # Calculate average rating

    cursor.execute("""
        SELECT AVG(rating)
        FROM food_feedback
        WHERE college_code = ?
    """,
    (
        session["college_code"],
    ))


    result = cursor.fetchone()


    if result[0]:

        average_rating = round(result[0],1)

    else:

        average_rating = 0



    conn.close()



    return render_template(
        "admin_food_feedback.html",
        feedbacks=feedbacks,
        average_rating=average_rating
    )

@app.route("/admin/delete_food_feedback/<int:feedback_id>")
def admin_delete_food_feedback(feedback_id):

    if "college_code" not in session:
        return redirect(url_for("admin_login"))


    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()



    cursor.execute("""
        DELETE FROM food_feedback

        WHERE id = ?

        AND college_code = ?

    """,
    (
        feedback_id,
        session["college_code"]
    ))



    conn.commit()

    conn.close()



    return redirect(
        url_for("admin_food_feedback")
    )

@app.route("/student/food_feedback", methods=["GET","POST"])
def student_food_feedback():

    if "student_id" not in session:
        return redirect(url_for("student_login"))


    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()


    if request.method == "POST":

        rating = request.form["rating"]

        review = request.form["review"]


        cursor.execute("""
            SELECT college_code
            FROM students
            WHERE id=?
        """,
        (
            session["student_id"],
        ))


        student = cursor.fetchone()


        cursor.execute("""
            INSERT INTO food_feedback
            (
                college_code,
                student_id,
                rating,
                review,
                feedback_date
            )

            VALUES(?,?,?,?,DATE('now'))

        """,
        (
            student[0],
            session["student_id"],
            rating,
            review
        ))


        conn.commit()


    conn.close()


    return render_template(
        "student_food_feedback.html"
    )

@app.route("/security/history")
def security_history():

    if "security_id" not in session:
        return redirect(url_for("security_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        outing_requests.permission_id,
        students.register_no,
        students.student_name,
        outing_requests.outing_type,
        outing_requests.destination,
        outing_requests.out_date,
        outing_requests.return_date,
        outing_requests.status
    FROM outing_requests

    JOIN students
        ON outing_requests.student_id = students.id

    ORDER BY outing_requests.id DESC
    """)

    history = cursor.fetchall()

    conn.close()

    return render_template(
        "security_history.html",
        history=history
    )

@app.route("/security/notices")
def security_notices():

    if "security_id" not in session:
        return redirect(url_for("security_login"))

    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        title,
        message,
        created_at
    FROM notices
    ORDER BY id DESC
    """)

    notices = cursor.fetchall()

    conn.close()

    return render_template(
        "security_notices.html",
        notices=notices
    )
# ===============================
# RUN APPLICATION
# ===============================
if __name__ == "__main__":
    app.run(debug=True)