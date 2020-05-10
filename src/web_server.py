# Made using https://flask.palletsprojects.com/ as a reference

import sys
import os
from flask import Flask, url_for, redirect, g, render_template, request, safe_join, send_from_directory, make_response
from flask_socketio import SocketIO, join_room, rooms
import mysql.connector
import hashlib
import secrets
import datetime

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
app.config['MAX_COMMENT_LENGTH'] = 50                                                              
                                                   # max length of comment
app.config.update(SC_N=16384, SC_R=8, SC_P=1)                                                                                                         # scrypt parameters
app.config.update(USERNAME_MIN=3, USERNAME_MAX=15, PASSWORD_MIN=8, PASSWORD_MAX=100)                                                                  # username and password length requirements
app.config.update(PASS_SALT_SIZE=16, SESSION_TOKEN_SIZE=32, CSRF_TOKEN_SIZE=32, TOKEN_SALT=b'token', TOKEN_EXPIRATION=datetime.timedelta(days=7))     # security info
app.config.update(SESSION_COOKIE_NAME='session-token', USER_PARAM='current_user')                                                                     # security info continued
app.config.update(DEFAULT_PROFILE_PIC='default.jpg', DEFAULT_PROFILE_DESCRIPTION='No profile description.')                                           # default database fields
app.config.update(USER_ROOM_PREFIX='user-', GENERAL_ROOM='general-notifications')                                                                     # socketio room information
new_app = SocketIO(app, cors_allowed_origins='*')


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
    self.profile_pic = ''
    self.salt = b''
    self.passhash = b''
    self.session_hash = b''
    self.session_expiration = datetime.date.today()
    self.csrf_token = ''
    self.unread_messages = False
    
# define a class to hold information about direct messages
class DirectMsgInfo():

  def __init__(self):
    self.dmid = 0
    self.userid = 0
    self.username = ''
    self.read = False
    self.empty = False


# check the session token
def check_session_token(db, cursor):
  
  # try to get token from cookies
  token = request.cookies.get(app.config['SESSION_COOKIE_NAME'])
  
  if not token:
    g.setdefault(app.config['USER_PARAM'], default=None)
    return
  
  try:
    token_hash = hashlib.scrypt(b''.fromhex(token), salt=app.config['TOKEN_SALT'], n=app.config['SC_N'], r=app.config['SC_R'], p=app.config['SC_P'])
  except Exception:
    g.setdefault(app.config['USER_PARAM'], default=None)
    return
  
  cursor.execute('SELECT userid, username, sessionexpiration, csrftoken FROM users WHERE sessioncookiehash=%s', (token_hash.hex(),))
  data = cursor.fetchall()
  
  if not (len(data) == 1):
    g.setdefault(app.config['USER_PARAM'], default=None)
    return
  
  # get information about user
  user = UserInfo()
  
  for (userid, username, sessionexpiration, csrftoken) in data:
    user.id = userid
    user.name = username
    user.session_expiration = sessionexpiration
    user.csrf_token = csrftoken
    
  # make sure the token has not expired, update db if so
  if user.session_expiration <= datetime.date.today():
    cursor.execute('UPDATE users SET sessioncookiehash=NULL, csrftoken=NULL WHERE userid=%s', (user.id,))
    db.commit()
    g.setdefault(app.config['USER_PARAM'], default=None)
    return
    
  # now set the actual user
  g.setdefault(app.config['USER_PARAM'], default=user)

# check for unread messages
def check_unread_messages(cursor, current_user):
  
  if not current_user:
    return
  
  # check for both low and high user ids
  cursor.execute('SELECT dmid FROM directmsg WHERE lowuserid=%s AND lowuserread=0 LIMIT 1', (current_user.id,))
  data = cursor.fetchall()
  
  if (len(data) == 1):
    current_user.unread_messages = True
    return
  
  cursor.execute('SELECT dmid FROM directmsg WHERE highuserid=%s AND highuserread=0 LIMIT 1', (current_user.id,))
  data = cursor.fetchall()
  
  if (len(data) == 1):
    current_user.unread_messages = True
    return
    
  current_user.unread_messages = False
  
