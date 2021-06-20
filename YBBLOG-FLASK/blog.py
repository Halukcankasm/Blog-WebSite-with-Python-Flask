import re
from flask import Flask, app #flask ile web sitesi sunucusu oluşturmam gerekiyor
from flask import render_template #fonk.jinja2 template(html template) dönmesi için
from flask import flash,redirect,url_for,session,logging,request

from flask_mysqldb import MySQL
from pymysql import cursors
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.handlers.sha2_crypt import sha256_crypt
from functools import wraps # for decorater

#Kullanıcı Kayıt Formu
#wtf kütüphanesini kullanarak hazır formları kullanıyoruz
class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[validators.Length(min=4,max=25)])
    username = StringField("Kullanıcı adı",validators=[validators.Length(min=5,max=35)])
    #email = StringField("Email Adresi",validators=[validators.Email(message="Lütfen Geçerli Bir Email Adresi Girin")])
    email = StringField("Email Adresi")
    password = PasswordField("Parola:",validators=[
        validators.DataRequired(message="Lütfen Bir Parola Belirleyin"),
        validators.EqualTo(fieldname="confirm",message="Parolanız uyuşmuyor..")
    ])
    confirm = PasswordField("Parola Doğrula")

#Kullanıcı Login Formu
class LoginForm(Form):
    username = StringField("Kullanıcı adı:")
    password = PasswordField("Parola:")

#Makale Formu
class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators=[validators.length(min = 5,max=100)])
    content = TextAreaField("Makale İçeriği",validators=[validators.length(min = 10)])


#web sunucusunu kendi bilgisayarımızda çallıştıracağımız için flask tan bir tane uygulama oluşturmamız lazım
app = Flask(__name__)
#(__name__) => eğer python dosyasını terminalden çalıştırırsak __name__ == __main__ olur
#bu ifade pyton dosyasının bir modülden mi aktarıldığını yoksa terminalden mi çalıştığını anlamak için.

app.secret_key="dbblog" #uygulamaların secret_key olması lazım flahs mesajları için

#MySQL veri tabanımızı app ile configüre etmek için veri tabanı bilgilerini vermemiz lazım
app.config["MYSQL_HOST"] = "127.0.0.1"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "dblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)


#Her bir url adresi istendiğinde kullanılan decorater
@app.route("/") #Ben (".....") adresine gitmek istiyorum ,(....) url adresine göre bir response dönmek istiyorum.(localhost:5000 == bizim kök dizinizmiz)
def index():
    return render_template("index.html") #Response
    #requesti jinja2 template olarak renponse yapmam lazım
    #jinja2 template flask tarafından kullanılan html template(html,css,python kodları bulunur)
    #bu template render ederek kullanuyorum = render_template("index.html") 

@app.route("/about")
def about():
    return render_template("about.html") 

#Kullanıcı Giriş Decorator'ı
#Eğer bir fpnk. çalıştıralac ise kul. login , logout old. anlamamız gerekiyor
#kul. login yap. func. çalıştır , else : fun. çalıştırma
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session: #kullanıcı login
            return f(*args, **kwargs)
        else:#kul.logout
            flash("Bu sayfayı görüntelemek için lütfen giriş yapın...","danger")
            return redirect(url_for("login"))

    return decorated_function

#Kayıt Olma
@app.route("/register",methods = ["GET","POST"]) #Bu fonk. hem get , hem post request old. belitmemiz lazım
def register():
    form = RegisterForm(request.form)
    
    if request.method == "POST" and form.validate() :
        #form.validate() = formumuzda herhangi bir sıkıntı yoksa , email geçersiz değilse vs.
        
        name = form.name.data #form içerisindeki name bilgisini aldık
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()
      
        sorgu = "Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"

        cursor.execute(sorgu,(name,email,username,password))

        mysql.connection.commit()

        cursor.close()

        flash("Başarıyla Kayıt Oldunuz....","success")

        return redirect(url_for("login"))
    else:
        return render_template("register.html",form = form)
         
#login işlemi
@app.route("/login",methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)

    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()

        sorgu = "Select * From users where username = %s"

        result = cursor.execute(sorgu,(username,))

        if result >0:
            data = cursor.fetchone()
            real_password =data["password"]
            if sha256_crypt.verify(password_entered,real_password):#Login pasword == Register pasword
                flash("Başarıyla Giriş Yaptınız...","success")

                session["logged_in"] = True #session kontrolu
                session["username"] = username #session kontrolu

                return redirect(url_for("index"))
            else:
                flash("Parolanızı Yanlış Gridiniz...","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunmuyor...","danger")
            return redirect(url_for("login"))

    return render_template("login.html",form=form)

#Logout işlemi
@app.route("/logout")
def logout():
    session.clear() #session kontrolu
    return redirect(url_for("index"))

#Kontrol Paneli
@app.route("/dashboard")
@login_required #decorator kontrolü
def dashboard():
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles where author = %s"

    result = cursor.execute(sorgu,(session["username"],))

    if result > 0 :
        articles = cursor.fetchall()
        return render_template("dash_board.html",articles = articles)

    else:
        return render_template("dash_board.html")

#Makale ekleme
@app.route("/addarticle",methods=["GET","POST"])
def addarticle():
    form = ArticleForm(request.form)

    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()

        sorgu = "Insert into articles (title,author,content) VALUES(%s,%s,%s)"

        cursor.execute(sorgu,(title,session["username"],content))

        mysql.connection.commit()

        cursor.close()

        flash("Makale Başarıyla Eklendi","success")

        return redirect(url_for("dashboard"))

    return render_template("addarticle.html",form = form)

#Makale silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles where author = %s and id = %s"

    result = cursor.execute(sorgu,(session["username"],id))

    if result > 0:
        sorgu2 = "Delete from articles where id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok / Bu işleme yetkniz bulunmuyor","danger")
        return redirect(url_for("index"))

#Makale Güncelleme
@app.route("/edit/<string:id>",methods = ["GET","POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "Select * from articles where id = %s and author = %s"
        result = cursor.execute(sorgu,(id,session["username"]))

        if result == 0:
            flash("Böyle bir makale bulunmuyor / Böyle bir işleme yetkiniz bulunmuyor","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()

            form.title.data = article["title"]
            form.content.data = article["content"]

            return render_template("update.html",form=form)
    else:
        #POST request
        form = ArticleForm(request.form)

        new_title = form.title.data
        new_content = form.content.data

        sorgu2 = "Update articles set title = %s,content = %s where id = %s"

        cursor = mysql.connection.cursor()
        
        cursor.execute(sorgu2,(new_title,new_content,id))

        mysql.connection.commit()

        flash("Makale başarıyla güncellendi" , "success")

        return redirect(url_for("dashboard"))

#Makale Sayfası
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles"

    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles = articles)
    else:
        return render_template("articles.html")

#Detay Sayfası
@app.route("/article/<string:id>")
def detail_article(id):
    cursor = mysql.connection.cursor()

    sorgu = "Select * from articles where id = %s"

    result = cursor.execute(sorgu,(id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html",article = article)
    else:
        return render_template("article.html")


#Arama Url
@app.route("/search",methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()

        sorgu = "Select * from articles where title like '%" + keyword +"%' "

        result = cursor.execute(sorgu)

        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()

            return render_template("articles.html",articles = articles)

if __name__ == "__main__":
#eğer bu koşul sağlanırsa benim localhost mu çalıştırmam gerekiyor
    
    app.run(debug = True)
    #gerhangi bir yerde hata olduğunda web sitesinde bu eror bize göstericek

