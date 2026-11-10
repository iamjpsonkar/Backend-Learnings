import os

from flask import Flask, request, jsonify, redirect, url_for
from flask.views import MethodView
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
from markupsafe import escape
from sqlalchemy.exc import SQLAlchemyError


# ============================================================
# Application Configuration
# ============================================================

load_dotenv()

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured in .env")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)


# ============================================================
# Student Model
# ============================================================

class Student(db.Model):

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age
        }

    def __repr__(self):
        return (
            f"<Student id={self.id} "
            f"name={self.name!r} age={self.age}>"
        )


# ============================================================
# Home View
# ============================================================

class Home(MethodView):

    def get(self):
        return """
        <h1>Welcome to Student Management System</h1>

        <h2>Available Functionalities</h2>

        <ul>
            <li><a href="/students">List All Students</a></li>
            <li><a href="/students/1">View Student ID 1</a></li>
            <li><a href="/students/new">Add New Student</a></li>
        </ul>
        """


# ============================================================
# Student View
# ============================================================

class StudentView(MethodView):

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    @staticmethod
    def wants_json():
        return (
            request.is_json
            or request.accept_mimetypes.best == "application/json"
        )

    def validate_student_data(self):
        """
        Returns:
            ((name, age), None) on success
            (None, (response, status_code)) on failure
        """

        if request.is_json:
            data = request.get_json(silent=True)

            if not isinstance(data, dict):
                return None, (
                    jsonify({"error": "JSON body must be an object"}),
                    400
                )
        else:
            data = request.form

        name = data.get("name")
        age = data.get("age")

        if not isinstance(name, str) or not name.strip():
            return None, (
                jsonify({"error": "Valid name is required"}),
                400
            )

        try:
            age = int(age)
        except (ValueError, TypeError):
            return None, (
                jsonify({"error": "Age must be an integer"}),
                400
            )

        if not 10 <= age <= 25:
            return None, (
                jsonify({"error": "Age must be between 10 and 25"}),
                400
            )

        return (name.strip(), age), None

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    def get(self, id=None, action=None):

        if action == "new":
            return self.student_form()

        if action == "edit":
            student = db.session.get(Student, id)

            if student is None:
                return "Student not found", 404

            return self.student_form(student)

        if id is None:
            return self.fetch_all_students()

        return self.fetch_student(id)

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    def post(self, id=None, action=None):

        if action == "new" or id is None:
            return self.create_student()

        if action == "edit":
            return self.update_student(id)

        if action == "delete":
            return self.delete_student(id)

        return jsonify({"error": "Invalid operation"}), 400

    # --------------------------------------------------------
    # PUT
    # --------------------------------------------------------

    def put(self, id):
        return self.update_student(id, json_only=True)

    # --------------------------------------------------------
    # DELETE
    # --------------------------------------------------------

    def delete(self, id):
        return self.delete_student(id, json_only=True)

    # ========================================================
    # CREATE STUDENT
    # ========================================================

    def create_student(self):

        data, error = self.validate_student_data()

        if error:
            return error

        name, age = data

        try:
            student = Student(
                name=name,
                age=age
            )

            db.session.add(student)
            db.session.commit()

        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Failed to create student")
            return jsonify({"error": "Could not create student"}), 500

        if request.is_json:
            return jsonify({
                "message": "Student created successfully",
                "student": student.to_dict()
            }), 201

        return redirect(url_for("student", id=student.id))

    # ========================================================
    # UPDATE STUDENT
    # ========================================================

    def update_student(self, id, json_only=False):

        student = db.session.get(Student, id)

        if student is None:
            return jsonify({"error": "Student not found"}), 404

        if json_only and not request.is_json:
            return jsonify({"error": "JSON body is required"}), 400

        data, error = self.validate_student_data()

        if error:
            return error

        name, age = data

        try:
            student.name = name
            student.age = age

            db.session.commit()

        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Failed to update student")
            return jsonify({"error": "Could not update student"}), 500

        if request.is_json:
            return jsonify({
                "message": "Student updated successfully",
                "student": student.to_dict()
            }), 200

        return redirect(url_for("student", id=id))

    # ========================================================
    # DELETE STUDENT
    # ========================================================

    def delete_student(self, id, json_only=False):

        student = db.session.get(Student, id)

        if student is None:
            return jsonify({"error": "Student not found"}), 404

        if json_only and not request.is_json:
            return jsonify({"error": "JSON request expected"}), 400

        try:
            db.session.delete(student)
            db.session.commit()

        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Failed to delete student")
            return jsonify({"error": "Could not delete student"}), 500

        if json_only:
            return jsonify({
                "message": "Student deleted successfully",
                "student_id": id
            }), 200

        return redirect(url_for("student"))

    # ========================================================
    # HTML FORMS
    # ========================================================

    def student_form(self, student=None):

        is_edit = student is not None

        title = "Update Student" if is_edit else "Add New Student"

        name = escape(student.name) if is_edit else ""
        age = student.age if is_edit else ""

        action = (
            url_for("student", id=student.id, action="edit")
            if is_edit
            else url_for("student", action="new")
        )

        return f"""
        <h1>{title}</h1>

        <form method="POST" action="{action}">

            <label for="name">Name:</label><br>

            <input
                type="text"
                id="name"
                name="name"
                value="{name}"
                maxlength="100"
                required
            >

            <br><br>

            <label for="age">Age:</label><br>

            <input
                type="number"
                id="age"
                name="age"
                value="{age}"
                min="10"
                max="25"
                required
            >

            <br><br>

            <button type="submit">
                {"Update" if is_edit else "Create"}
            </button>

        </form>

        <br>

        <a href="/students">Back to Students</a>
        """

    # ========================================================
    # FETCH ALL STUDENTS
    # ========================================================

    def fetch_all_students(self):

        students = db.session.execute(
            db.select(Student).order_by(Student.id)
        ).scalars().all()

        if self.wants_json():
            return jsonify([
                student.to_dict()
                for student in students
            ])

        html = """
        <h1>All Students</h1>

        <a href="/students/new">Add New Student</a>

        <br><br>

        <table border="1" cellpadding="8">

            <tr>
                <th>ID</th>
                <th>NAME</th>
                <th>AGE</th>
                <th>ACTIONS</th>
            </tr>
        """

        for student in students:

            html += f"""
            <tr>
                <td>{student.id}</td>
                <td>{escape(student.name)}</td>
                <td>{student.age}</td>

                <td>
                    <a href="/students/{student.id}">
                        View
                    </a>

                    |

                    <a href="/students/{student.id}/edit">
                        Edit
                    </a>

                    |

                    <form
                        method="POST"
                        action="/students/{student.id}/delete"
                        style="display:inline"
                    >
                        <button type="submit">Delete</button>
                    </form>
                </td>
            </tr>
            """

        html += """
        </table>

        <br>

        <a href="/">Back to Home</a>
        """

        return html

    # ========================================================
    # FETCH SINGLE STUDENT
    # ========================================================

    def fetch_student(self, id):

        student = db.session.get(Student, id)

        if student is None:
            return jsonify({"error": "Student not found"}), 404

        if self.wants_json():
            return jsonify(student.to_dict())

        return f"""
        <h1>Student Details</h1>

        <table border="1" cellpadding="8">

            <tr>
                <th>ID</th>
                <th>NAME</th>
                <th>AGE</th>
            </tr>

            <tr>
                <td>{student.id}</td>
                <td>{escape(student.name)}</td>
                <td>{student.age}</td>
            </tr>

        </table>

        <br>

        <a href="/students/{id}/edit">
            Update Student
        </a>

        <br><br>

        <a href="/students">
            Back to Students
        </a>
        """


# ============================================================
# Register Views and Routes
# ============================================================

home_view = Home.as_view("home")
student_view = StudentView.as_view("student")

app.add_url_rule(
    "/",
    view_func=home_view,
    methods=["GET"]
)

app.add_url_rule(
    "/students",
    view_func=student_view,
    methods=["GET"]
)

app.add_url_rule(
    "/students/new",
    view_func=student_view,
    defaults={"action": "new"},
    methods=["GET", "POST"]
)

app.add_url_rule(
    "/students/<int:id>",
    view_func=student_view,
    methods=["GET", "PUT", "DELETE"]
)

app.add_url_rule(
    "/students/<int:id>/edit",
    view_func=student_view,
    defaults={"action": "edit"},
    methods=["GET", "POST"]
)

app.add_url_rule(
    "/students/<int:id>/delete",
    view_func=student_view,
    defaults={"action": "delete"},
    methods=["POST"]
)


# ============================================================
# Application Entry Point
# ============================================================

if __name__ == "__main__":

    with app.app_context():
        db.create_all()
        print("Database tables verified/created successfully!")

    print("\nRegistered Routes:")

    for rule in app.url_map.iter_rules():
        print(rule, sorted(rule.methods))

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )