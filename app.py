from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# --------------------
# Models
# --------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.String(200))
    caption = db.Column(db.String(300))
    likes = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --------------------
# Routes
# --------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if not user:
            flash("User does not exist")
        elif not check_password_hash(user.password, password):
            flash("Invalid password")
        else:
            login_user(user)
            return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return redirect(url_for("register"))

        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/home")
@login_required
def home():
    tag = request.args.get("tag")

    if tag:
        posts = Post.query.filter(
            Post.caption.contains("#" + tag)
        ).order_by(Post.id.desc()).all()
    else:
        posts = Post.query.order_by(Post.id.desc()).all()

    comments = Comment.query.all()
    users = User.query.all()

    return render_template(
        "home.html",
        posts=posts,
        comments=comments,
        users=users,
        user=current_user,
        active_tag=tag
    )


@app.route("/create_post", methods=["POST"])
@login_required
def create_post():
    caption = request.form.get("caption")
    file = request.files.get("photo")

    filename = None
    if file and file.filename != "":
        unique_name = str(uuid.uuid4()) + "_" + file.filename
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
        file.save(filepath)
        filename = unique_name

    post = Post(image=filename, caption=caption, user_id=current_user.id)
    db.session.add(post)
    db.session.commit()

    return redirect(url_for("home"))


@app.route("/edit_post/<int:post_id>", methods=["POST"])
@login_required
def edit_post(post_id):
    post = Post.query.get(post_id)

    if post and post.user_id == current_user.id:
        post.caption = request.form["caption"]
        db.session.commit()

    return redirect(url_for("home"))


@app.route("/delete_post/<int:post_id>")
@login_required
def delete_post(post_id):
    post = Post.query.get(post_id)

    if post and post.user_id == current_user.id:
        Comment.query.filter_by(post_id=post_id).delete()
        db.session.delete(post)
        db.session.commit()

    return redirect(url_for("home"))


@app.route("/like/<int:post_id>")
@login_required
def like(post_id):
    post = Post.query.get(post_id)
    post.likes += 1
    db.session.commit()
    return redirect(url_for("home"))


# --------------------
# COMMENT ROUTES
# --------------------
@app.route("/comment/<int:post_id>", methods=["POST"])
@login_required
def comment(post_id):
    text = request.form.get("comment")

    if text:
        new_comment = Comment(
            text=text,
            post_id=post_id,
            user_id=current_user.id
        )
        db.session.add(new_comment)
        db.session.commit()

    return redirect(url_for("home"))


@app.route("/delete_comment/<int:comment_id>")
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get(comment_id)

    if comment and comment.user_id == current_user.id:
        db.session.delete(comment)
        db.session.commit()

    return redirect(url_for("home"))


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# --------------------
# START APP
# --------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
