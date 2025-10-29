from flask import Flask, render_template, request, session, redirect, url_for
from flask_session import Session
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
import x 
import time
import uuid
import os

import traceback
# traceback.print_exc()

from icecream import ic
ic.configureOutput(prefix=f'----- | ', includeContext=True)

app = Flask(__name__)

# Set the maximum file size to 10 MB
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024   # 1 MB

app.config['SESSION_TYPE'] = 'filesystem'
Session(app)


##############################
##############################
##############################
def _____USER_____(): pass 
##############################
##############################
##############################

@app.get("/")
def view_index():
    return render_template("index.html")

############# LOGIN #############
@app.route("/login", methods=["GET", "POST"])
@x.no_cache
def login():

    if request.method == "GET":
        if session.get("user", ""): return redirect(url_for("home"))
        return render_template("login.html", x=x)

    if request.method == "POST":
        try:
            # Validate           
            user_email = x.validate_user_email()
            user_password = x.validate_user_password()
            # Connect to the database
            q = "SELECT * FROM users WHERE user_email = %s"
            db, cursor = x.db()
            cursor.execute(q, (user_email,))
            user = cursor.fetchone()
            if not user: raise Exception("User not found", 400)

            if not check_password_hash(user["user_password"], user_password):
                raise Exception("Invalid credentials", 400)

            if user["user_verification_key"] != "":
                raise Exception("User not verified. Please check your email", 400)

            user.pop("user_password")

            session["user"] = user
            return f"""<browser mix-redirect="/home"></browser>"""

        except Exception as ex:
            ic(ex)

            # User errors
            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<browser mix-update="#toast">{ toast_error }</browser>""", 400

            # System or developer error
            toast_error = render_template("___toast_error.html", message="System under maintenance")
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()




############# SIGNUP #############
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "GET":
        return render_template("signup.html", x=x)

    if request.method == "POST":
        try:
            # Validate
            user_email = x.validate_user_email()
            user_password = x.validate_user_password()
            user_username = x.validate_user_username()
            user_first_name = x.validate_user_first_name()

            user_pk = uuid.uuid4().hex
            user_last_name = ""
            user_avatar_path = "https://avatar.iran.liara.run/public/40"
            user_verification_key = uuid.uuid4().hex
            user_verified_at = 0

            user_hashed_password = generate_password_hash(user_password)

            # Connect to the database
            q = "INSERT INTO users VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            db, cursor = x.db()
            cursor.execute(q, (user_pk, user_email, user_hashed_password, user_username, 
            user_first_name, user_last_name, user_avatar_path, user_verification_key, user_verified_at))
            db.commit()

            # send verification email
            email_verify_account = render_template("_email_verify_account.html", user_verification_key=user_verification_key)
            ic(email_verify_account)
            x.send_email(user_email, "Verify your account", email_verify_account)

            return f"""<mixhtml mix-redirect="{ url_for('login') }"></mixhtml>""", 400
        except Exception as ex:
            ic(ex)
            # User errors
            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            
            # Database errors
            if "Duplicate entry" and user_email in str(ex): 
                toast_error = render_template("___toast_error.html", message="Email already registered")
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            if "Duplicate entry" and user_username in str(ex): 
                toast_error = render_template("___toast_error.html", message="Username already registered")
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            
            # System or developer error
            toast_error = render_template("___toast_error.html", message="System under maintenance")
            return f"""<mixhtml mix-bottom="#toast">{ toast_error }</mixhtml>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()



############# HOME #############
@app.get("/home")
@x.no_cache # prevents showing cached content after logout / "back" button
def home():
    try:
        user = session.get("user", "")
        if not user: return redirect(url_for("login"))
        db, cursor = x.db()
        q = "SELECT * FROM users JOIN posts ON user_pk = post_user_fk ORDER BY RAND() LIMIT 5"
        cursor.execute(q)
        tweets = cursor.fetchall()
        ic(tweets)

        q = "SELECT * FROM trends ORDER BY RAND() LIMIT 3"
        cursor.execute(q)
        trends = cursor.fetchall()
        ic(trends)

        q = "SELECT * FROM users WHERE user_pk != %s ORDER BY RAND() LIMIT 3"
        cursor.execute(q, (user["user_pk"],))
        suggestions = cursor.fetchall()
        ic(suggestions)

        return render_template("home.html", tweets=tweets, trends=trends, user=user, suggestions=suggestions)
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

############## VERIFY ACCOUNT ################
@app.route("/verify-account", methods=["GET"])
def verify_account():
    try:
        user_verification_key = x.validate_uuid4_without_dashes(request.args.get("key", ""))
        user_verified_at = int(time.time())
        db, cursor = x.db()
        q = "UPDATE users SET user_verification_key = '', user_verified_at = %s WHERE user_verification_key = %s"
        cursor.execute(q, (user_verified_at, user_verification_key))
        db.commit()
        if cursor.rowcount != 1: raise Exception("Invalid key", 400)
        return redirect( url_for('login') )
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        # User errors
        if ex.args[1] == 400: return ex.args[0], 400    

        # System or developer error
        return "Cannot verify user"

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

############# LOGOUT #############
@app.get("/logout")
def logout():
    try:
        session.clear()
        return redirect(url_for("login"))
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        pass



