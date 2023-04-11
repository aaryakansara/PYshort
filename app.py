from pymongo import MongoClient
from hashlib import md5
from flask import Flask, render_template, request, flash, redirect, url_for
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'this should be a secret random string'

client = MongoClient('mongodb://localhost:27017/')
db = client['url_shortener']

urls = db['urls']

@app.route('/', methods=('GET', 'POST'))
def index():

    if request.method == 'POST':
        url = request.form['url']

        if not url:
            flash('The URL is required!')
            return redirect(url_for('index'))

        # generate a hash of the url using md5
        url_hash = md5(url.encode('utf-8')).hexdigest()

        existing_url = urls.find_one({'original_url': url})
        if existing_url:
            # use the existing short_url from the database
            short_url = existing_url['short_url']
        else:
            url_data = {
                'original_url': url,
                'clicks': 1,
                'created': datetime.datetime.utcnow(),
                'short_url': ''
            }
            result = urls.insert_one(url_data)
            url_id = str(result.inserted_id)
            short_url = request.host_url + url_hash
            urls.update_one({'_id': result.inserted_id}, {'$set': {'short_url': short_url}})

        if 'regenerate' in request.form:
            short_url = request.host_url + md5(url.encode('utf-8')).hexdigest()
            urls.update_one({'_id': existing_url['_id']}, {'$set': {'short_url': short_url}})

        return render_template('index.html', short_url=short_url)

    return render_template('index.html')



@app.route('/<id>')
def url_redirect(id):
    try:
        url_data = urls.find_one({'short_url': request.host_url + id})
        if url_data:
            original_url = url_data['original_url']
            clicks = url_data['clicks']
            urls.update_one({'_id': url_data['_id']}, {'$set': {'clicks': clicks + 1}})
            return redirect(original_url)
        else:
            flash('Invalid URL')
    except Exception as e:
        print('Exception:', e)
        flash('Invalid URL')
    return redirect(url_for('index'))


@app.route('/stats')
def stats():

    urls = db.urls
    db_urls = urls.find()
    url_list = []

    for url in db_urls:
        url = {
            'id': str(url['_id']),
            'created': url['created'],
            'original_url': url['original_url'],
            'clicks': url['clicks'],
            'short_url': url['short_url']
        }
        url_list.append(url)

    return render_template('stats.html', urls=url_list)
