import os
import re
import time

from slackclient import SlackClient

API_TOKEN = os.environ["SECRET_BOT_SLACK_API_KEY"]
BOT_ID = os.environ["SECRET_BOT_SLACK_ID"]

sc = SlackClient(API_TOKEN)

def is_supervocalic(text):
	vowels = {v: False for v in ("a", "e", "i", "o", "u")}
	for char in text:
		if char in vowels:
			if vowels[char]: 
				return False
			else:
				vowels[char] = True

	return all(vowels.values())

def listen_for_text():
	def add_reaction(emoji):
		sc.api_call("reactions.add", name=emoji, channel=activity["channel"], timestamp=activity["ts"])

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
				if activity and activity["type"] == "message" and "subtype" not in activity and activity["user"] != BOT_ID:
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

					text = activity["text"].lower()

					if "secret" in text:
						with open("LOZ_Secret.wav", "rb") as f:
							sc.api_call("files.upload", filename="LOZ_Secret.wav", file=f, channels=activity["channel"])

					watch_words = (
						((lambda t: "squirrel" in t), "squirrel"),
						((lambda t: "bug" in t), "bug"),
						(is_supervocalic, "aeiou"),
						)

					for func, emoji in watch_words:
						if func(text):
							add_reaction(emoji)

			except KeyError as e:
				print("Key error parsing activity")
				print(e)
		time.sleep(.2)

if __name__ == '__main__':
	if sc.rtm_connect():
		print("Connected?")
		listen_for_text()