import os
import re
import threading
import time

from slackclient import SlackClient

SECRET_RE = re.compile(r"secret", re.I)
SQUIRREL_RE = re.compile(r"squirrel", re.I)
BUG_RE = re.compile(r"bug", re.I)

API_TOKEN = os.environ["SECRET_BOT_SLACK_API_KEY"]
BOT_ID = os.environ["SECRET_BOT_SLACK_ID"]

sc = SlackClient(API_TOKEN)

def listen_for_text():
	while True:
		data = sc.rtm_read()
		if data:
			activity = data[0]
			try:
				if activity["type"] == "message" and activity["user"] != BOT_ID:
					if "secret" in activity["text"]:
						with open("LOZ_Secret.wav", "rb") as f:
							sc.api_call("files.upload", filename="LOZ_Secret.wav", file=f, channels=activity["channel"])
					
					if "squirrel" in activity["text"]:
						sc.api_call("reactions.add", name="squirrel", channel=activity["channel"], timestamp=activity["ts"])

					if "bug" in activity["text"]:
						sc.api_call("reactions.add", name="bug", channel=activity["channel"], timestamp=activity["ts"])
			except KeyError as e:
				print("Key error parsing activity")
				print(e)
		time.sleep(.2)

def check_for_channels():
	channels = {}
	while True:
		api_res = sc.api_call("channels.list", exclude_archived=True)
		if api_res["ok"]:
			if not channels:
				for channel in api_res["channels"]:
					channels[channel["id"]] = channel["name"]
			else:
				for channel in api_res["channels"]:
					if channel["id"] not in channels:
						try:
							sc.api_call("chat.postMessage", text="New channel: #{}".format(channel["name"]), channel="#general", link_names=1, as_user=True)
							channels[channel["id"]] = channel["name"]
						except KeyError as e:
							print("Key error joining channel")
							print(e)

		time.sleep(10)

if __name__ == '__main__':
	if sc.rtm_connect():
		print("Connected?")
		channel_thread = threading.Thread(target=check_for_channels, name="channel_thread")
		text_thread = threading.Thread(target=listen_for_text, name="text_thread")

		channel_thread.daemon = text_thread.daemon = True

		channel_thread.start()
		text_thread.start()

		while True:
			time.sleep(60)

		# check_for_channels()
