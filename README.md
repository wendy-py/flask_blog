### Motivation
After learning online, I improved upon and decided to share.

blog features:
* quickly register yourself as the first user (i.e. admin)
* blog is public, but logged in users can add blogs [improved]
* logged in users can also add comment [improved]
* only admin can edit or delete blogs

### Install Guide
copy and run (assume linux with python3):
```
python3 -m venv test
cd test
source bin/activate
git clone https://github.com/wendy-py/flask_blog.git
cd flask_blog
pip install -r requirements.txt
python main.py
```
