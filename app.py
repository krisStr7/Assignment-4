from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET_KEY"

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg.connect(DATABASE_URL)

# ---------------------------
# Authentication Protection
# ---------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ---------------------------
# Login Page
# ---------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, username, password_hash, role
                    FROM app_user
                    WHERE username = %s
                """, (username,))
                user = cur.fetchone()

                if user and check_password_hash(user[2], password):
                    session["user_id"] = user[0]
                    session["username"] = user[1]
                    session["role"] = user[3]
                    return redirect(url_for("home"))
                else:
                    error = "Invalid username or password."

    return render_template("login.html", error=error)




# ---------------------------
# Logout
# ---------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------
# Home Page (A2)
# ---------------------------
@app.route("/")
@login_required
def home():
    search = request.args.get("search", "")
    dept = request.args.get("dept", "")
    sort = request.args.get("sort", "name_asc")

    # Safe whitelist for ORDER BY
    sort_options = {
        "name_asc": "Lname ASC, Fname ASC",
        "name_desc": "Lname DESC, Fname DESC",
        "hours_asc": "total_hours ASC",
        "hours_desc": "total_hours DESC"
    }
    order_clause = sort_options.get(sort, "Lname ASC")

    with get_db() as conn:
        with conn.cursor() as cur:

            # Department dropdown
            cur.execute("SELECT Dnumber, Dname FROM Department ORDER BY Dname;")
            departments = cur.fetchall()

            # Main query with LEFT JOINs (required by project)
            query = f"""
                SELECT 
                    e.Ssn,
                    e.Fname,
                    e.Minit,
                    e.Lname,
                    d.Dname,
                    COALESCE(dep.count_dep, 0),
                    COALESCE(w.count_proj, 0),
                    COALESCE(w.total_hours, 0)
                FROM Employee e
                JOIN Department d ON d.Dnumber = e.Dno

                LEFT JOIN (
                    SELECT Essn, COUNT(*) AS count_dep
                    FROM Dependent
                    GROUP BY Essn
                ) dep ON dep.Essn = e.Ssn

                LEFT JOIN (
                    SELECT Essn, COUNT(*) AS count_proj, SUM(Hours) AS total_hours
                    FROM Works_On
                    GROUP BY Essn
                ) w ON w.Essn = e.Ssn

                WHERE (%s = '' OR LOWER(e.Fname || ' ' || e.Lname) LIKE LOWER(%s))
                  AND (%s = '' OR e.Dno = %s)

                ORDER BY {order_clause}
            """

            like_param = f"%{search}%"
            dept_param = None if dept == "" else int(dept)
            cur.execute(query, (search, like_param, dept, dept_param))

            employees = cur.fetchall()

    return render_template(
        "home.html",
        employees=employees,
        departments=departments,
        search=search,
        dept=dept,
        sort=sort
    )




# -----------------------
#  A4 page - Project Details
# --------------------------
@app.route("/projects/<int:project_id>", methods=["GET", "POST"])
@login_required
def project_details(project_id):
    # connect to database
    with get_db() as conn:
        with conn.cursor() as cur:

            # get all the employee names and hours for a certain project
            cur.execute("""
                SELECT e.Fname, e.Lname, w.Hours
                FROM Works_On w
                JOIN Employee e ON w.Essn = e.Ssn
                WHERE w.Pno = %s;
            """, (project_id,))
            employees = cur.fetchall()

            # when the user updates the hours (upsert)
            if request.method == "POST":
                # info the user submitted 
                emp_ssn = int(request.form["employee"])
                hours = float(request.form["hours"])
                # upsert query - updates database
                cur.execute("""
                    INSERT INTO Works_On (Essn, Pno, Hours)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (Essn, Pno)
                    DO UPDATE SET Hours = Works_On.Hours + EXCLUDED.Hours;
                """, (emp_ssn, project_id, hours))
                conn.commit()
                # reloads the pages after the user submits the new hours
                return redirect(url_for("project_details", project_id=project_id))

            #get all employee names from the database for the drop down menu
            cur.execute("SELECT Ssn, Fname || ' ' || Lname FROM Employee;")
            all_employees = cur.fetchall()

    # sends the project id, employees working for that project, and full list of employees to the new page
    return render_template(
        "project_details.html",
        project_id=project_id,
        employees=employees,
        all_employees=all_employees
    )


# ---------------------------
# Run App
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)
