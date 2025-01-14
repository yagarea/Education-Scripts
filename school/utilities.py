"""A class that contains various useful utility methods."""

import calendar
import os
import re
import sys
import time
import urllib.request
from requests import get, post
from dataclasses import *
from pprint import pprint
from typing import *

import typesentry
from yaml import YAMLError, safe_load

from config import *

WD_EN = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def check_type(instance, type_hint):
    """Return True if instance corresponds to its type hint."""
    return typesentry.Config().is_type(instance, type_hint)


@dataclass
class Strict:
    """A class for strictly checking whether each of the dataclass variable types match."""

    def __post_init__(self):
        """Perform the check."""
        for name, field_type in self.__annotations__.items():
            value = self.__dict__[name]

            if value is not None and not check_type(value, field_type):
                raise TypeError(
                    f"The key '{name}' "
                    + f"in {self.__class__.__name__} "
                    + f"expected type '{field_type}' "
                    + f"but got '{value}' instead."
                )

    @classmethod
    def from_dictionary(cls, d: Dict):
        """Initialize the object from the given dictionary."""
        return cls._from_dictionary(cls, d)

    @classmethod
    def _from_dictionary(cls, c, d):
        """A helper function that converts a nested dictionary to a dataclass.
        Inspired by https://stackoverflow.com/a/54769644."""
        if is_dataclass(c):
            fieldtypes = {f.name: f.type for f in fields(c)}
            return c(**{f: cls._from_dictionary(fieldtypes[f], d[f]) for f in d})
        return d

    @classmethod
    def _from_file(cls, path: str):
        """Helper function for neatly catching various exceptions that parsing can
        throw."""
        try:
            with open(path, "r") as f:
                return cls.from_dictionary(safe_load(f) or {})
        except (YAMLError, TypeError) as e:
            exit_with_error(str(e), path)
        except KeyError as e:
            exit_with_error(f"Invalid key {e}", path)


def minutes_to_HHMM(minutes: int) -> str:
    """Converts a number of minutes to a string in the form HH:MM."""
    return f"{str(minutes // 60).rjust(2)}:{minutes % 60:02d}"


def exit_with_error(message: str, path: str = None):
    """Exit with an error, possibly giving its path."""
    msg = Ansi.color(Ansi.bold("ERROR"), 9)
    if path is not None:
        msg += Ansi.color(f" in {path}", 9)
    msg = msg + Ansi.color(":", 9)
    print(f"{msg} {message}")
    sys.exit(1)


def exit_with_success(message: str):
    """Exit with an error, possibly giving its path."""
    print(Ansi.color("SUCCESS: ", 10) + message)
    sys.exit(0)


def due_message_from_timedelta(delta):
    """Return a '3 days, 2 hours'-type message from a timedelta object."""
    due_msg = ""

    days = abs(delta).days
    if days != 0:
        due_msg = f"{days} day{'s' if days > 1 else ''}, "

    hours = abs(delta).seconds // 3600
    if hours != 0:
        due_msg += f"{hours} hour{'s' if hours > 1 else ''}"
    else:
        minutes = abs(delta).seconds // 60

        if minutes != 0:
            due_msg += f"{minutes} minute{'s' if minutes > 1 else ''}"

        if due_msg == "":
            due_msg = "now"

    due_msg = due_msg.strip().strip(",")

    return due_msg


class Ansi:
    """A set of ANSI convenience methods."""

    @classmethod
    def color(cls, text, color: int):
        return f"\u001b[38;5;{color}m{text}\u001b[0m"

    @classmethod
    def gray(cls, text):
        """Gray coloring."""
        return f"\u001b[38;5;240m{text}\u001b[0m"

    @classmethod
    def bold(cls, text):
        return f"\u001b[1m{text}\u001b[0m"

    @classmethod
    def underline(cls, text):
        return f"\u001b[4m{text}\u001b[0m"

    @classmethod
    def italics(cls, text):
        return f"\u001b[3m{text}\u001b[0m"

    @classmethod
    def escape(cls, text):
        return re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])").sub("", text)

    @classmethod
    def __align(cls, text: str, length: int, function: str, *args, **kwargs):
        return getattr(text, function)(
            length + (len(text) - cls.len(text)), *args, **kwargs
        )

    @classmethod
    def ljust(cls, text: str, length: int, *args, **kwargs) -> str:
        return cls.__align(text, length, "ljust", *args, **kwargs)

    @classmethod
    def rjust(cls, text: str, length: int, *args, **kwargs) -> str:
        return cls.__align(text, length, "rjust", *args, **kwargs)

    @classmethod
    def center(cls, text: str, length: int, *args, **kwargs) -> str:
        return cls.__align(text, length, "center", *args, **kwargs)

    @classmethod
    def len(cls, text: str, *args, **kwargs) -> int:
        return len(cls.escape(text))


def print_table(table: List[List[str]]):
    # find max width of each of the columns of the table
    column_widths = [0] * max(len(row) for row in table)
    for row in table:
        # skip weekday rows
        if len(row) != 1:
            for i, entry in enumerate(row):
                if column_widths[i] < Ansi.len(entry):
                    column_widths[i] = Ansi.len(entry)

    for i, row in enumerate(table):
        print(end="╭─" if i == 0 else "│ ")

        column_sep = Ansi.gray(" │ ")
        max_row_width = sum(column_widths) + Ansi.len(column_sep) * (
            len(column_widths) - 1
        )

        # if only one item is in the row, it will be printed specially
        if len(row) == 1:
            print(
                (f"{' ' * max_row_width} │\n├─" if i != 0 else "")
                + Ansi.center(Ansi.bold(f"{{ {row[0]} }}"), max_row_width, "─")
                + ("─╮" if i == 0 else "─┤")
            )
        else:
            for j, entry in enumerate(row):
                print(
                    Ansi.ljust(entry, column_widths[j])
                    + (column_sep if j != (len(row) - 1) else " │\n"),
                    end="",
                )

    print(f"╰{'─' * (max_row_width + 2)}╯")


def pick_one(l: list):
    """Pick one of the items from the list."""
    # special case for picking only one item
    if len(l) == 1:
        return l[0]

    for i, item in enumerate(l):
        print(f"{i + 1}) {item}")

    index = None
    while True:
        try:
            val = input("Pick one (leave blank for 1): ")
            if val == "":
                index = 0
            else:
                index = int(val) - 1
        except ValueError:
            continue
        except EOFError:
            break

        if not 0 <= index < len(l):
            continue

        return l[index]

    sys.exit(0)
