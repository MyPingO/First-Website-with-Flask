from datetime import datetime
from io import BytesIO
import traceback
from turtle import title
import youtube_dl
import re
import os
from pytube import Playlist, YouTube
from flask import send_file, flash
import zipfile
from zipfile import ZipFile
from website.database import User, YoutubeLinks, db

def downloader(url: str, user: User):
    if "/playlist?list=" in url:
        # while True:
        #     playlist = Playlist(url)
        #     if len(playlist.video_urls) == 0:
        #         print("\n--------------------------------------------------------------------------------------------------\n| There was an error, please make sure you entered a valid link to a playlist that is not empty. | \n--------------------------------------------------------------------------------------------------\n")
        #         url = input("Enter the youtube link you want to download: ")
        #         downloader(url)
        #     else:
        #         break          
        # while True:
        #     yes_no = input("This is a playlist! Would you like to specify a custom download range? Yes/No\n")
        #     if yes_no.casefold() != "no" and yes_no.casefold() != "yes":
        #         print("\n----------------------------------------------\n| Error: Invalid response, please try again! | \n----------------------------------------------\n")
        #         continue
        #     break
        # if yes_no.casefold() == "yes":
        #     pattern = r"(https:\/\/www\.youtube\.com\/watch\?v=[A-Za-z0-9-_]{11}).*"
        #     while True:
        #         try:
        #             first_video = re.fullmatch(pattern,input("Enter the url of the song in the playlist you want to start downloading from: ")).group(1)
        #             playlist_min_range = playlist.index(first_video)
        #             break
        #         except:
        #             print("\n------------------------------------------------------------------------\n| This url cannot be found in the playlist you gave, please try again! |\n------------------------------------------------------------------------\n")
        #     while True:
        #         try:
        #             last_video = re.fullmatch(pattern,input("Enter the url of the song in the playlist you want to download to: ")).group(1)
        #             playlist_max_range = playlist.index(last_video) + 1
        #             break
        #         except:
        #             print("\n------------------------------------------------------------------------\n| This url cannot be found in the playlist you gave, please try again! |\n------------------------------------------------------------------------\n")
        #     playlist = playlist[playlist_min_range: playlist_max_range]
        playlist = Playlist(url)
        zip_bytes = BytesIO()
        with ZipFile(zip_bytes, "w") as zip:
            for video_url in playlist:
                try_counter = 0
                while True:
                    if try_counter == 3:
                        flash(f"Error: This url cannot be found, please try again! URL = {video_url}", category="error")
                        break
                    try:
                        try_counter += 1
                        print(f"Getting video information for {video_url}")
                        audio_data = BytesIO()
                        video = YouTube(video_url)
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
        return send_file(zip_bytes, download_name=f"playlist{playlist.playlist_id}.zip", as_attachment=True)
    else:
        print("Downloading URL")
        try_counter = 0
        while True:
            #sometimes theres some error that doesn't allow a video to be downloaded properly, happens rarely so I let it try 3 times before asking for another link
            if try_counter == 3:
                flash("Something went wrong, please try again!", category="error")
                return False
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
