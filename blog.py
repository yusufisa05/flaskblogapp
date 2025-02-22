from flask import Flask,render_template,flash,url_for,redirect,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps
from datetime import datetime

#Kullanıcı Giriş Decorator'ı
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın.","danger")
            return redirect(url_for("login"))
    return decorated_function

app = Flask(__name__)
app.secret_key = "blog"
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "blog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators = [validators.Length(min = 4,max = 25)])
    username = StringField("Kullanıcı Adı",validators = [validators.Length(min = 4,max = 15)])
    email = StringField("Mail Adresi",validators = [validators.Email(message = "Lütfen geçerli bir mail adresi giriniz.")])
    password = PasswordField("Parola",validators=[
        validators.DataRequired(message = "Lütfen bir parola belirleyin"),
        validators.EqualTo(fieldname = "confirm",message = "Parolanız uyuşmuyor.")
        ])
    confirm = PasswordField("Parola Doğrula")

class LoginForm(Form):
    username = StringField("Kullanıcı adı")
    password = PasswordField("Parola")

class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators = [validators.length(min=4,max=40)])
    content = TextAreaField("Makale İçeriği",validators = [validators.length(min=10)])

class CommentForm(Form):
    commentContent = TextAreaField("Yorum yap...")

@app.route("/")
def index():
    return render_template("index.html")
@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles"
    result = cursor.execute(sorgu)
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles = articles)

    else:
        return render_template("articles.html")

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s"
    result = cursor.execute(sorgu,(session["username"],)) 
    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    else:
        return render_template("dashboard.html")
    
#Makale Silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s and id = %s"
    result = cursor.execute(sorgu,(session["username"],id))
    if result > 0:
        sorgu2 = "DELETE FROM articles WHERE id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya silmeye yetkiniz yok.","danger")
        return redirect(url_for("index"))

#Makale Güncelleme
@app.route("/edit/<string:id>",methods = ["GET","POST"])
@login_required
def edit(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE id = %s AND author = %s"
        result = cursor.execute(sorgu,(id,session["username"]))

        if result == 0:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yok.","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form = form)

    else:
        #POST REQUEST
        form = ArticleForm(request.form)

        newTitle = form.title.data
        newContent = form.content.data

        sorgu2 = "UPDATE articles SET title = %s, content = %s WHERE id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,id))
        mysql.connection.commit()
        flash("Makale başarıyla güncellendi","success")
        return redirect(url_for("dashboard"))


#Kayıt olma
@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.hash(form.password.data)

        cursor = mysql.connection.cursor()
        sorgu = "INSERT INTO users (name,username,email,password) VALUES (%s,%s,%s,%s)"
        cursor.execute(sorgu,(name,username,email,password))
        mysql.connection.commit()
        cursor.close()
        flash("Başarıyla Kayıt Oldunuz.","success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html",form = form)
#Login işlemi
@app.route("/login",methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM users where username = %s"
        result = cursor.execute(sorgu,(username,))

        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]

            if sha256_crypt.verify(password_entered,real_password):
                flash("Başarıyla giriş yaptınız.","success")
                session["logged_in"] = True
                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Yanlış parola girdiniz.","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunmuyor.","danger")
            return redirect(url_for("login"))
    return render_template("login.html",form = form)
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

def time_since(time):
    """Verilen datetime nesnesine göre 'X gün önce', 'X saat önce', 'Az önce' gibi zaman farkını döndürür."""
    now = datetime.now()  # Şu anki zamanı al
    diff = now - time  # Şu anki zamandan verilen zamanı çıkar

    if diff.days > 0:
        return f"{diff.days} gün önce"
    elif diff.seconds // 3600 > 0:
        return f"{diff.seconds // 3600} saat önce"
    elif diff.seconds // 60 > 0:
        return f"{diff.seconds // 60} dakika önce"
    else:
        return "Az önce"


@app.route("/article/<string:id>", methods=["GET", "POST"])
def article(id):
    form = CommentForm(request.form)
    cursor = mysql.connection.cursor()

    # Makale bilgilerini al
    sorgu = "SELECT * FROM articles WHERE id = %s"
    result = cursor.execute(sorgu, (id,))

    if result > 0:
        article = cursor.fetchone()

        if request.method == "POST":
            commentContent = form.commentContent.data.strip()  # 🛠️ Boşlukları temizle

            if not commentContent:  # Eğer boşsa hata ver
                flash("Yorum alanı boş bırakılamaz!", "danger")
                return redirect(url_for("article", id=id))

            comments_sorgu = "INSERT INTO comments (comment, comment_date, user_comment, article_id) VALUES (%s, NOW(), %s, %s)"
            cursor.execute(comments_sorgu, (commentContent, session["username"], id))
            mysql.connection.commit()
            flash("Yorum başarıyla eklendi!", "success")
            return redirect(url_for("article", id=id))

        # Makaleye ait tüm yorumları getir
        comments_sorgu = "SELECT * FROM comments WHERE article_id = %s ORDER BY comment_date DESC"
        cursor.execute(comments_sorgu, (id,))
        comments = cursor.fetchall()
        for comment in comments:
            comment["time_ago"] = time_since(comment["comment_date"])
        return render_template("article.html", article=article, comments=comments, form=form)

    else:
        flash("Böyle bir makale bulunamadı.", "danger")
        return redirect(url_for("articles"))


#Makale ekleme
@app.route("/addarticle",methods = ["GET","POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        cursor = mysql.connection.cursor()
        sorgu = "INSERT INTO articles (title,author,content) VALUES (%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale Başarıyla Eklendi.","success")
        return redirect(url_for("dashboard"))
    return render_template("addarticle.html",form = form)

#Arama URL
@app.route("/search",methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE title LIKE '%" + keyword +"%'"
        result = cursor.execute(sorgu)
        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı","warning")
            return redirect(url_for("articles"))
        
        articles = cursor.fetchall()
        return render_template("articles.html",articles = articles)
if __name__ == "__main__":
    app.run(debug = True)