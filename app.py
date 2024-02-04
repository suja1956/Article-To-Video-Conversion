from flask import Flask, render_template, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, FileField
from wtforms.validators import InputRequired,DataRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from googletrans import Translator
from gtts import gTTS
# from IPython.display import Audio,display
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from firebase_admin import credentials, initialize_app, storage,db
from flask_cors import CORS
import schedule
import time
import os
import shutil
import requests

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
cred = credentials.Certificate("flasksih-938f8-firebase-adminsdk-ivrxh-191b3e4435.json")
firebase_app = initialize_app(cred, {
    'storageBucket': 'flasksih-938f8.appspot.com',
    'databaseURL': 'https://flasksih-938f8-default-rtdb.firebaseio.com/'
})
root_ref = db.reference()

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db1 = SQLAlchemy(app)
bcrypt = Bcrypt(app)
app.config['SECRET_KEY'] = 'thisisasecretkey'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'




def audio_fun(text,language):
    english_text = text

    # List of supported Indian languages and their language codes
    indian_languages = {
        "hi": "Hindi",
        "bn": "Bengali",
        "ta": "Tamil",
        "te": "Telugu",
        "mr": "Marathi",
        "gu": "Gujarati",
        "kn": "Kannada",
        "ur": "Urdu",
        "ml": "Malayalam",
        "or": "Oriya",
        "as": "Assamese"
    }

    # Let the user choose the target language
    # print("Select a target language:")
    # for code, lang in indian_languages.items():
    #     print(f"{code}: {lang}")

    # target_language = input("Enter the language code: ")

    # Check if the selected language is supported
    if language not in indian_languages:
        print("Selected language is not supported.")
    else:
        # Initialize the Translator object
        translator = Translator()

        # Translate English text to the chosen Indian language
        translated_text = translator.translate(english_text, src='en', dest=language).text

        # Display the translated text on the screen
        print(f"Translation to {indian_languages[language]}:")
        print(translated_text)

        # Convert the translated text to audio in the same language
        tts = gTTS(translated_text, lang=language)
        audio_file = f"{language}_output.mp3"
        tts.save(audio_file)

        # Play the audio and download it
        print(f"Playing and downloading {indian_languages[language]} audio...")
        return audio_file





def delete_video_file(video_path,output_path,audio_file):
    try:
        os.remove(video_path)
        shutil.rmtree('downloads')
        print(f"Deleted video file: {video_path}")
        for path in output_path:
            os.remove(path)
        for path in audio_file:
            os.remove(path)
    except Exception as e:
        print(f"Error deleting video file: {str(e)}")





@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db1.Model, UserMixin) :
    id = db1.Column(db1.Integer, primary_key=True)
    username = db1.Column(db1.String(20), nullable=False, unique=True)
    password = db1.Column(db1.String(80), nullable=False)
    role = db1.Column(db1.String(200), nullable=False)

class Article(db1.Model, UserMixin) :
    id = db1.Column(db1.Integer, primary_key=True)
    title = db1.Column(db1.String(50), nullable=False, unique=True)
    content = db1.Column(db1.Text, nullable=False)
    status = db1.Column(db1.String(20), default='Pending approval')
    ratings = db1.Column(db1.Float, default=0.0)  
    num_ratings = db1.Column(db1.Integer, default=0)  

    def add_rating(self, rating):
        """Add a rating to the article."""
        self.ratings += rating
        self.num_ratings += 1

    def average_rating(self):
        """Calculate the average rating for the article."""
        if self.num_ratings > 0:
            return self.ratings / self.num_ratings
        else:
            return 0.0


class Registerform(FlaskForm): 
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})
    role = SelectField('Role', choices=[('reader', 'Reader'),('editor', 'Editor'), ('approver', 'Approver')], render_kw={"placeholder": "Role"})
    submit = SubmitField("Register")

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(username=username.data).first()
        if existing_user_username:
            raise ValidationError("That username already exists. Please choose a different one.")

class LoginForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})
    
    role = SelectField('Role', choices=[('reader', 'Reader'), ('editor', 'Editor'), ('approver', 'Approver')], render_kw={"placeholder": "Role"})

    submit = SubmitField('Login')


class ArticleForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Submit Article')


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user.role==form.role.data:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                if form.role.data=='reader':
                    return redirect(url_for('readerLandingPage'))  
                if form.role.data=='editor':
                    return redirect(url_for('editorLandingPage'))  
                if form.role.data=='approver':
                    return redirect(url_for('approverLandingPage')) 
        
    return render_template('login.html', form=form)



@app.route('/readerLandingPage',methods=['GET', 'POST'])
@login_required
def readerLandingPage():
    # Query the database to retrieve articles with 'Approved' status
    approved_articles = Article.query.filter_by(status='Approved').all()
    return render_template('readerLandingPage.html', approved_articles=approved_articles)


