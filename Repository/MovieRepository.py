from pymongo import MongoClient
import os
from dotenv import load_dotenv
 
load_dotenv()
 
client     = MongoClient(os.getenv('url_mongodb'))
db         = client.get_database("Projeto1")
collection = db.get_collection("Movies")
 




class MovieRepository:
    
    @staticmethod
    def getFilmsByGender(genres: list, limit=20):
        print(f"Buscando gêneros: {genres}")
        query = {
            "$and": [
                {"genres": {"$regex": f"\\b{genre}\\b", "$options": "i"}}
                for genre in genres
            ]
        }
        return list(collection.find(query, {"_id": 0}).limit(limit))
    @staticmethod
    def getMoviesByIds(movie_ids: list) -> list:
        query = {"movieId": {"$in": [int(mid) for mid in movie_ids]}}
        return list(collection.find(query, {"_id": 0}))