############## HOME COMP ################
@app.get("/home-comp")
def home_comp():
    try:

        user = session.get("user", "")
        if not user: return "error"
        db, cursor = x.db()
        q = "SELECT * FROM users JOIN posts ON user_pk = post_user_fk ORDER BY RAND() LIMIT 5"
        cursor.execute(q)
        tweets = cursor.fetchall()
        ic(tweets)

        html = render_template("_home_comp.html", tweets=tweets, user=user)
        return f"""<mixhtml mix-update="main">{ html }</mixhtml>"""
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        pass


############# PROFILE #############
@app.get("/profile")
def profile():
    try:
        user = session.get("user", "")
        if not user: return "error"
        q = "SELECT * FROM users WHERE user_pk = %s"
        db, cursor = x.db()
        cursor.execute(q, (user["user_pk"],))
        user = cursor.fetchone()
        user.pop("user_password")
        ic(user)
        profile_html = render_template("_profile.html", x=x, user=user)
        return f"""<browser mix-update="main">{ profile_html }</browser>"""
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        pass


############### UPDATE PROFILE ###############
@app.route("/api-update-profile", methods=["POST"])
def api_update_profile():

    try:

        user = session.get("user", "")
        if not user: return "invalid user"

        # Validate
        user_email = x.validate_user_email()
        user_username = x.validate_user_username()
        user_first_name = x.validate_user_first_name()

        # Connect to the database
        q = "UPDATE users SET user_email = %s, user_username = %s, user_first_name = %s WHERE user_pk = %s"
        db, cursor = x.db()
        cursor.execute(q, (user_email, user_username, user_first_name, user["user_pk"]))
        db.commit()

        # Response to the browser
        toast_ok = render_template("___toast_ok.html", message="Profile updated successfully")
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-update="#profile_tag .name">{user_first_name}</browser>
            <browser mix-update="#profile_tag .handle">{user_username}</browser>
            
        """, 200
    except Exception as ex:
        ic(ex)
        # User errors
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
        
        # Database errors
        if "Duplicate entry" and user_email in str(ex): 
            toast_error = render_template("___toast_error.html", message="Email already registered")
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
        if "Duplicate entry" and user_username in str(ex): 
            toast_error = render_template("___toast_error.html", message="Username already registered")
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
        
        # System or developer error
        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<mixhtml mix-bottom="#toast">{ toast_error }</mixhtml>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


############# Like tweet #############
@app.patch("/like-tweet")
@x.no_cache
def api_like_tweet():
    try:
        button_unlike_tweet = render_template("___button_unlike_tweet.html")
        return f"""
            <mixhtml mix-replace="#button_1">
                {button_unlike_tweet}
            </mixhtml>
        """
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


############### CREATE POST ###############
@app.route("/api-create-post", methods=["POST"])
def api_create_post():
    try:
        user = session.get("user", "")
        if not user: return "invalid user"
        user_pk = user["user_pk"]        
        post = x.validate_post(request.form.get("post", ""))
        post_pk = uuid.uuid4().hex
        post_image_path = ""
        db, cursor = x.db()
        q = "INSERT INTO posts VALUES(%s, %s, %s, %s, %s)"
        cursor.execute(q, (post_pk, user_pk, post, 0, post_image_path))
        db.commit()
        toast_ok = render_template("___toast_ok.html", message="The world is reading your post !")
        tweet = {
            "user_first_name": user["user_first_name"],
            "user_last_name": user["user_last_name"],
            "user_username": user["user_username"],
            "user_avatar_path": user["user_avatar_path"],
            "post_message": post,
        }
        html_post_container = render_template("___post_container.html")
        html_post = render_template("_tweet.html", tweet=tweet)
        html_post_message = render_template("___post_message.html")
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-top="#posts">{html_post}</browser>
        <browser mix-replace="#post_message">{html_post_message}</browser>
            <browser mix-replace="#post_container">{html_post_container}</browser>
        """
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        # User errors
        if "x-error post" in str(ex):
            toast_error = render_template("___toast_error.html", message=f"Post - {x.POST_MIN_LEN} to {x.POST_MAX_LEN} characters")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        # System or developer error
        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()    




############### SEARCH ###############
@app.post("/api-search")
def api_search():
    try:
        # TODO: The input seach_for must be validated
        search_for = request.form.get("search_for", "") # point to the input field
        
        if not search_for:
            return f"""
            <browser mix-remove="#search_results"></browser>
            """
        
        part_of_query = f"%{search_for}%"
        ic(search_for)
        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_username LIKE %s"
        cursor.execute(q, (part_of_query,))
        users = cursor.fetchall()
        orange_box = render_template("_orange_box.html", users=users)
        return f"""
            <browser mix-remove="#search_results"></browser>
            <browser mix-bottom="#search_form">{orange_box}</browser>
        """
    except Exception as ex:
        ic(ex)
        return str(ex)
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close() 



"""
##############################
@app.get("/signup")
@app.get("/signup/<lan>")
def view_signup(lan="en"):
    if lan not in dictionary.allowed_languages: lan = "en"
    return render_template("view_signup.html", dictionary=dictionary, lan=lan, x=x)
"""
