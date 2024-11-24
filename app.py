from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "Michi.2009"


# Funktion, um die Datenbank und die Tabellen zu erstellen
def create_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Lösche alte Tabellen, falls sie existieren
    c.execute('DROP TABLE IF EXISTS songs')
    c.execute('DROP TABLE IF EXISTS users')
    c.execute('DROP TABLE IF EXISTS final_songs')

    # Erstelle Users-Tabelle
    c.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Erstelle Songs-Tabelle
    c.execute('''
        CREATE TABLE songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            url TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Erstelle Final Songs-Tabelle
    c.execute('''
        CREATE TABLE final_songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            url TEXT NOT NULL
        )
    ''')

    # Prüfen, ob der Admin-Benutzer existiert
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    admin = c.fetchone()

    if not admin:
        # Admin-Daten anlegen, falls noch nicht vorhanden
        hashed_password = generate_password_hash("admin")  # Admin Passwort "admin"
        c.execute('''
            INSERT INTO users (username, email, password)
            VALUES (?, ?, ?)
        ''', ('admin', 'admin@example.com', hashed_password))

    conn.commit()
    conn.close()

# Datenbank erstellen
create_db()


@app.route("/")
def index():
    return render_template("login.html")


@app.route("/all_songs_admin")
def all_songs_admin():
    user_id = session.get("user_id")
    if not user_id:
        flash("Bitte melde dich an.", "error")
        return redirect(url_for("login"))

    # Admin-Prüfung: Stelle sicher, dass der Benutzer ein Admin ist
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    if not user or user[0] != "admin":
        flash("Du hast keine Berechtigung, diese Seite aufzurufen.", "error")
        return redirect(url_for("submit"))

    # Alle Songs aus final_songs abrufen und Benutzernamen hinzufügen
    c.execute('''
        SELECT final_songs.*, users.username 
        FROM final_songs 
        JOIN users ON final_songs.user_id = users.id
    ''')
    songs = c.fetchall()
    conn.close()

    return render_template("all_songs.html", songs=songs)


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

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            flash("Erfolgreich eingeloggt!", "success")
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

        # Benutzer registrieren
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            c.execute('''
                INSERT INTO users (username, email, password)
                VALUES (?, ?, ?)
            ''', (username, email, hashed_password))
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Benutzername oder E-Mail existiert bereits.", "error")
        finally:
            conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.pop('user_id', None)
    return redirect(url_for("login"))


@app.route("/submit", methods=["GET", "POST"])
def submit():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    if request.method == "POST":
        title = request.form["title"]
        artist = request.form["artist"]
        url = request.form["url"]

        # Song speichern
        c.execute(''' 
            INSERT INTO songs (user_id, title, artist, url)
            VALUES (?, ?, ?, ?)
        ''', (user_id, title, artist, url))
        conn.commit()

    # Abrufen der Songs des Nutzers
    c.execute("SELECT * FROM songs WHERE user_id = ?", (user_id,))
    songs = c.fetchall()

    # Anzahl der Songs
    song_count = len(songs)
    conn.close()

    # Übergabe der `is_testing`-Variable an das Template
    return render_template("submit.html", songs=songs, song_count=song_count, is_testing=True)



@app.route("/submit_final", methods=["POST"])
def submit_final():
    is_testing = True  # In Testumgebung auf True setzen
    
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    try:
        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()

            # Songs des Nutzers abrufen
            c.execute("SELECT * FROM songs WHERE user_id = ?", (user_id,))
            user_songs = c.fetchall()

            # Überprüfen, ob mindestens 10 Songs eingereicht wurden
            if len(user_songs) < 10:
                flash("Du musst mindestens 10 Songs einreichen, um diese Funktion zu nutzen.", "error")
                return redirect(url_for("submit"))

            # Songs in final_songs verschieben
            songs_to_insert = [(song[1], song[2], song[3], song[4]) for song in user_songs]
            c.executemany('''
                INSERT INTO final_songs (user_id, title, artist, url)
                VALUES (?, ?, ?, ?)
            ''', songs_to_insert)

            # Songs aus der Tabelle songs löschen
            c.execute("DELETE FROM songs WHERE user_id = ?", (user_id,))
            conn.commit()

        flash("Deine Songs wurden erfolgreich eingereicht!", "success")
        return redirect(url_for("thanks"))
    except sqlite3.Error as e:
        flash(f"Es ist ein Fehler bei der Datenbankoperation aufgetreten: {str(e)}", "error")
        return redirect(url_for("submit"))

@app.route("/thanks")
def thanks():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    return render_template("thanks.html")



@app.route("/delete/<int:song_id>", methods=["POST"])
def delete(song_id):
    user_id = session.get('user_id')  # Überprüfen, ob der Benutzer eingeloggt ist
    if not user_id:
        flash("Bitte melde dich zuerst an.", "error")
        return redirect(url_for("login"))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Lösche den Song des Benutzers
    c.execute("DELETE FROM songs WHERE id = ? AND user_id = ?", (song_id, user_id))
    conn.commit()
    conn.close()

    flash("Song erfolgreich entfernt!", "success")
    return redirect(url_for("submit"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
