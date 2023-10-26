import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from extra import login_required
import gunicorn
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

#app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SECRET_KEY"]="27182818"
#app.config["SESSION_TYPE"] = "filesystem"
#Session(app)

db = SQL("sqlite:///database.db")

@app.route('/')
@login_required
def index():
   if session['mode']: return redirect("/teacher_mode")
   else: return redirect("/student_mode")
   return render_template("index.html", message="Hello World") 

@app.route("/login", methods=["GET", "POST"])
def login():
   session.clear()
   if request.method == "POST":
      if not request.form.get("username"):
         return render_template("error.html", msg="Please Enter your username", prev="login")
      if not request.form.get("password"):
         return render_template("error.html", msg="Please Enter your password", prev="login")
      info = db.execute("SELECT * FROM users WHERE username=?", request.form.get("username"))
      if not len(info) or not check_password_hash(info[0]["password"],request.form.get("password")):
         return render_template("error.html", msg="The password and the username doesn't match", prev="login")
      session["user_id"] = info[0]['id']
      session["mode"] = info[0]['mode']
      if session["mode"]: session["teacher"]=False
      return redirect ('/')
   else : return render_template("login.html")

@app.route("/logout")
def logout():
   session.clear()
   return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
   if request.method == "POST":
      if not request.form.get("username"):
         return render_template("error.html", msg="Please make sure you have your name", prev="register")
      if not request.form.get("password"):
         return render_template("error.html", msg="Please make sure you have your password for security sake", prev="register")
      if not request.form.get("confirmation"):
         return render_template("error.html", msg="Please make sure you have confirmed you password in case you had typos", prev="register")
      if request.form.get("mode")!="teacher" and request.form.get("mode")!="student": 
         return render_template("error.html", msg="Please make sure you have entered the mode (If you tried to inspect, not this time :P)", prev="register")
      if request.form.get("password")!=request.form.get("confirmation"):
         return render_template("error.html", msg="Please make sure that you entered the same password while confirming again", prev="register")
      mode = None
      if request.form.get("mode")=="teacher": mode=1
      else: mode=0
      password=generate_password_hash(request.form.get("password"))
      name = request.form.get("username")
      validation = db.execute("SELECT username FROM users WHERE username=?",name)
      if len(validation): return render_template("error.html", msg="Please consider using your true name!!! And the name already exists!", prev="register")
      db.execute("INSERT INTO users (username, mode, password) VALUES (?,?,?)", name, mode, password)
      return redirect('/')
   elif request.method=="GET":
      return render_template("register.html")

@app.route("/teacher_mode_validation", methods=["GET", "POST"])
@login_required
def validating():
   if not session['mode']: return redirect('/')
   if session["teacher"]: return redirect("/teacher_mode")
   if request.method == "POST":
      if not request.form.get("secret"):
         return render_template("error.html", msg="Please enter the secret key", prev="teacher_mode_validation")
      if request.form.get("secret") != "27182818":
         return render_template("error.html", msg="Please make sure you input the correct secret key", prev="teacher_mode_validation")
      session["teacher"]= True 
      return redirect("/teacher_mode")
   else: return render_template("teacher_validation.html")

@app.route("/teacher_mode", methods=["POST", "GET"])
@login_required
def teacher():
   if not session['mode']: return redirect('/')
   if not session["teacher"]:return redirect("/teacher_mode_validation")  
   if request.method == "POST":
      if not request.form.get("exercise"): return render_template("error.html", msg="Please name the exercise", prev="teacher_mode")
      if not request.form.get("format"): return render_template("error.html", msg="Please ensure the format", prev="teacher_mode")
      if not request.form.get("quantity"): return render_template("error.html", msg="Please ensure the quantity", prev="teacher_mode")
      quan = int(request.form.get("quantity"))
      ex = request.form.get("exercise")
      pon= request.form.get("format")
      u = db.execute("SELECT username FROM users WHERE id=?", session["user_id"])
      u = u[0]['username']
      exist = db.execute("SELECT name FROM history WHERE name=? AND by=?", f"{u}{ex}",u)
      if pon not in ["long", "short", "blank"]:return render_template("error.html", msg="Invalid format", prev="teacher_mode")
      if (len(exist)): return render_template("error.html", msg="The same name already exists", prev="teacher_mode")
      db.execute("CREATE TABLE ? (id INTEGER, username TEXT, format TEXT, PRIMARY KEY (id))", f"{u}{ex}")
      for i in range(1, quan+1):
         db.execute("ALTER TABLE ? ADD ? TEXT", f"{u}{ex}", f"no{i}")
      db.execute("INSERT INTO history (name, quan, format,by) VALUES(?,?,?,?)", f"{u}{ex}", quan, pon,u)
      history = db.execute("SELECT * FROM history WHERE by=?", u)
      history.reverse()
      return render_template("teacher_mode.html", message=f"Exercise '{ex}' generated successfully", history=history)
   else:
      u = db.execute("SELECT username FROM users WHERE id=?", session["user_id"])
      history = db.execute("SELECT * FROM history WHERE by=?", u[0]['username'])
      history.reverse()
      return render_template("teacher_mode.html", history=history)

