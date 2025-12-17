# app.py
from flask import Flask, render_template, redirect, request
from models import db, Recipe, Ingredient, Step, User
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from forms import LoginForm

import os

app = Flask(__name__)
app.secret_key = 'tech-recipes-secret-change-in-prod'

# Настройка БД
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'recipes.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 МБ максимум

# Инициализация
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
    ingredients = recipe.ingredients
    steps = recipe.steps
    return render_template('recipe.html', recipe=recipe, ingredients=ingredients, steps=steps)



# === Маршруты авторизации ===
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

@app.route('/recipe/new', methods=['GET', 'POST'])
@login_required
def add_recipe():
    if not current_user.is_admin:
        return redirect('/recipes')

    if request.method == 'POST':
        title = request.form['title'].strip()
        slug = request.form['slug'].strip()

        if not title or not slug:
            return "Название и slug обязательны", 400

        # Проверка уникальности slug
        if Recipe.query.filter_by(slug=slug).first():
            return f"Slug '{slug}' уже занят", 400

        recipe = Recipe(title=title, slug=slug)

        # Обработка обложки рецепта
        recipe_image = request.files.get('recipe_image')
        if recipe_image and recipe_image.filename:
            filename = secure_filename(f"{slug}_cover_{recipe_image.filename}")
            recipe_image.save(f"static/uploads/{filename}")
            recipe.image = f"uploads/{filename}"  # сохраняем путь

        db.session.add(recipe)
        db.session.commit()

        # Ингредиенты
        for name, amount, unit, phase in zip(
            request.form.getlist('ingredient-name'),
            request.form.getlist('ingredient-amount'),
            request.form.getlist('ingredient-unit'),
            request.form.getlist('ingredient-phase')
        ):
            if name.strip():
                db.session.add(Ingredient(
                    recipe_id=recipe.id,
                    name=name.strip(),
                    amount=float(amount or 0),
                    unit=unit or 'г',
                    phase=phase or 'Основа'
                ))

        # Шаги
        instructions = request.form.getlist('step-instruction')
        durations = request.form.getlist('step-duration') or [None]*len(instructions)
        temps = request.form.getlist('step-temp') or [None]*len(instructions)
        images = request.files.getlist('step-image')

        for i, instr in enumerate(instructions):
            if instr.strip():
                image_filename = None
                if i < len(images) and images[i].filename:
                    filename = secure_filename(f"{slug}_step{i+1}_{images[i].filename}")
                    images[i].save(f"static/step_images/{filename}")
                    image_filename = f"step_images/{filename}"

                db.session.add(Step(
                    recipe_id=recipe.id,
                    step_number=i+1,
                    instruction=instr.strip(),
                    duration_min=int(durations[i]) if durations[i] and durations[i].isdigit() else None,
                    target_temp_c=int(temps[i]) if temps[i] and temps[i].isdigit() else None,
                    image=image_filename
                ))

        db.session.commit()
        return redirect(f'/recipe/{slug}')

    return render_template('add_recipe.html')

# === Инициализация БД ===
def init_db():
    with app.app_context():
        db.create_all()
        if Recipe.query.count() == 0:
            recipe = Recipe(
                title="Классический крем-брюле",
                slug="creme-brulee",

            )
            db.session.add(recipe)
            db.session.commit()

            ingredients = [
                Ingredient(recipe_id=recipe.id, name="Желтки яичные", amount=120, unit="г", phase="Основа"),
                Ingredient(recipe_id=recipe.id, name="Сливки 33%", amount=500, unit="мл", phase="Основа"),
                Ingredient(recipe_id=recipe.id, name="Сахар", amount=80, unit="г", phase="Основа"),
                Ingredient(recipe_id=recipe.id, name="Ванильный экстракт", amount=2, unit="мл", phase="Основа"),
                Ingredient(recipe_id=recipe.id, name="Сахар (для карамели)", amount=20, unit="г", phase="Глазурь")
            ]
            steps = [
                Step(recipe_id=recipe.id, step_number=1, instruction="Нагреть сливки до 82°C.", duration_min=5,
                     target_temp_c=82),
                Step(recipe_id=recipe.id, step_number=2, instruction="Взбить желтки с сахаром до однородности.",
                     duration_min=3),
                Step(recipe_id=recipe.id, step_number=3,
                     instruction="Медленно влить горячие сливки в яичную смесь, постоянно помешивая.", duration_min=2),
                Step(recipe_id=recipe.id, step_number=4, instruction="Добавить ванильный экстракт.", duration_min=1),
                Step(recipe_id=recipe.id, step_number=5, instruction="Процедить смесь через сито.", duration_min=2),
                Step(recipe_id=recipe.id, step_number=6,
                     instruction="Разлить по формочкам и запечь при 150°C до достижения центром 75°C.", duration_min=35,
                     target_temp_c=75),
                Step(recipe_id=recipe.id, step_number=7, instruction="Охладить до 4°C (не менее 4 часов).",
                     duration_min=240),
                Step(recipe_id=recipe.id, step_number=8,
                     instruction="Посыпать сверху сахаром и карамелизировать горелкой до 180°C.", target_temp_c=180)
            ]
            db.session.add_all(ingredients)
            db.session.add_all(steps)
            db.session.commit()
            print("✅ Пример рецепта добавлен!")

        if User.query.count() == 0:
            admin = User(username="admin", email="admin@example.com", is_admin=True)
            admin.set_password("password")
            db.session.add(admin)
            db.session.commit()
            print("✅ Админ создан: логин=admin, пароль=password")

if __name__ == '__main__':
    init_db()
    print("🚀 Запуск сервера Flask...")
    print("Сайт: http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)