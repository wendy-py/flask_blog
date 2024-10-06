from flask import Flask, render_template, redirect, url_for
from flask import flash, abort
import os
from functools import wraps
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_login import UserMixin, LoginManager, login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text, ForeignKey
from datetime import date
from flask_gravatar import Gravatar
from form import PostForm, RegisterForm, LoginForm, CommentForm

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY', '8BYkEfBA6O6donzWlSihBXox7C0sKR6b')
Bootstrap5(app)
ckeditor = CKEditor(app)

# INIT LoginManager, requires SECRET_KEY
login_mgr = LoginManager()
login_mgr.init_app(app)

# for adding avatars to comments
gravatar = Gravatar(app, size=100, rating='g',default='retro', force_default=False, use_ssl=False, base_url=None)

# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URI', 'sqlite:///posts.db')
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# CONFIGURE TABLE
# ForeignKey (table users, column id) allows us to get author's info
class BlogPost(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    author = relationship("User", back_populates="blogs")
    comments = relationship("Comment", back_populates="post")

# CREATE TABLE IN DB with UserMixin
# UserMixin supplies what login_user and logout_user needs
# By inheriting both, we can use a common user object for LoginManager and DB
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))
    blogs = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="commenter")

# ForeignKey (table users, column id) allows us to get commenter's info
# ForeignKey (table blog_post, column id) allows us to get blog's info
class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    commenter_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    commenter = relationship("User", back_populates="comments")
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("blog_post.id"))
    post = relationship("BlogPost", back_populates="comments")
    text: Mapped[str] = mapped_column(Text, nullable=False)

with app.app_context():
    db.create_all()

# define function used by LoginManager
@login_mgr.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

# Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if not form.validate_on_submit():
        return render_template("register.html", form=form, is_login=current_user.is_authenticated)
    user = db.session.execute(db.select(User).where(User.email==form.email.data)).scalar()
    if user:
        flash("Email already registered, please login.")
        return redirect(url_for('login'))
    user = User(
        name=form.name.data,
        email=form.email.data,
        password=generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8),
    )
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return redirect(url_for('get_all_posts'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if not form.validate_on_submit():
        return render_template("login.html", form=form, is_login=current_user.is_authenticated)
    user = db.session.execute(db.select(User).where(User.email==form.email.data)).scalar()
    if user and check_password_hash(user.password, form.password.data):
        login_user(user)
        return redirect(url_for('get_all_posts'))
    else:
        if not user:
            flash("Email does not exist, please try again.")
        else:
            flash("Password mismatch, please try again.")
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))

def admin_only(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return wrapper

@app.route('/')
def get_all_posts():
    # Query the database for all the posts. Convert the data to a python list.
    posts = db.session.execute(db.select(BlogPost)).scalars().all()
    return render_template("index.html", all_posts=posts, is_login=current_user.is_authenticated)

# Add a route to click on individual posts.
@app.route('/<int:post_id>', methods=['GET', 'POST'])
def show_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    form = CommentForm()
    if not form.validate_on_submit():
        return render_template("post.html", post=post, form=form, is_login=current_user.is_authenticated)
    if not current_user.is_authenticated:
        flash("You need to login or register to comment.")
        return redirect(url_for('login'))
    comment = Comment(
        commenter_id = current_user.id,
        post_id = post_id,
        text = form.comment.data,
    )
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

# add_new_post() to create a new blog post
@app.route("/new-post", methods=['GET', 'POST'])
@login_required
def add_post():
    form = PostForm()
    if not form.validate_on_submit():
        return render_template("make-post.html", is_new=True, form=form, is_login=current_user.is_authenticated)
    blog = BlogPost(
        title = form.title.data,
        subtitle = form.subtitle.data,
        date = date.today().strftime("%B %d, %Y"),
        author_id = current_user.id,
        img_url = form.img_url.data,
        body = form.body.data,
    )
    db.session.add(blog)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

# edit_post() to change an existing blog post
@app.route("/edit-post/<int:post_id>", methods=['GET', 'POST'])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    form = PostForm(
        title=post.title,
        subtitle=post.subtitle,
        author_id=current_user.id,
        img_url=post.img_url,
        body=post.body,
    )
    if not form.validate_on_submit():
        return render_template("make-post.html", is_new=False, form=form, is_login=current_user.is_authenticated)
    post.title=form.title.data
    post.subtitle=form.subtitle.data
    post.author_id = current_user.id
    post.img_url=form.img_url.data
    post.body=form.body.data
    db.session.commit()
    return redirect(url_for('show_post', post_id=post.id))

# delete_post() to remove a blog post from the database
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

if __name__ == "__main__":
    app.run(debug=True)
