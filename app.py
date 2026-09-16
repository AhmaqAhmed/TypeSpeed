from flask import Flask, render_template, request, session, redirect, url_for
import psycopg2 as p
import random as r
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

app = Flask(__name__)
database_url = os.getenv('DATABASE_URL')
app.secret_key = os.getenv('SECRET_KEY')

if database_url:
    r = urlparse(database_url)
    DB_CONFIG = {
        'host':     r.hostname,
        'database': r.path[1:],
        'user':     r.username,
        'password': r.password,
        'port':     r.port or 5432,
    }
else:
    DB_CONFIG = {
        'host':     os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'typespeed_db'),
        'user':     os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD'),
        'port':     5432,
    }

texts = [
    "The ability to type quickly and accurately is one of the most valuable skills in the modern world. Whether you are writing emails, coding software, or drafting reports, your typing speed directly affects your productivity. Most professionals spend several hours a day at a keyboard, and even a small improvement in typing speed can save a significant amount of time over the course of a year. The key is not just speed but the combination of speed and accuracy working together seamlessly.",

    "Touch typing is the technique of typing without looking at the keyboard. It relies on muscle memory rather than conscious thought. Beginners often struggle with this because they are used to hunting for each key individually. However with enough practice the fingers begin to find their positions naturally. The home row keys are the foundation of touch typing and keeping your fingers resting there between keystrokes makes the whole process more efficient and less tiring over long sessions.",

    "Good posture plays a surprisingly large role in typing performance. Sitting up straight with your feet flat on the floor and your wrists slightly elevated reduces strain on your hands and forearms. Many typists develop repetitive stress injuries from poor ergonomics over time. A good chair, a properly positioned monitor, and a comfortable keyboard can make a significant difference. Investing in your workspace is just as important as practicing your technique if you want to type consistently over long periods.",

    "The English language contains a small set of very common words that appear far more often than others. Words like the, and, that, have, for, not, with, you, this, and are make up a large portion of everyday writing. Becoming extremely fast at typing these common words gives you a noticeable speed advantage during any typing test. Targeting your practice at high frequency words rather than random letters can accelerate your progress more quickly than general drills alone.",

    "Speed typing competitions have grown in popularity alongside the rise of the internet. Online platforms now allow typists from around the world to compete in real time, pushing the boundaries of what was once considered possible. The fastest typists in the world can exceed two hundred and fifty words per minute, far beyond what most people believe is achievable. These elite typists train for years, treating typing not as a simple office skill but as an athletic discipline requiring dedication, precision, and constant improvement.",

    "Learning a programming language is not just about understanding logic and syntax. It also requires the ability to type special characters, brackets, semicolons, and symbols quickly and without hesitation. Programmers who type slowly often lose their train of thought while writing code, which can make debugging and problem solving far harder than it needs to be. Developing strong typing skills early in a programming journey pays dividends throughout an entire career in software development.",

    "The brain and the fingers communicate through well established neural pathways that strengthen with repetition. Every time you type a word correctly your brain reinforces the motor pattern associated with it. Over time these patterns become automatic, freeing your conscious mind to focus on what you are writing rather than how you are writing it. This is why experienced typists can hold a conversation while typing without making more errors than usual. The skill eventually becomes as natural and effortless as walking.",

    "Reading and typing share a deep connection that many people overlook. People who read widely tend to be better typists because they have a stronger sense of how words and sentences are constructed. Their fingers anticipate what comes next in a sentence, allowing them to type in smooth bursts rather than one word at a time. Writers who type their own work often find that the act of typing actually helps them think more clearly, as the physical rhythm of keystrokes can mirror the rhythm of thought itself.",

    "Consistent daily practice is far more effective than occasional long sessions when it comes to building typing speed. Even fifteen minutes of focused practice every morning can lead to remarkable improvements over the course of a few months. The key is deliberate practice, meaning you should be pushing slightly beyond your comfort zone rather than simply repeating what you already do well. Targeting your weakest keys and most common mistakes will yield faster progress than endlessly repeating passages you can already type comfortably.",

    "The history of the keyboard stretches back to the invention of the typewriter in the nineteenth century. The QWERTY layout was designed in part to prevent mechanical jams by separating commonly used letter pairs. Although the mechanical limitations that inspired the layout no longer exist, QWERTY remains the dominant standard across the world. Alternative layouts like Dvorak and Colemak claim to offer faster and more comfortable typing, but switching requires relearning years of deeply ingrained muscle memory, which most typists are unwilling to undertake."
]

FIXED_DURATION = 60  # seconds, fixed-time test

# ==================== Database ====================

def get_db_connection():
    try:
        return p.connect(**DB_CONFIG)
    except p.Error as e:
        print(f"DB connection error: {e}")
        return None

def login_f(username, password):
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE username=%s AND password=%s", (username, password))
        return cur.fetchone()
    except p.Error as e:
        print(f"Login error: {e}")
        return None
    finally:
        cur.close(); conn.close()

