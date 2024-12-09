from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import uuid
from typing import Dict
from utils import Utils
from database import DataBase
from datetime import datetime
DB = DataBase()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

@app.get("/")
def root():
    return {"message":"hello World"}

@app.post("/register_user")
def register_user(user_info: Dict[str, str]):
    """
    Registers users
    user_info: contains the registration information. The user fills the form on the client side and the data is sent
    """

    print(user_info)
    code = Utils.generate_code(7)
    print(f"\n The code is: {code} \n")
    post = {"sid": "", "name": user_info["name"], "email": user_info["email"],"cliques":[], "online_status": 1, "verification_code": code, "last_seen": datetime.today(), "joined_date": datetime.today(
    ), "profile_pic": user_info["profile_picture"], "messages_table": user_info["name"]+"msg_table", "verified": 0, "desktop": user_info["computer"], "phone": user_info["mobile_phone"]}
    DB.enter_post(table=DB.users_table, post=post)
    post = Utils.encode(post)

    # SEND VERIFICATION CODE THROUGH EMAIL
    return post


@app.patch("/verify_code")
def verify_user_registration_code(info: Dict[str, str]):
    """
    Checks if the verification code of a newly registered user is correct
    """
    verification_result = 0
    post = DB.find(filter={"email": info["email"]}, table=DB.users_table)
    print(post["verification_code"])
    if post["verification_code"] == info["code"]:
        print("success")
        post = Utils.encode(obj=post)
        DB.update(filter={"email": info["email"]}, update={
                  "$set": {"verified": 1}}, table=DB.users_table)
        verification_result = 1

    return verification_result

@app.patch("/verify_contact")
def verify_contact(info: Dict[str, str]):
    """
    Checks if contacts exists when adding a contact
    """
    contact = ''
    post = DB.find(filter={"email": info["email"]}, table=DB.users_table)

    if post != None:
        contact = Utils.encode(post)
    
    return contact


@app.post("/uploadfile")
async def create_upload_file(file: UploadFile = File(...)):
    file_extension = file.filename.split(".")[1]
    new_filename = f"{str(uuid.uuid1())}.{file_extension}"
    with open(file=new_filename, mode="wb") as buffer:
        shutil.copyfileobj(file.file,buffer)
    return {"success":True,"mediaURL":new_filename}

@app.get("/file/{filename}")
async def get_file(filename: str):
    # Construct the file path
    file_path = filename  # assuming files are stored in a directory named 'files'
    # Return the file response
    return FileResponse(file_path)

@app.get("/get_emoji")
async def get_emoji():
    """
    THIS FUNCTION SENDS THE EMOJIS TO THE USER WHEN USER REQUESTS FOR IT    
    """
    return FileResponse("./resources/emojis.json")

@app.get("/get_default_profile_pic")
async def get_default_profile_pic():
    """
    THIS FUNCTION SENDS THE EMOJIS TO THE USER WHEN USER REQUESTS FOR IT    
    """
    return FileResponse("./resources/default_profile_pic.jpg")
