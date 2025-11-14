import dataclasses
import datetime
import itertools
import os
import re
import warnings

import frontmatter  # type: ignore
import jinja2

BLOGS_PATH = "content/posts/"
TEMPLATE_PATH = "content/templates/"

MAIN_INDEX_OUTPUT_PATH = "content/post_index.md"
TAG_INDEX_OUTPUT_PATH = "content/tag_index.md"

MAIN_INDEX_TEMPLATE_NAME = "post_index.md.jinja"
TAG_INDEX_TEMPLATE_NAME = "tag_index.md.jinja"

H1_PATTERN = re.compile(
    r"^#[^\S\r\n]+(?P<title>(\S+[^\S\r\n]*)+)\n",
    re.MULTILINE,
)


def slugify(string: str) -> str:
    return string.lower().strip("-")


@dataclasses.dataclass
class Data:
    name: str
    title: str | None
    date: datetime.datetime
    tags: dict[str, str]


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

    metadata, content = frontmatter.parse(content)

    match = re.search(H1_PATTERN, content)

    if match:
        title = match.groupdict()["title"]
    else:
        warnings.warn(f"'{filename}' title not found, using the default title")
        title = None

    tags = {}
    if "tags" in metadata:
        if isinstance(metadata["tags"], list):
            for tag_name in metadata["tags"]:
                if isinstance(tag_name, str):
                    tag_slug = slugify(tag_name)
                    tags[tag_slug] = tag_name
                else:
                    warnings.warn(
                        f"Ignoring '{filename}' tags: invalid data type of values of 'tags'"
                    )
                    tags = {}
                    break
        else:
            warnings.warn(f"Ignoring '{filename}' tags: invalid data type of 'tags'")

    posts.append(Data(name, title, date, tags))

# 按照日期排序，日期早的排名靠前
sorted_posts = sorted(posts, key=lambda a: a.date, reverse=True)

grouped_by_timeline: dict[int, dict[int, list[Data]]] = {}
for year, group_y in itertools.groupby(sorted_posts, key=lambda x: x.date.year):
    year_dict = {}
    for month, group_m in itertools.groupby(group_y, key=lambda x: x.date.month):
        year_dict[month] = list(group_m)
    grouped_by_timeline[year] = year_dict

grouped_by_tag: dict[str, tuple[str, list[Data]]] = {}
for data in sorted_posts:
    for tag_slug, tag_name in data.tags.items():
        if tag_slug in grouped_by_tag:
            grouped_by_tag[tag_slug][1].append(data)
        else:
            grouped_by_tag[tag_slug] = (tag_name, [data])

# 按照tag的引用次数排序，引用次数最多的排名靠前
grouped_by_tag = {
    key: value
    for key, value in sorted(
        grouped_by_tag.items(), key=lambda a: len(a[1][1]), reverse=True
    )
}

env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_PATH))

main_index_template: jinja2.Template = env.get_template(MAIN_INDEX_TEMPLATE_NAME)

result = main_index_template.render(grouped_posts=grouped_by_timeline)

with open(MAIN_INDEX_OUTPUT_PATH, "w", encoding="utf8") as output_file:
    output_file.write(result)

tag_index_template: jinja2.Template = env.get_template(TAG_INDEX_TEMPLATE_NAME)

result = tag_index_template.render(grouped_posts=grouped_by_tag)

with open(TAG_INDEX_OUTPUT_PATH, "w", encoding="utf8") as output_file:
    output_file.write(result)
