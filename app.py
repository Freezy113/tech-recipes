# app.py
import os
basedir = os.path.abspath(os.path.dirname(__file__))

from flask import Flask, render_template, redirect, request
from models import db, Recipe, Ingredient, Step, User
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from forms import LoginForm
from recipes import init_db, handle_add_recipe,handle_edit_recipe  # ← ИМПОРТ ЛОГИКИ


import os
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.secret_key = 'tech-recipes-secret-change-in-prod'

# Настройка БД
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'recipes.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

db.init_app(app)

# === Авторизация ===
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# === Маршруты ===
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recipes')
def recipes_list():
    recipes = Recipe.query.all()
    return render_template('recipes.html', recipes=recipes)

@app.route('/recipe/<slug>')
def recipe_detail(slug):
    recipe = Recipe.query.filter_by(slug=slug).first_or_404()
    return render_template('recipe.html', recipe=recipe, ingredients=recipe.ingredients, steps=recipe.steps)

# === Авторизация (без изменений) ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/recipes')
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect('/recipes')
        return render_template('login.html', form=form, error="Неверное имя или пароль")
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

# === Рецепты: только маршруты, логика — в recipes.py ===
@app.route('/recipe/new', methods=['GET', 'POST'])
@login_required
def add_recipe():
    if not current_user.is_admin:
        return redirect('/recipes')
    if request.method == 'POST':
        return handle_add_recipe()  # ← ВСЯ ЛОГИКА В ДРУГОМ ФАЙЛЕ
    return render_template('add_recipe.html')


@app.route('/recipe/<slug>/edit', methods=['GET', 'POST'])
@login_required
def edit_recipe(slug):
    if not current_user.is_admin:
        return redirect(f'/recipe/{slug}')
    recipe = Recipe.query.filter_by(slug=slug).first_or_404()
    # Принудительно загружаем связи (на всякий случай)
    _ = recipe.ingredients  # это триггерит загрузку
    _ = recipe.steps  # это триггерит загрузку

    if request.method == 'POST':
        return handle_edit_recipe(recipe)  # ← обработка сохранения

    # GET: показать форму с данными
    return render_template('edit_recipe.html', recipe=recipe)

# === Запуск ===
if __name__ == '__main__':
    init_db(app)  # ← передаём app
    print("🚀 Запуск сервера Flask...")
    print("Сайт: http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)