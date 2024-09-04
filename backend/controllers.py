from pymongo import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import PyMongoError
from config import MONGO_URI
from backend.movie_services import fetch_movie_data
import certifi
import certifi
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
try:
    client = MongoClient(MONGO_URI, server_api=ServerApi('1'), tlsCAFile=certifi.where())
    db = client['moviesdb']
    collection = db['movies']
    users_collection = db['users']
except PyMongoError as e:
    print(f"Failed to connect to the database: {str(e)}")

def register_user(username, email, password):
    try:
        existing_user = users_collection.find_one({'$or': [{'username': username}, {'email': email}]})
        if existing_user:
            return {'error': 'Username or email already exists'}, 400

        hashed_password = generate_password_hash(password)
        new_user = {
            'username': username,
            'email': email,
            'password': hashed_password
        }
        result = users_collection.insert_one(new_user)
        new_user['_id'] = str(result.inserted_id)
        del new_user['password']  # Don't send password back to client
        return new_user, 201
    except PyMongoError as e:
        print(f"An error occurred while registering the user: {str(e)}")
        return {'error': 'Registration failed'}, 500

def login_user(username, password):
    try:
        user = users_collection.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            access_token = create_access_token(identity=str(user['_id']))
            return {'access_token': access_token}, 200
        else:
            return {'error': 'Invalid username or password'}, 401
    except PyMongoError as e:
        print(f"An error occurred while logging in the user: {str(e)}")
        return {'error': 'Login failed'}, 500

@jwt_required()
def get_user_profile():
    try:
        current_user_id = get_jwt_identity()
        user = users_collection.find_one({'_id': current_user_id})
        if user:
            user['_id'] = str(user['_id'])
            del user['password']  # Don't send password back to client
            return user, 200
        else:
            return {'error': 'User not found'}, 404
    except PyMongoError as e:
        print(f"An error occurred while fetching the user profile: {str(e)}")
        return {'error': 'Failed to fetch user profile'}, 500

@jwt_required()
def update_user_profile(update_data):
    try:
        current_user_id = get_jwt_identity()
        result = users_collection.update_one({'_id': current_user_id}, {'$set': update_data})
        if result.modified_count:
            return {'message': 'Profile updated successfully'}, 200
        else:
            return {'error': 'No changes made to the profile'}, 400
    except PyMongoError as e:
        print(f"An error occurred while updating the user profile: {str(e)}")
        return {'error': 'Failed to update user profile'}, 500

def process_movies(title, year):

    existing_movie = collection.find_one({'title': title, 'year': year})

    if existing_movie:
        # Convert ObjectId to string for JSON serialization
        existing_movie['_id'] = str(existing_movie['_id'])
        
        return existing_movie
    else:
        # Step 3: Fetch movie data from OMDb API
        movie_data = fetch_movie_data(title, year)

        if movie_data:
            # Step 4: Insert the new movie into the database
            inserted_movie = insert_movie(movie_data)
            inserted_movie['_id'] = str(inserted_movie['_id'])
            return inserted_movie
        else: 
            return []

def insert_movie(movie_data):
    result = collection.insert_one(movie_data)
    inserted_id = result.inserted_id
    inserted_movie = collection.find_one({"_id": inserted_id})
    if inserted_movie:
        inserted_movie['_id'] = str(inserted_movie['_id'])
    return inserted_movie

def get_movie(movie_id):
    try:
        return collection.find_one({'id': movie_id})
    except PyMongoError as e:
        print(f"An error occurred while fetching the movie: {str(e)}")
        return None

def get_all_movies():
    try:
        movies = list(collection.find())
        for movie in movies:
            movie['_id'] = str(movie['_id'])
        return movies
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return []

def update_movie(movie_id, update_data):
    try:
        result = collection.update_one({'id': movie_id}, {'$set': update_data})
        return result.modified_count
    except PyMongoError as e:
        print(f"An error occurred while updating the movie: {str(e)}")
        return 0

def delete_movie(movie_id):
    try:
        result = collection.delete_one({'id': movie_id})
        return result.deleted_count
    except PyMongoError as e:
        print(f"An error occurred while deleting the movie: {str(e)}")
        return 0