@app.route('/editorLandingPage',methods=['GET', 'POST'])
@login_required
def editorLandingPage():
    articles = Article.query.all()
    form = ArticleForm()
    return render_template('editorLandingPage.html', form=form, articles=articles)


@app.route('/approverLandingPage',methods=['GET', 'POST'])
@login_required
def approverLandingPage():
     # Query the database to retrieve articles with 'Pending' status
    pending_articles = Article.query.filter_by(status='Pending approval').all()
    return render_template('approverLandingPage.html', pending_articles=pending_articles)


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = Registerform()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password, role=form.role.data)
        db1.session.add(new_user)
        db1.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

# editor submits the article 
@app.route('/submit_article', methods=['GET', 'POST'])
def submit_article():
    form = ArticleForm()

    if form.validate_on_submit():
        # Article is stored in the database 
        
        new_article = Article(title=form.title.data, content=form.content.data, status='Pending approval')
        db1.session.add(new_article)
        db1.session.commit()
        return redirect(url_for('editorLandingPage'))

    return render_template('submitArticle.html', form=form)


# approver approves the article
@app.route('/approve_article/<int:article_id>', methods=['POST'])
def approve_article(article_id):
    # Retrieve the article from the database
    article = Article.query.get(article_id)

    if article:
        # Update the status to 'Approved'
        article.status = 'Approved'
        db1.session.commit()

    # Redirect back to the approver's landing page
    return redirect(url_for('approverLandingPage'))

# reader clicks on the title of article to be raed
@app.route('/view_article/<int:article_id>', methods=['GET'])
def view_article(article_id):
    # Retrieve the article from the database
    article = Article.query.get(article_id)

    if article and article.status == 'Approved':
        return render_template('view_article.html', article=article)
    
    # redirect or display error if article is not found or not approved
    return "Article not found or not approved."


# Reader rates the article
@app.route('/rate_article/<int:article_id>/<float:rating>', methods=['POST'])
def rate_article(article_id, rating):
    # Retrieve the article from the database
    article = Article.query.get(article_id)

    if article and article.status == 'Approved':
        # Add the reader's rating to the article
        article.add_rating(rating)
        db1.session.commit()

        # Redirect back to the article view page or reader's landing page
        return redirect(url_for('view_article', article_id=article_id))

    # Redirect or display an error if article is not found or not approved
    return "Article not found or not approved."




@app.route('/readervideo/<int:article_id>',methods=['GET'])
def reader_video(article_id):
    article = Article.query.get(article_id)
    keyforvideo=str(article_id)  
    videovalue=request.args.get('language')
    videos_ref = root_ref.child("videos").child(keyforvideo)
    video_data = videos_ref.get()
    res = list(video_data.keys())[0]
    print(res)
    video_url_lang=video_data[res]['video'][videovalue]
    print(f"Video of language {videovalue} is called")
    # return render_template('new.html',video_url=video_metadata["video"][videovalue])
    return render_template('readervideo.html',video_url=video_url_lang,article=article)