def register_f(user, password, email):
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO users(username, password, email) VALUES(%s,%s,%s)", (user, password, email))
        conn.commit()
        return True
    except p.Error as e:
        conn.rollback()
        print(f"Register error: {e}")
        return None
    finally:
        cur.close(); conn.close()

def get_user_id(username):
    """Look up the numeric id for a username — needed as scores.user_id (FK)."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username=%s", (username,))
        row = cur.fetchone()
        return row[0] if row else None
    except p.Error as e:
        print(f"get_user_id error: {e}")
        return None
    finally:
        cur.close(); conn.close()

def save_score(user_id, final_wpm, raw_wpm, accuracy, duration_seconds,
                total_chars, correct_chars, wrong_chars):
    """Insert one completed test into scores. test_no auto-increments per user."""
    conn = get_db_connection()
    if not conn:
        print("[save_score] no db connection")
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(MAX(test_no), 0) + 1 FROM scores WHERE user_id=%s",
            (user_id,)
        )
        next_test_no = int(cur.fetchone()[0])

        # cast everything to the exact postgres column types
        vals = (
            int(user_id),
            next_test_no,
            int(final_wpm),
            int(raw_wpm),
            float(accuracy),        # numeric(5,2)
            int(duration_seconds),
            int(total_chars or 0),
            int(correct_chars or 0),
            int(wrong_chars or 0),
        )
        print(f"[save_score] inserting: {vals}")

        cur.execute(
            """INSERT INTO scores
               (user_id, test_no, final_wpm, raw_wpm, accuracy,
                duration_seconds, total_chars, correct_chars, wrong_chars)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            vals
        )
        conn.commit()
        print(f"[save_score] committed successfully — test_no={next_test_no}")
        return True
    except p.Error as e:
        conn.rollback()
        print(f"[save_score] DB error: {e}")
        return None
    finally:
        cur.close(); conn.close()

