from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime

 
load_dotenv()
 
client     = MongoClient(os.getenv('url_mongodb'))
db         = client.get_database("Projeto1")
collection = db.get_collection("Ratings")
 
 
def decode_rating(rating_str):
    if not rating_str or rating_str == "Sem nota":
        return None
    full_stars = str(rating_str).count('★')
    half_star  = 0.5 if '½' in str(rating_str) else 0
    return float(full_stars + half_star)
 
 
class RatingRepository:
 
    @staticmethod
    def hasRatings(user_id: str) -> bool:
        return collection.find_one({"userId": user_id}) is not None

    @staticmethod
    def getTopRated(limit: int = 60):
        pipeline = [
            {"$match": {"nota": {"$ne": None}}},
            {"$group": {
                "_id":        "$movieId",
                "movie_name": {"$first": "$movie_name"},
                "img_src":    {"$first": "$img_src"},
                "avg_rating": {"$avg": "$nota"},
                "total":      {"$sum": 1},
            }},
            {"$sort": {"total": -1}},
            {"$limit": limit},
            {"$project": {
                "_id":        0,
                "movieId":    "$_id",
                "movie_name": 1,
                "img_src":    1,
                "avg_rating": {"$round": ["$avg_rating", 1]},
                "total":      1,
            }},
        ]
        return list(collection.aggregate(pipeline))    
    @staticmethod
    def getWatchedMovieIds(user_id: str) -> set:
        """Retorna os movieIds que o usuário já avaliou."""
        docs = collection.find({"userId": user_id}, {"movieId": 1, "_id": 0})
        return {doc["movieId"] for doc in docs}
    
    
    @staticmethod
    def getUnwatchedMovies(user_id: str, limit: int = 20) -> list:
        """Retorna filmes que o usuário ainda não avaliou, ordenados por média."""
        watched = RatingRepository.getWatchedMovieIds(user_id)

        pipeline = [
            {"$match": {"movieId": {"$nin": list(watched)}}},
            {"$group": {
                "_id":        "$movieId",
                "movie_name": {"$first": "$movie_name"},
                "img_src":    {"$first": "$img_src"},
            }},
            {"$limit": limit},
            {"$project": {
                "_id":        0,
                "movieId":    "$_id",
                "movie_name": 1,
                "img_src":    1,
            }},
        ]
        return list(collection.aggregate(pipeline))
    
    
    @staticmethod
    def createRating(user_id: str, movie_id: int, nota: str) -> str:
        result = collection.insert_one({
            "userId":     user_id,
            "movieId":    movie_id,
            "nota":       nota,
            "data_coleta": datetime.utcnow().strftime("%Y-%m-%d"),
        })
        return str(result.inserted_id)