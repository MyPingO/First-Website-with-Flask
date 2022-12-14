from website import create_app, mp3_downloader
from website.database import User, YoutubeLinks, db
from werkzeug.security import generate_password_hash, check_password_hash
from flask import get_flashed_messages, jsonify, render_template, request, flash, redirect
from flask import send_file, flash, url_for, Response, stream_with_context
from flask_login import login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, join_room, leave_room, send, emit
import zipfile
from zipfile import ZipFile
import concurrent.futures

from pytube import Playlist, YouTube
from datetime import datetime
from io import BytesIO
from re import fullmatch
import traceback


app = create_app()
socketio = SocketIO(app, cors_allowed_origins="*")

#currently does nothing and is useless
#TODO make this keep track of whether a user is downloading something or not
socket_id_to_percentage = {}


@app.route("/", methods=["GET"])
def home():
    return redirect(url_for("playlist_downloader"))


@app.route("/playlist-downloader", methods=["GET"])
def playlist_downloader():
    return render_template("playlist_downloader.html", user=current_user)


@app.route("/downloads-list", methods=["GET"])
def downloads_list():
    return render_template("downloads_list.html", user=current_user)


@app.route("/download/<socketid>", methods=["POST"])
def download(socketid):
    data = request.form
    print(data)
    url = data.get("url")
    start_video = data.get("start_video")
    end_video = data.get("end_video")
    ignore_list = data.get("ignore_list")
    if ignore_list:
        ignore_list = ignore_list.split(",")
    file = downloader(url=url, user=current_user, start_video=start_video, end_video=end_video, ignore_list=ignore_list, socketid=socketid)
    return file or Response(status=204) #204 is "no content" status code


@socketio.on("connect")
def connect():
    print("Connected!")
    socketio.emit("get id")


@socketio.on("disconnect")
def disconnect():
    if request.sid in socket_id_to_percentage:
        # Remove the socket id from the dictionary
        del socket_id_to_percentage[request.sid]
        print(f"Disconnected: {request.sid}")
        print(f"Map: {socket_id_to_percentage}")


# set up the socketid to percentage dictionary for this user
@socketio.on("socket id")
def join(id):
    socket_id_to_percentage[id] = 0
    print(socket_id_to_percentage)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        print(request.form)
        user = User.query.filter_by(email=request.form["email"]).first()
        if user:
            if check_password_hash(user.password, request.form["password"]):
                flash(f"Logged in successfully! Welcome back, {user.username}.", category="success")
                login_user(user, remember=True)
                return redirect(url_for("playlist_downloader"))
            else:
                flash("Incorrect password.", category="error")
        else:
            flash("Email does not exist.", category="error")
    return render_template("login.html", user=current_user)


@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/clear-history", methods=["POST"])
def clear_history():
    try:
        links = YoutubeLinks.query.filter_by(user_id=current_user.id).all()
        for link in links:
            db.session.delete(link)
        db.session.commit()
    except Exception as e:
        print(e)
        db.session.rollback()
        return Response(status=500)
    return Response(status=200)


def check_sign_up_details(email, username, password, confirm_password) -> bool:
    if email and username and password and confirm_password:
        if len(email) < 4:
            flash("Email must be greater than 3 characters.", category="error")
        if len(username) < 2:
            flash("Username must be greater than 1 character.", category="error")
        if len(password) < 5:
            flash("Password must be greater than 4 characters.", category="error")
            return False
        else:
            valid_details = True
            if password != confirm_password:
                flash("Passwords don't match.", category="error")
                valid_details = False
            if User.query.filter_by(email=email).first() != None:
                flash("Email already exists.", category="error")
                valid_details = False
            if User.query.filter_by(username=username).first() != None:
                flash("Username already exists.", category="error")
                valid_details = False
            return valid_details
    else:
        flash("Please fill out all fields.", category="error")
    return False


@app.route("/sign-up", methods=["GET", "POST"])
def sign_up():
    data = request.form
    valid_sign_up_details = False
    print(data)
    if request.method == "POST":
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm-password"]
        valid_sign_up_details = check_sign_up_details(email, username, password, confirm_password)

        if valid_sign_up_details:
            new_user = User(email=email, username=username, password=generate_password_hash(password, method="sha256"))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash(f"Account created! Welcome, {username}.", category="success")

    return (
        redirect(url_for("playlist_downloader"))
        if valid_sign_up_details
        else render_template("sign-up.html", user=current_user)
    )