def get_user_scores(user_id, limit=10):
    """Fetch most recent scores for dashboard display."""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT test_no, final_wpm, raw_wpm, accuracy, created_at
               FROM scores WHERE user_id=%s
               ORDER BY created_at DESC LIMIT %s""",
            (user_id, limit)
        )
        return cur.fetchall()
    except p.Error as e:
        print(f"get_user_scores error: {e}")
        return []
    finally:
        cur.close(); conn.close()

# ==================== Helpers ====================

def calculate_accuracy_and_chars(original, user_input):
    """Word-level accuracy plus char counts for the scores table."""
    t = original.split()
    u = user_input.split()

    correct_words = sum(1 for i in range(min(len(u), len(t))) if u[i] == t[i])
    accuracy = int((correct_words / len(t)) * 100) if t else 0

    total_chars   = len(user_input)
    correct_chars = sum(1 for i in range(min(len(user_input), len(original)))
                         if user_input[i] == original[i])
    wrong_chars   = total_chars - correct_chars

    return accuracy, total_chars, correct_chars, wrong_chars

def calculate_results(original, user_input, duration_seconds=60):
    """WPM = words typed / (duration / 60). Works for any duration."""
    words   = len(user_input.strip().split()) if user_input.strip() else 0
    minutes = duration_seconds / 60
    raw_wpm = round(words / minutes, 2) if minutes > 0 else 0

    accuracy, total_chars, correct_chars, wrong_chars = calculate_accuracy_and_chars(original, user_input)
    final_wpm = round(raw_wpm * (accuracy / 100), 2)

    return {
        'raw_wpm': int(raw_wpm),
        'accuracy': accuracy,
        'final_wpm': final_wpm,
        'total_chars': total_chars,
        'correct_chars': correct_chars,
        'wrong_chars': wrong_chars
    }

# ==================== Auth ====================

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@app.route("/debug-db")
def debug_db():
    conn = get_db_connection()
    if conn:
        return "DB connected"
    return "DB connection FAILED"
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@app.route("/")
def home():
    # mark both test flows as "fresh" so next visit clears old results
    session['g_fresh'] = True
    session['l_fresh'] = True
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        register_f(request.form.get("username"), request.form.get("password"), request.form.get("email"))
        return redirect(url_for('login'))
    return render_template("register.html", msg=None)

@app.route("/login", methods=["GET", "POST"])
def login():
    msg = None
    if request.method == "POST":
        user = login_f(request.form.get("username"), request.form.get("password"))
        if user:
            session.clear()
            session['logged_in'] = True
            session['username']  = request.form.get("username")
            session['l_fresh']   = True
            return redirect(url_for('start_test_logged'))
        msg = ("Invalid username or password", "error")
    return render_template("login.html", msg=msg)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))

# ==================== Guest Test ====================

@app.route("/start_guest", methods=["GET", "POST"])
def start_test():
    if request.method == "POST":
        session['g_text']    = r.choice(texts)
        session['g_started'] = True
        session.pop('g_res', None)
        session.pop('g_fresh', None)
        return redirect(url_for('start_test'))

    # if arriving fresh (from home / nav), clear old results
    if session.pop('g_fresh', False):
        session.pop('g_res', None)
        session.pop('g_text', None)
        session.pop('g_started', None)

    text    = session.get('g_text') or r.choice(texts)
    started = session.get('g_started', False)
    results = session.get('g_res', None)
    if 'g_text' not in session:
        session['g_text'] = text
    return render_template('start_guest.html', text=text, started=started, results=results)

@app.route("/start-test", methods=["POST"])
def start_test_post():
    session['g_text']    = r.choice(texts)
    session['g_started'] = True
    session.pop('g_res', None)
    return redirect(url_for('start_test'))

@app.route("/submit-test", methods=["POST"])
def submit_test():
    user_input    = request.form.get('user_input', '')
    original_text = session.get('g_text', '')
    res = calculate_results(original_text, user_input)
    session['g_res']     = res
    session['g_started'] = False
    session.modified     = True
    return redirect(url_for('start_test'))

@app.route("/reset-test", methods=["POST"])
def reset_test():
    session.pop('g_text', None)
    session.pop('g_started', None)
    session.pop('g_res', None)
    return redirect(url_for('start_test'))

# ==================== Logged-in Test ====================

@app.route("/set-duration-logged", methods=["POST"])
def set_duration_logged():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        dur = int(request.form.get('duration', 60))
        if dur not in [15, 30, 60, 120, 180]:
            dur = 60
    except (ValueError, TypeError):
        dur = 60
    session['l_duration'] = dur
    session.pop('l_text', None)   # fresh passage for new duration
    session.pop('l_started', None)
    session.pop('l_res', None)
    return redirect(url_for('start_test_logged'))

@app.route("/start-test-logged", methods=["GET", "POST"])
def start_test_logged():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == "POST":
        session['l_text']    = r.choice(texts)
        session['l_started'] = True
        session.pop('l_res', None)
        return redirect(url_for('start_test_logged'))

    # if arriving fresh (from home / nav), clear old results
    if session.pop('l_fresh', False):
        session.pop('l_res', None)
        session.pop('l_text', None)
        session.pop('l_started', None)

    text    = session.get('l_text') or r.choice(texts)
    started = session.get('l_started', False)
    results = session.get('l_res', None)
    if 'l_text' not in session:
        session['l_text'] = text
    return render_template('start_log.html', text=text, started=started, results=results)

@app.route("/submit-test-logged", methods=["POST"])
def submit_test_logged():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_input    = request.form.get('user_input', '')
    original_text = session.get('l_text', '')
    duration_used = session.get('l_duration', FIXED_DURATION)
    res = calculate_results(original_text, user_input, duration_used)

    # persist to scores table
    user_id = get_user_id(session.get('username'))
    if user_id:
        save_score(
            user_id=user_id,
            final_wpm=int(res['final_wpm']),
            raw_wpm=res['raw_wpm'],
            accuracy=res['accuracy'],
            duration_seconds=duration_used,
            total_chars=res['total_chars'],
            correct_chars=res['correct_chars'],
            wrong_chars=res['wrong_chars']
        )
    else:
        print(f"[submit_test_logged] could not resolve user_id for {session.get('username')} — score not saved")

    session['l_res']     = res
    session['l_started'] = False
    session.modified     = True
    return redirect(url_for('start_test_logged'))

@app.route("/reset-test-logged", methods=["POST"])
def reset_test_logged():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    session.pop('l_text', None)
    session.pop('l_started', None)
    session.pop('l_res', None)
    return redirect(url_for('start_test_logged'))

# ==================== Dashboard ====================

@app.route("/dashboard")
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_id = get_user_id(session.get('username'))
    rows = get_user_scores(user_id, limit=10) if user_id else []

    # rows: (test_no, final_wpm, raw_wpm, accuracy, created_at) — most recent first
    rows = list(reversed(rows))  # chronological order for the graph

    scores = [
        {'test_no': t, 'final_wpm': fw, 'raw_wpm': rw, 'accuracy': float(acc), 'created_at': ts}
        for (t, fw, rw, acc, ts) in rows
    ]

    best_wpm = max((s['final_wpm'] for s in scores), default=0)
    avg_wpm  = round(sum(s['final_wpm'] for s in scores) / len(scores), 1) if scores else 0
    avg_acc  = round(sum(s['accuracy'] for s in scores) / len(scores), 1) if scores else 0

    total_conn = get_db_connection()
    total_tests = 0
    if total_conn:
        try:
            cur = total_conn.cursor()
            cur.execute("SELECT COUNT(*) FROM scores WHERE user_id=%s", (user_id,))
            total_tests = cur.fetchone()[0]
        except p.Error as e:
            print(f"dashboard count error: {e}")
        finally:
            cur.close(); total_conn.close()

    return render_template(
        "dashboard.html",
        scores=scores,
        best_wpm=best_wpm,
        avg_wpm=avg_wpm,
        avg_acc=avg_acc,
        total_tests=total_tests
    )

if __name__ == "__main__":
    app.run(debug=True)
