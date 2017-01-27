import datetime
import os
import pprint
import re
import threading
import time
import traceback

from slackclient import SlackClient

SECRET_RE = re.compile(r"secret", re.I)
SQUIRREL_RE = re.compile(r"squirrel", re.I)
BUG_RE = re.compile(r"bug", re.I)

API_TOKEN = os.environ["SECRET_BOT_SLACK_API_KEY"]
BOT_ID = os.environ["SECRET_BOT_SLACK_ID"]

sc = SlackClient(API_TOKEN)

def report_errors(desc, stack_trace, variables=None):
	with open("errors.txt", "a+") as f:
		f.write("~"*50 + "\n\n")
		f.write(f"{datetime.datetime.now()}\n\n")
		f.write(desc + "\n\n")
		traceback.print_tb(stack_trace, file=f)
		f.write("\n")
		if variables:
			f.write(pprint.pformat(variables))
			f.write("\n\n")

def listen_for_text():
	close_puzzles = set()

	SOLVED_RE = re.compile(r"^(<@{}> )?!solved ?(?P<puzzle_name>\S+)? ?(?P<solution>.+)?$".format(BOT_ID))
	ALMOST_RE = re.compile(r"^(<@{}> )?!almost( (?P<puzzle_name>\S+))?$".format(BOT_ID))
	ALMOST_PUZZLES_RE = re.compile(r"^(<@{}> )?!(almostpuzzles|whatshouldiworkon|whatsgoingon|close|whatsclose)$".format(BOT_ID))
	HELP_RE = re.compile(r"^(<@{}> )?!help$".format(BOT_ID))

	while True:
		data = sc.rtm_read()
		if data:
			activity = data[0]
			try:
				if activity["type"] == "message" and activity["user"] != BOT_ID:
					is_solved = SOLVED_RE.match(activity["text"])
					almost = ALMOST_RE.match(activity["text"])
					almost_puzzles = ALMOST_PUZZLES_RE.match(activity["text"])
					help = HELP_RE.match(activity["text"])
					message = None

					if is_solved:
						if is_solved.group("puzzle_name"):
							puzzle_name = is_solved.group("puzzle_name")
						else:
							channel_res = sc.api_call("channels.info", channel=activity["channel"])
							if channel_res["ok"]:
								puzzle_name = channel_res["channel"]["name"]
							else:
								continue
						if is_solved.group("solution"):
							solution = re.sub(r"[^A-Z]", "", is_solved.group("solution").upper())
							message = f":confetti_ball: *{puzzle_name}*  was solved! :tada:  and the answer is *{solution}*"
						else:
							message = f":confetti_ball: *{puzzle_name}*  was solved! :tada:"
						# print(activity["channel"])
						if activity["channel"] != "C3N1ZQWP2":
							sc.api_call("chat.postMessage", text=message, channel="#general", link_names=1, as_user=True)
						close_puzzles.discard(puzzle_name.title())
					elif almost:
						if almost.group("puzzle_name"):
							puzzle_name = almost.group("puzzle_name")
						else:
							channel_res = sc.api_call("channels.info", channel=activity["channel"])
							if channel_res["ok"]:
								puzzle_name = channel_res["channel"]["name"]
							else:
								continue
						message = f"Thanks.  I'll remember that we're very close on *{puzzle_name}*."
						close_puzzles.add(puzzle_name.title())
					elif almost_puzzles:
						if close_puzzles:
							message = "We're currently very close on the following: "+ ", ".join(f"*{puzz}*" for puzz in close_puzzles)
						else:
							message = "We currently have no puzzles marked as close."
					elif help:
						message = [
							'@simple_bot is here to help!  Usage:',
							'`!solved Puzzlename` => ":confetti_ball: *Puzzlename*  was solved! :tada:"',
							'`!solved Puzzlename SOLUTION` => ":confetti_ball: *Puzzlename*  was solved! :tada:  and the answer is *SOLUTION*"',
							'`!almost HardPuzzle` => "Thanks.  I\'ll remember that we\'re very close on *HardPuzzle*."',
							'`!almostpuzzles` => "We\'re currently very close on the following: *Hardpuzzle*, *Nastypuzzle*." _(also !whatshouldiworkon, !whatsgoingon, !close, and !whatsclose)_ ',
						]
						message = "\n".join(message)
						
					if message:
						sc.api_call("chat.postMessage", text=message, channel=activity["channel"], link_names=1, as_user=True)

					if "secret" in activity["text"]:
						with open("LOZ_Secret.wav", "rb") as f:
							sc.api_call("files.upload", filename="LOZ_Secret.wav", file=f, channels=activity["channel"])
					
					if "squirrel" in activity["text"]:
						sc.api_call("reactions.add", name="squirrel", channel=activity["channel"], timestamp=activity["ts"])

					if "bug" in activity["text"]:
						sc.api_call("reactions.add", name="bug", channel=activity["channel"], timestamp=activity["ts"])
			except KeyError as e:
				report_errors("Key error parsing activity", e.__traceback__, {"activity": activity})
				# print("Key error parsing activity")
				# print(e)
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
							user_res = sc.api_call("users.info", user=channel["creator"])
							if user_res["ok"]:
								message = f"@{user_res['user']['name']} created the channel #{channel['name']}  Don't forget to `/invite @simple_bot`!"
							else:
								message = "New channel: #{channel['name']}  Don't forget to `/invite @simple_bot`!"
							
							sc.api_call("chat.postMessage", text=message, channel="#general", link_names=1, as_user=True)
							channels[channel["id"]] = channel["name"]
						except KeyError as e:
							variables = {
								"user_res": user_res,
								"channel": channel,
							}
							report_errors("Key error notifying about new channel", e.__traceback__, variables)
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
