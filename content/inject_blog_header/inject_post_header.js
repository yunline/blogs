function slugify(text) {
    return text
        .toLowerCase() // 全小写
        .replace(/^-|-$/g, ''); // 移除开头和结尾的连字符
}


function get_inject_post_header_div() {
    header = document.querySelector('div.inj-post-header');
    if (header) {
        return header;
    }

    let md_content_div = document.querySelector('div.md-content');
    if (!md_content_div) {
        return null;
    }

    let first_h1 = md_content_div.querySelector('h1');
    if (!first_h1) {
        return null;
    }

    first_h1.insertAdjacentHTML('afterend', '<div class="inj-post-header"><hr></div>')

    return document.querySelector('div.inj-post-header');
}

function inject_post_date() {
    let path = window.location.pathname;
    let path_segments = path.split("/");
    if (path_segments[path_segments.length - 3] !== "blogs") {
        return;
    }

    let date_str = path_segments[path_segments.length - 2];
    let match = date_str.match(/^(\d\d\d\d)(\d\d)(\d\d)(-\S*)*$/);

    if (!match) {
        return;
    }

    let year = date_str.slice(0, 4);
    let month = date_str.slice(4, 6);
    let day = date_str.slice(6, 8);
    

    const custom_html = `<em class="inj-post-header-date">发布于：${year}-${month}-${day}</em>`;

    let header_div = get_inject_post_header_div();
    header_div.innerHTML += custom_html;

}

function inject_post_tags(tags_data) {
    let tag_html_array = new Array();

    for(tag of tags_data) {
        tag_html_array.push(`<a class="md-tag" href="../tag_index#${slugify(tag)}">${tag}</a>`);
    }

    const custom_html = `<p class="inj-post-header-tags">${tag_html_array.join(" ")}</p>`;

    let header_div = get_inject_post_header_div();
    header_div.innerHTML += custom_html;
}
