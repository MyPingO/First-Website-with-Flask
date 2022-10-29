from datetime import datetime
from io import BytesIO
import traceback
import youtube_dl
import re
from re import fullmatch
import os
from pytube import Playlist, YouTube
from flask import send_file, flash, jsonify
import zipfile
from zipfile import ZipFile
from website.database import User, YoutubeLinks, db

#TODO: replace '/' in video title with '-'

def downloader(url: str, user: User, start_video: str, end_video: str):
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
                        break
                    except Exception as e:
                        print(e)
                        traceback.print_exc()
                yield f"Downloaded {video.title} {round((playlist.index(video_url) + 1) / len(playlist) * 100, 2)}%"
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
                return send_file(audio_data, as_attachment=True, download_name=f"{video.title}.mp3")
            except Exception as e:
                print(e)
                db.session.rollback()
                print("Something went wrong, trying again.")
