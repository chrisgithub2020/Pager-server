from pymongo import MongoClient
client = MongoClient()


class DataBase:

    db = client["Pager"]
    users_table = db["users"]
   
    messages_table = db["messages"]
    clique_table = db["cliques"]
    users_table.find()

    def find(self, filter, table):
        post = table.find_one(filter)
        return post
    
    def update(self,filter,update,table):
        table.find_one_and_update(filter,update)

    def enter_post(self, table, post):
        table.insert_one(post)
