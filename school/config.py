"""A configuration file for the school script."""
from dataclasses import dataclass


@dataclass
class CourseType:
    """A class for various types of courses (lectures/labs/whatever)."""

    color: int
    has_homework: bool


# the relative path to the folder where the courses are stored
courses_folder = "courses/"


# settings regarding course types -- labs/lectures/...
# the numbers are ANSI colors that the course type will be painted with
# see https://www.lihaoyi.com/post/BuildyourownCommandLinewithANSIescapecodes.html
course_types = {
    "cvičení": CourseType(118, True),
    "přednáška": CourseType(39, False),
}


# default handlers for opening course folders/websites/notes...
file_browser = ["ranger"]
web_browser = ["firefox", "--target", "window"]
text_editor = ["vim"]
note_handlers = {".xopp": "xournalpp", ".md": "vim"}
