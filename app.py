from flask import Flask, render_template, request, url_for, session, redirect, flash
from webforms import SearchForm
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired
from search import filter_search
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
import json
import os
from datetime import datetime
from dotenv import find_dotenv, load_dotenv
from authlib.integrations.flask_client import OAuth
from os import environ as env
from urllib.parse import quote_plus, urlencode
import datetime


ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY")

oauth = OAuth(app)
oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration'
)


## STATIC VARS
current_file_dir = os.path.dirname(__file__)
class_json_path = os.path.join(current_file_dir, "json", "classes.json")
days_map = {"M": "Monday", "T": "Tuesday", "W": "Wednesday", "Th": "Thursday", "F": "Friday"}
class_prof_rating_path = os.path.join(current_file_dir, "json", "Professor_Ratings.json")




## DATABASE CONFIG
db_name = "database.db"
# app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_name
app.config["SQLALCHEMY_DATABASE_URI"] = "postgres://mhzraoglfqvuhd:a4e57cabc9e70578e43a1a4ddadcf4581a294024e877fbbe55436ecb03837ed4@ec2-3-209-124-113.compute-1.amazonaws.com:5432/d80of9t8c82dt8"


app.config["SECRET_KEY"] = "abcde"

db = SQLAlchemy(app)

class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)

    #create one to many relationship with courses
    classes = db.relationship("Courses")

    def __repr__(self):
        return "<Name %r>" % self.name

class Courses(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)

    #foreignkey is user id
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    class_code = db.Column(db.String(100))
    class_title = db.Column(db.String(100))
    section_number = db.Column(db.Integer)
    section_number_str = db.Column(db.String(5))
    credit_hours = db.Column(db.Integer)
    day_of_week = db.Column(db.String(20)) 
    time = db.Column(db.String(50)) 
    professor_name = db.Column(db.String(100))
    professor_rating = db.Column(db.String(10))


##ROUTES
@app.route('/')
def index():
    full_name = "Pushin"
    if "user" in session:
        full_name = session["user"]["userinfo"]["name"]
        
        #get classes from user's db
        user_courses = Courses.query.filter_by(user_id=session["user_id"])
        # for course in user_courses:
        #     print(course.class_title)
        #     print(course.class_code)
        #     print(course.section_number)


        monday = user_courses.filter_by(day_of_week="Monday").order_by(Courses.time.desc())
        tuesday = user_courses.filter_by(day_of_week="Tuesday").order_by(Courses.time.desc())
        wednesday = user_courses.filter_by(day_of_week="Wednesday").order_by(Courses.time.desc())
        thursday = user_courses.filter_by(day_of_week="Thursday").order_by(Courses.time.desc())
        friday = user_courses.filter_by(day_of_week="Friday").order_by(Courses.time.desc())
        
        return render_template("index.html", name = full_name, monday=monday, tuesday=tuesday, wednesday=wednesday, thursday=thursday, friday=friday)

    return render_template('index_old.html', name=full_name)

import os
SECRET_KEY = "pushin-pp"
app.config['SECRET_KEY'] = SECRET_KEY

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login')
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token

    email = session["user"]["userinfo"]["email"]
    full_name = session["user"]["userinfo"]["name"]

    user = Users.query.filter_by(email=email).first()
    if not user:
        user = Users(name=full_name, email=email)
        db.session.add(user)
        db.session.commit()
        print("user added to db.")
        # flash("user added to db.", category="success")
    else:
        print("user found to db.")
        # flash("user found in db.", category="success")

    #store user id in session
    session["user_id"] = user.id

    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("index", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )

#Pass things to index_base.html
@app.context_processor
def base():
    form = SearchForm()
    return dict(form=form)

@app.route("/search", methods = ["POST"])
def search():
    class_list = []
    if request.method == "POST":
        form = SearchForm()
        searched = form.searched.data
        
    if len(searched) == 0:
        return render_template('index.html')

    filtered = filter_search(searched)
    return render_template("search.html", searched=searched, form = form, filtered = filtered)

