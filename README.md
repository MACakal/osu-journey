Copyright (C) 2026 MACakal

Licensed under the GNU GPL v3

## What is osu!journey?

osu!journey is an open source companion platform for osu! that gives players a structured progression system built on top of the game they already play. osu! is an incredible game but for a lot of players, especially newer ones and those stuck in the mid-ranks, it can start to feel directionless. You open the game, browse maps for ten minutes, play a few, close it, and repeat. There's no answer to the question that actually matters: *what should I do next?*

osu!journey fixes that. It reads your play data through the osu! API and wraps it in a lightweight RPG-style layer XP, levels, quests, regions, and milestone boss challenges all scaled to your current skill level. Whether you're a beginner learning the basics or a mid 5-digit player who's lost sight of what to grind, osu!journey gives you concrete goals, tracks your progress toward them, and keeps each session feeling meaningful.

This project does not modify osu! in any way. It is completely free, contains no ads, and is built with one goal: to make more people fall in love with the game and give meaning to what sometimes feels like the meaningless.

## osu!journey – Prerequisites & Running Guide

### Prerequisites

Make sure you have the following installed:

* Python (3.10+ recommended)
* pip
* Git

---

### 1. Clone the Project

```bash
git clone <your-repository-url>
cd osu-journey
```

---

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

---

### 3. Activate the Virtual Environment

**Windows:**

```bash
venv\Scripts\activate
```

**macOS/Linux:**

```bash
source venv/bin/activate
```

---

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 5. Set Up Environment Variables

Create a `.env` file in the root of the project:

```env
SECRET_KEY=
DEBUG=True

OSU_CLIENT_ID=
OSU_CLIENT_SECRET=
OSU_REDIRECT_URL=
```

#### Generate a Django SECRET_KEY

You can generate a secure key using Django itself:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output and paste it as your `SECRET_KEY` in the `.env` file.

---

### 6. Apply Migrations

```bash
python manage.py migrate
```

---

### 7. Create a Superuser (optional)

```bash
python manage.py createsuperuser
```

---

### 8. Run the Development Server

```bash
python manage.py runserver
```

Open in browser:

```
http://127.0.0.1:8000/
```

---

### Notes

* Always activate the virtual environment before working on the project
* Never commit your `.env` file
* Update dependencies when needed:

  ```bash
  pip freeze > requirements.txt
  ```

