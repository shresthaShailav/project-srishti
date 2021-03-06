import os
import re
from cs50 import SQL
from flask import Flask, jsonify, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.context import CryptContext
from tempfile import mkdtemp
from flask_jsglue import JSGlue

from helpers import *

# configure application
app = Flask(__name__)
JSGlue(app)
app.debug = True


# turn off SQLAlchemy event system
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# ensure that the responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response



# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)



# configure database with sqlalchemy

db = SQL("sqlite:///data.db")

@app.route("/")
def index():
    """ !!! 
        This is the first page that is loaded on loading the site.
        It shows the different things to display in the dashboard as per the user type
        For now simply displays the guest index, seller_index or buyer_index as per the type of the user logged in
    """
    if session.get("user_id"):
        if session["user_category"] == 1:
            return render_template("seller_index.html")
        else:
            return render_template("buyer_index.html")
    else:
        return render_template("guest_index.html")

@app.route("/check")
def check():
    """  !!!
    Just for checking purposes, will remove later
    """
    tables = db.engine.execute('SELECT name FROM sqlite_master WHERE type = "table";')
    print(tables)
    session['user_category'] = 3
    return render_template("check.html", tables=tables)



@app.route("/login", methods=["GET", "POST"])
def login():
    """ !!! """
    """ Logs the user into the system 
        And loads the respective index
        if a logged in user goes to this page, the user will have to log in again
    """
    session.clear()

    if request.method == "POST":

        # ensure required values are filled
        if not request.form.get("username"):
            return error("Sorry!", "No username entered")
        if not request.form.get("password"):
            return error("Sorry!", "No password entered")
        if not request.form.get("userType"):
            return error("Sorry!", "No accounttype selected")

        # set things up
        if request.form.get("userType") == 'seller':
            account_type = 1
        elif request.form.get("userType") == 'buyer':
            account_type = 2
        else:
            account_type = 0

        # query the database for matching account
        hasher = CryptContext(schemes=["sha256_crypt", "md5_crypt", "des_crypt"])
        result = db.execute('SELECT * FROM user_credentials WHERE username = :username AND user_category = :category',
                username = request.form.get("username"),
                category = account_type)

        if len(result) != 1 or not hasher.verify(request.form.get("password"), result[0]["password_hash"]):
            flash("Invalid Username and/or password")
            return render_template('login.html')
            return error("Invalid username or password")

        # add the user to the session
        session["user_name"] = result[0]["username"]
        session["user_id"] = result[0]["user_id"]
        session["user_category"] = result[0]["user_category"] 

        flash ("Welcome! {}".format(session["user_name"]))
        return redirect(url_for('index'))

    else:
        return render_template("login.html")
    
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route("/register", methods=["GET", "POST"])
def register():
    """ !!! """
    """ Registers the user by adding their credentials into the database
        Only register the user. Does not log the user in
    """
    if request.method == "POST":

        # handle all the required cases (frontend should handle it but just in case)
        if not request.form.get("userType"):
            return error("Sorry!", "Account type not entered")
        if not request.form.get("email"):
            return error("Sorry", "Email not entered")
        if not request.form.get("username"):
            return error("Sorry", "Username not entered")
        pass1 = request.form.get("password")
        pass2 = request.form.get("password_again")
        if not (pass1 and pass2):
            return error("Sorry!", "Must provide password")
        if not request.form.get("firstname"):
            return error("Sorry!", "Must provide firstname")
        if not request.form.get("lastname"):
            return error("Sorry!", "MUst provide lastname")
        if not request.form.get("userGender"):
            return error("Sorry!", "Must select a valid gender")
        if not request.form.get("contact"):
            return error("Sorry!", "Must enter a contact number")


        # handle password mismatch
        if pass1 != pass2:
            return error("Sorry!", "Passwords do not match")

        # ensure username and email are unique and do not already exist in the database
        result = db.execute("SELECT * FROM user_credentials WHERE username = :username", username = request.form.get("username"))
        if result:
            return error("Sorry!", "Username already exists")
        result = db.execute("SELECT * FROM user_info WHERE email = :email", email = request.form.get("email"))
        if result:
            return error("Sorry!", "Email already used")

        # handle extra information if available
        if (request.form.get("userType") == 'seller'):
            user_category = '1'
        else:
            user_category = '2'
        
        if request.form.get("midname"):
            midname = request.form.get("midname")
        else:
            midname = ''

        if request.form.get("userDOB"):
            dob = request.form.get("userDOB")
        else:
            dob = ''

        if request.form.get("userAddress"):
            address = request.form.get("userAddress")
        else:
            address = ''
        
        # add to database after validity of information
        hasher = CryptContext(schemes=["sha256_crypt", "md5_crypt", "des_crypt"])
        pass_hash = hasher.hash(pass1)

        # login credentials stored in user_credentails
        db.execute('INSERT INTO "user_credentials" ("user_id","username","password_hash","password_hint","user_category") VALUES (NULL, :username, :hash, :hint, :category)',
                username = request.form.get("username"), hash = pass_hash, hint = '', category = user_category)
 
        # user info stored in user_info
        user = db.execute('SELECT * FROM user_credentials WHERE username = :username', username = request.form.get("username"))
        user_id = user[0]["user_id"]
        db.execute('INSERT INTO "user_info" ("user_id","first_name","middle_name","last_name","gender","dob","email","address","contact","link") VALUES (:i_d, :fname, :mname, :lname, :gender, :date, :email, :address, :contact, :link)',
                i_d = user_id,
                fname = request.form.get("firstname"),
                mname = midname,
                lname = request.form.get("lastname"),
                gender = request.form.get("userGender"),
                date = request.form.get("userDOB"),
                email = request.form.get("email"),
                address = address,
                contact = request.form.get("contact"),
                link = '')


        flash("Congratulations! You are registered")
    
        return redirect(url_for('index'))
    else:
        return render_template("register.html")
    

