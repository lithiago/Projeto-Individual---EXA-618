from flask import Flask, jsonify, request
from Model.User import User
from Repository.UserRepository import UserRepository
from Repository.RatingRepository import RatingRepository
from Repository.MovieRepository import MovieRepository
from Service.RecommendationService import get_recommendationByFilm, get_recommendationsByUser
from jose import jwt
import datetime
import os

app = Flask(__name__)
SECRET_KEY = os.environ.get("JWT_SECRET", "dev_secret")

@app.route('/')
def index():
    return "Minha API Flask"
@app.route('/auth/register', methods=['POST'])
def createUser():
    body = request.get_json()

    if not body or not body.get("name") or not body.get("email") or not body.get("password"):
        return jsonify({"error": "Campos 'nome', 'email' e 'senha' são obrigatórios."}), 400

    user = User(name=body["name"], email=body["email"], password=body["password"])

    if UserRepository.findByUser(user.name):
        return jsonify({"error": "Usuário já cadastrado."}), 400

    if UserRepository.findByEmail(user.email):
        return jsonify({"error": "E-mail já cadastrado."}), 400

    UserRepository.create(user)

    token = jwt.encode({
        "sub": user.name,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }, SECRET_KEY, algorithm="HS256")

    return jsonify({"token": token, "user": user.name}), 201


@app.route('/auth/login', methods=['POST'])
def login():
    body = request.get_json()

    if not body or not body.get("email") or not body.get("password"):
        return jsonify({"error": "Campos 'email' e 'senha' são obrigatórios."}), 400

    user = UserRepository.findByEmail(body["email"])

    if (not user) or (user['password'] != body["password"]):
        return jsonify({"error": "Credenciais inválidas."}), 401

    has_ratings = RatingRepository.hasRatings(user["name"])
    print("has_ratings:", has_ratings)

    token = jwt.encode({
        "sub": user["name"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }, SECRET_KEY, algorithm="HS256")

    return jsonify({"token": token, "has_ratings": has_ratings}), 200


@app.route('/featured', methods=['GET'])
def getFeatured():
    movies = RatingRepository.getTopRated(limit=1)
    return jsonify(movies), 200

@app.route('/new-featured', methods=['GET'])
def getNewFeatured():
    movieId = request.args.get('movieId')
    movie = get_recommendationByFilm(movieId)
    return jsonify(movie), 200


@app.route('/movies/top-rated', methods=["GET"])
def top_rated():
    movies = RatingRepository.getTopRated(limit=60)
    return jsonify({"Lista de Filmes": movies}), 200

@app.route('/movies/most-rated', methods=["GET"])
def most_rated():
    movies = RatingRepository.getTopRated(limit=15)
    return jsonify({"Lista de Filmes": movies}), 200


@app.route('/movies/genres', methods=['GET'])
def getFilmsByGender():
    genres = request.args.getlist('genre')

    if not genres:
        return jsonify({"error": "Informe ao menos um gênero."}), 400

    try:
        movies = MovieRepository.getFilmsByGender(genres, limit=20)
        return jsonify(movies), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/movies/non-watched', methods=['GET'])
def getFilmsNonWatched():
    user_id = request.args.get('user_id')
    limit = request.args.get('limit', default=20, type=int)

    if not user_id:
        return jsonify({"error": "O parâmetro 'user_id' é obrigatório."}), 400

    try:
        movies = RatingRepository.getUnwatchedMovies(user_id, limit)
        return jsonify(movies), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar filmes não assistidos: {str(e)}"}), 500


@app.route('/movies/rating', methods=['POST'])
def createRating():
    body = request.get_json()

    if not body or not body.get("userId") or not body.get("movieId") or not body.get("nota"):
        return jsonify({"error": "Campos 'userId', 'movieId' e 'nota' são obrigatórios."}), 400

    inserted_id = RatingRepository.createRating(
        user_id=body["userId"],
        movie_id=body["movieId"],
        nota=body["nota"],
    )

    return jsonify({"message": "Avaliação registrada.", "id": inserted_id}), 201


@app.route('/movies/recommendations/', methods=['GET'])
def getRecommendationsByUser():
    user_id = request.args.get('userId')
    result = get_recommendationsByUser(user_id)

    if "error" in result:
        return jsonify(result), 404

    movie_ids = result["recommended_movie_ids"]
    movies = MovieRepository.getMoviesByIds(movie_ids)

    return jsonify({"movies": movies}), 200

@app.route('/movies/recommendation/', methods=["GET"])
def getRecommendationsByFilm():
    movieId = request.args.get('movieId')
    result = get_recommendationByFilm(movieId)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result), 200


@app.route('/movies/rated/', methods=["GET"])
def getRatedFilm():
    userId = request.args.get('userId')
    result = RatingRepository.getWatchedMovies(userId)
    print(result)
    if "error" in result:
        return jsonify(result), 404
    return jsonify({"movies": result}), 200



@app.route('/movies/most-rated', methods=["GET"])
def getMostRatedFilm():
    movies = RatingRepository.getTopRated(limit=1)
    return jsonify(movies), 200

@app.route('/model/retrain', methods=['POST'])
def retrain():
    try:
        from Service.TrainService import retrain_model
        retrain_model()
        return jsonify({"message": "Modelo retreinado com sucesso."}), 200
    except Exception as e:
        print("ERRO NO RETRAIN:", e)  # <- log
        import traceback
        traceback.print_exc()  # <- stack trace completo
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)