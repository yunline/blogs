import dataclasses
import datetime
import itertools
import os
import re
import warnings

import jinja2

BLOGS_PATH = "content/blogs/"
OUTPUT_PATH = "content/blog_index.md"
TEMPLATE_PATH = OUTPUT_PATH + ".in"
H1_PATTERN = re.compile(
    r"^#[^\S\r\n]+(?P<title>(\S+[^\S\r\n]*)+)\n",
    re.MULTILINE,
)


@dataclasses.dataclass
class Data:
    name: str
    title: str | None
    date: datetime.datetime


posts: list[Data] = []

for name in os.listdir(BLOGS_PATH):
    path = os.path.join(BLOGS_PATH, name)
    if not os.path.isdir(path):
        continue
    try:
        # 文件夹命名格式: "yyyymmdd[-后缀]"
        # 中括号内的后缀为可选项，这样如果一天有多个post，便得以区分
        date_str = name.split("-")[0]
        date = datetime.datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        warnings.warn(
            f"Ignoring '{path}' because of invalid date format. 'yyyymmdd[-suffix]' expected"
        )
        continue

    filename = os.path.join(path, "index.md")
    if not os.path.exists(filename):
        warnings.warn(f"Ignoring '{path}' because index.md doesn't exist")
        continue
    if not os.path.isfile(filename):
        warnings.warn(f"Ignoring '{path}' because index.md is not a file")
        continue

    with open(filename, encoding="utf8") as md_file:
        content = md_file.read()

    match = re.search(H1_PATTERN, content)

    if match:
        title = match.groupdict()["title"]
    else:
        warnings.warn(f"'{filename}' title not found, using the default title")
        title = None

    posts.append(Data(name, title, date))


sorted_posts = sorted(posts, key=lambda a: a.date, reverse=True)

grouped_posts: dict[int, dict[int, list[Data]]] = {}
for year, group_y in itertools.groupby(sorted_posts, key=lambda x: x.date.year):
    year_dict = {}
    for month, group_m in itertools.groupby(group_y, key=lambda x: x.date.month):
        year_dict[month] = list(group_m)
    grouped_posts[year] = year_dict

with open(TEMPLATE_PATH, encoding="utf8") as template_file:
    template: jinja2.Template = jinja2.Template(template_file.read())

result = template.render(grouped_posts=grouped_posts)

with open(OUTPUT_PATH, "w", encoding="utf8") as output_file:
    output_file.write(result)
