from flask import Flask, jsonify, request
from email.message import EmailMessage
from Model.User import User
from Repository.UserRepository import UserRepository
from Repository.RatingRepository import RatingRepository
from Repository.MovieRepository import MovieRepository
from Service.RecommendationService import get_recommendationByFilm, get_recommendationsByUser
from jose import jwt
from dotenv import load_dotenv
import datetime
import os
import smtplib

load_dotenv()
app = Flask(__name__)
SECRET_KEY = os.environ.get("JWT_SECRET", "dev_secret")

def generate_reset_token(email: str) -> str:
    payload = {
        "reset_password": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_reset_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("reset_password")
    except Exception:
        return None


def send_reset_email(recipient: str, reset_url: str):
    smtp_server = os.environ.get("MAIL_SERVER")
    smtp_port = int(os.environ.get("MAIL_PORT", 587))
    smtp_username = os.environ.get("MAIL_USERNAME")
    smtp_password = os.environ.get("MAIL_PASSWORD")
    mail_sender = os.environ.get("MAIL_DEFAULT_SENDER", smtp_username)
    use_ssl = os.environ.get("MAIL_USE_SSL", "false").lower() in ("1", "true", "yes")
    use_tls = os.environ.get("MAIL_USE_TLS", "true").lower() in ("1", "true", "yes")

    if not smtp_server or not smtp_username or not smtp_password or not mail_sender:
        raise RuntimeError("Configuração SMTP incompleta. Verifique MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD e MAIL_DEFAULT_SENDER.")

    message = EmailMessage()
    message["Subject"] = "Redefinição de senha"
    message["From"] = mail_sender
    message["To"] = recipient
    message.set_content(
        f"Para redefinir sua senha, acesse o link:\n{reset_url}\n\nSe você não solicitou essa alteração, ignore esta mensagem."
    )

    if use_ssl:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
    else:
        server = smtplib.SMTP(smtp_server, smtp_port)
        if use_tls:
            server.starttls()

    server.login(smtp_username, smtp_password)
    server.send_message(message)
    server.quit()


@app.route('/')
def index():
    return "Minha API Flask"




@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    body = request.get_json() or {}
    email = body.get('email')

    if not email:
        return jsonify({"error": "O campo 'email' é obrigatório."}), 400

    user = UserRepository.findByEmail(email)
    if not user:
        return jsonify({"error": "Usuário não encontrado."}), 404

    token = generate_reset_token(email)
    base_url = os.environ.get('APP_BASE_URL', request.host_url.rstrip('/'))
    reset_url = f"{base_url}/reset-password/{token}"

    try:
        send_reset_email(email, reset_url)
    except Exception as err:
        return jsonify({"error": f"Falha ao enviar email: {str(err)}"}), 500

    return jsonify({
        "message": "Email de redefinição enviado com sucesso.",
        "email": email
    }), 200


@app.route('/reset-password/<token>', methods=['POST'])
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        return jsonify({"error": "Token inválido ou expirado."}), 400

    body = request.get_json() or {}
    new_password = body.get('password')
    if not new_password:
        return jsonify({"error": "O campo 'password' é obrigatório."}), 400

    user = UserRepository.findByEmail(email)
    if not user:
        return jsonify({"error": "Usuário não encontrado."}), 404

    UserRepository.updatePassword(email, new_password)
    return jsonify({"message": "Senha atualizada com sucesso."}), 200
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