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
    def getTopRated(limit: int):
        pipeline = [
            {"$match": {"nota": {"$ne": None}}},
            {"$group": {
                "_id": "$movieId",
                "avg_rating": {"$avg": "$nota"},
                "total": {"$sum": 1},
            }},
            {"$sort": {"total": -1}},
            {"$limit": limit},
            {"$lookup": {
                "from": "Movies",
                "localField": "_id",
                "foreignField": "movieId",
                "as": "movie_data"
            }},
            {"$unwind": "$movie_data"},
            # deduplica por movieId caso o lookup traga duplicatas
            {"$group": {
                "_id": "$_id",
                "movie_name": {"$first": "$movie_data.movie_name"},
                "img_src":    {"$first": "$movie_data.img_src"},
                "genres":     {"$first": "$movie_data.genres"},
                "year":       {"$first": "$movie_data.release_year"},
                "backdrop_src": {"$first": "$movie_data.backdrop_url"},
                "avg_rating": {"$first": "$avg_rating"},
                "total":      {"$first": "$total"},
            }},
            {"$project": {
                "_id": 0,
                "movieId":    "$_id",
                "movie_name": 1,
                "img_src":    1,
                "genres":     1,
                "year":       1,
                "backdrop_src": 1,
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
    def getWatchedMovies(user_id: str) -> list:
       
        watched = RatingRepository.getWatchedMovieIds(user_id)
        
        pipeline = [
        # 1. Filtra na coleção de ratings apenas os IDs assistidos
        {"$match": {"movieId": {"$in": list(watched)}}},
        
        # 2. Agrupa por movieId para remover duplicatas
        {"$group": {
            "_id": "$movieId",
            "user_rating": {"$first": "$nota"}
        }},
        
        # 3. CORREÇÃO DE TIPO: Converte o _id (que era a String movieId de ratings) para Inteiro
        {"$addFields": {
            "movieId_convertido": {"$toInt": "$_id"}
        }},
        
        # 4. Faz o JOIN com a coleção 'Movies' usando o ID convertido
        {
            "$lookup": {
                "from": "Movies",            
                "localField": "movieId_convertido", # Campo agora convertido para Inteiro
                "foreignField": "movieId",          # Campo que já é Inteiro em Movies
                "as": "movie_data"            
            }
        },
        
        # 5. Desfaz a lista do lookup para virar um objeto direto
        {"$unwind": "$movie_data"},
        
        # deduplica por movieId caso o lookup traga duplicatas
            {"$group": {
                "_id": "$_id",
                "user_rating": {"$first": "$user_rating"},
                "movie_name": {"$first": "$movie_data.movie_name"},
                "img_src":    {"$first": "$movie_data.img_src"},
                "genres":     {"$first": "$movie_data.genres"},
                "year":       {"$first": "$movie_data.release_year"},
                "backdrop_src": {"$first": "$movie_data.backdrop_url"},
                "avg_rating": {"$first": "$avg_rating"},
                "total":      {"$first": "$total"},
            }},
            {"$project": {
                "_id": 0,
                "movieId":    "$_id",
                "movie_name": 1,
                "img_src":    1,
                "genres":     1,
                "year":       1,
                "backdrop_src": 1,
                "total":      1,
            }},
        ]
        return list(collection.aggregate(pipeline))
    
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
    
        
    @staticmethod
    def getAllRatings() -> list:
        docs = list(collection.find({}, {"_id": 0, "userId": 1, "movieId": 1, "nota": 1}))
        for doc in docs:
            doc["movieId"] = int(doc["movieId"])  # normaliza para int
        return docs