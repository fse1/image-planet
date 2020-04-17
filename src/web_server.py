# Made using https://flask.palletsprojects.com/ as a reference

import sys
import os
from flask import Flask, url_for, redirect, g, render_template, request, safe_join, send_from_directory, escape, json
from flask_socketio import SocketIO, join_room
import mysql.connector
import hashlib

# try and get the database password and username from env variable
if not ('DB_USER' in os.environ):
  raise ValueError('Cannot find environment variable "DB_USER"')
if not ('DB_PASS' in os.environ):
  raise ValueError('Cannot find environment variable "DB_PASS"')

# create and configure the Flask application
app = Flask(__name__)
app.config.update(DB_USER=(os.environ['DB_USER']), DB_HOST='127.0.0.1', DB_PASS=(os.environ['DB_PASS']), DB_NAME='imageplanet', DB_PARAM='db')        # database information
app.config['UPLOAD_DIRECTORY'] = 'user-images'                                                                                                        # upload image directory
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024                                                                                                   # max file size (15 MB)
app.config['MAX_COMMENT_LENGTH'] = 50                                                                                                                 # max length of comment
new_app = SocketIO(app)


# define a class to hold information about images
class ImageInfo():

  def __init__(self):
    self.id = 0
    self.userid = 0
    self.title = ''
    self.username = ''
    self.path = ''
    self.likes = 0
    self.description = ''
    self.comments = []
   
# define a class to hold information about user messages
class MessageInfo():

  def __init__(self):
    self.userid = 0
    self.username = ''
    self.message = ''
    
# define a class to hold information about users
class UserInfo():

  def __init__(self):
    self.id = 0
    self.name = ''
    self.profile_text = ''


# handle home page
@app.route('/')
def generate_home_page():

  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  follow = []
  recent = []
  
  db_cursor.execute('SELECT imageid, imgtitle, userid, imgfile, imgdesc, likes FROM images ORDER BY imageid DESC LIMIT 3')
  
  # get data on the lastest three images
  for (imageid, imgtitle, userid, imgfile, imgdesc, likes) in db_cursor:
    image = ImageInfo()
    image.id = imageid
    image.userid = userid
    image.title = imgtitle
    image.username = 'Anonymous User'
    image.path = url_for('send_user_image', img_name=imgfile)
    image.likes = likes
    image.description = imgdesc
    recent.append(image)
  
  # now get the comments for each recent image
  for image in recent:
    db_cursor.execute('SELECT userid, comtext FROM comments WHERE imageid=%s', (image.id,))
    for (userid, comtext) in db_cursor:
      com = MessageInfo()
      com.userid = userid
      com.username = 'Anonymous User'
      com.message = comtext
      image.comments.append(com)
  
  return render_template('index.html', follower_images=follow, recent_images=recent)
  
@app.route('/submit-comment', methods=['POST'])
def process_comment():
  
  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  imageid = request.form['imgid']
  comtext = request.form['comment'].strip()
  
  if len(comtext) > app.config['MAX_COMMENT_LENGTH']:
    return 'Comment too long!', 400
  
  # make sure the image exists
  db_cursor.execute('SELECT userid FROM images WHERE imageid=%s', (imageid,))
  if (len(db_cursor.fetchall())) != 1:
    return 'Image does not exist!', 400
  
  # now add the comment to the database
  db_cursor.execute('INSERT INTO comments (imageid, userid, comtext) VALUES (%s, 0, %s)', (imageid, comtext))
  db.commit()
  
  # now send the new comment to all connected clients
  send_data = {}
  com_info = MessageInfo()
  com_info.userid = 0
  com_info.username = 'Anonymous User'
  com_info.message = comtext
  send_data['imageid'] = imageid
  send_data['html'] = render_template('one-comment.html', comment=com_info)
  new_app.emit('new-comment-full', send_data, room='general-notifications')
  
  return 'Successfully submitted comment!'
  
