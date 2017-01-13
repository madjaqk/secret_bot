import os
import re
import time

from slackclient import SlackClient

SECRET_RE = re.compile(r"\bsecrets?\b", re.I)
SQUIRREL_RE = re.compile(r"squirrel", re.I)

API_TOKEN = os.environ["SECRET_BOT_SLACK_API_KEY"]
BOT_ID = os.environ["SECRET_BOT_SLACK_ID"]

sc = SlackClient(API_TOKEN)

if __name__ == '__main__':
	if sc.rtm_connect():
		print("Connected?")
		while True:
			data = sc.rtm_read()
			if data:
				activity = data[0]
				print(activity)
				try:
					if activity["type"] == "message" and activity["user"] != BOT_ID and SECRET_RE.search(activity["text"]):
						with open("LOZ_Secret.wav", "rb") as f:
							sc.api_call("files.upload", filename="LOZ_Secret.wav", file=f, channels=activity["channel"])
					elif activity["type"] == "message" and SQUIRREL_RE.search(activity["text"]):
						sc.api_call("reactions.add", name="squirrel", channel=activity["channel"], timestamp=activity["ts"])
				except KeyError as e:
					print("Key error parsing activity")
					print(e)
			time.sleep(.2)
