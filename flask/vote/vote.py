from flask import Flask

vote = Flask(__name__)

@vote.route('/')
def home():
    return 'hello world'

if __name__ == '__main__':
    vote.run()