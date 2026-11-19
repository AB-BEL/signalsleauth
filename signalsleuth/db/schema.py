"""Schema creation, first-run seeding and lazily-created tables."""
import pymysql
from datetime import datetime
from werkzeug.security import generate_password_hash
from pathlib import Path
from .core import CHAPTER_TITLES, DEFAULT_ADMIN_USER, INITIAL_ADMIN_PASS, _cfg, get_conn, utcnow

# database/schema.sql lives at the project root so DBAs can find and run it.
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "database" / "schema.sql"


def init_db():
    """Create tables if missing and seed admin + chapters + season."""
    cfg = _cfg()
    # Connect without DB to create it
    base = {k: v for k, v in cfg.items() if k != "database"}
    try:
        conn = pymysql.connect(**base)
        with conn.cursor() as c:
            c.execute(
                f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        conn.close()
    except Exception as e:
        print("Note: could not auto-create database:", e)

    schema_path = SCHEMA_PATH
    if schema_path.is_file():
        with open(schema_path, "r", encoding="utf-8") as f:
            sql = f.read()
        # Skip CREATE DATABASE / USE lines when already connected to DB
        statements = []
        for part in sql.split(";"):
            p = part.strip()
            if not p or p.upper().startswith("CREATE DATABASE") or p.upper().startswith("USE "):
                continue
            statements.append(p)
        with get_conn() as conn:
            with conn.cursor() as c:
                for stmt in statements:
                    try:
                        c.execute(stmt)
                    except Exception as e:
                        # Table may already exist
                        if "already exists" not in str(e).lower():
                            print("Schema stmt note:", e)

    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT id FROM admins WHERE username = %s", (DEFAULT_ADMIN_USER,))
            if not c.fetchone():
                c.execute(
                    "INSERT INTO admins (username, password_hash, email) VALUES (%s, %s, %s)",
                    (DEFAULT_ADMIN_USER, generate_password_hash(INITIAL_ADMIN_PASS), "admin@signalsleuth.local"),
                )
            c.execute("SELECT id FROM season WHERE id = 1")
            if not c.fetchone():
                c.execute(
                    "INSERT INTO season (id, name, start_date, end_date, updated_at) VALUES (1, %s, NULL, NULL, %s)",
                    ("Default Season", utcnow()),
                )
            for n, title in CHAPTER_TITLES.items():
                c.execute("SELECT chapter_num FROM chapters WHERE chapter_num = %s", (n,))
                if not c.fetchone():
                    c.execute(
                        "INSERT INTO chapters (chapter_num, title, is_active, activated_at) VALUES (%s, %s, %s, %s)",
                        (n, title, 1 if n == 1 else 0, utcnow() if n == 1 else None),
                    )


def ensure_level_scores_schema():
    """Add feedback_json column if missing; ensure question_bank table."""
    with get_conn() as conn:
        with conn.cursor() as c:
            try:
                c.execute("SELECT feedback_json FROM level_scores LIMIT 1")
            except Exception:
                try:
                    c.execute("ALTER TABLE level_scores ADD COLUMN feedback_json LONGTEXT NULL")
                except Exception as e:
                    print("ensure feedback_json:", e)
            c.execute("""
                CREATE TABLE IF NOT EXISTS question_bank (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    chapter_num INT NOT NULL,
                    level_num INT NOT NULL,
                    q_index INT NOT NULL,
                    level_title VARCHAR(255) NULL,
                    question_text TEXT NOT NULL,
                    points INT NOT NULL DEFAULT 0,
                    model_answer TEXT NULL,
                    keys_json LONGTEXT NULL,
                    feedback_note TEXT NULL,
                    updated_at DATETIME NULL,
                    UNIQUE KEY uq_ch_lv_q (chapter_num, level_num, q_index)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)


CHAPTER1_QUESTION_SEED = [
  {"level_num":1,"level_title":"The Nature of a Signal","q_index":1,"question_text":"What essential property makes something a signal?","points":10,"model_answer":"A signal conveys information, contained in a pattern of variations.","keys_json":"[{\"phrases\": [\"conveys information\", \"convey information\", \"carries information\", \"contains information\"], \"weight\": 6, \"label\": \"conveys information\"}, {\"phrases\": [\"pattern of variations\", \"variations\", \"varies\"], \"weight\": 4, \"label\": \"pattern of variations\"}]","feedback_note":"See model answer for L1 Q1."},
  {"level_num":1,"level_title":"The Nature of a Signal","q_index":2,"question_text":"Distinguish continuous-time, discrete-time, and digital signals.","points":12,"model_answer":"Continuous-time: continuous independent variable. Discrete-time: sequence at discrete instants. Digital: time and amplitude discrete.","keys_json":"[{\"phrases\": [\"continuous-time\", \"continuous time\", \"analog\", \"continuum\"], \"weight\": 3, \"label\": \"continuous-time\"}, {\"phrases\": [\"discrete-time\", \"discrete time\", \"sequence\"], \"weight\": 4, \"label\": \"discrete-time\"}, {\"phrases\": [\"digital\", \"amplitude\", \"quantized\", \"finite precision\", \"both time and amplitude\"], \"weight\": 5, \"label\": \"digital\"}]","feedback_note":"See model answer for L1 Q2."},
  {"level_num":1,"level_title":"The Nature of a Signal","q_index":3,"question_text":"Why emphasize discrete-time rather than only digital processing?","points":8,"model_answer":"Discrete-time theory is more general and remains valid for digital implementations.","keys_json":"[{\"phrases\": [\"more general\", \"general framework\", \"includes digital\", \"special case\", \"discrete-time\"], \"weight\": 4, \"label\": \"more general\"}, {\"phrases\": [\"high-precision\", \"fine quantization\", \"valid for digital\"], \"weight\": 4, \"label\": \"valid for digital\"}]","feedback_note":"See model answer for L1 Q3."},
  {"level_num":2,"level_title":"The Great Shift","q_index":1,"question_text":"Dominant technology before the 1960s?","points":8,"model_answer":"Continuous-time analog technology.","keys_json":"[{\"phrases\": [\"analog\", \"continuous-time\", \"continuous time\"], \"weight\": 8, \"label\": \"analog/continuous-time\"}]","feedback_note":"See model answer for L2 Q1."},
  {"level_num":2,"level_title":"The Great Shift","q_index":2,"question_text":"Name three enabling factors for the shift.","points":12,"model_answer":"Computers/microprocessors; A/D & D/A; FFT and related theory.","keys_json":"[{\"phrases\": [\"computer\", \"microprocessor\"], \"weight\": 3, \"label\": \"computers\"}, {\"phrases\": [\"a/d\", \"d/a\", \"converter\", \"conversion\"], \"weight\": 3, \"label\": \"A/D D/A\"}, {\"phrases\": [\"fft\", \"fast fourier\", \"parametric\", \"multirate\", \"polyphase\", \"wavelet\"], \"weight\": 3, \"label\": \"FFT/theory\"}, {\"phrases\": [\"three\", \"3\"], \"weight\": 3, \"label\": \"multiple factors\"}]","feedback_note":"See model answer for L2 Q2."},
  {"level_num":2,"level_title":"The Great Shift","q_index":3,"question_text":"Why were early computers seen as simulators of analog systems?","points":10,"model_answer":"Expensive/slow; used offline to simulate analog systems.","keys_json":"[{\"phrases\": [\"slow\", \"expensive\", \"not real-time\", \"non-real-time\", \"offline\"], \"weight\": 5, \"label\": \"limits\"}, {\"phrases\": [\"simulate\", \"approximation\", \"approximate\", \"analog\"], \"weight\": 5, \"label\": \"simulate analog\"}]","feedback_note":"See model answer for L2 Q3."},
  {"level_num":3,"level_title":"The FFT Revelation","q_index":1,"question_text":"Who published the modern FFT and in what year?","points":10,"model_answer":"Cooley and Tukey, 1965.","keys_json":"[{\"phrases\": [\"cooley\", \"tukey\"], \"weight\": 6, \"label\": \"Cooley & Tukey\"}, {\"phrases\": [\"1965\"], \"weight\": 4, \"label\": \"1965\"}]","feedback_note":"See model answer for L3 Q1."},
  {"level_num":3,"level_title":"The FFT Revelation","q_index":2,"question_text":"What conceptual shift did the FFT help trigger?","points":12,"model_answer":"Reformulation in exact discrete-time mathematics; field in its own right.","keys_json":"[{\"phrases\": [\"discrete-time\", \"exact\", \"independent field\", \"in its own right\", \"reformulation\"], \"weight\": 6, \"label\": \"discrete-time field\"}, {\"phrases\": [\"practical\", \"interactive\", \"experimentation\"], \"weight\": 4, \"label\": \"practical use\"}]","feedback_note":"See model answer for L3 Q2."},
  {"level_num":3,"level_title":"The FFT Revelation","q_index":3,"question_text":"Why is the FFT inherently discrete-time significant?","points":10,"model_answer":"Yields exact discrete-time relationships, not a continuous-time approximation.","keys_json":"[{\"phrases\": [\"exact\", \"not an approximation\", \"not approximation\", \"stands on its own\"], \"weight\": 6, \"label\": \"exact DT\"}, {\"phrases\": [\"sequence\", \"discrete-time signal\"], \"weight\": 4, \"label\": \"on sequences\"}]","feedback_note":"See model answer for L3 Q3."},
  {"level_num":4,"level_title":"Real-Time vs Stored Processing","q_index":1,"question_text":"Define asymmetric processing (CD/MP3).","points":10,"model_answer":"Process once, store, reconstruct in real time later.","keys_json":"[{\"phrases\": [\"once\", \"processed once\", \"offline\", \"stored\", \"store\"], \"weight\": 5, \"label\": \"process once/store\"}, {\"phrases\": [\"playback\", \"reconstruct\", \"real time\", \"real-time\", \"later\"], \"weight\": 5, \"label\": \"later playback\"}]","feedback_note":"See model answer for L4 Q1."},
  {"level_num":4,"level_title":"Real-Time vs Stored Processing","q_index":2,"question_text":"Historical non-real-time example?","points":10,"model_answer":"Seismic/geophysical exploration processed offline.","keys_json":"[{\"phrases\": [\"seismic\", \"geophysical\", \"geophysic\", \"exploration\"], \"weight\": 8, \"label\": \"seismic\"}, {\"phrases\": [\"offline\", \"hours\", \"non-real-time\"], \"weight\": 2, \"label\": \"offline\"}]","feedback_note":"See model answer for L4 Q2."},
  {"level_num":4,"level_title":"Real-Time vs Stored Processing","q_index":3,"question_text":"Why was non-real-time digital still a major advance?","points":10,"model_answer":"Flexibility without building new analog hardware.","keys_json":"[{\"phrases\": [\"flexibility\", \"flexible\", \"change\", \"adjust\"], \"weight\": 5, \"label\": \"flexibility\"}, {\"phrases\": [\"hardware\", \"analog\", \"economic\", \"payoff\"], \"weight\": 5, \"label\": \"avoid hardware cost\"}]","feedback_note":"See model answer for L4 Q3."},
  {"level_num":5,"level_title":"Why Fundamentals Still Matter","q_index":1,"question_text":"What must users still understand with high-level software?","points":10,"model_answer":"What is computed and how to interpret results; underlying concepts.","keys_json":"[{\"phrases\": [\"what is computed\", \"interpret\", \"interpretation\", \"how the result\"], \"weight\": 6, \"label\": \"interpret results\"}, {\"phrases\": [\"concepts\", \"theorems\", \"properties\", \"fundamentals\", \"theory\"], \"weight\": 4, \"label\": \"concepts\"}]","feedback_note":"See model answer for L5 Q1."},
  {"level_num":5,"level_title":"Why Fundamentals Still Matter","q_index":2,"question_text":"Example property enabling automatic alternative implementations?","points":12,"model_answer":"Convolution↔multiplication or sampling rate↔aliasing.","keys_json":"[{\"phrases\": [\"convolution\", \"multiplication\", \"frequency domain\"], \"weight\": 6, \"label\": \"conv\u2194mult\"}, {\"phrases\": [\"sampling\", \"aliasing\", \"decimation\", \"interpolation\"], \"weight\": 6, \"label\": \"sampling/aliasing\"}]","feedback_note":"See model answer for L5 Q2."},
  {"level_num":5,"level_title":"Why Fundamentals Still Matter","q_index":3,"question_text":"Meaning of “uncover rather than cover” a subject?","points":8,"model_answer":"Open rich theory/applications rather than list every topic.","keys_json":"[{\"phrases\": [\"uncover\", \"explore\", \"open up\", \"variety\", \"further\"], \"weight\": 5, \"label\": \"explore\"}, {\"phrases\": [\"not exhaust\", \"not list every\", \"rather than cover\"], \"weight\": 3, \"label\": \"not exhaustive\"}]","feedback_note":"See model answer for L5 Q3."},
  {"level_num":6,"level_title":"Applications That Shaped the Field","q_index":1,"question_text":"Three early application domains?","points":10,"model_answer":"Seismology, radar, communications/speech.","keys_json":"[{\"phrases\": [\"seismic\", \"seismology\", \"geophysic\"], \"weight\": 3, \"label\": \"seismic\"}, {\"phrases\": [\"radar\"], \"weight\": 3, \"label\": \"radar\"}, {\"phrases\": [\"communication\", \"speech\", \"vocoder\"], \"weight\": 3, \"label\": \"comms/speech\"}]","feedback_note":"See model answer for L6 Q1."},
  {"level_num":6,"level_title":"Applications That Shaped the Field","q_index":2,"question_text":"Three contemporary/emerging areas?","points":10,"model_answer":"Multimedia, financial engineering, medical/DNA/MEMS.","keys_json":"[{\"phrases\": [\"video\", \"audio\", \"multimedia\", \"mpeg\", \"jpeg\", \"phone\"], \"weight\": 3, \"label\": \"multimedia\"}, {\"phrases\": [\"finance\", \"financial\", \"economic\"], \"weight\": 3, \"label\": \"finance\"}, {\"phrases\": [\"medical\", \"imaging\", \"dna\", \"mems\", \"sensor\"], \"weight\": 3, \"label\": \"medical/DNA/MEMS\"}]","feedback_note":"See model answer for L6 Q2."},
  {"level_num":6,"level_title":"Applications That Shaped the Field","q_index":3,"question_text":"How do new applications borrow and stimulate new algorithms?","points":10,"model_answer":"Adapt existing knowledge; new needs stimulate new algorithms.","keys_json":"[{\"phrases\": [\"adapt\", \"borrow\", \"existing\"], \"weight\": 4, \"label\": \"borrow\"}, {\"phrases\": [\"stimulate\", \"new algorithm\", \"invent\", \"drive new\"], \"weight\": 4, \"label\": \"new algorithms\"}, {\"phrases\": [\"two-way\", \"interaction\"], \"weight\": 2, \"label\": \"two-way\"}]","feedback_note":"See model answer for L6 Q3."},
  {"level_num":7,"level_title":"The Unfinished Story – Synthesis","q_index":1,"question_text":"Why are fundamentals still indispensable? (use ≥3 ideas from the chapter)","points":20,"model_answer":"Fundamentals are the stable core; theory precedes hardware; interpretation and new apps still need deep knowledge.","keys_json":"[{\"phrases\": [\"stable\", \"core\", \"mathematics\", \"fundamentals\", \"underlying\"], \"weight\": 4, \"label\": \"math core\"}, {\"phrases\": [\"hardware\", \"impractical\", \"viable\", \"ready\"], \"weight\": 4, \"label\": \"hardware lag\"}, {\"phrases\": [\"interpret\", \"interpretation\", \"properties\"], \"weight\": 4, \"label\": \"interpretation\"}, {\"phrases\": [\"new application\", \"emerging\", \"future\", \"contribute\"], \"weight\": 4, \"label\": \"new apps\"}, {\"phrases\": [\"software\", \"library\", \"not enough\"], \"weight\": 4, \"label\": \"software limits\"}]","feedback_note":"See model answer for L7 Q1."},
  {"level_num":7,"level_title":"The Unfinished Story – Synthesis","q_index":2,"question_text":"Most memorable guiding principle from Ch.1 and why?","points":8,"model_answer":"Any thoughtful principle with a clear reason.","keys_json":"[{\"phrases\": [\"uncover\", \"cover\", \"fundamental\", \"principle\", \"because\", \"important\"], \"weight\": 5, \"label\": \"principle+reason\"}, {\"phrases\": [\"fft\", \"discrete-time\", \"field\", \"flexibility\"], \"weight\": 3, \"label\": \"concrete idea\"}]","feedback_note":"See model answer for L7 Q2."},
]


def ensure_question_bank_seeded():
    """Ensure all Chapter 1 questions (7 levels, 20 questions) exist; upsert seed rows."""
    ensure_level_scores_schema()
    with get_conn() as conn:
        with conn.cursor() as c:
            now = utcnow()
            for q in CHAPTER1_QUESTION_SEED:
                c.execute(
                    """INSERT INTO question_bank
                       (chapter_num, level_num, q_index, level_title, question_text, points,
                        model_answer, keys_json, feedback_note, updated_at)
                       VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE
                         level_title=VALUES(level_title),
                         question_text=VALUES(question_text),
                         points=VALUES(points),
                         model_answer=VALUES(model_answer),
                         keys_json=VALUES(keys_json),
                         feedback_note=VALUES(feedback_note),
                         updated_at=VALUES(updated_at)""",
                    (q["level_num"], q["q_index"], q["level_title"], q["question_text"], q["points"],
                     q["model_answer"], q["keys_json"], q["feedback_note"], now),
                )


def ensure_architecture_tables():
    """Create expanded architecture tables if missing (safe on existing DBs)."""
    stmts = [
        """CREATE TABLE IF NOT EXISTS courses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(64) NOT NULL UNIQUE,
            title VARCHAR(255) NOT NULL,
            description TEXT NULL,
            is_active TINYINT NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS game_versions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            chapter_num INT NOT NULL,
            version_label VARCHAR(64) NOT NULL,
            filename VARCHAR(255) NOT NULL,
            storage_key VARCHAR(512) NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'published',
            notes TEXT NULL,
            uploaded_by_admin_id INT NULL,
            created_at DATETIME NOT NULL,
            INDEX (chapter_num)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS levels (
            id INT AUTO_INCREMENT PRIMARY KEY,
            chapter_num INT NOT NULL,
            level_num INT NOT NULL,
            title VARCHAR(255) NOT NULL,
            sequence_order INT NOT NULL DEFAULT 1,
            pass_percent DOUBLE NOT NULL DEFAULT 50.0,
            is_active TINYINT NOT NULL DEFAULT 1,
            UNIQUE KEY uq_ch_level (chapter_num, level_num)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS game_attempts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            chapter_num INT NOT NULL,
            level_num INT NOT NULL,
            attempt_no INT NOT NULL DEFAULT 1,
            score INT NOT NULL DEFAULT 0,
            max_score INT NOT NULL DEFAULT 0,
            cleared TINYINT NOT NULL DEFAULT 0,
            answers_json LONGTEXT NULL,
            feedback_json LONGTEXT NULL,
            created_at DATETIME NOT NULL,
            INDEX (user_id, chapter_num, level_num)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS student_achievements (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            code VARCHAR(64) NOT NULL,
            title VARCHAR(255) NOT NULL,
            meta_json TEXT NULL,
            awarded_at DATETIME NOT NULL,
            UNIQUE KEY uq_user_code (user_id, code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NULL,
            audience VARCHAR(32) NOT NULL DEFAULT 'user',
            title VARCHAR(255) NOT NULL,
            body TEXT NULL,
            is_read TINYINT NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS admin_activity_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            admin_id INT NULL,
            action VARCHAR(128) NOT NULL,
            detail TEXT NULL,
            ip VARCHAR(64) NULL,
            created_at DATETIME NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS audit_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            actor_type VARCHAR(32) NOT NULL,
            actor_id INT NULL,
            event_type VARCHAR(128) NOT NULL,
            entity_type VARCHAR(64) NULL,
            entity_id VARCHAR(64) NULL,
            detail TEXT NULL,
            created_at DATETIME NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS system_settings (
            setting_key VARCHAR(128) PRIMARY KEY,
            setting_value TEXT NULL,
            updated_at DATETIME NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS users_extra (
            user_id INT PRIMARY KEY,
            is_suspended TINYINT NOT NULL DEFAULT 0,
            course_id INT NULL,
            cohort VARCHAR(64) NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]
    with get_conn() as conn:
        with conn.cursor() as c:
            for s in stmts:
                try:
                    c.execute(s)
                except Exception as e:
                    print("ensure_architecture_tables:", e)
            # Default course
            c.execute("SELECT id FROM courses WHERE code=%s", ("DSP-SS",))
            if not c.fetchone():
                c.execute(
                    "INSERT INTO courses (code, title, description, is_active, created_at) VALUES (%s,%s,%s,1,%s)",
                    ("DSP-SS", "Signal Sleuth — Discrete-Time Signal Processing",
                     "Primary course for Oppenheim & Schafer chapter games", utcnow()),
                )
            # Default settings
            defaults = {
                "pass_percent": "50",
                "max_levels_per_chapter": "7",
                "season_name": "Current semester",
                "architecture_version": "2.0",
                "app_name": "Signal Sleuth",
                "course_name": "Multi-course learning platform",
                "content_model": "independent_html",
                "ads_enabled_default": "0",
            }
            for k, v in defaults.items():
                c.execute(
                    """INSERT INTO system_settings (setting_key, setting_value, updated_at)
                       VALUES (%s,%s,%s)
                       ON DUPLICATE KEY UPDATE setting_key=setting_key""",
                    (k, v, utcnow()),
                )


def ensure_initialized():
    """Create schema and seed data only if the database is still empty.

    Cheap probe (one SELECT) so it can run on every serverless cold start
    without re-executing the whole schema.
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("SELECT 1 FROM admins LIMIT 1")
                c.fetchone()
        return False
    except Exception:
        init_db()
        return True
