import datetime
import json
import pathlib
import zipfile
from collections import OrderedDict, defaultdict
from typing import Any, NamedTuple, Optional, TypedDict, Union

SomePath = Union[pathlib.Path, zipfile.Path]

# This is, AFAICT, the date format used in GChat takeout. Locale must be set to
# en_US for this to work because of weekdays and month names.
#
# This isn't a standard format and I don't fully trust that it won't change, so
# I'm trying to be careful not to rely on parsing working.
TIME_FORMAT = "%A, %B %d, %Y at %I:%M:%S %p %Z"

# These are the colors used for a chat's users in the HTML output.
USER_COLORS = (
    "red",
    "blue",
    "green",
    "orange",
    "gold",
    "magenta",
    "darkseagreen",
    "chocolate",
    "steelblue",
    "olive",
)

# Seen in various places
class UserInfo(TypedDict):
    name: str
    email: str
    user_type: str


# Converted user type
class User:
    def __init__(self, json_user: UserInfo):
        super().__init__()
        self.name = json_user["name"]
        self.email = json_user["email"]


# group_info.json format
class GroupInfo(TypedDict, total=False):
    name: str  # May not be set
    members: list[UserInfo]


# As in messages.json
class MessageInfo(TypedDict, total=False):
    creator: UserInfo
    created_date: str
    text: str
    topic_id: str  # I don't know what this is
    annotations: list[Any]  # There's stuff in here...


class MessageFile(TypedDict):
    messages: list[MessageInfo]


class Message:
    created_date: Optional[datetime.datetime]

    def __init__(self, json_msg: MessageInfo):
        super().__init__()
        self.creator = User(json_msg["creator"])
        try:
            self.created_date = datetime.datetime.strptime(
                json_msg["created_date"], TIME_FORMAT
            )
        except Exception:
            self.created_date = None
        self.text = json_msg.get("text", "")
        self.has_annotations = bool(json_msg.get("annotations"))


# Converted group type
class Group:
    first_msg_time: Optional[datetime.datetime]
    last_msg_time: Optional[datetime.datetime]

    def __init__(self, json_group: GroupInfo, key: str):
        super().__init__()
        self.key = key
        self.name = json_group.get("name", "DM")
        self.members = OrderedDict[str, User](
            (m["email"].lower(), User(m)) for m in json_group["members"]
        )
        self.user_idxs = {
            json_group["members"][i]["email"].lower(): i
            for i in range(len(json_group["members"]))
        }
        self.count = 0
        self.first_msg_time = None
        self.last_msg_time = None

        # Keyed by lowercase email
        self.usercounts = defaultdict[str, int](int)

    def add_member(self, u: User) -> None:
        em = u.email.lower()
        if em not in self.members:
            self.members[em] = u
            self.user_idxs[em] = len(self.members) - 1

    def get_idx(self, u: User) -> int:
        return self.user_idxs.get(u.email.lower(), 0)

    def load_messages(self, search_path: SomePath) -> list[Message]:
        msgs_path = search_path / "Groups" / self.key / "messages.json"
        if msgs_path.exists() and msgs_path.is_file():
            with msgs_path.open("r", encoding="utf-8") as msgs_file:
                msg_file: MessageFile = json.load(msgs_file)

            msgs = [Message(m) for m in msg_file["messages"]]

            if msgs:
                self.first_msg_time = msgs[0].created_date
                self.last_msg_time = msgs[-1].created_date

            return msgs
        else:
            return []


class SummaryData(NamedTuple):
    groups: list[Group]
    usercounts: defaultdict[str, int]