@app.route('/submit-like', methods=['POST'])
def process_like():

  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  imageid = request.form['imgid']

  # make sure the image exists
  db_cursor.execute('SELECT userid FROM images WHERE imageid=%s', (imageid,))
  if (len(db_cursor.fetchall())) != 1:
    return 'Image does not exist!', 400
  
  # now increment the like count
  db_cursor.execute('UPDATE images SET likes=likes+1 WHERE imageid=%s', (imageid,))
  db.commit()
  
  # now send the new like to all connected clients
  send_data = {}
  send_data['imageid'] = imageid
  new_app.emit('new-like', send_data, room='general-notifications')
  
  return 'Successfully submitted like!'
  
# handle sending all images
@app.route('/images')
def generate_image_gallery():

  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  display_images = []
  
  db_cursor.execute('SELECT userid, imgfile FROM images')
  
  # get data on each image
  for (userid, imgfile) in db_cursor:
    image = ImageInfo()
    image.userid = userid
    image.path = url_for('send_user_image', img_name=imgfile)
    display_images.append(image)
  
  return render_template('images.html', images=display_images)
  
# handle sending user list
@app.route('/users')
def generate_user_list():
  
  user_list = []
  
  user = UserInfo()
  user.id = 0
  user.name = 'Anonymous User'
  user_list.append(user)
  
  return render_template('userlist.html', users=user_list)
  
  
# handle sending user profile page
@app.route('/users/0')
def generate_user_page():
  
  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  user = UserInfo()
  user.id = 0
  user.name = 'Anonymous User'
  user.profile_text = 'No profile description.'
  
  image_list = []
  
  db_cursor.execute('SELECT imageid, imgtitle, imgfile, imgdesc, likes FROM images')
  
  # get data on all images
  for (imageid, imgtitle, imgfile, imgdesc, likes) in db_cursor:
    image = ImageInfo()
    image.id = imageid
    image.userid = user.id
    image.title = imgtitle
    image.username = user.name
    image.path = url_for('send_user_image', img_name=imgfile)
    image.likes = likes
    image.description = imgdesc
    image_list.append(image)
  
  # now get the comments for each recent image
  for image in image_list:
    db_cursor.execute('SELECT userid, comtext FROM comments WHERE imageid=%s', (image.id,))
    for (userid, comtext) in db_cursor:
      com = MessageInfo()
      com.userid = userid
      com.username = 'Anonymous User'
      com.message = comtext
      image.comments.append(com)
  
  return render_template('user.html', user=user, images=image_list)
  
# handle display of the login/registration form
@app.route('/login-or-register')
def display_login_register_page():
  return render_template('login.html')
  
# handle display of direct messaging
@app.route('/direct-msg')
def generate_direct_message_page():

  return render_template('chat.html')

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
    
    # generate data to send over websocket connection
    send_data = {}
    image_data = ImageInfo()
    image_data.id = db_cursor.lastrowid
    image_data.userid = 0
    image_data.title = title
    image_data.username = 'Anonymous User'
    image_data.path = url_for('send_user_image', img_name=img_filename)
    image_data.likes = 0
    image_data.description = description
    send_data['userid'] = image_data.userid
    send_data['imageid'] = image_data.id
    send_data['html'] = render_template('one-image.html', image=image_data)
    send_data['thumbnailhtml'] = render_template('one-image-thumbnail.html', image=image_data)
    new_app.emit('new-image-full', send_data, room='general-notifications')
    
    
    return render_template('upload-image.html', error_str='', success_str=(url_for('send_user_image', img_name=img_filename)))


# send user images
@app.route('/img/<img_name>')
def send_user_image(img_name):
  return send_from_directory(app.config['UPLOAD_DIRECTORY'], img_name)
    
# handle joining general rooms
@new_app.on('join-general-room')
def join_general_room():
  join_room('general-notifications')


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
  