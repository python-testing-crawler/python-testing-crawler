
from collections import namedtuple

from flask import Flask, Blueprint, Response, render_template, request, redirect, url_for, abort, current_app


bp = Blueprint('main', __name__)


RequestLogEntry = namedtuple('RequestlogEntry', ['path', 'method', 'params'])


def record_request(path, method, params):
    current_app.request_log = current_app.request_log or []
    entry = RequestLogEntry(path, method, tuple(sorted(params)))
    current_app.request_log.append(entry)


def lookup_requests(app, path, method=None, params=None):
    for entry in app.request_log:
        if entry.path != path:
            continue
        if method is not None and method != entry.method:
            continue
        if params is not None and tuple(sorted(params)) != entry.params:
            continue
        yield entry


@bp.before_request
def before_request_func():
    # fail if asked to
    if request.path in current_app.config.get('FAILURE_PATHS', []):
        raise Exception("Instructed to fail at {}".format(request.path))

    # record requests
    record_request(path=request.path, method=request.method, params=request.values.items())


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/page-a")
def page_a():
    return render_template("page_a.html")


@bp.route("/page-b")
def page_b():
    return render_template("page_b.html")


@bp.route("/page-c")
def page_c():
    return render_template("page_c.html")


@bp.route("/page-d", methods=["GET", "POST"])
def page_d():
    if request.values:
        if request.method == 'GET':
            return redirect(url_for("main.form_submitted_by_get"))
        if request.method == 'POST':
            return redirect(url_for("main.form_submitted_by_post"))
    else:
        return render_template("page_d.html")


@bp.route("/page-gallery")
def page_gallery():
    return render_template("page_gallery.html")


@bp.route("/form-submitted-by-get")
def form_submitted_by_get():
    return render_template("form_submitted_by_get.html")


@bp.route("/form-submitted-by-get-onward-link")
def form_submitted_by_get_onward_link():
    return render_template("form_submitted_by_get_onward_link.html")


@bp.route("/form-submitted-by-post")
def form_submitted_by_post():
    return render_template("form_submitted_by_post.html")


@bp.route("/form-submitted-by-post-onward-link")
def form_submitted_by_post_onward_link():
    return render_template("form_submitted_by_post_onward_link.html")


@bp.route("/redirect/with/<int:redirect_code>")
def redirector(redirect_code):
    return redirect(url_for("main.redirect_target"), code=redirect_code)


@bp.route("/redirect-target")
def redirect_target():
    return render_template("redirect_target.html")


@bp.route("/image-map-target")
def image_map_target():
    return render_template("image_map_target.html")


@bp.route("/abort/with/<int:status_code>")
def abort_with(status_code):
    abort(status_code)


@bp.route("/style.css")
def stylesheet():
    return Response("dummy stylesheet", 200)


@bp.route("/image.png")
def image():
    return Response("", 200)


def create_app():
    app = Flask(__name__)
    app.secret_key = b'not so secret key'
    app.request_log = []
    app.register_blueprint(bp)
    return app


if __name__ == '__main__':
    app = create_app()