import eventlet
import socketio
import os
import json
import uuid
from utils import Utils
from database import DataBase
from datetime import datetime
import base64
from mutagen import File
from threading import Thread
from aiohttp import web
from io import BytesIO
from PIL import Image
users_online = {}
eventlet.monkey_patch()

DB = DataBase()
# , async_mode='gevent', logger=True, engineio_logger=True
# sio = socketio.Server(cors_allowed_origins="*")
sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)
# app = socketio.ASGIApp(sio, static_files={
#     '/': {'content_type': 'text/html', 'filename': 'index.html'}
# })



async def index(request):
    """Serve the client-side application."""
    with open('index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')
    

@sio.event
def connect(sid, environ):
    print('connect ', sid)


@sio.event
def update_status(sid, filter):
    if bool(filter):
        users_online[filter["email"]] = sid
        print(users_online)
        doc = DB.update(filter={"email": filter["email"]}, update={
                        "$set": {"online_status": 1, "sid": sid}}, table=DB.users_table)
        # print("Updating this user: "+doc["sid"])
        print("This is my email "+filter["email"])

        file = "./"+filter["email"]+".pagemsg"
        isFile = os.path.isfile(file)

        if isFile:
            json_msg = json.load(file)
            print(json_msg)


@sio.event
def check_if_acc_exist(sid, param):
    post = DB.find(filter={"email": param["email"]}, table=DB.users_table)

    if post != None:
        contact = Utils.encode(post)
        print(contact)

        if param["request_type"] == "message_from_unknown_source":
            sio.emit(event="verify_acc", data=contact, to=sid)
        else:
            contact["user_saving_name"] = param["name"]
            sio.emit(data=contact, to=sid, event="verify_acc_contact")


@sio.event
def recieve_message(sid, msg_data):
    print(msg_data)
    message_to_save = {"id": msg_data["uuid"], "message": msg_data["message"],
                       "time": msg_data["time"], "type": "txt", "sender": msg_data["from"], "recipient": msg_data["to"]}
    recipient = DB.find(filter={"email": msg_data["to"]}, table=DB.users_table)
    if recipient != None:
        if recipient["online_status"] == 0:
            json_content = ''

            if os.path.exists(f"./saved-messages/{recipient['email']}.json"):

                # When the file that the saved messages are kept in for the user does exist

                with open(file=f"./saved-messages/{recipient['email']}.json", mode="r") as file:
                    json_content = json.load(file)

                if bool(json_content) == False:
                    # File does not have any message saved
                    print("Natin in json file")
                    json_content = {msg_data["from"]: message_to_save}
                    print(json_content)
                else:
                    # File has message saved
                    print("Something dey")

                    if msg_data["from"] in json_content:
                        # Already contains message from the sender
                        print("This key already exists")

                        if isinstance(json_content[msg_data["from"]], list):
                            # Contains multiple messages from the sender
                            json_content[msg_data["from"]].append(
                                message_to_save)
                        else:
                            # Has just one message from the sender
                            msg_list = [json_content[msg_data["from"]]]
                            msg_list.append(message_to_save)

                            json_content[msg_data["from"]] = msg_list
                            print(json_content)
                    else:
                        # Does not contain any message from the sender
                        print("The key does not exist")
                        json_content[msg_data["from"]] = message_to_save
                        print(json_content)

                # Saving messages
                with open(file=f"./saved-messages/{recipient['email']}.json", mode="w") as file:
                    json.dump(json_content, file)

            else:
                # When the file that the saved messages are kept in for the user does not exist
                json_content = {msg_data["from"]: message_to_save}

                # Saving messages
                with open(file=f"./saved-messages/{recipient['email']}.json", mode="w") as file:
                    json.dump(json_content, file)
        else:
            sio.emit(event="recieve_message",
                     data=msg_data, to=recipient["sid"])
            print("Sending message to this user " + recipient["sid"])


@sio.event
def send_saved_messages(sid, code):
    if code == 102:
        requester = DB.find(filter={"sid": sid}, table=DB.users_table)
        if os.path.isfile(f"./saved-messages/{requester['email']}.json"):

            with open(file=f"./saved-messages/{requester['email']}.json", mode="r") as file:
                messages = json.load(file)
                sio.emit("server_saved_messages", messages, sid)