@app.route("/about", methods=["GET"])
def about():
    """ !!! """
    """ Just loads the about page 
        BUT the about page inherits different pages depending on the login in status
        If logged in as seller, inherits the seller index
        If logged in as buyer, inherits the buyer index
        If Guest inherits the guest index
        Will probably have to be implemented with Jinja at the front 
    """
    return render_template("about.html")



@app.route('/post', methods=["GET", "POST"])
@login_required_as_seller
def post():
    """ !!!
        item posted by the user """
    
    if request.method == "POST":

        # ensure that the required values are entered
        if not request.form.get("itemcategory"):
            return error("Sorry!", "Enter item category")
        if not request.form.get("recyclable"):
            return error("Sorry!", "select either of recyclabe or not recyclable")
        if not request.form.get("itemname"):
            return error("Sorry!", "Enter the item name")

        if not request.form.get("itemprice"):
            return error("Sorry!", "Item price not set")
        if not request.form.get("itemusage"):
            return error("Sorry!", "Item usage period left empty")


        # add to the database
        db.execute('INSERT INTO "repository" ("item_id","item_name","item_description","user_id","item_category","usage_period","price","recyclable") VALUES (NULL, :item_name, :item_description, :user_id, :category, :usage, :price, :recyclability)',
                item_name = request.form.get("itemname"),
                item_description = request.form.get("itemDescription"),
                user_id = session["user_id"],
                category = request.form.get("itemcategory"),
                usage = request.form.get("itemusage"),
                price = request.form.get("itemprice"),
                recyclability = request.form.get("recyclable"))

        flash("Congratulation! Your item is posted")
        return redirect(url_for('index'))

        # INSERT INTO "repository" ("item_id","item_name","item_description","user_id","item_category","usage_period","price","recyclable") 
        # VALUES (NULL, :item_name, :item_description, :user_id, :category, :usage, :price, :recyclablity)

    else :
        return render_template("post.html")