# TODO check for same file names
def downloader(url: str, user: User, start_video: str, end_video: str, ignore_list: list[str], socketid: str):
    if not url:
        socketio.emit("alert", {"message" : "Please enter a link to a YouTube video or Playlist.", "category" : "error"}, to = socketid)
        return None
    pattern = r"(https:\/\/www\.youtube\.com\/watch\?v=[A-Za-z0-9-_]{11}).*"
    # https://youtu.be/eleven11111
    pattern2 = r"(https:\/\/youtu\.be\/[A-Za-z0-9-_]{11}).*"
    if "/playlist?list=" in url:
        playlist = Playlist(url)
        try:
            title = playlist.title  # tests to see if the playlist has a title
        except KeyError as ke:
            socketio.emit("alert", {"message" : "Cannot download playlist. Reason: Invalid playlist link.", "category" : "error"}, to = socketid)
            return None
        except Exception as e:
            socketio.emit("alert", {"message" : "Cannot download playlist. Reason: Unknown error.", "category" : "error"}, to = socketid)
            print(type(e))
            return None
        if len(playlist.video_urls) == 0:
            socketio.emit("alert", {"message" : "Cannot download playlist. Reason: Playlist is empty.", "category" : "error"}, to = socketid)
            return None
        playlist_min_range = 0
        playlist_max_range = len(playlist.video_urls)
        if start_video:
            match = fullmatch(pattern=pattern, string=start_video) or fullmatch(pattern=pattern2, string=start_video)
            if match:
                try:
                    start_video = match.group(1)
                    playlist_min_range = playlist.index(start_video)
                    # TODO 'https://www.youtube.com/watch?v=fsP8ByqNVOE&list=PLpq1vrb8z_YcqqsLsf6W1YZXhibS7bPSA&index=1' invalid link
                except ValueError as ve:
                    socketio.emit("alert", {"message" : "Cannot download playlist. Reason: Start video link is not in playlist.", "category" : "error"}, to = socketid)
                    print(ve)
                    return None
                except Exception as e:
                    socketio.emit("alert", {"message" : "Cannot download playlist. Reason: Unknown error.", "category" : "error"}, to = socketid)
                    print(type(e))
                    return None
            else:
                socketio.emit("alert", {"message" :
                    "Cannot download playlist. Reason: Start video link is not a valid YouTube link.", "category" : "error"}, to = socketid
                )
                return None
        if end_video:
            match = fullmatch(pattern=pattern, string=end_video) or fullmatch(pattern=pattern2, string=end_video)
            if match:
                try:
                    end_video = match.group(1)
                    playlist_max_range = playlist.index(end_video) + 1
                except ValueError as ve:
                    socketio.emit("alert", {"message" : "Cannot download playlist. Reason: End video link is not in playlist.", "category" : "error"}, to = socketid)
                    print(ve)
                    return None
                except Exception as e:
                    socketio.emit("alert", {"message" : "Cannot download playlist. Reason: Unknown error.", "category" : "error"}, to = socketid)
                    print(type(e))
                    return None
            else:
                socketio.emit("alert", {"message" : "Cannot download playlist. Reason: End video link is not a valid YouTube link.", "category" : "error"}, to = socketid)
                return None
        if playlist_min_range > playlist_max_range:
            socketio.emit("alert", {"message" : "Cannot download playlist. Reason: Start video is after End video.", "category" : "error"}, to = socketid)
            return None
        playlist = playlist[playlist_min_range:playlist_max_range]

        zip_bytes = BytesIO()  # final zip file that will be sent to the user
        byte_files_to_zip = []  # a list of [video_bytes, video_title]
        new_links: list[YoutubeLinks] = []  # links to add to database after download if authenticated

        # use threads to make the download faster
        # no idea if this is "memory leak safe/dangerous" but it works
        with concurrent.futures.ThreadPoolExecutor() as executor:
            videos_handled = []
            for video_url in playlist:
                if video_url not in ignore_list:
                    byte_files_to_zip.append(
                        executor.submit(get_video_info, video_url=video_url, playlist = playlist, videos_handled = videos_handled, socketid = socketid)
                    )
                    video = YouTube(video_url)
                    new_links.append(
                        YoutubeLinks(
                            link=video_url,
                            user_id = None if not user.is_authenticated else user.id,
                            title=video.title,
                            date_added=datetime.now().strftime("%b %d %Y %#I:%M %p"),
                            thumbnail_link=f"https://img.youtube.com/vi/{video.video_id}/mqdefault.jpg",
                        )
                    )
                else:
                    #if a video_url is skipped, still add it to videos_handled
                    #so that the perecentages dont get messed up
                    videos_handled.append(video_url)
        #The previous with statement should close once all workers/threads are done
        #so now we can add all the files to the zip file
        with ZipFile(zip_bytes, "w") as zip:
            for byte_file in byte_files_to_zip:
                #calling .result() on a future object who's value is None wil throw an exception
                try:
                    zip.writestr(
                        zinfo_or_arcname=byte_file.result()[1],
                        data=byte_file.result()[0].read(),
                        compress_type=zipfile.ZIP_DEFLATED, #TODO check if this is the best compression type
                    )
                except Exception as e:
                    continue

        print("Done downloading mp3 files")
        zip_bytes.seek(0) #reset the file pointer to the start of the file
        if user.is_authenticated:
            try:
                db.session.add_all(new_links)
                db.session.commit()
            except Exception as e:
                print(e)
                db.session.rollback()
                traceback.print_exc()
        socketio.emit("file name", f"{title}.zip", to=socketid) #send the file name to the client/frontend
        #check if zip_bytes is empty
        if zip_bytes.getbuffer().nbytes != 0:
            return send_file(zip_bytes, download_name=f"{title}.zip", as_attachment=True)
        else:
            return None
    #if only one video needs to be downloaded
    else:
        match = fullmatch(pattern=pattern, string=url) or fullmatch(pattern=pattern2, string=url)
        if not match:
            socketio.emit("alert", {"message" : "Cannot download video. Reason: Invalid YouTube link.", "category" : "error"}, to = socketid)
            return None
        url = match.group(1)
        print("Downloading URL")
        try_counter = 0
        while True:
            # sometimes theres some error that doesn't allow a video to be downloaded properly, happens rarely so I let it try 3 times before flashing an error
            if try_counter == 3:
                socketio.emit("alert", {"message" : "Something went wrong, please try again!", "category" : "error"}, to = socketid)
                return None
            try:
                try_counter += 1
                audio_data = BytesIO()
                video = YouTube(url)
                print(f"Getting video information for {video.title}")
                video.streams.get_audio_only().stream_to_buffer(audio_data)
                audio_data.seek(0)
                if user.is_authenticated:
                    new_link = YoutubeLinks(
                        link=url,
                        user_id=user.id,
                        title=video.title,
                        date_added=datetime.now().strftime("%b %d %Y %#I:%M %p"),
                        thumbnail_link=f"https://img.youtube.com/vi/{video.video_id}/mqdefault.jpg",
                    )
                    db.session.add(new_link)
                    db.session.commit()
                print("Download is complete!")
                socketio.emit("file name", f"{video.title}.mp3", to=socketid) #send the file name to the client/frontend
                return send_file(audio_data, as_attachment=True, download_name=f"{video.title}.mp3")
            except Exception as e:
                print(e)
                db.session.rollback()
                print("Something went wrong, trying again.")


#function for returning a videos' bytes and title from its url
def get_video_info(video_url: str, playlist: Playlist, videos_handled: list, socketid) -> ZipFile:
    try_counter = 0
    video = YouTube(video_url)
    while True:
        # sometimes theres some error that doesn't allow a video to be downloaded properly, happens rarely so I let it try 3 times before flashing an error
        if try_counter == 3:
            #add a video_url to list in case a video could not be downloaded
            #so that the perecentages dont get messed up
            videos_handled.append(video_url)
            socketio.emit("alert", {"message" : f'Error: Something went wrong while downloading <a href = "{video_url}">{video.title}</a>', "category" : "error"}, to = socketid)
            return None
        try:
            try_counter += 1
            audio_data = BytesIO()
            print(f"Downloading {video.title}...")
            video.streams.get_audio_only().stream_to_buffer(audio_data)
            audio_data.seek(0)

            videos_handled.append(video_url)
            percentage = round(len(videos_handled) / len(playlist) * 100, 2)
            socketio.emit("zip update", percentage, to=socketid)

            return [audio_data, video.title + str(".mp3")]
        except Exception as e:
            print(e)
            traceback.print_exc()
if __name__ == "__main__":
    socketio.run(app=app, debug=True, host="0.0.0.0", port=25565)