@app.route("/add_class/<class_code>/<section_num>", methods = ["POST"])
def add_class(class_code, section_num):
    if request.method == "POST":
        course_query = Courses.query.filter_by(user_id=session["user_id"], class_code=class_code).count()
        course_exists = False if course_query == 0 else True

        if not course_exists:
            class_file = open(class_json_path)
            data = json.load(class_file)

            ratings_file = open(class_prof_rating_path)
            ratings_data = json.load(ratings_file)
            
            course_name = data[class_code]["Class Title"]
            credit_hours = data[class_code]["Credit Hours"]
            professor = data[class_code]["Professors"]
            time = data[class_code]["Sections"][int(section_num) - 1]["Times"]
            time_list = time.split(" ")
            print(time_list)

            #find ratings of professor
            prof_rating = "N/A"
            if professor in ratings_data:
                prof_rating = ratings_data[professor]["Level of Difficulty"]

            days_in_week = {}
            for j, ele in enumerate(time_list):
                if ele[0].isupper():
                    for i, char in enumerate(ele):
                        if not char.isupper():
                            continue
                        if days_map[char] not in days_in_week:
                            days_in_week[days_map[char]] = time_list[j + 1].rstrip(";")
                        else:   #if in seen, must have encountered Thursday. can't fall into else statement unless T has been added and Th is found. 
                            days_in_week[days_map["Th"]] = time_list[j + 1].rstrip(";")
                        
            for day in days_in_week:
                curr_time = days_in_week[day]

                #creating datetime object

                # start_time = curr_time.split("-")[0]
                # # print(start_time)
                
                # if ":" not in start_time:
                #     time_obj = datetime.time(int(start_time))
                #     # print(time_obj)
                # else:
                #     time_split = start_time.split(":")
                #     time_obj = datetime.time(int(time_split[0]), int(time_split[1][:2]))
                #     # print(time_obj)

                new_class = Courses(user_id = session["user_id"], class_code=class_code, class_title=course_name, 
                section_number = section_num, credit_hours=credit_hours, day_of_week = day, time = curr_time, professor_name = professor, professor_rating=prof_rating, section_number_str=str(section_num))
                db.session.add(new_class)
                db.session.commit()
                print("class added to db.")
                # flash("class added to db.", category="success")
        else:
            print("course already exists in db.")
            # flash("course already exists in db.", category="error")
                # classes = Courses.query.filter_by()
                # classes = classes.filter(Courses.user_id)
                # rows = classes.statement.execute().fetchall()
                # for row in rows:
                #     print(row)

        return redirect("/")

@app.route("/remove_class/<class_code>/<section_num>", methods = ["POST"])
def remove_class(class_code, section_num):
    if request.method == "POST":
        class_to_delete = Courses.query.filter_by(user_id=session["user_id"], class_code=class_code, section_number = section_num).first()
        
        # print(class_to_delete.class_code)
        # print(class_to_delete.section_number)

        db.session.delete(class_to_delete)
        db.session.commit()
        print("class deleted successfully.")

        full_name = session["user"]["userinfo"]["name"]
        user_courses = Courses.query.filter_by(user_id=session["user_id"])
        # for course in user_courses:
        #     print(course.class_title)
        #     print(course.class_code)
        #     print(course.section_number)

        monday = user_courses.filter_by(day_of_week="Monday").order_by(Courses.time.desc())
        tuesday = user_courses.filter_by(day_of_week="Tuesday").order_by(Courses.time.desc())
        wednesday = user_courses.filter_by(day_of_week="Wednesday").order_by(Courses.time.desc())
        thursday = user_courses.filter_by(day_of_week="Thursday").order_by(Courses.time.desc())
        friday = user_courses.filter_by(day_of_week="Friday").order_by(Courses.time.desc())

        return render_template("index.html", name = full_name, monday=monday, tuesday=tuesday, wednesday=wednesday, thursday=thursday, friday=friday)
    


if __name__ == '__main__':
    app.run(threaded=True, port=5000, debug=True)