# handle home page
@app.route('/')
def generate_home_page():

  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  # try to authenticate the user
  check_session_token(db, db_cursor)
  current_user = g.get(app.config['USER_PARAM'])
  
  # check for unread messages
  check_unread_messages(db_cursor, current_user)
  
  follow = []
  recent = []
  
  if current_user:
    #Get the latest images from users the current users follow.
    db_cursor.execute('SELECT images.imageid, images.imgtitle, images.userid, images.imgfile, images.imgdesc, images.likes, users.username FROM images INNER JOIN followers ON images.userid=followers.followingthisuserid AND followers.userid=%s JOIN users ON images.userid=users.userid ORDER BY images.imageid DESC LIMIT 3',(current_user.id,))
    
    # get data on the lastest three images
    for (imageid, imgtitle, userid, imgfile, imgdesc, likes, username) in db_cursor:
      image = ImageInfo()
      image.id = imageid
      image.userid = userid
      image.title = imgtitle
      image.username = username
      image.path = url_for('send_user_image', img_name=imgfile)
      image.likes = likes
      image.description = imgdesc
      follow.append(image)
    
    # now get the comments for each recent image
    for image in recent:
      db_cursor.execute('SELECT comments.userid, comments.comtext, users.username FROM comments JOIN users ON comments.userid=users.userid WHERE comments.imageid=%s', (image.id,))
      for (userid, comtext, username) in db_cursor:
        com = MessageInfo()
        com.userid = userid
        com.username = username
        com.message = comtext
        image.comments.append(com)
  
  db_cursor.execute('SELECT images.imageid, images.imgtitle, images.userid, images.imgfile, images.imgdesc, images.likes, users.username FROM images JOIN users ON images.userid=users.userid ORDER BY images.imageid DESC LIMIT 3')
  
  
  # get data on the lastest three images
  for (imageid, imgtitle, userid, imgfile, imgdesc, likes, username) in db_cursor:
    image = ImageInfo()
    image.id = imageid
    image.userid = userid
    image.title = imgtitle
    image.username = username
    image.path = url_for('send_user_image', img_name=imgfile)
    image.likes = likes
    image.description = imgdesc
    recent.append(image)
  
  # now get the comments for each recent image
  for image in recent:
    db_cursor.execute('SELECT comments.userid, comments.comtext, users.username FROM comments JOIN users ON comments.userid=users.userid WHERE comments.imageid=%s', (image.id,))
    for (userid, comtext, username) in db_cursor:
      com = MessageInfo()
      com.userid = userid
      com.username = username
      com.message = comtext
      image.comments.append(com)
  
  return render_template('index.html', follower_images=follow, recent_images=recent, cur_user=current_user)
  
@app.route('/submit-comment', methods=['POST'])
def process_comment():
  
  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  # try to authenticate the user
  check_session_token(db, db_cursor)
  current_user = g.get(app.config['USER_PARAM'])
  
  # if not authenticated reject
  if not current_user:
    return 'Not Authenticated!', 403
  
  imageid = request.form['imgid']
  comtext = request.form['comment'].strip()
  
  if len(comtext) > app.config['MAX_COMMENT_LENGTH']:
    return 'Comment too long!', 400
  
  # make sure the image exists
  db_cursor.execute('SELECT userid FROM images WHERE imageid=%s', (imageid,))
  if (len(db_cursor.fetchall())) != 1:
    return 'Image does not exist!', 400
  
  # now add the comment to the database
  db_cursor.execute('INSERT INTO comments (imageid, userid, comtext) VALUES (%s, %s, %s)', (imageid, current_user.id, comtext))
  db.commit()
  
  # now send the new comment to all connected clients
  send_data = {}
  com_info = MessageInfo()
  com_info.userid = current_user.id
  com_info.username = current_user.name
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
  
  # try to authenticate the user
  check_session_token(db, db_cursor)
  current_user = g.get(app.config['USER_PARAM'])
  
  # if not authenticated reject
  if not current_user:
    return 'Not Authenticated!', 403
  
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
  
  # try to authenticate the user
  check_session_token(db, db_cursor)
  current_user = g.get(app.config['USER_PARAM'])
  
  # check for unread messages
  check_unread_messages(db_cursor, current_user)
  
  display_images = []
  
  db_cursor.execute('SELECT userid, imgfile FROM images')
  
  # get data on each image
  for (userid, imgfile) in db_cursor:
    image = ImageInfo()
    image.userid = userid
    image.path = url_for('send_user_image', img_name=imgfile)
    display_images.append(image)
  
  return render_template('images.html', images=display_images, cur_user=current_user)
  
