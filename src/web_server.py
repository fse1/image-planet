# Made using https://flask.palletsprojects.com/ as a reference

from flask import Flask, url_for, redirect
app = Flask(__name__)


@app.route('/')
def send_home_page():
  return redirect(url_for('static', filename='index.html'))

