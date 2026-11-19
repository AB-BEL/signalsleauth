"""Route groups. Each module exposes a Flask ``bp``; URLs are unchanged from the
original single-file app, only endpoint names gained a blueprint prefix
(e.g. ``url_for("auth.login")``)."""


def register_blueprints(app):
    from . import main
    from . import auth
    from . import student
    from . import game_api
    from . import mobile_api
    from . import system
    from . import admin_auth
    from . import admin_students
    from . import admin_chapters
    from . import admin_content
    from . import admin_rankings
    from . import admin_system

    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(student.bp)
    app.register_blueprint(game_api.bp)
    app.register_blueprint(mobile_api.bp)
    app.register_blueprint(system.bp)
    app.register_blueprint(admin_auth.bp)
    app.register_blueprint(admin_students.bp)
    app.register_blueprint(admin_chapters.bp)
    app.register_blueprint(admin_content.bp)
    app.register_blueprint(admin_rankings.bp)
    app.register_blueprint(admin_system.bp)
