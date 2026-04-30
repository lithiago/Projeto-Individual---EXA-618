from pymongo import MongoClient
from Model.User import User
import os 
from dotenv import load_dotenv

load_dotenv() 

client = MongoClient(os.getenv('url_mongodb'))
print(os.getenv('url_mongodb'))
db     = client.get_database("Projeto1")
collection = db.get_collection("Users")


class UserRepository:

    @staticmethod
    def findByUser(name: str):
        return collection.find_one({"name": name})

    @staticmethod
    def findByEmail(email: str):
        return collection.find_one({"email": email})

    @staticmethod
    def create(user: User):
        result = collection.insert_one({"name": user.name, "email": user.email, "password": user.password})
        print("Inserted ID:", result.inserted_id)
