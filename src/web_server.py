# Made using https://flask.palletsprojects.com/ as a reference

from flask import Flask, send_from_directory, abort
app = Flask(__name__)

@app.route('/styles/<path:path>')
def send_style_file(path):
    try:
        return send_from_directory('./static/styles', path)
    except:
        return abort(404)

@app.route('/images/<path:path>')
def send_image_file(path):
    try:
        return send_from_directory('./static/images', path)
    except:
        return abort(404)

@app.route('/html/<path:path>')
def send_html_file(path):
    try:
        return send_from_directory('./static/html', path)
    except:
        return abort(404)

if __name__ == "__main__":
    app.run(port=8000)