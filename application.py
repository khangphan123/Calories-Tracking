import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from flask_mail import Mail, Message

from helper import login_required, error, count_macros
app = Flask(__name__)
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_PORT"] = 587
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
mail = Mail(app)

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///fitness.db")



@app.route("/login", methods = ["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return error("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return error("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        
        if len(rows) != 1  or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return error("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect("/")

@app.route("/register", methods = ["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if not username:
            return error("Please enter username")
        if not email:
            return error("Please enter email")
        if not password or not confirmation:
            return error("Please enter your password")
        if password != confirmation:
            return error("Your password do not match")
        hash = generate_password_hash(password)
        
        
        try:
            db.execute("INSERT INTO users (username, email, hash) VALUES (?,?,?)", username, email, hash)
            # message = Message("You are registered!", recipients=[email])
            # mail.send(message)
            flash("Register succesful")
            return redirect("/login")
        except:
            return error("Username already existed")
        
    else:
        return render_template("register.html")
        
@app.route("/information", methods = ["GET", "POST"])
def information():
    if request.method == "POST":
        age = request.form.get("age")
        gender = request.form.get("gender")
        weight = request.form.get("weight")
        height = request.form.get("height")
        BMI = float(weight) / (float(height) * float(height))
        if not age:
            return error("Please enter your age")
        if not weight:
            return error("Please enter your weight")
        if not height:
            return error("Please enter your height")
        db.execute("INSERT INTO informations (age, gender, weight, height, BMI, user_id) VALUES (:age,:gender,:weight,:height,:BMI,:user_id)", age = age, gender = gender, weight = weight, height = height, BMI = BMI, user_id = session["user_id"])
        flash("Information entered")
        return redirect("/")
    else:
        return render_template("information.html")

@app.route("/")
@login_required
def index():
    user_id = session["user_id"]
    result = db.execute("SELECT user_id, age, gender, weight, height, BMI FROM informations WHERE user_id =:user_id", user_id = session['user_id'])
    if len(result) > 0:
        information = result[0]
    else:
        information = result
    #Finding Basal Metaboloc rate using Mifflin-St Jeor equation
    BMR = 0
    current_calories_intake = 0
    macros = 0
    calories_per_day = 0
    macros_for_goal = 0
    info = db.execute("SELECT age, gender,weight, height FROM informations WHERE user_id = :user_id", user_id = session["user_id"])
    if len(result) > 0:
        info = info[0]
        age = info["age"]
        gender = info["gender"]
        weight = info["weight"]
        height = info["height"] * 100
        if gender == "Male":
            BMR = 10 * weight + 6.25 * height - 5 * age + 5
        elif gender == "Female":
            BMR = 10 * weight + 6.25 * height - 5 * age - 161
        
        result2 = db.execute("SELECT ratio FROM activity WHERE user_id = :user_id", user_id = session['user_id'])
        if len(result2) < 1:
            ratio = 0
        else:
            ratio = result2[0]['ratio']
            result3 = db.execute("SELECT days_goal, goal_weight FROM activity WHERE user_id = :user_id", user_id = session['user_id'])
            days_goal = result3[0]['days_goal']
            goal_weight = result3[0]['goal_weight']
            current_calories_intake = round(BMR * ratio)
            weight_needed = weight - goal_weight
            
            calories_needed = weight_needed * 7700
            calories_adjustment = calories_needed / days_goal
            calories_per_day = round(current_calories_intake - calories_adjustment)
            if calories_per_day < 0:
                return error("This goal is impossible")
            # Calculate how many carb, protein, fat needed for a day using a count_macros function from helper
            macros = count_macros(current_calories_intake)
            macros_for_goal = count_macros(calories_per_day)
            db.execute("INSERT INTO nutrition (user_id, calories, carb, protein, fat) VALUES (?,?,?,?,?)", user_id, calories_per_day, macros_for_goal[1], macros_for_goal[0], macros_for_goal[2])
            db.execute("INSERT INTO remaining_macros(user_id, remaining_calories, remaining_carb, remaining_protein, remaining_fat) VALUES (?,?,?,?,?)", user_id, calories_per_day, macros_for_goal[1], macros_for_goal[0], macros_for_goal[2])
    
    return render_template("index.html", information = information, current_calories_intake = current_calories_intake, macros = macros, calories_per_day = calories_per_day, macros_for_goal = macros_for_goal)
        
@app.route("/planning", methods = ["GET", "POST"])
@login_required
def planning():
    if request.method == "POST":
        user_id = session["user_id"]
        goal_weight = request.form.get("weight_goal")
        if not goal_weight:
            return error("Please enter your goal weight")
        days_goal = request.form.get("days_goal")
        if not days_goal:
            return error("Please enter your days goal")
        daily_activity = request.form.get("daily_activity")
        ratio = 0
        if daily_activity == "Sedentary: little or no exercise":
            ratio = 1.2
        elif daily_activity == "Lightly active(light exercise/sport 1-3 days/week)":
            ratio = 1.375
        elif daily_activity == "Moderate exercise(moderate exercise/sports 3-5 days/week)":
            ratio = 1.55
        elif daily_activity == "Very active(hard exercise/sports 6-7 days a week)":
            ratio = 1.725
        elif daily_activity == "Extra active(very hard exercise/sports & physical job or 2x training":
            ratio = 1.9
        
        db.execute("INSERT INTO activity (goal_weight, ratio, user_id, days_goal) VALUES (?,?,?,?) ", goal_weight, ratio, user_id, days_goal)
        return redirect("/")
        
    else:
        return render_template("planning.html")

@app.route("/tracking", methods = ["GET", "POST"])
@login_required
def tracking():
    if request.method == "POST":
        food = request.form.get("food")
        calories = float(request.form.get("calories"))
        gram_carb = float(request.form.get("gram_carb"))
        gram_protein = float(request.form.get("gram_protein"))
        gram_fat = float(request.form.get("gram_fat"))
        user_id = session['user_id']
        db.execute("INSERT INTO foods (user_id, food, calories, gram_carb, gram_protein, gram_fat) VALUES (?,?,?,?,?,?)", user_id, food, calories, gram_carb, gram_protein, gram_fat)
        result = db.execute("SELECT * FROM remaining_macros WHERE user_id =:user_id", user_id = user_id)
        default_calories = float(result[0]["remaining_calories"])
        default_carb = float(result[0]["remaining_carb"])
        default_protein = float(result[0]["remaining_protein"])
        default_fat = float(result[0]["remaining_fat"])
        
        remaining_calories = default_calories -  calories
        remaining_carb = default_carb - gram_carb
        remaining_protein = default_protein - gram_protein 
        remaining_fat = default_fat - gram_fat
        db.execute("UPDATE remaining_macros SET remaining_calories = :remaining_calories, remaining_carb = :remaining_carb, remaining_protein =:remaining_protein, remaining_fat =:remaining_fat WHERE user_id = :user_id"
        , remaining_calories = remaining_calories, remaining_carb = remaining_carb, remaining_protein = remaining_protein, remaining_fat = remaining_fat, user_id = user_id)
        # db.execute("INSERT INTO remaining_macros(user_id, remaining_calories, remaining_carb, remaining_protein, remaining_fat) VALUES (?,?,?,?,?)", user_id, remaining_calories, remaining_carb, remaining_protein, remaining_fat)
        return redirect("/tracked")
    else:
        return render_template("tracking.html")


@app.route("/tracked", methods = ["GET", "POST"])
@login_required
def tracked():
    if request.method == "POST":
        user_id = session['user_id']
        result = db.execute("SELECT * FROM nutrition WHERE user_id = :user_id", user_id = user_id)
        if len(result) > 0:
            information = result[0]
        else:
            information = result
        calories = information['calories']
        carb = information['carb']
        protein = information['protein']
        fat = information['fat']
        db.execute("UPDATE remaining_macros SET remaining_calories = :remaining_calories, remaining_carb = :remaining_carb, remaining_protein =:remaining_protein, remaining_fat =:remaining_fat WHERE user_id = :user_id",
        remaining_calories = calories, remaining_carb = carb, remaining_protein = protein, remaining_fat = fat, user_id = user_id)
        return redirect("/tracked")
    else:
        user_id = session['user_id']
        result = db.execute("SELECT * FROM remaining_macros WHERE user_id = :user_id", user_id = user_id)
        if len(result) > 0:
            information = result[0]
        else:
            information = result
        remaining_calories = information["remaining_calories"]
        remaining_carb = information["remaining_carb"]
        remaining_protein = information["remaining_protein"]
        remaining_fat = information["remaining_fat"]
        return render_template("tracked.html", remaining_calories = remaining_calories, remaining_carb = remaining_carb, remaining_protein = remaining_protein, remaining_fat = remaining_fat)

@app.route("/exercising", methods = ["GET", "POST"])
@login_required
def exercising():
    if request.method == "POST":
        calories_burned = int(request.form.get("calories_burned"))
        user_id = session['user_id']
        result = db.execute("SELECT * FROM remaining_macros WHERE user_id = :user_id", user_id = user_id)
        if len(result) > 0:
            information = result[0]
        else:
            information = result
        remaining_calories = information["remaining_calories"]
        new_calories = remaining_calories + calories_burned
        db.execute("UPDATE remaining_macros SET remaining_calories = :new_calories WHERE user_id = :user_id", new_calories = new_calories, user_id = user_id)
        return redirect("/tracked")
    else:
        return render_template("exercising.html")
if __name__ == "__main__":
    app.run()