@sio.event
def media_message(sid, msg_data: dict):
    msg_data["sender"] = msg_data["from"]
    msg_data["recipient"] = msg_data["to"]
    msg_data["path"] = msg_data["mediaURL"]

    msg_data["id"] = msg_data["uuid"]

    recipient = DB.find(
        filter={"email": msg_data["recipient"]}, table=DB.users_table)
    if recipient != None:
        if recipient["online_status"] == 0:
            json_content = ''
            with open(file=f"./saved-messages/{recipient['email']}.json", mode="r") as file:
                json_content = json.load(file)

            if bool(json_content) == False:
                print("Natin in json file")
                json_content = {msg_data["from"]: msg_data}
                print(json_content)
            else:
                print("Something dey")
                if msg_data["from"] in json_content:
                    print("This key already exists")

                    if isinstance(json_content[msg_data["from"]], list):
                        json_content[msg_data["from"]].append(msg_data)
                    else:
                        msg_list = [json_content[msg_data["from"]]]
                        msg_list.append(msg_data)

                        json_content[msg_data["from"]] = msg_list
                        print(json_content)
                else:
                    print("The key does not exist")
                    json_content[msg_data["from"]] = msg_data
                    print(json_content)

            # Saving messages
            with open(file=f"./saved-messages/{recipient['email']}.json", mode="w") as file:
                json.dump(json_content, file)
        else:
            if msg_data["type"] == "audio":
                if msg_data["albumCover"] != "music.png":
                    # Replace with your audio file
                    audio_file = File(msg_data["mediaURL"])
                    if "APIC:" in audio_file.tags:
                        apic = audio_file.tags["APIC:"].data
                        image_data = apic

                        # Open the image using PIL and create a thumbnail
                        with BytesIO(image_data) as f:
                            with Image.open(f) as img:
                                img.thumbnail((100, 100))
                                thumbnail_data = BytesIO()
                                img.save(thumbnail_data, format='JPEG')

                        # Get the Base64-encoded thumbnail data
                        thumbnail_b64 = base64.b64encode(
                            thumbnail_data.getvalue()).decode()

                        # Print the Base64-encoded thumbnail data
                        print(thumbnail_b64)
                        msg_data["albumCover"] = thumbnail_b64
                    else:
                        print("No album cover found")
            sio.emit(to=recipient["sid"],
                     event="recieve_message", data=msg_data)


@sio.event
def sign_in(sid, details):
    post = DB.find(filter={"email": details["email"]}, table=DB.users_table)
    if post != None:
        DB.update(filter={"email": details["email"]}, update={
                  "$set": {"online_status": 1}}, table=DB.users_table)
        sio.emit(data=Utils.encode(post), to=sid, event="sign-check-complete")

    elif post == None:
        sio.emit(data=False, to=sid, event="sign-check-complete")


@sio.event
def create_clique(sid, info):
    """
    Adds the newly created clique to the database

    It also start a thread to add the members of the clique who are online to the room
    """
    print(info)
    # Commented beacause i am testing
    admin = DB.find(filter={"sid": sid}, table=DB.users_table)
    post = {
        "name": info["name"],
        "link": info["link"],
        "description": info["about"],
        "members": info["members"],
        "admins": ["john@gmail.com"],
        "settings": info["settings"],
        "profile_pic": info["profile_pic"],
        "roomname": info["link"]
    }
    sio.enter_room(sid=sid, room=info["link"])
    DB.enter_post(table=DB.clique_table, post=post)
    post = Utils.encode(post)
    sio.emit(event="creation-done", data=post, to=sid)

    for m in post["members"]:
        DB.update(filter={"email": m}, update={
            "$push": {"cliques": info["link"]}}, table=DB.users_table)
        if m in users_online:
            sio.enter_room(sid=users_online[m], room=info["link"])
        else:
            print(m + " not online")
    sio.emit(event="added_to_clique", data=post,
             room=info["link"], skip_sid=sid)


