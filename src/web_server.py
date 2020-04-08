# Made using https://flask.palletsprojects.com/ as a reference

import sys
import os
from flask import Flask, url_for, redirect, g
import mysql.connector

# try and get the database password from env variable
try:
  os.environ['DB_PASS']
except Exception as ex:
  sys.stderr.write('Cannot find environment variable "DB_PASS"\n')
  raise ex

# create and configure the Flask application
app = Flask(__name__)
app.config.update(DB_USER='root', DB_HOST='127.0.0.1', DB_PASS=(os.environ['DB_PASS']))



@app.route('/')
def send_home_page():
  return redirect(url_for('static', filename='index.html'))

@app.cli.command('init-db')
def init_database():
  try:
    db = get_database()
    db_cursor = db.cursor()
    with app.open_resource('initdb.sql') as schema:
      commands = schema.read().decode('utf-8')
      for e in db_cursor.execute(commands, multi=True):
        pass
    db.commit()
    db.close()
  except Exception as ex:
    sys.stderr.write('Error Setting Up Database\n')
    raise ex
  
@app.teardown_appcontext
def close_db(arg):
  if 'db' in g:
    g.db.close()
  
# grab a copy of the database  
def get_database():
  try:
    db = mysql.connector.connect(host=app.config['DB_HOST'], user=app.config['DB_USER'], password=app.config['DB_PASS'])
  except Exception as ex:
    sys.stderr.write('Error Connecting to Database\n')
    raise ex
    
  return db
  