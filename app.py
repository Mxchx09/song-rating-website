from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = "Michi.2009"

# Funktion, um die Datenbank und die Tabellen zu erstellen
# Funktion, um die Datenbank und die Tabellen zu erstellen und zurückzusetzen
def create_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Lösche die Tabellen, falls sie existieren
    c.execute('DROP TABLE IF EXISTS songs')
    c.execute('DROP TABLE IF EXISTS users')

    # Users-Tabelle erstellen (falls nicht vorhanden)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Songs-Tabelle erstellen (falls nicht vorhanden) mit einer Verknüpfung zur Benutzer-ID
    c.execute('''
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            url TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()


# Rufe die Funktion create_db beim Start der Anwendung auf, um sicherzustellen, dass die Tabelle existiert
create_db()

@app.route("/")
def index():
    return render_template("login.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["Username"]
        password = request.form["Password"]

        # Überprüfen, ob der Benutzer existiert
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):  # user[3] enthält das gehashte Passwort
            # Benutzer-ID in der Session speichern
            session['user_id'] = user[0]
            return redirect(url_for("submit"))
        else:
            flash("Falscher Benutzername oder Passwort!", "error")
            return redirect(url_for("login"))
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["Username"]
        email = request.form["email"]
        password = request.form["Password"]

        hashed_password = generate_password_hash(password)

        # Speichern in der Datenbank
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            c.execute(''' 
                INSERT INTO users (username, email, password)
                VALUES (?, ?, ?)
            ''', (username, email, hashed_password))
            conn.commit()
            flash("Erfolgreich registriert!", "success")
        except sqlite3.IntegrityError:
            flash("Benutzername oder E-Mail existiert bereits.", "error")
        finally:
            conn.close()
        return redirect(url_for("login"))
    
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.pop('user_id', None)  # Löscht die user_id aus der Sitzung
    return redirect(url_for("login"))


@app.route("/submit", methods=["GET", "POST"])
def submit():
    # Holen der Benutzer-ID aus der Sitzung
    user_id = session.get('user_id')

    if not user_id:
        flash("Benutzer-ID fehlt! Bitte melde dich erneut an.", "error")
        return redirect(url_for("login"))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    if request.method == "POST":
        title = request.form["title"]
        artist = request.form["artist"]
        url = request.form["url"]

        # Song in die Datenbank speichern
        c.execute(''' 
            INSERT INTO songs (user_id, title, artist, url)
            VALUES (?, ?, ?, ?)
        ''', (user_id, title, artist, url))
        conn.commit()
        flash("Song erfolgreich eingereicht!", "success")
        return redirect(url_for("submit"))

    # Songs aus der Datenbank abrufen, die nur dem aktuellen Benutzer gehören
    c.execute("SELECT * FROM songs WHERE user_id = ?", (user_id,))
    songs = c.fetchall()
    conn.close()

    return render_template("submit.html", songs=songs)



if __name__ == "__main__":
    app.run(host="0.0.0.0")

