import pickle

import numpy as np
from Repository.RatingRepository import RatingRepository
from Repository.MovieRepository import MovieRepository
import os

model_path = os.path.join(os.path.dirname(__file__), "model.pkl")
with open(model_path, "rb") as f:
    model = pickle.load(f)
 
knn_user         = model["knn_user"]
X                = model["X"]
user_mapper      = model["user_mapper"]
user_inv_mapper  = model["user_inv_mapper"]
movie_inv_mapper = model["movie_inv_mapper"]
df_ratings       = model["df"]
knn_item     = model["knn_item"]
movie_mapper = model["movie_mapper"]


def get_recommendationsByUser(user_id):
    
    if user_id not in user_mapper:
        return {"error": "Usuário sem avaliações"}
    
    user_ind = user_mapper[user_id]
    user_vec = X[user_ind]  # era X[user_id], corrigido para X[user_ind]
    
    neighbours = knn_user.kneighbors(user_vec, return_distance=False).flatten()
    usuarios_similares = [user_inv_mapper[n] for n in neighbours if n != user_ind]
    
    ja_assistidos = RatingRepository.getWatchedMovieIds(user_id)

    candidatos = (
        df_ratings[
            (df_ratings["userId"].isin(usuarios_similares)) &
            (~df_ratings["movieId"].isin(ja_assistidos)) &
            (df_ratings["nota"] >= 4.0)
        ]
        .groupby("movieId")["nota"]
        .mean()
        .sort_values(ascending=False)
        .head(20)
    )

    return {"recommended_movie_ids": candidatos.index.tolist()}


def get_recommendationByFilm(movie_id):

    movie_id = int(movie_id)
    if movie_id not in movie_mapper:
        return {"error": "Filme não encontrado"}

    movie_ind = movie_mapper[movie_id]
    movie_vec = X.T[movie_ind]

    neighbours = knn_item.kneighbors(movie_vec, return_distance=False).flatten()
    similar_ids = [
        movie_inv_mapper[n] for n in neighbours if n != movie_ind
    ][:10]
    movies = MovieRepository.getMoviesByIds(similar_ids)

    return {"recommended_movie_ids": movies}