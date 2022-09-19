from datetime import datetime
from io import BytesIO
import traceback
from typing import Optional
import youtube_dl
import re
from re import fullmatch
import os
from pytube import Playlist, YouTube
from flask import send_file, flash
import zipfile
from zipfile import ZipFile
from website.database import User, YoutubeLinks, db

def downloader(url: str, user: User, start_video: str, end_video: str):
    if not url:
        flash("Please enter a link to a youtube video or Playlist.", category="error")
        return None
    pattern = r"(https:\/\/www\.youtube\.com\/watch\?v=[A-Za-z0-9-_]{11}).*"
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
            if fullmatch(pattern=pattern, string=start_video):
                try:
                    playlist_min_range = playlist.index(start_video)
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
            if fullmatch(pattern=pattern, string=end_video):
                try:
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
                        print(f"Getting video information for {video.title}")
                        video.streams.get_audio_only().stream_to_buffer(audio_data)
                        audio_data.seek(0)
                        zip.writestr(zinfo_or_arcname=f"{video.title}.mp3", data=audio_data.read(), compress_type=zipfile.ZIP_DEFLATED)
                        new_link = YoutubeLinks(link=video_url, user_id=user.id, title=video.title, date_added=datetime.now().strftime("%b %d %Y %#I:%M %p"))
                        db.session.add(new_link)
                        db.session.commit()
                        break
                    except Exception as e:
                        print(e)
                        db.session.rollback()
                        traceback.print_exc()
            print("Done downloading mp3 files") 
        zip_bytes.seek(0)
        return send_file(zip_bytes, download_name=f"{title}.zip", as_attachment=True)
    else:
        print("Downloading URL")
        try_counter = 0
        while True:
            #sometimes theres some error that doesn't allow a video to be downloaded properly, happens rarely so I let it try 3 times before asking for another link
            if try_counter == 3:
                flash("Something went wrong, please try again!", category="error")
                return None
            try:
                try_counter += 1
                print("Getting video information...")
                audio_data = BytesIO()
                video = YouTube(url)
                video.streams.get_audio_only().stream_to_buffer(audio_data)
                audio_data.seek(0)
                new_link = YoutubeLinks(link=url, user_id=user.id, title=video.title, date_added=datetime.now().strftime("%b %d %Y %#I:%M %p"))
                db.session.add(new_link)
                db.session.commit()
                print("Download is complete!")
                return send_file(audio_data, as_attachment=True, download_name=f"{video.title}.mp3")
            except Exception as e:
                print(e)
                db.session.rollback()
                print("Something went wrong, trying again.")
