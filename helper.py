import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps
def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def error(message, code=400):
    return render_template("Error.html", message = message)

def count_macros(current_calories_intake):
    carb_calories = current_calories_intake * 0.45
    fat_calories = current_calories_intake * 0.2
    protein_calories = current_calories_intake * 0.35
    carb_gram = round(carb_calories / 4)
    protein_gram = round(protein_calories / 4) 
    fat_gram = round(fat_calories / 4)
    return [protein_gram, carb_gram, fat_gram]