# handle sending user list
@app.route('/users')
def generate_user_list():
  
  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  # try to authenticate the user
  check_session_token(db, db_cursor)
  current_user = g.get(app.config['USER_PARAM'])
  
  # check for unread messages
  check_unread_messages(db_cursor, current_user)
  
  user_list = []
  
  db_cursor.execute('SELECT userid, username FROM users')
  
  for (userid, username) in db_cursor:
    user = UserInfo()
    user.id = userid
    user.name = username
    user_list.append(user)
  
  return render_template('userlist.html', users=user_list, cur_user=current_user)
  
  
# handle sending user profile page
@app.route('/users/<int:user_id>')
def generate_user_page(user_id):
  
  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  # try to authenticate the user
  check_session_token(db, db_cursor)
  current_user = g.get(app.config['USER_PARAM'])
  
  # get information about the requested user
  db_cursor.execute('SELECT username, profilepic, profiledesc FROM users WHERE userid=%s', (user_id,))
  data = db_cursor.fetchall()
  if not (len(data) == 1):
    return 'Not Found!', 404
  
  # check for unread messages
  check_unread_messages(db_cursor, current_user)
  
  user = UserInfo()
  for (username, profilepic, profiledesc) in data:
    user.id = user_id
    user.name = username
    user.profile_text = profiledesc
    user.profile_pic = profilepic
  
  image_list = []
  
  db_cursor.execute('SELECT imageid, imgtitle, imgfile, imgdesc, likes FROM images WHERE userid=%s', (user.id,))
  
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
    db_cursor.execute('SELECT comments.userid, comments.comtext, users.username FROM comments JOIN users ON comments.userid=users.userid WHERE comments.imageid=%s', (image.id,))
    for (userid, comtext, username) in db_cursor:
      com = MessageInfo()
      com.userid = userid
      com.username = username
      com.message = comtext
      image.comments.append(com)
      
  db_cursor.execute('SELECT followingthisuserid FROM followers WHERE userid=%s', (current_user.id,))
  followed = False
  for followingthisuserid in db_cursor:
    if followingthisuserid[0] == user_id:
          followed = True
  
  return render_template('user.html', user=user, images=image_list, cur_user=current_user, followed=followed)
  
# handle display of the login/registration form
@app.route('/login-or-register')
def display_login_register_page():

  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  # try to authenticate the user
  check_session_token(db, db_cursor)
  current_user = g.get(app.config['USER_PARAM'])
  
  # redirect to user page if already logged in
  if current_user:
    return redirect(url_for('generate_user_page', user_id=current_user.id))
  
  return render_template('login.html')
  
