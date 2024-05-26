from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import DataRequired
import requests
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
Bootstrap5(app) 

# SET UP HEADERS FOR TMDB API
headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {os.getenv('AUTH_TOKEN')}",
}

# CREATE DB
class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///movie.db"
db.init_app(app)


# CREATE TABLE
class Movie(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(unique=True)
    year: Mapped[int]
    description: Mapped[str]
    rating: Mapped[float] = mapped_column(nullable=True)
    ranking: Mapped[int] = mapped_column(nullable=True)
    review: Mapped[str] = mapped_column(nullable=True)
    img_url: Mapped[str]

with app.app_context():
    db.create_all()

# CREATE FORMS
class EditForm(FlaskForm):
    rating = FloatField("Your Rating Out of 10 (e.g. 7.5)", validators=[DataRequired()])
    review = StringField("Review", validators=[DataRequired()])
    submit = SubmitField("Done")


class AddForm(FlaskForm):
    title = StringField("Movie Title", validators=[DataRequired()])
    submit = SubmitField("Add Movie")


@app.route("/")
def home():
    movies = Movie.query.order_by(Movie.rating.desc()).all()
    for idx, movie in enumerate(movies):
        movie.ranking = idx+1
    db.session.commit()
    
    return render_template("index.html", movies=movies)


@app.route("/add", methods=["GET", "POST"])
def add():
    form = AddForm()

    if form.validate_on_submit():
        movie_to_add = form.title.data
        
        url = f"https://api.themoviedb.org/3/search/movie?query={movie_to_add}"
        movies = requests.get(url, headers=headers).json()["results"]
        return render_template("select.html", movies=movies)
        
    return render_template("add.html", form=form)


@app.route("/add-movie")
def create_entry():
    movie_id = request.args.get("id")
    
    # Get the details of the movie by ID
    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    movie = requests.get(url, headers=headers).json()
    
    movie_to_add = Movie(title=movie["original_title"],
                         year=int(movie["release_date"].split("-")[0]),
                         img_url=f"https://image.tmdb.org/t/p/w500{movie['poster_path']}",
                         description=movie["overview"])
    db.session.add(movie_to_add)
    db.session.commit()
    return redirect(url_for("edit", id=movie_to_add.id))


@app.route("/edit", methods=["GET", "POST"])
def edit():
    form = EditForm()
    id = int(request.args.get("id"))
    movie_to_edit = db.session.execute(db.select(Movie).filter_by(id=id)).scalar_one()

    if form.validate_on_submit():
        rating = form.rating.data
        review = form.review.data
        
        movie_to_edit.rating = rating
        movie_to_edit.review = review
        db.session.commit()

        return redirect(url_for("home"))

    return render_template("edit.html", form=form, movie=movie_to_edit)


@app.route("/delete")
def delete():
    id = int(request.args.get("id"))
    movie_to_delete = db.session.execute(db.select(Movie).filter_by(id=id)).scalar_one()
    db.session.delete(movie_to_delete)
    db.session.commit()
    
    return redirect(url_for("home"))


if __name__ == '__main__':
    app.run(debug=True)
