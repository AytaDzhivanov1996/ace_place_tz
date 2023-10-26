import hashlib
import datetime
import os

from bson import ObjectId
from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, request
from flask_jwt_extended import JWTManager, create_access_token
from flask_mail import Mail, Message
from pymongo import MongoClient

from services import JSONEncoder

load_dotenv('.env')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

client = MongoClient(os.environ['DB_URI'])
db = client['ace_place']
users_collection = db['users']
notifications_collection = db['notifications']

jwt = JWTManager(app)
app.config['JWT_SECRET_KEY'] = os.environ['JWT_SECRET_KEY']

app.config['MAIL_SERVER'] = os.environ['SMTP_HOST']
app.config['MAIL_PORT'] = os.environ['SMTP_PORT']
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ['SMTP_LOGIN']
app.config['MAIL_DEFAULT_SENDER'] = os.environ['SMTP_EMAIL']
app.config['MAIL_PASSWORD'] = os.environ['SMTP_PASSWORD']
mail = Mail(app)

@app.route("/users/signup", methods=['POST'])
def register():
	"""User registration"""
	new_user = request.get_json()
	new_user['password'] = hashlib.sha256(new_user['password'].encode('utf-8')).hexdigest()
	doc = users_collection.find_one({"email": new_user['email']})
	
	if not doc:
		users_collection.insert_one(new_user)
		return make_response(jsonify({'msg': 'User created successfully'}), 201)
	else:
		return make_response(jsonify({'msg': 'Username already exists'}), 409)
	

@app.route("/users/login", methods=['POST'])
def login():
	"""User authentification with JWT"""
	login_credentials = request.get_json()
	existing_user = users_collection.find_one({"email": login_credentials['email']})

	if existing_user:
		encripted_password = hashlib.sha256(login_credentials['password'].encode("utf-8")).hexdigest()
		if encripted_password == existing_user['password']:
			access_token = create_access_token(identity=existing_user['email'])
			return make_response(jsonify(access_token=access_token))
	
	return make_response(jsonify({'msg': 'The username or password is incorrect'}), 401)


@app.route("/notifications/create", methods=['POST'])
def notification_create():
	"""Creating a notification"""
	notification_credentials = request.get_json()
	user = users_collection.find_one({"_id": ObjectId(notification_credentials['user_id'])})
	json_encoder = JSONEncoder()
	notification = {'timestamp': datetime.datetime.now(),
				  	'is_new': True,
					'user_id': json_encoder.encode(user['_id']),
					'key': notification_credentials.get('key'),
					'data': {
						"field": "value"
					}}
	
	if notification_credentials.get('key') == 'registration':
		msg = Message('New notification', recipients=[json_encoder.encode(user['email'])])
		msg.body = "You have a new notification"
		mail.send(msg)
		return make_response(jsonify({'msg': 'Notification has been sent to e-mail'}), 201)
	elif notification_credentials.get('key') == 'new_message':
		notifications_collection.insert_one(notification)
		return make_response(jsonify({'msg': 'Notification has been added to the database'}), 201)
	elif notification_credentials.get('key') == 'new_login':
		msg = Message('New notification', recipients=[json_encoder.encode(user['email'])])
		msg.body = "You have a new notification"
		mail.send(msg)
		notifications_collection.insert_one(notification)
		return make_response(jsonify({'msg': 'Notification has been sent to e-mail and been added to the database'}, 201))	
	

@app.route('/notifications/list', methods=['GET'])
def notification_list():
	"""Getting a list of notifications"""
	notification_credentials = request.get_json()
	user = users_collection.find_one({"_id": ObjectId(notification_credentials['user_id'])})
	json_encoder = JSONEncoder()
	
	json_data = {
				"success": True,
				"data": {
					"elements": notifications_collection.estimated_document_count(),
					"new": notifications_collection.count_documents({"is_new": True}),
					"request": {
						"user_id": json_encoder.encode(user['_id']),
						"skip": request.args.get('skip'),
						"limit": request.args.get('limit')
					},
					"list": []
				},
			}
	if request.args:
			skip = int(request.args.get('skip'))
			limit = int(request.args.get('limit'))
			notification_list = notifications_collection.find({}, {"_id": 0}).skip(skip).limit(limit)
			for notification in notification_list:
				json_data['data']['list'].append(notification)
	else:
		for x in notifications_collection.find({}, {"_id": 0}):
			json_data['data']['list'].append(x)
			
	return json_data

@app.route('/notifications/read', methods=['POST'])
def notification_read():
	"""Read a notification"""
	notification_credentials = request.get_json()
	filter = {"_id": ObjectId(notification_credentials['notification_id'])}
	values = {"$set": {"is_new": False}}
	notifications_collection.update_one(filter, values)
	return make_response(jsonify({"msg": "Notification has been read"}, 200))
		
if __name__ == '__main__': 
	app.run() 