# handle user registration
@app.route('/register', methods=['POST'])
def process_registration():
  
  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  # store any errors
  errors = []
  
  # get form parameters
  username = request.form['username']
  password = request.form['password']
  password2 = request.form['password2']
  
  # check form parameters: ascii printable, no leading/trailing whitespace, length requirements
  if not (username.isascii()):
    errors.append('Error: Username contains non-ASCII characters.')
    
  if not (password.isascii()):
    errors.append('Error: Password contains non-ASCII characters.')
    
  if not (username.isprintable()):
    errors.append('Error: Username contains unprintable characters.')
    
  if not (password.isprintable()):
    errors.append('Error: Password contains unprintable characters.')
  
  if not (username == username.strip()):
    errors.append('Error: Username contains leading and/or trailing whitespace.')
    
  if not (password == password.strip()):
    errors.append('Error: Password contains leading and/or trailing whitespace.')
    
  if len(username) < app.config['USERNAME_MIN']:
    errors.append('Error: Username is less than {} characters.'.format(app.config['USERNAME_MIN']))
  
  if len(username) > app.config['USERNAME_MAX']:
    errors.append('Error: Username is greater than {} characters.'.format(app.config['USERNAME_MAX']))
    
  if len(password) < app.config['PASSWORD_MIN']:
    errors.append('Error: Password is less than {} characters.'.format(app.config['PASSWORD_MIN']))
  
  if len(password) > app.config['PASSWORD_MAX']:
    errors.append('Error: Password is greater than {} characters.'.format(app.config['PASSWORD_MAX']))
    
  # make sure the two entered passwords match
  if not (password == password2):
    errors.append('Error: Passwords do not match.')
    
  # check password strength
  lower = False
  upper = False
  digit = False
  special = False
  for char in password:
    if char.isupper():
      upper = True
    elif char.islower():
      lower = True
    elif char.isdecimal():
      digit = True
    elif char in ' !"#$%&\'()*+,-./:;<=>?@[]\\^_`~{}|':
      special = True
      
  if not (lower and upper and digit and special):
    errors.append('Error: Password must contain at least one lowercase letter, one uppercase letter, one digit, and one special character.')
    
  # now return on error
  if errors:
    return render_template('login.html', errors_reg=errors)
    
  # make sure the username does not already exist
  db_cursor.execute('SELECT userid FROM users WHERE username=%s', (username,))
  if len(db_cursor.fetchall()) > 0:
    errors.append('Error: Username already taken. Please select another one.')
    return render_template('login.html', errors_reg=errors)
    
  # now start generating user information
  salt = secrets.token_bytes(app.config['PASS_SALT_SIZE'])
  session_token = secrets.token_bytes(app.config['SESSION_TOKEN_SIZE'])
  csrf_token = secrets.token_bytes(app.config['CSRF_TOKEN_SIZE'])
  
  # now generate hashes of password and session token
  pass_hash = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=app.config['SC_N'], r=app.config['SC_R'], p=app.config['SC_P'])
  session_hash = hashlib.scrypt(session_token, salt=app.config['TOKEN_SALT'], n=app.config['SC_N'], r=app.config['SC_R'], p=app.config['SC_P'])
  
  # generate expiration of token
  expiration = datetime.date.today() + app.config['TOKEN_EXPIRATION']
  
  # now insert the data into the database
  db_cursor.execute('INSERT INTO users (username, profilepic, profiledesc, salt, passhash, sessioncookiehash, sessionexpiration, csrftoken) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', (username, app.config['DEFAULT_PROFILE_PIC'], app.config['DEFAULT_PROFILE_DESCRIPTION'], salt.hex(), pass_hash.hex(), session_hash.hex(), expiration, csrf_token.hex()))
  db.commit()
  
  response = make_response(redirect(url_for('generate_user_page', user_id=db_cursor.lastrowid)))
  response.set_cookie(app.config['SESSION_COOKIE_NAME'], value=session_token.hex(), expires=(datetime.datetime.today() + app.config['TOKEN_EXPIRATION']))
  return response

# handle user login
@app.route('/login', methods=['POST'])
def process_login():
  
  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  # store any errors
  errors = []
  
  # get form parameters
  username = request.form['username']
  password = request.form['password']
  
  # get the user id, password hash, and salt for the specified username
  db_cursor.execute('SELECT userid, salt, passhash FROM users WHERE username=%s', (username,))
  data = db_cursor.fetchall()
  
  # make sure the user exists
  if not (len(data) == 1):
    errors.append('Error: Incorrect Username and/or Password.')
    return render_template('login.html', errors_log=errors)
  
  # get the data
  user = UserInfo()
  
  for (userid, salt, passhash) in data:
    user.id = userid
    user.salt = b''.fromhex(salt)
    user.passhash = b''.fromhex(passhash)
    
  # calculate the entered password hash
  entered_pass_hash = hashlib.scrypt(password.encode('utf-8'), salt=user.salt, n=app.config['SC_N'], r=app.config['SC_R'], p=app.config['SC_P'])
  
  # finally, compare the hashes
  if not (secrets.compare_digest(entered_pass_hash, user.passhash)):
    errors.append('Error: Incorrect Username and/or Password.')
    return render_template('login.html', errors_log=errors)
       
  # now start generating new tokens
  session_token = secrets.token_bytes(app.config['SESSION_TOKEN_SIZE'])
  csrf_token = secrets.token_bytes(app.config['CSRF_TOKEN_SIZE'])
  
  # now generate hash of session token
  session_hash = hashlib.scrypt(session_token, salt=app.config['TOKEN_SALT'], n=app.config['SC_N'], r=app.config['SC_R'], p=app.config['SC_P'])
  
  # generate expiration of token
  expiration = datetime.date.today() + app.config['TOKEN_EXPIRATION']
  
  # now update session info for the user in the database
  db_cursor.execute('UPDATE users SET sessioncookiehash=%s, sessionexpiration=%s, csrftoken=%s WHERE userid=%s', (session_hash.hex(), expiration, csrf_token.hex(), user.id))
  db.commit()
  
  response = make_response(redirect(url_for('generate_user_page', user_id=user.id)))
  response.set_cookie(app.config['SESSION_COOKIE_NAME'], value=session_token.hex(), expires=(datetime.datetime.today() + app.config['TOKEN_EXPIRATION']))
  return response
  