@app.route("/details", methods=['GET', "POST"])
@login_required
def view_details():
   if not session["mode"]: return redirect("/")
   if not session["teacher"]:return redirect("/teacher_mode_validation")
   if request.method=="POST":
      if not request.form.get("e"): return render_template("error.html", msg="Please don't inspect", prev="teacher_mode")
      exname = request.form.get("e")
      valida = db.execute("SELECT name FROM history WHERE name=?", exname)
      if (len(valida)==0): return render_template("error.html", msg="Please don't inspect", prev="teacher_mode")
      Lists = db.execute("SELECT username FROM ?", exname)
      return render_template("lists.html", Lists=Lists, exname=exname, todo=False)
   else:
      if not request.args.get("goo") or not request.args.get("eee"): render_template("error.html", msg="Please make sure all requirements are filled", prev="teacher_mode")
      exname = request.args.get("eee")
      Lists = db.execute("SELECT username FROM ?", exname)
      numberof = db.execute("SELECT format FROM history WHERE name=?",exname)
      if (len(numberof)==0): return render_template("error.html", msg="Please don't inspect", prev="teacher_mode")
      data = db.execute("SELECT * FROM ? WHERE username=?", exname, request.args.get('goo'))
      FORMAT = numberof[0]['format']
      data=data[0]
      data.pop("id", None)
      data.pop("username", None)
      data.pop("format", None)
      return render_template("lists.html", Lists=Lists, exname=exname, todo=True, Format=FORMAT, data=data, USER=request.args.get("goo"))

@app.route("/student_mode")
@login_required
def student_mode():
   if session["mode"]: return redirect('/')
   return render_template("student.html")

@app.route("/exercise_mode", methods=["POST", "GET"])
@login_required
def working():
   if session["mode"]: return redirect('/')
   if request.method=="GET":
      return redirect("/")
   elif request.method=="POST":
      if not request.form.get("ex-name"): return render_template("error.html", msg="Please confirm the exercise name", prev="exercise_mode")
      exercise = request.form.get("ex-name")
      tov=db.execute("SELECT * FROM history WHERE name=?", exercise)
      if (len(tov)==0): return render_template("error.html", msg="The excercise name doesn't match", prev="exercise_mode")
      FORMAT=tov[0]["format"]
      currentu = db.execute("SELECT username FROM users WHERE id=?", session["user_id"])
      check = db.execute("SELECT * FROM ? WHERE username=?", exercise, currentu[0]["username"])
      session["ex"]=tov[0]["id"]
      if (len(check)==0):
         toadd = db.execute("SELECT started FROM history WHERE name=?", exercise)
         toadd = toadd[0]['started']+1
         db.execute("UPDATE history SET started=? WHERE name=?", toadd, exercise)
         db.execute("INSERT INTO ? (username, format) VALUES(?, ?)", exercise, currentu[0]["username"], FORMAT)
         can = False
      else:
         tominus = db.execute("SELECT submitted FROM history WHERE id=?", tov[0]['id'])
         tominus = tominus[0]['submitted']-1
         db.execute("UPDATE history SET submitted=? WHERE id=?",tominus, tov[0]['id'])
         check = check[0]
         check.pop("id", None)
         check.pop("username", None)
         check.pop("format", None)
         can = True
      return render_template("exercise_mode.html", quan=range(1,tov[0]["quan"]+1), Format=FORMAT, exname=exercise, data=check, can=can)

@app.route("/submitted", methods=["POST", "GET"])
@login_required
def submission():
   if session["mode"]: return redirect("/")
   if request.method=="GET":
      return redirect("/")
   elif request.method=="POST":
      exer = db.execute("SELECT * FROM history WHERE id=?", session["ex"])
      exna = exer[0]["name"]
      username = db.execute("SELECT username FROM users WHERE id=?", session["user_id"])
      username = username[0]['username']
      exerc = range(1, exer[0]['quan']+1)
      for i in exerc:
         db.execute("UPDATE ? SET ?=? WHERE username=?", exna, f"no{i}", request.form.get(f"no{i}"), username)
      subm = db.execute("SELECT submitted FROM history WHERE id=?", session["ex"])
      submm=1+subm[0]["submitted"]
      db.execute("UPDATE history SET submitted=? WHERE id=?", submm, session['ex'])
      return redirect("/student_mode")