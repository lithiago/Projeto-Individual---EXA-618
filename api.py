from flask import Flask, jsonify, request
from Model.User import User
from Repository.UserRepository import UserRepository
from Repository.RatingRepository import RatingRepository
from Repository.MovieRepository import MovieRepository
from Service.RecommendationService import get_recommendationByFilm, get_recommendationsByUser

app = Flask(__name__)


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
 
    return jsonify({"message": "Usuário criado com sucesso.", "user": user.name}), 201

@app.route('/auth/login', methods=['POST'])
def login():
    body = request.get_json()
    if not body or not body.get("name") or not body.get("password"):
        return jsonify({"error": "Campos 'nome', 'email' e 'senha' são obrigatórios."}), 400
    
    
    user = UserRepository.findByUser(body["name"])
    if (not user) or (user['password'] != body["password"]):
        return jsonify({"error": "Credenciais inválidas."}), 401
    
    has_ratings = RatingRepository.hasRatings(user["name"])
    
    return jsonify({"O usuário tem avaliações": has_ratings}), 200

@app.route('/movies/top-rated', methods=["GET"])
def top_rated():
    movies = RatingRepository.getTopRated(limit=60)
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
        return jsonify({"error": "O parâmetro 'user_id' é obrigatório para filtrar filmes não vistos."}), 400

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
    return jsonify(result), 200


@app.route('/movies/recommendation/', methods=["GET"])
def getRecommendationsByFilm():
    movieId = request.args.get('movieId')
    result = get_recommendationByFilm(movieId)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result), 200    
if __name__ == "__main__":
    app.run(debug=True)
 