# handle user logout
@app.route('/logout')
def process_logout():
  
  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  # try to authenticate the user
  check_session_token(db, db_cursor)
  current_user = g.get(app.config['USER_PARAM'])
  
  # if not logged in, redirect to home page
  if not current_user:
    return redirect(url_for('generate_home_page'))
    
  # if logged in, clear tokens in database and redirect to homepage
  db_cursor.execute('UPDATE users SET sessioncookiehash=NULL, csrftoken=NULL WHERE userid=%s', (current_user.id,))
  db.commit()
  return redirect(url_for('generate_home_page'))

# handle following of new user
@app.route('/follow', methods=['POST'])
def create_new_follower():
  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  # try to authenticate the user
  check_session_token(db, db_cursor)
  current_user = g.get(app.config['USER_PARAM'])
  
  #get the user_id of the user we want to follow
  user_id = request.form['user_id']
  #if the user_id is valid... 
  db_cursor.execute('SELECT username FROM users WHERE userid=%s', (user_id,))
  if (len(db_cursor.fetchall()) != 1):
    return 'Not found!', 404
  #and if the user is not already following them
  db_cursor.execute('SELECT followingthisuserid FROM followers WHERE userid=%s AND followingthisuserid=%s', (current_user.id, user_id)) 
  result = db_cursor.fetchone()
  if result is not None:
    return 'Already Following!', 404
  #add the current user and the user they follow to the follow list
  db_cursor.execute('INSERT INTO followers (userid,followingthisuserid) VALUES (%s,%s)', (current_user.id, user_id))
  db.commit()
  return redirect(url_for('generate_user_page', user_id=user_id))
  
# handle display of direct messaging
@app.route('/dm/<int:user_id>')
def generate_direct_message_page(user_id):

  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  # try to authenticate the user
  check_session_token(db, db_cursor)
  current_user = g.get(app.config['USER_PARAM'])
  
  # if not logged in, redirect to login page
  if not current_user:
    return redirect(url_for('display_login_register_page'))
    
  # prevent direct message with self
  if user_id == current_user.id:
    return 'Not found!', 404
    
  # make sure the other user exists
  db_cursor.execute('SELECT username FROM users WHERE userid=%s', (user_id,))
  if (len(db_cursor.fetchall()) != 1):
    return 'Not found!', 404
  
  # determine ordering of user ids and status of requesting user id
  lowid = None
  highid = None
  cur_islow = False
  
  if user_id > current_user.id:
    lowid = current_user.id
    highid = user_id
    cur_islow = True
  else:
    lowid = user_id
    highid = current_user.id
    
  # query database for direct message id; if none, create an entry
  dmid = None
  db_cursor.execute('SELECT dmid FROM directmsg WHERE lowuserid=%s AND highuserid=%s', (lowid, highid))
  data = db_cursor.fetchall()
  if len(data) == 1:
    dmid = data[0][0]
    if cur_islow:
      db_cursor.execute('UPDATE directmsg SET lowuserread=1 WHERE dmid=%s', (dmid,))
      db.commit()
    else:
      db_cursor.execute('UPDATE directmsg SET highuserread=1 WHERE dmid=%s', (dmid,))
      db.commit()
  else:
    db_cursor.execute('INSERT INTO directmsg (lowuserid, highuserid, lowuserread, highuserread) VALUES (%s, %s, %s, %s)', (lowid, highid, 1, 1))
    db.commit()
    dmid = db_cursor.lastrowid
  
  # gather information about the messages
  direct_msgs = []
  db_cursor.execute('SELECT messages.userid, messages.msgtext, users.username FROM messages JOIN users ON messages.userid=users.userid WHERE messages.dmid=%s ORDER BY messages.dmid', (dmid,))
  
  for (userid, msgtext, username) in db_cursor:
    msg = MessageInfo()
    msg.userid = userid
    msg.username = username
    msg.message = msgtext
    direct_msgs.append(msg)
    
  # check for unread messages
  check_unread_messages(db_cursor, current_user)

  return render_template('chat.html', cur_user=current_user, direct_messages=direct_msgs, dm_id=dmid)
  
