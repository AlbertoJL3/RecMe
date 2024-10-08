from pymongo import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import PyMongoError
from config import MONGO_URI
from backend.movie_services import fetch_movie_data
import certifi
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import timedelta
from datetime import datetime

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
        print(f"Username or email already exists: {str(e)}")
        return {'error': 'Registration failed'}, 500

def login_user(user_input, password, is_email=False):
    try:
        if is_email:
            user = users_collection.find_one({'email': user_input.lower()})
        else:
            user = users_collection.find_one({'username': user_input.lower()})

        if user and check_password_hash(user['password'], password):
            access_token = create_access_token(identity=str(user['_id']), expires_delta=timedelta(hours=1))
            refresh_token = create_refresh_token(identity=str(user['_id']))
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user_id': str(user['_id']),
                'username': user['username']
            }, 200
        else:
            return {'error': 'Invalid username/email or password'}, 401
    except PyMongoError as e:
        print(f"Invalid username/email or password: {str(e)}")
        return {'error': 'Login failed'}, 500

def save_prompt_results(user_id, prompt, movie_ids):
    truncated_prompt = prompt[:100]  # Limit prompt to 100 characters
    prompt_result = {
        '_id': ObjectId(),  # Generate a new ObjectId for the prompt result
        'prompt': truncated_prompt,
        'movie_ids': movie_ids,
        'timestamp': datetime.utcnow()
    }
    users_collection.update_one(
        {'_id': ObjectId(user_id)},
        {'$push': {'prompt_results': prompt_result}}
    )

def get_user_prompt_results(user_id):
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    return user.get('prompt_results', [])

@jwt_required()
def get_user_profile():
    try:
        current_user_id = get_jwt_identity()
        user = users_collection.find_one({'_id': ObjectId(current_user_id)})
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
def delete_prompt_result(current_user_id, prompt_id):
    try:
        result = users_collection.update_one(
            {'_id': ObjectId(current_user_id)},
            {'$pull': {'prompt_results': {'_id': ObjectId(prompt_id)}}}
        )
    except Exception as e:
        print(f"An error occurred while deleting prompt result: {str(e)}")
        return {'error': 'Failed to delete prompt result'}, 500

@jwt_required()
def update_user_profile(update_data):
    try:
        current_user_id = get_jwt_identity()
        result = users_collection.update_one({'_id': ObjectId(current_user_id)}, {'$set': update_data})
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
        existing_movie['_id'] = str(existing_movie['_id'])
        print('found existing movie', existing_movie['title'])
        return existing_movie
    else:
        movie_data = fetch_movie_data(title, year)
        if movie_data:
            inserted_movie = insert_movie(movie_data)
            inserted_movie['_id'] = str(inserted_movie['_id'])
            print('inserted movie', inserted_movie['title'])
            return inserted_movie
        else: 
            return []
       
import ast

def clean_list(value):
    if isinstance(value, str):
        # Try to safely evaluate the string as a literal
        try:
            value = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            pass
    
    if isinstance(value, list):
        # Flatten the list and remove extra quotes
        return [item.strip("'") for sublist in value for item in (sublist if isinstance(sublist, list) else [sublist])]
    else:
        return [str(value).strip("'")]

def process_cached_movies(row):
    data = row.to_dict()  # Convert Series to dictionary
    
    # Process specific fields
    for field in ['genres', 'actors', 'director']:
        if field in data:
            data[field] = clean_list(data[field])

    # Ensure all data is JSON serializable
    for key, value in data.items():
        if isinstance(value, ObjectId):
            data[key] = str(value)

    return data
def insert_movie(movie_data):
    result = collection.insert_one(movie_data)
    inserted_id = result.inserted_id
    inserted_movie = collection.find_one({"_id": inserted_id})
    if inserted_movie:
        inserted_movie['_id'] = str(inserted_movie['_id'])
    return inserted_movie

def get_movie(movie_id):
    try:
        return collection.find_one({'_id': ObjectId(movie_id)})
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

@jwt_required()
def get_watchlist():
    try:
        current_user_id = get_jwt_identity()
        user = users_collection.find_one({'_id': ObjectId(current_user_id)})
        if user and 'watchlist' in user:
            watchlist_ids = [ObjectId(movie_id) for movie_id in user['watchlist']]
            watchlist_movies = list(collection.find({'_id': {'$in': watchlist_ids}}))
            for movie in watchlist_movies:
                movie['_id'] = str(movie['_id'])
            return watchlist_movies, 200
        else:
            return [], 200
    except PyMongoError as e:
        print(f"An error occurred while fetching watchlist: {str(e)}")
        return {'error': 'Failed to fetch watchlist'}, 500

@jwt_required()
def add_to_watchlist(movie_id):
    try:
        current_user_id = get_jwt_identity()
        movie_object_id = ObjectId(movie_id)
        print('Movie Object ID: ', movie_object_id)
        print('Movie  ID: ', movie_id)

        movie = collection.find_one({'_id': movie_object_id})
        if not movie:
            return {'error': 'Movie not found'}, 404

        result = users_collection.update_one(
            {'_id': ObjectId(current_user_id)},
            {'$addToSet': {'watchlist': str(movie_object_id)}}
        )
        
        if result.modified_count:
            updated_user = users_collection.find_one({'_id': ObjectId(current_user_id)})
            return {'message': 'Movie added to watchlist', 'watchlist': updated_user.get('watchlist', [])}, 200
        else:
            return {'message': 'Movie already in watchlist'}, 200
    except PyMongoError as e:
        print(f"An error occurred while adding to watchlist: {str(e)}")
        return {'error': 'Failed to add movie to watchlist'}, 500

@jwt_required()
def remove_from_watchlist(movie_id):
    try:
        current_user_id = get_jwt_identity()
        result = users_collection.update_one(
            {'_id': ObjectId(current_user_id)},
            {'$pull': {'watchlist': str(movie_id)}}
        )
        if result.modified_count:
            return {'message': 'Movie removed from watchlist'}, 200
        else:
            return {'message': 'Movie not in watchlist'}, 200
    except PyMongoError as e:
        print(f"An error occurred while removing from watchlist: {str(e)}")
        return {'error': 'Failed to remove movie from watchlist'}, 500

@jwt_required(refresh=True)
def refresh_access_token():
    current_user_id = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user_id, expires_delta=timedelta(hours=1))
    return {'access_token': new_access_token}, 200