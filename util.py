import datetime
import pathlib
import zipfile
from collections import defaultdict
from typing import Any, Optional, TypedDict, Union

SomePath = Union[pathlib.Path, zipfile.Path]

# This should work for message dates as long as locale is set to en_US
TIME_FORMAT = "%A, %B %d, %Y at %I:%M:%S %p %Z"

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


# Converted group type
class Group:
    first_msg_time: Optional[datetime.datetime]
    last_msg_time: Optional[datetime.datetime]

    def __init__(self, json_group: GroupInfo):
        super().__init__()
        self.name = json_group.get("name", "DM")
        self.members = {
            m["email"].lower(): User(m) for m in json_group["members"]
        }
        self.count = 0
        self.first_msg_time = None
        self.last_msg_time = None

        # Keyed by lowercase email
        self.usercounts = defaultdict[str, int](int)


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