@sio.event
def send_clique_message(sid, message):
    clique = DB.find(filter={"link": message["to"]}, table=DB.clique_table)
    sio.emit(data=message, event="recieve_message",
             room=message["to"], skip_sid=sid)

    for user in clique["members"]:
        recipient = DB.find(filter={"email": user}, table=DB.users_table)
        if recipient != None:
            if recipient["online_status"] == 0:
                with open(file=f"./saved-messages/{recipient['email']}.json", mode="w") as file:
                    json.dump(message, file)


@sio.event
def disconnect(sid):
    print('disconnect ', sid)
    DB.update(filter={"sid": sid}, update={
              "$set": {"online_status": 0, "last_seen": datetime.today()}}, table=DB.users_table)

    # Removes you from the dictionary that keeps track of users thath are online
    user = DB.find(filter={"sid": sid}, table=DB.users_table)
    users_online.pop(user["email"])
    print(users_online)


@sio.event
def send_ice_cand(sid, obj):
    print("INCOMING CALL")
    print("ICE cand ", obj)
    callee = DB.find(filter={"email": obj["email"]}, table=DB.users_table)
    if callee != None:
        if callee["online_status"] == 1:
            sio.emit("icecandidate", obj["cand"], callee["sid"])  # callee["sid"])


@sio.event
def _ice_cand(sid, obj):
    print("INCOMING CALL")
    print("ICE cand ", obj)
    callee = DB.find(filter={"email": obj["email"]}, table=DB.users_table)
    if callee != None:
        if callee["online_status"] == 1:
            sio.emit("icecandidate", obj["cand"], callee["sid"])


@sio.event
def send_offer(sid, offer):
    offer = dict(offer)
    print(type(offer))
    callee = DB.find(
        filter={"email": offer["email"]}, table=DB.users_table)
    caller = DB.find(filter={"sid": sid}, table=DB.users_table)
    if callee != None:
        if callee["online_status"] == 1:

            offer_obj = {
                "offer": offer["offer"], "email": caller["email"], "calltype": offer["calltype"]}
            sio.emit(event="rtc-offer", data=offer_obj,
                     to=callee["sid"])  # to=callee["sid"])


@sio.event
def send_answer(sid, answer):
    print(answer)
    caller = DB.find(
        filter={"email": answer["email"]}, table=DB.users_table)
    # callee = DB.find(filter={"sid": sid}, table=DB.users_table)
    if caller != None:
        if caller["online_status"] == 1:
            answer_obj = {
                "answer": answer["answer"], "email": caller["email"]}
            print(caller["sid"])
            sio.emit("rtc-answer", answer_obj, caller["sid"])


def thread_for_joining_cliques(sid, cliques):
    for clique in cliques:
        clique = DB.find(filter={"name": clique}, table=DB.clique_table)
        sio.enter_room(sid=sid, room=clique["roomname"])


@sio.event
def join_clique_rooms(sid, clique_list):
    thread = Thread(target=thread_for_joining_cliques,
                    args=(sid, clique_list), daemon=True)
    thread.start()

@sio.event
def start_audio_call(sid, callee):
    room_name = str(uuid.uuid4())
    callee = DB.find(filter={"email": callee}, table=DB.users_table)
    caller = DB.find(filter={"sid":sid}, table=DB.users_table)
    if callee["online_status"] == 1:
        sio.emit("incomingCall",{"call_type":"audio","caller":caller["email"],"call_room":room_name},callee["sid"])
        sio.enter_room(sid=sid,room=room_name)
        sio.enter_room(sid=callee["sid"],room=room_name)
        sio.emit("audioCallStarted",room_name, sid)
    else:
        sio.emit("callee_offline",False,sid)

@sio.event
def voice_call_data(sid,call_data):
    sio.emit(event="recieve_call_data",room_name=call_data["call_room"])


app.router.add_static("/static", "static")
app.router.add_get("/index.html", index)


if __name__ == '__main__':
    # eventlet.wsgi.server(eventlet.listen(("0.0.0.0", 9000)), app)
    web.run_app(app, host="0.0.0.0", port=8080)
