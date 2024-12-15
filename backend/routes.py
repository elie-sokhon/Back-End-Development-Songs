from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route('/health')
def health():
    return jsonify({"status":"OK"}),200

@app.route('/count')
def count():
    count = db.songs.count_documents({})
    return {"count":count},200

@app.route('/song',methods=["GET"])
def songs():
    try:
        songs_cursor = db.songs.find({})
        songs_list = [parse_json(song) for song in songs_cursor]
        return jsonify({"songs":songs_list}),200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/song/<int:id>',methods=["GET"])
def get_song_by_id(id):
    song_by_id = db.songs.find_one({"id":id})
    song_by_id = jsonify(parse_json(song_by_id))
    if not song_by_id:
        return {"message":f"song with id {id} not found"},404
    return song_by_id,200

@app.route('/song',methods=["POST"])
def create_song():
    try:
        new_song = request.get_json()
        if not new_song:
            return jsonify({"message":"Wrong input data"}),400
        if "id" not in new_song:
            return jsonify({"message":"ID not in request"}),400
        id = new_song["id"]
        existing_song = db.songs.find_one({"id": id})
        if existing_song:
            return jsonify({"Message": f"song with id {existing_song['id']} already present"}), 302

        result = db.songs.insert_one(new_song)
        inserted_id_str = str(result.inserted_id)
        return jsonify({"inserted id":inserted_id_str}),201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/song/<int:id>',methods=["PUT"])
def update_song(id: int) -> tuple:
    """
    Update a song currently in the data.
    :param id: int. ID field of the song to be updated.
    :return: tuple
        dict: data for new song (json) or message (json) if not found.
        http status code:
            200 Song found, nothing updated     -- Code: OK
            201 Song updated                    -- Code: Created
            404 Song not found                  -- Code: Not Found
    """

    updated_data = request.json  # Updated data

    # Check if the id exists
    original_query = db.songs.find_one({"id": id})
    if original_query:
        # Update data
        set_data = {"$set": updated_data}
        result = db.songs.update_one(original_query, set_data)

        # Response
        if result.modified_count == 0:
            response: tuple = {"message": "song found, but nothing updated"}, 200

        else:
            response: tuple = parse_json(db.songs.find_one({"id": id})), 201

    else:
        # Not found
        response: tuple = {"message": f"song not found"}, 404

    return response
    
@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id: int) -> tuple:
    """
    Delete a song if it is in the data.
    :return: tuple
        dict: empty body or message (json) if not found.
        http status code:
            204 Picture deleted    -- Code: No content
            404 Picture not found  -- Code: Not Found
    """
    deletion_result = db.songs.delete_one({"id": id})

    if deletion_result.deleted_count == 0:
        # No changes/ song not found
        response: tuple = {"message": f"song not found"}, 404

    else:
        response: tuple = {}, 204

    return response