# handle display of direct message conversations
@app.route('/messages')
def generate_direct_message_listing():

  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  # try to authenticate the user
  check_session_token(db, db_cursor)
  current_user = g.get(app.config['USER_PARAM'])
  
  # if not logged in, redirect to login page
  if not current_user:
    return redirect(url_for('display_login_register_page'))
  
  # store direct message conversations
  direct_msgs = []
  
  # get all low user id conversations and then all high user id conversations
  db_cursor.execute('SELECT directmsg.dmid, directmsg.lowuserread, directmsg.highuserid, users.username FROM directmsg JOIN users ON directmsg.highuserid=users.userid WHERE directmsg.lowuserid=%s', (current_user.id,))
  
  for (dmid, lowuserread, highuserid, username) in db_cursor:
    dminfo = DirectMsgInfo()
    dminfo.userid = highuserid
    dminfo.username = username
    dminfo.dmid = dmid
    dminfo.read = lowuserread
    direct_msgs.append(dminfo)
    
  db_cursor.execute('SELECT directmsg.dmid, directmsg.highuserread, directmsg.lowuserid, users.username FROM directmsg JOIN users ON directmsg.lowuserid=users.userid WHERE directmsg.highuserid=%s', (current_user.id,))
  
  for (dmid, highuserread, lowuserid, username) in db_cursor:
    dminfo = DirectMsgInfo()
    dminfo.userid = lowuserid
    dminfo.username = username
    dminfo.dmid = dmid
    dminfo.read = highuserread
    direct_msgs.append(dminfo)
     
  # handle any direct messages that are empty
  no_valid_entries = True
  for dm in direct_msgs:
    db_cursor.execute('SELECT userid FROM messages WHERE dmid=%s LIMIT 1', (dm.dmid,))
    if len(db_cursor.fetchall()) != 1:
      dm.empty = True
    else:
      dm.empty = False
      no_valid_entries = False
      
  if no_valid_entries:
    direct_msgs = []

  return render_template('messages.html', cur_user=current_user, direct_message_list=direct_msgs)
  
# handle direct message submission
@app.route('/submit-dm', methods=['POST'])
def process_dm_message():
  
  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  # try to authenticate the user
  check_session_token(db, db_cursor)
  current_user = g.get(app.config['USER_PARAM'])
  
  # if not logged in, reject
  if not current_user:
    return 'Not Authenticated!', 403
  
  # get form data fields
  message = request.form['msg']
  dmid = request.form['dmid']
  
  # reject blank messages
  if len(message.strip()) == 0:
    return 'Cannot send blank message!', 400
  
  # look up the current dmid
  db_cursor.execute('SELECT lowuserid, highuserid FROM directmsg WHERE dmid=%s', (dmid,))
  data = db_cursor.fetchall()
  
  if (len(data) != 1):
    return 'Nonexistant Conversation!', 400
    
  # make sure user is in conversation and update read values
  if current_user.id == data[0][0]:
    db_cursor.execute('UPDATE directmsg SET highuserread=0 WHERE dmid=%s', (dmid,))
    db.commit()
  elif current_user.id == data[0][1]:
    db_cursor.execute('UPDATE directmsg SET lowuserread=0 WHERE dmid=%s', (dmid,))
    db.commit()
  else:
    return 'Not Party to this Conversation!', 403
    
  # finally add the message
  db_cursor.execute('INSERT INTO messages (dmid, userid, msgtext) VALUES (%s, %s, %s)', (dmid, current_user.id, message))
  db.commit()
  
  return 'Successfully submitted direct message!'

