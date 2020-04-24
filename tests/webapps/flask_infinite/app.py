from flask import Flask, Blueprint, render_template, request, redirect, url_for, abort, current_app


bp = Blueprint('main', __name__)


@bp.route("/")
def index():
    return render_template("index.html")


def create_app():
    app = Flask(__name__)
    app.secret_key = b'not so secret key'
    app.register_blueprint(bp)
    return app


if __name__ == '__main__':
    app = create_app()
