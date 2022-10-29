from website import create_app, mp3_downloader
from website.database import User, YoutubeLinks, db
from werkzeug.security import generate_password_hash, check_password_hash
from flask import render_template, request, flash, redirect
from flask import send_file, flash, url_for, Response, stream_with_context
from flask_login import login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, join_room, leave_room, send, emit
import zipfile
from zipfile import ZipFile

from pytube import Playlist, YouTube
from datetime import datetime
from io import BytesIO
from re import fullmatch
import traceback


app = create_app()
socketio = SocketIO(app, cors_allowed_origins="*")
percentage = None #TODO make dict

socketid = None

socket_id_to_percentage = {

}

@app.route('/', methods = ['GET', 'POST'])
def home():
    return redirect(url_for('playlist_downloader'))

@app.route('/playlist-downloader')
def playlist_downloader():
    return render_template('playlist_downloader.html', user = current_user)

@app.route('/download/<socketid>', methods=['POST'])
def download(socketid):
    data = request.form
    print(data)
    start_video = data.get('start_video')
    end_video = data.get('end_video')
    url = data.get('url')
    file = downloader(url = url, user = current_user, start_video = start_video, end_video = end_video, socketid = socketid)
    return file or redirect(url_for('playlist_downloader'))

@socketio.on('connect')
def connect():
    print("Connected!")

@socketio.on('message')
def handle_percent_change(message):
    pass

@socketio.on('socket id')
def join(id):
    socket_id_to_percentage[id] = percentage
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
    return render_template("login.html", user = current_user)

@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

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

    return redirect(url_for('playlist_downloader')) if valid_sign_up_details else render_template("sign-up.html", user = current_user)

def downloader(url: str, user: User, start_video: str, end_video: str, socketid: str):
    if not url:
        flash("Please enter a link to a youtube video or Playlist.", category="error")
        return None
    pattern = r"(https:\/\/www\.youtube\.com\/watch\?v=[A-Za-z0-9-_]{11}).*"
    #https://youtu.be/eleven11111
    pattern2 = r"(https:\/\/youtu\.be\/[A-Za-z0-9-_]{11}).*"
    if "/playlist?list=" in url:
        playlist = Playlist(url)
        try:
            title = playlist.title #tests to see if the playlist has a title
        except KeyError as ke:
            flash("Cannot download playlist. Reason: Invalid playlist link.", category="error")
            return None
        except Exception as e:
            flash ("Cannot download playlist. Reason: Unknown error.", category="error")
            print(type(e))
            return None
        if len(playlist.video_urls) == 0:
            flash("Cannot download playlist. Reason: Playlist is empty.", category="error")
            return None
        playlist_min_range = 0
        playlist_max_range = len(playlist.video_urls)
        if start_video:
            match = fullmatch(pattern=pattern, string=start_video) or fullmatch(pattern=pattern2, string=start_video)
            if match:
                try:
                    start_video = match.group(1)
                    playlist_min_range = playlist.index(start_video)
                    #TODO 'https://www.youtube.com/watch?v=fsP8ByqNVOE&list=PLpq1vrb8z_YcqqsLsf6W1YZXhibS7bPSA&index=1' invalid link
                except ValueError as ve:
                    flash("Cannot download playlist. Reason: Start video link is not in playlist.", category="error")
                    print(ve)
                    return None
                except Exception as e:
                    flash("Cannot download playlist. Reason: Unknown error.", category="error")
                    print(type(e))
                    return None
            else:
                flash("Cannot download playlist. Reason: Start video link is not a valid youtube link.", category="error")
                return None
        if end_video:
            match = fullmatch(pattern=pattern, string=end_video) or fullmatch(pattern=pattern2, string=end_video)
            if match:
                try:
                    end_video = match.group(1)
                    playlist_max_range = playlist.index(end_video) + 1
                except ValueError as ve:
                    flash("Cannot download playlist. Reason: End video link is not in playlist.", category="error")
                    print(ve)
                    return None
                except Exception as e:
                    flash("Cannot download playlist. Reason: Unknown error.", category="error")
                    print(type(e))
                    return None
            else:
                flash("Cannot download playlist. Reason: End video link is not a valid youtube link.", category="error")
                return None
        if playlist_min_range > playlist_max_range:
            flash("Cannot download playlist. Reason: Start video is after End video.", category="error")
            return None
        playlist = playlist[playlist_min_range: playlist_max_range]
        zip_bytes = BytesIO()
        new_links: list[YoutubeLinks] = []
        global percentage
        percentage = 0
        with ZipFile(zip_bytes, "w") as zip:
            for video_url in playlist:
                try_counter = 0
                while True:
                    if try_counter == 3:
                        flash(f"Error: Something went wrong. URL = {video_url}", category="error")
                        break
                    try:
                        try_counter += 1
                        audio_data = BytesIO()
                        video = YouTube(video_url)
                        print(f"Downloading {video.title}...")
                        video.streams.get_audio_only().stream_to_buffer(audio_data)
                        audio_data.seek(0)
                        zip.writestr(zinfo_or_arcname=f"{video.title}.mp3", data=audio_data.read(), compress_type=zipfile.ZIP_DEFLATED)
                        if (user.is_authenticated):
                            new_links.append(YoutubeLinks(link=video_url, user_id=user.id, title=video.title, date_added=datetime.now().strftime("%b %d %Y %#I:%M %p"), thumbnail_link=video.thumbnail_url))
                        percentage = round((playlist.index(video_url) + 1) / len(playlist) * 100, 2)
                        socketio.emit("zip update", percentage, to=socketid)
                        break
                    except Exception as e:
                        print(e)
                        traceback.print_exc()
        print("Done downloading mp3 files") 
        zip_bytes.seek(0)
        if user.is_authenticated:
            try:
                db.session.add_all(new_links)
                db.session.commit()
            except Exception as e:
                print(e)
                db.session.rollback()
                traceback.print_exc()
        socketio.emit("file name", f"{title}.zip", to=socketid)
        return send_file(zip_bytes, download_name=f"{title}.zip", as_attachment=True)
    else:
        #TODO zip.open(zip.filelist[0], "w")
        match = fullmatch(pattern=pattern, string=url) or fullmatch(pattern=pattern2, string=url)
        if not match:
            flash("Cannot download video. Reason: Invalid youtube link.", category="error")
            return None
        url = match.group(1)
        print("Downloading URL")
        try_counter = 0
        while True:
            #sometimes theres some error that doesn't allow a video to be downloaded properly, happens rarely so I let it try 3 times before asking for another link
            if try_counter == 3:
                flash("Something went wrong, please try again!", category="error")
                return None
            try:
                try_counter += 1
                audio_data = BytesIO()
                video = YouTube(url)
                print(f"Getting video information for {video.title}")
                video.streams.get_audio_only().stream_to_buffer(audio_data)
                audio_data.seek(0)
                if user.is_authenticated:
                    new_link = YoutubeLinks(link=url, user_id=user.id, title=video.title, date_added=datetime.now().strftime("%b %d %Y %#I:%M %p"), thumbnail_link=video.thumbnail_url)
                    db.session.add(new_link)
                    db.session.commit()
                print("Download is complete!")
                socketio.emit("file name", f"{video.title}.mp3", to=socketid)
                return send_file(audio_data, as_attachment=True, download_name=f"{video.title}.mp3")
            except Exception as e: 
                print(e)
                db.session.rollback()
                print("Something went wrong, trying again.")

if __name__ == '__main__':
    socketio.run(app = app, debug=True, host='0.0.0.0', port = 25565)
