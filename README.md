# DTI412 Lab 3-4: Django ORM (Windows / PowerShell)

These are the lab files. Put them inside the project you create in Part 1.

## 1. Setup (Part 1)
```powershell
cd $env:USERPROFILE\Desktop
mkdir django_labs; cd django_labs
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install "django>=5.0,<6.0"
django-admin startproject training_system .
python manage.py startapp core
```
Add `'core'` and `'challenges'` to `INSTALLED_APPS` in `training_system/settings.py`.

## 2. Copy in these files
- `core/models.py`, `core/admin.py` (replace the generated ones)
- `challenges/` folder (new app, Part 6)
- `seed_data.py`, `part4_practice.py`, `part6_challenges.py`, `.gitignore`, `requirements.txt` (project root, next to manage.py)

## 3. Migrate & run (Part 3-4, 6)
```powershell
python manage.py makemigrations core challenges
python manage.py migrate
python manage.py createsuperuser
python seed_data.py
python part4_practice.py
python part6_challenges.py
python manage.py runserver   # admin at http://127.0.0.1:8000/admin/
```
`part4_practice.py` Task 4.2 and `part6_challenges.py` Challenge 3 change data each time they run, so run them once per fresh database.

## 4. Git (Part 5)
```powershell
git init
git add .
git commit -m "feat: initial commit for weeks 3-4 django ORM lab"
git branch -M main
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/django-orm-lab-week3-4.git
git push -u origin main
```