# handle image upload form
@app.route('/upload-image', methods=['GET', 'POST'])
def handle_image_upload():

  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  # try to authenticate the user
  check_session_token(db, db_cursor)
  current_user = g.get(app.config['USER_PARAM'])
  
  if not current_user:
    return redirect(url_for('display_login_register_page'))
  
  # check for unread messages
  check_unread_messages(db_cursor, current_user)
  
  # check for actual upload versus form view
  if request.method == 'GET':
    return render_template('upload-image.html', error_str='', success_str='', cur_user=current_user)
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
      return render_template('upload-image.html', error_str='Error: No image file selected for upload. Please select an image to upload and try again.', success_str='', cur_user=current_user)
    
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
      return render_template('upload-image.html', error_str='Error: Unsupported image format. Only BMP, GIF, JPEG, and PNG file formats are supported.', success_str='', cur_user=current_user)
      
    # now read the file and generate a hash of it for the filename
    img_hash = hashlib.sha384()
    img_hash.update(image.read())
    img_filename = img_hash.hexdigest() + file_extension
    image.stream.seek(0)
    
    # now save the file
    image.save(safe_join(app.config['UPLOAD_DIRECTORY'], img_filename))
    
    # finally save the details to the database
    db_cursor.execute('INSERT INTO images (userid, imgtitle, imgfile, imgdesc, likes) VALUES (%s, %s, %s, %s, 0)', (current_user.id, title, img_filename, description))
    db.commit()
    
    # generate data to send over websocket connection
    send_data = {}
    image_data = ImageInfo()
    image_data.id = db_cursor.lastrowid
    image_data.userid = current_user.id
    image_data.title = title
    image_data.username = current_user.name
    image_data.path = url_for('send_user_image', img_name=img_filename)
    image_data.likes = 0
    image_data.description = description
    send_data['userid'] = image_data.userid
    send_data['imageid'] = image_data.id
    send_data['html'] = render_template('one-image.html', image=image_data)
    send_data['thumbnailhtml'] = render_template('one-image-thumbnail.html', image=image_data)
    new_app.emit('new-image-full', send_data, room='general-notifications')
    
    return render_template('upload-image.html', error_str='', success_str=(url_for('send_user_image', img_name=img_filename)), cur_user=current_user)

# send user images
@app.route('/img/<img_name>')
def send_user_image(img_name):
  return send_from_directory(app.config['UPLOAD_DIRECTORY'], img_name)
     
# handle connections
@new_app.on('connect')
def process_new_connnect():

  # general notifications room
  join_room(app.config['GENERAL_ROOM'])
  
  # now, user-specific room
  # get the database if it does not exist
  if not (app.config['DB_PARAM'] in g):
    g.setdefault(app.config['DB_PARAM'], default=get_database(app.config['DB_NAME']))
  db = g.get(app.config['DB_PARAM'])
  db_cursor = db.cursor()
  
  # try to authenticate the user
  check_session_token(db, db_cursor)
  current_user = g.get(app.config['USER_PARAM'])
  
  if current_user:
    join_room(app.config['USER_ROOM_PREFIX'] + str(current_user.id))
    
    
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
    
@app.cli.command('drop-db')
def drop_database():

  try:
    if input('Are you sure you want to drop the database? (Type "yEs" to confirm): ') != 'yEs':
      sys.stderr.write('Database not dropped.\n')
      return
   
    db = get_database()
    db_cursor = db.cursor()
    db_cursor.execute('DROP DATABASE ' + app.config['DB_NAME'])
    db.commit()
    db.close()
  except Exception as ex:
    sys.stderr.write('Error Dropping Database\n')
    raise ex
  
@app.teardown_appcontext
def close_db(ex):
  if app.config['DB_PARAM'] in g:
    g.pop(app.config['DB_PARAM']).close()
  
# grab a copy of the database  
def get_database(db_name=None):
  ## ///Remove port parameter from connect function at end of coding, needs to be 3306
  try:
    if db_name:
      db = mysql.connector.connect(host=app.config['DB_HOST'], user=app.config['DB_USER'], password=app.config['DB_PASS'], database=db_name)
    else:
      db = mysql.connector.connect(host=app.config['DB_HOST'], user=app.config['DB_USER'], password=app.config['DB_PASS'])
  except Exception as ex:
    sys.stderr.write('Error Connecting to Database\n')
    raise ex
    
  return db
  