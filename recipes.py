# recipes.py
from models import db, Recipe, Ingredient, Step
from flask import request, redirect
from werkzeug.utils import secure_filename
import os

# Укажи basedir (как в app.py)
basedir = os.path.abspath(os.path.dirname(__file__))

def init_db(app):
    """Инициализация БД + демо-данные"""
    with app.app_context():
        db.create_all()
        if Recipe.query.count() == 0:
            recipe = Recipe(
                title="Классический крем-брюле",
                slug="creme-brulee",
                description="Французский десерт с нежным заварным кремом и хрустящей карамельной корочкой. Требует точного контроля температуры при выпечке и охлаждении."
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
                Step(recipe_id=recipe.id, step_number=1, instruction="Нагреть сливки до 82°C.", duration_min=5, target_temp_c=82),
                Step(recipe_id=recipe.id, step_number=2, instruction="Взбить желтки с сахаром до однородности.", duration_min=3),
                Step(recipe_id=recipe.id, step_number=3, instruction="Медленно влить горячие сливки в яичную смесь, постоянно помешивая.", duration_min=2),
                Step(recipe_id=recipe.id, step_number=4, instruction="Добавить ванильный экстракт.", duration_min=1),
                Step(recipe_id=recipe.id, step_number=5, instruction="Процедить смесь через сито.", duration_min=2),
                Step(recipe_id=recipe.id, step_number=6, instruction="Разлить по формочкам и запечь при 150°C до достижения центром 75°C.", duration_min=35, target_temp_c=75),
                Step(recipe_id=recipe.id, step_number=7, instruction="Охладить до 4°C (не менее 4 часов).", duration_min=240),
                Step(recipe_id=recipe.id, step_number=8, instruction="Посыпать сверху сахаром и карамелизировать горелкой до 180°C.", target_temp_c=180)
            ]
            db.session.add_all(ingredients)
            db.session.add_all(steps)
            db.session.commit()
            print("✅ Пример рецепта добавлен!")

        # Создание демо-админа (оставим здесь или переместим в отдельный файл позже)
        from models import User
        if User.query.count() == 0:
            admin = User(username="admin", email="admin@example.com", is_admin=True)
            admin.set_password("password")
            db.session.add(admin)
            db.session.commit()
            print("✅ Админ создан: логин=admin, пароль=password")

def handle_add_recipe():
    """Обработка POST-запроса на создание рецепта"""
    title = request.form['title'].strip()
    slug = request.form['slug'].strip()

    if not title or not slug:
        return "Название и slug обязательны", 400

    if Recipe.query.filter_by(slug=slug).first():
        return f"Slug '{slug}' уже занят", 400

    recipe = Recipe(
        title=title,
        slug=slug,
        description=request.form.get('description', '').strip() or None
    )

    # Обложка
    recipe_image = request.files.get('recipe_image')
    if recipe_image and recipe_image.filename:
        upload_folder = os.path.join(basedir, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        filename = secure_filename(f"{slug}_cover_{recipe_image.filename}")
        filepath = os.path.join(upload_folder, filename)
        recipe_image.save(filepath)
        recipe.image = f"uploads/{filename}"

    db.session.add(recipe)
    db.session.commit()

    # Ингредиенты
    for name, amount, unit, phase in zip(
        request.form.getlist('ingredient-name'),
        request.form.getlist('ingredient-amount'),
        request.form.getlist('ingredient-unit'),

    ):
        if name.strip():
            db.session.add(Ingredient(
                recipe_id=recipe.id,
                name=name.strip(),
                amount=float(amount or 0),
                unit=unit or 'г'
            ))

    # Шаги
    instructions = request.form.getlist('step-instruction')
    durations = request.form.getlist('step-duration') or [None]*len(instructions)
    temps = request.form.getlist('step-temp') or [None]*len(instructions)
    images = request.files.getlist('step-image')
    step_upload_folder = os.path.join(basedir, 'static', 'step_images')
    os.makedirs(step_upload_folder, exist_ok=True)

    for i, instr in enumerate(instructions):
        if instr.strip():
            image_filename = None
            if i < len(images) and images[i].filename:
                filename = secure_filename(f"{slug}_step{i+1}_{images[i].filename}")
                images[i].save(os.path.join(step_upload_folder, filename))
                image_filename = f"step_images/{filename}"

            db.session.add(Step(
                recipe_id=recipe.id,
                step_number=i+1,
                instruction=instr.strip(),
                duration_min=int(durations[i]) if durations[i] and durations[i].isdigit() else None,
                image=image_filename
            ))

    db.session.commit()
    return redirect(f'/recipe/{slug}')