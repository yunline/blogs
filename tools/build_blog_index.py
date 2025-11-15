import dataclasses
import datetime
import itertools
import os
import re
import typing
import warnings

import frontmatter  # type: ignore
import jinja2

BLOGS_PATH = "content/posts/"
TEMPLATE_PATH = "content/templates/"

MAIN_INDEX_OUTPUT_PATH = "content/post_index.md"
TAG_INDEX_OUTPUT_PATH = "content/tag_index.md"
TAG_PAGE_OUTPUT_PATH = "content/tags"

MAIN_INDEX_TEMPLATE_NAME = "post_index.md.jinja"
TAG_INDEX_TEMPLATE_NAME = "tag_index.md.jinja"
TAG_PAGE_TEMPLATE_NAME = "tag_page.md.jinja"

H1_PATTERN = re.compile(
    r"^#[^\S\r\n]+(?P<title>(\S+[^\S\r\n]*)+)\n",
    re.MULTILINE,
)

SLUGIFY_PATTERN = re.compile(r"[\\/\s\#\?&=%\+]")


def slugify(s: str) -> str:
    # 全小写
    s = s.lower()

    # 将敏感字符替换为横杠
    s = re.sub(SLUGIFY_PATTERN, "-", s)

    # 移除开头和结尾的连字符
    s = s.strip("-")

    return s


@dataclasses.dataclass
class PostData:
    name: str
    title: str | None
    date: datetime.datetime
    tags: dict[str, str]


def collect_post_data() -> list[PostData]:
    posts: list[PostData] = []

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
                warnings.warn(
                    f"Ignoring '{filename}' tags: invalid data type of 'tags'"
                )

        posts.append(PostData(name, title, date, tags))

    # 按时间排序，时间越晚，排名越靠前
    posts = sorted(posts, key=lambda a: a.date, reverse=True)

    return posts


TagIndexType: typing.TypeAlias = dict[str, tuple[str, list[PostData]]]


def collect_tags(posts: list[PostData]) -> TagIndexType:
    tags: TagIndexType = {}

    # 按tag分组
    for data in posts:
        for tag_slug, tag_name in data.tags.items():
            if tag_slug in tags:
                tags[tag_slug][1].append(data)
            else:
                tags[tag_slug] = (tag_name, [data])

    # 按照tag的引用次数排序，引用次数最多的排名靠前
    tags = {
        key: value
        for key, value in sorted(
            tags.items(),
            key=lambda a: len(a[1][1]),
            reverse=True,
        )
    }

    return tags


def build_main_index(posts: list[PostData], jinja_env: jinja2.Environment):
    grouped_by_timeline: dict[int, dict[int, list[PostData]]] = {}
    for year, group_y in itertools.groupby(posts, key=lambda x: x.date.year):
        year_dict = {}
        for month, group_m in itertools.groupby(group_y, key=lambda x: x.date.month):
            year_dict[month] = list(group_m)
        grouped_by_timeline[year] = year_dict

    main_index_template: jinja2.Template
    main_index_template = jinja_env.get_template(MAIN_INDEX_TEMPLATE_NAME)

    result = main_index_template.render(grouped_posts=grouped_by_timeline)

    with open(MAIN_INDEX_OUTPUT_PATH, "w", encoding="utf8") as output_file:
        output_file.write(result)


def build_tag_index(tags: TagIndexType, jinja_env: jinja2.Environment):
    tag_index_template: jinja2.Template
    tag_index_template = jinja_env.get_template(TAG_INDEX_TEMPLATE_NAME)

    result = tag_index_template.render(tag_index=tags)

    with open(TAG_INDEX_OUTPUT_PATH, "w", encoding="utf8") as output_file:
        output_file.write(result)


def build_tag(tags: TagIndexType, jinja_env: jinja2.Environment):
    if not os.path.exists(TAG_PAGE_OUTPUT_PATH):
        os.mkdir(TAG_PAGE_OUTPUT_PATH)
    elif os.path.isfile(TAG_PAGE_OUTPUT_PATH):
        warnings.warn(
            f"Unable to create path '{TAG_PAGE_OUTPUT_PATH}': "
            f"path name occupied by a file"
        )
        return

    template: jinja2.Template
    template = jinja_env.get_template(TAG_PAGE_TEMPLATE_NAME)

    for tag_slug, (tag_name, data_list) in tags.items():
        tag_path = os.path.join(TAG_PAGE_OUTPUT_PATH, f"{tag_slug}.md")
        result = template.render(
            tag_name=tag_name,
            data_list=data_list,
        )
        with open(tag_path, "w", encoding="utf8") as output_file:
            output_file.write(result)


if __name__ == "__main__":
    # 收集数据
    posts = collect_post_data()
    tags = collect_tags(posts)

    # 初始化jinja环境
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_PATH))

    # 生成目录
    build_main_index(posts, env)
    build_tag_index(tags, env)
    build_tag(tags, env)