@app.route('/my_posts')
@login_required_as_seller
def my_posts():
    """ !!! """
    posts = db.execute("SELECT * FROM repository WHERE user_id = :userID", userID = session["user_id"])
    #return jsonify(posts)
    return render_template("my_posts.html", posts = posts)




@app.route('/search', methods=["GET", "POST"])
def search():
    """ !!! """
    if request.method == 'POST':
        # Query with category and possible price if available
        pricehigh = request.form.get("pricehigh")
        pricelow = request.form.get("pricelow")
        item_category = request.form.get("itemcategory")

        if pricehigh and pricelow:
            results = db.execute('SELECT * FROM repository WHERE item_category = :category AND (price <= :high AND price >= :low)',
                    category = item_category,
                    high = pricehigh,
                    low = pricelow)

        elif pricehigh and not pricelow:
            results = db.execute('SELECT * FROM repository WHERE item_category = :category AND price <= :high',
                    category = item_category,
                    high = pricehigh)

        elif pricelow and not pricehigh:
            results = db.execute('SELECT * FROM repository WHERE item_category = :category AND price >= :low',
                    category = item_category,
                    low = pricelow)

        else:
            results = db.execute('SELECT * FROM repository WHERE item_category = :category', category = item_category)
        

        final_list = list()
        # filter for recyclability
        # note that the user can query particularly recyclabe items. If unselected, simply all the results will be displayed
        if request.form.get("recyclable"):
            print("reached")
            for result in results:
                if result.get("recyclable") == "true" :
                    final_list.append(result)
        else :
            final_list = results
        
        return jsonify(final_list)
    else :
        return render_template('search.html')
 

@app.route('/item', methods=["GET"])
def item():
    """ returns a json object with all the detailed information about  the item and the user selling it"""
    
    # ensure that the parameters are present
    id = str(request.args.get('q'))
    if not request.args.get('q'):
        return error("Sorry the item does not exist")

    # here we are assuming that there is only one item with that item id since thats how we designed post
    item = db.execute('SELECT * FROM repository WHERE item_id = :iId', iId = id)
    item = item[0]
    owner = db.execute('SELECT * FROM user_info WHERE user_id = :uid', uid = int (item["user_id"])) 
    owner = owner[0]
    return render_template('item_page.html', item = item, owner = owner)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    """ !!! """
    """ Just loads the contacts page 
        BUT the contact page inherits different pages depending on the login in status
        If logged in as seller, inherits the seller index
        If logged in as buyer, inherits the buyer index
        If Guest inherits the guest index
        Will probably have to be implemented with Jinja at the front 
    """
    return render_template("contact.html")

@app.route('/image')
def storeImage():
    """ Check Try to store images """
    return render_template("image.html")


@app.route('/hotmap')
def hotmap():
    """ Hotmap """
    if not os.environ.get("API_KEY"):
        raise RuntimeError("API Key not set ");
    return render_template('hotmap.html', key=os.environ.get("API_KEY"))

@app.route('/update')
def update():
    """ Update """

    places = db.execute('SELECT * FROM places');
    places = places[:10];
    
    return jsonify(places);


     # ensure parameters are present

    if not request.args.get("sw"):
       raise RuntimeError("missing sw")
    if not request.args.get("ne"):
       raise RuntimeError("missing ne")

    # ensure parameters are in lat,lng format
    if not re.search("^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$", request.args.get("sw")):
        raise RuntimeError("invalid sw")
    if not re.search("^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$", request.args.get("ne")):
      raise RuntimeError("invalid ne")

    
    # explode southwest corner into two variables
    (sw_lat, sw_lng) = [float(s) for s in request.args.get("sw").split(",")]

    # explode northeast corner into two variables
    (ne_lat, ne_lng) = [float(s) for s in request.args.get("ne").split(",")]

    # select all the places within view that are present in the map database
    # for checking puproses selects the first 10 places from places
 

if __name__ == "__main__":
    app.run()
