import pickle
import os
import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors
from Repository.RatingRepository import RatingRepository
from Service import RecommendationService


def retrain_model():
    # busca todos os ratings do MongoDB
    ratings = list(RatingRepository.getAllRatings())
    df = pd.DataFrame(ratings)
    df = df.dropna(subset=["nota"])

    # normaliza tipos
    df["movieId"] = df["movieId"].astype(int)
    df["nota"]    = df["nota"].astype(float)
    df["userId"]  = df["userId"].astype(str)

    df = df.drop_duplicates(subset=["userId", "movieId"], keep="last")
    df = df[["userId", "movieId", "nota"]]

    M = df["userId"].nunique()
    N = df["movieId"].nunique()

    # mesmos mappers do treino original
    movie_mapper      = dict(zip(np.unique(df["movieId"]), range(N)))
    movie_inv_mapper  = {v: k for k, v in movie_mapper.items()}
    user_mapper       = dict(zip(np.unique(df["userId"]), range(M)))
    user_inv_mapper   = {v: k for k, v in user_mapper.items()}

    # mesma matriz esparsa
    X = csr_matrix(
        (df["nota"],
         ([user_mapper[u] for u in df["userId"]],
          [movie_mapper[m] for m in df["movieId"]])),
        shape=(M, N),
    )

    # mesmos parâmetros do treino original
    knn_item = NearestNeighbors(n_neighbors=11, algorithm="brute", metric="cosine")
    knn_item.fit(X.T)

    knn_user = NearestNeighbors(n_neighbors=11, algorithm="brute", metric="cosine")
    knn_user.fit(X)

    model = {
        "knn_item":         knn_item,
        "knn_user":         knn_user,
        "X":                X,
        "movie_mapper":     movie_mapper,
        "movie_inv_mapper": movie_inv_mapper,
        "user_mapper":      user_mapper,
        "user_inv_mapper":  user_inv_mapper,
        "df":               df,
    }

    model_path = os.path.join(os.path.dirname(__file__), "model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    print(f"Modelo retreinado: {M} usuários × {N} filmes")

    # recarrega em memória sem reiniciar o servidor
    RecommendationService.knn_user         = knn_user
    RecommendationService.knn_item         = knn_item
    RecommendationService.X               = X
    RecommendationService.user_mapper      = user_mapper
    RecommendationService.user_inv_mapper  = user_inv_mapper
    RecommendationService.movie_mapper     = movie_mapper
    RecommendationService.movie_inv_mapper = movie_inv_mapper
    RecommendationService.df_ratings       = df