@app.route('/video',methods=['POST','GET'])
def process_text():
    


    if request.method=='GET':
        keyforvideo=request.args.get('customkey')    
        videovalue=request.args.get('language')
        videos_ref = root_ref.child("videos").child(keyforvideo)
        video_data = videos_ref.get()
        res = list(video_data.keys())[0]
        print(res)
        video_url_lang=video_data[res]['video'][videovalue]
        print(f"Video of language {videovalue} is called")
        # return render_template('new.html',video_url=video_metadata["video"][videovalue])
        return render_template('approvervideo.html',video_url=video_url_lang)

    # text=request.form.get('text')
    custom_key=request.form.get('custom_key')
    article = Article.query.get(custom_key)
    text=article.content
   
    import json
    import os

    import spacy


    nlp = spacy.load("en_core_web_sm")

    # Text to be analyzed
    #text = '''It's a beatiful summer day with clear sky and no clouds.'''


    doc = nlp(text)


    keywords = [token.text for token in doc if token.pos_ in ["NOUN", "ADJ"]]

    print(keywords)
    print("Keywords:")
    print(keywords)

    # Replace 'YOUR_ACCESS_KEY' with your actual Unsplash access key
    access_key = 'TFpISOv9fS95u4a9r9hb4Mmjx8TKiu5L_qDKuDsXIzY'

    def fetch_and_download_images(keywords, per_page=1, total_pages=1, download_folder="downloads"):
        # Create a folder for downloaded images if it doesn't exist
        os.makedirs(download_folder, exist_ok=True)
        image_info = []

        j=1
        for keyword in keywords:
            for page in range(1, total_pages + 1):
                url = f'https://api.unsplash.com/search/photos?query={keyword}&per_page={per_page}&page={page}&client_id={access_key}'

                response = requests.get(url)
                if response.status_code == 200:
                    data = json.loads(response.text)
                    for i, photo in enumerate(data['results']):
                        image_url = photo['urls']['regular']
                        image_extension = image_url.split('.')[-1]
                        image_filename = f"{j}.png"
                        print(j)
                        j=j+1
                        image_path = os.path.join(download_folder, image_filename)

                        # Download and save the image
                        with open(image_path, 'wb') as image_file:
                            image_file.write(requests.get(image_url).content)

                        # Store image information for HTML page
                        image_info.append({'url': image_url, 'filename': image_filename})
                else:
                    print(f"Failed to fetch images for keyword '{keyword}' on page {page}")

        return image_info

    # List of keywords for which you want to fetch images
    # keyword_list = ["countryside", "city"]

    # Number of images per keyword
    images_per_keyword = 1

    # Total pages to fetch (adjust based on your needs)
    total_pages = 1
    # Folder to save downloaded images
    download_folder = "downloads"

    fetched_image_info = fetch_and_download_images(keywords, per_page=images_per_keyword, total_pages=total_pages, download_folder=download_folder)

    # Create an HTML page to display the fetched images
    with open("Dimage_gallery.html", "w") as html_file:
        html_file.write("<html>\n<head>\n<title>Image Gallery</title>\n</head>\n<body>\n")
        
        for i, image_info in enumerate(fetched_image_info):
            html_file.write(f"<img src='{download_folder}/{image_info['filename']}' alt='Image {i + 1}' />\n")
        
        html_file.write("</body>\n</html>")

    print("Images fetched, downloaded, and displayed on the HTML page.")


    from moviepy.editor import ImageSequenceClip

    import cv2

    # Path to the directory containing your images
    image_folder = 'downloads'

    # Output video file name
    video_path = 'static/uploads/output_video.mp4'


    # Get a list of image files in the specified directory
    images = [img for img in os.listdir(image_folder) if img.endswith(".png")]

    # Sort the image filenames in the correct order
    images.sort(key=lambda x: int(x.split('.')[0]))
    print(images)

    # Load the first image to get its dimensions
    first_image = cv2.imread(os.path.join(image_folder, images[0]))
    height, width, layers = first_image.shape

    # Create a list of resized and converted-to-RGB images with the same dimensions
    resized_images = [cv2.cvtColor(cv2.resize(cv2.imread(os.path.join(image_folder, image)), (width, height)), cv2.COLOR_BGR2RGB) for image in images]

    clip = ImageSequenceClip(resized_images, fps=1)
    clip.write_videofile(video_path, codec='libx264')
    
    
    from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
    import os

    indian_languages = ["hi","bn","ta","te","mr","gu","kn","ur","ml"]
    audio_file = ["","","","","","","","",""]
    output_path = ["","","","","","","","",""]
    video_url = ["","","","","","","","",""]
    i=0 
    for lan in indian_languages:
        audio_file[i]=audio_fun(text=text,language=lan)
        video_clip = VideoFileClip(video_path)
        audio_clip = AudioFileClip(audio_file[i])
        final_clip = video_clip.set_audio(audio_clip)
        output_path[i] = f"{custom_key}_{lan}_temp.mp4"
        final_clip.write_videofile(output_path[i])	
        print(output_path[i])
        video_name = 'output_video.mp4'
        bucket = storage.bucket(app=firebase_app)
        blob = bucket.blob(output_path[i])
        blob.upload_from_filename(output_path[i])
        blob.make_public()
        video_url[i] = blob.public_url
        i=i+1
    video_metadata = {
        "title": "My Video",
        "description": "A video description",
        "uploader": "John Doe",
        "video": {
            "hindi":f"{video_url[0]}",
            "bengali":f"{video_url[1]}",
            "tamil":f"{video_url[2]}",
            "telugu":f"{video_url[3]}",
            "marathi":f"{video_url[4]}",
            "gujrati":f"{video_url[5]}",
            "kannada":f"{video_url[6]}",
            "urdu":f"{video_url[7]}",
            "malayalam":f"{video_url[8]}",
    }  
    }
    
    video_ref = root_ref.child("videos").child(custom_key).push()
    video_ref.set(video_metadata)
    print(f"Video metadata stored in Realtime Database with key: {video_ref.key}")
    
    
    # delete_video_file(video_path,output_path_hi,output_path_mr,output_path_ur,output_path_gu,output_path_ta,audio_file_hi,audio_file_mr,audio_file_ur,audio_file_gu,audio_file_ta)
    delete_video_file(video_path,output_path,audio_file)
    
    
    return render_template('yout.html',custom_key=custom_key)




if __name__=='__main__':
    app.run(debug=True)