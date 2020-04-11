# Made using https://flask.palletsprojects.com/ as a reference

import sys
import os
from flask import Flask, url_for, redirect, g, render_template, request, safe_join, send_from_directory
import mysql.connector
import hashlib

# try and get the database password from env variable
if not ('DB_PASS' in os.environ):
  raise ValueError('Cannot find environment variable "DB_PASS"')

# create and configure the Flask application
app = Flask(__name__)
app.config.update(DB_USER='root', DB_HOST='127.0.0.1', DB_PASS=(os.environ['DB_PASS']), DB_NAME='imageplanet', DB_PARAM='db')       # database information
app.config['UPLOAD_DIRECTORY'] = 'user-images'                                                                                      # upload image directory
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024                                                                                 # max file size (15 MB)

# handle home page
@app.route('/')
def send_home_page():
  return redirect(url_for('static', filename='index.html'))
  
# handle image upload form
@app.route('/upload-image', methods=['GET', 'POST'])
def handle_image_upload():

  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  # check for actual upload versus form view
  if request.method == 'GET':
    return render_template('upload-image.html', error_str='', success_str='')
  else:
    
    # grab data from form
    title = request.form['title']
    if title.strip() == '':
      title = 'No Title Given'
    description = request.form['description']
    if description.strip() == '':
      description = 'No Description Given'
      
    # get the image
    image = request.files['img']
    if image.filename == '':
      return render_template('upload-image.html', error_str='Error: No image file selected for upload. Please select an image to upload and try again.', success_str='')
    
    # check if the image is an allowed format
    file_extension = ''
    if image.mimetype == 'image/bmp':
      file_extension = '.bmp'
    elif image.mimetype == 'image/gif':
      file_extension = '.gif'
    elif image.mimetype == 'image/jpeg':
      file_extension = '.jpg'
    elif image.mimetype == 'image/png':
      file_extension = '.png'
    else:
      return render_template('upload-image.html', error_str='Error: Unsupported image format. Only BMP, GIF, JPEG, and PNG file formats are supported.', success_str='')
      
    # now read the file and generate a hash of it for the filename
    img_hash = hashlib.sha384()
    img_hash.update(image.read())
    img_filename = img_hash.hexdigest() + file_extension
    image.stream.seek(0)
    
    # now save the file
    image.save(safe_join(app.config['UPLOAD_DIRECTORY'], img_filename))
    
    # finally save the details to the database
    db_cursor.execute('INSERT INTO images (userid, imgtitle, imgfile, imgdesc, likes) VALUES (0, %s, %s, %s, 0)', (title, img_filename, description))
    db.commit()
    
    return render_template('upload-image.html', error_str='', success_str=(url_for('send_user_image', img_name=img_filename)))


# send user images
@app.route('/img/<img_name>')
def send_user_image(img_name):
  return send_from_directory(app.config['UPLOAD_DIRECTORY'], img_name)
    

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
def close_db(ex):
  if app.config['DB_PARAM'] in g:
    g.pop(app.config['DB_PARAM']).close()
  
# grab a copy of the database  
def get_database(db_name=None):
  try:
    if db_name:
      db = mysql.connector.connect(host=app.config['DB_HOST'], user=app.config['DB_USER'], password=app.config['DB_PASS'], database=db_name)
    else:
      db = mysql.connector.connect(host=app.config['DB_HOST'], user=app.config['DB_USER'], password=app.config['DB_PASS'])
  except Exception as ex:
    sys.stderr.write('Error Connecting to Database\n')
    raise ex
    
  return db
  